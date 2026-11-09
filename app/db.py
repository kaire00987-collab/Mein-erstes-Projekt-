"""SQLite-Datenbank: Benutzer, Sitzungen, Chats und Nachrichten."""
import hashlib
import hmac
import os
import secrets
import sqlite3
import time

DB_PATH = os.environ.get("DB_PATH", "/data/ki.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    pw_hash TEXT NOT NULL,
    system_prompt TEXT NOT NULL DEFAULT '',
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    model TEXT NOT NULL,
    created REAL NOT NULL,
    updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_chats_user ON chats(user_id, updated);
"""


def connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


# --- Passwörter (scrypt aus der Standardbibliothek) ---

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{salt.hex()}${digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(digest.hex(), digest_hex)


# --- Benutzer ---

def add_user(username: str, password: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO users (username, pw_hash, created) VALUES (?, ?, ?)",
            (username, hash_password(password), time.time()),
        )


def set_password(username: str, password: str) -> bool:
    with connect() as conn:
        cur = conn.execute(
            "UPDATE users SET pw_hash = ? WHERE username = ?",
            (hash_password(password), username),
        )
        conn.execute(
            "DELETE FROM sessions WHERE user_id = (SELECT id FROM users WHERE username = ?)",
            (username,),
        )
        return cur.rowcount > 0


def delete_user(username: str) -> bool:
    with connect() as conn:
        return conn.execute("DELETE FROM users WHERE username = ?", (username,)).rowcount > 0


def list_users() -> list[str]:
    with connect() as conn:
        return [r["username"] for r in conn.execute("SELECT username FROM users ORDER BY id")]


def login(username: str, password: str) -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT id, pw_hash FROM users WHERE username = ?", (username,)).fetchone()
        if not row or not check_password(password, row["pw_hash"]):
            return None
        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO sessions (token, user_id, created) VALUES (?, ?, ?)",
            (token, row["id"], time.time()),
        )
        return token


def logout(token: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def user_for_token(token: str) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(
            "SELECT u.id, u.username, u.system_prompt FROM sessions s "
            "JOIN users u ON u.id = s.user_id WHERE s.token = ?",
            (token,),
        ).fetchone()


def set_system_prompt(user_id: int, prompt: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE users SET system_prompt = ? WHERE id = ?", (prompt, user_id))


# --- Chats ---

def list_chats(user_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, title, model, updated FROM chats WHERE user_id = ? ORDER BY updated DESC",
            (user_id,),
        )
        return [dict(r) for r in rows]


def create_chat(user_id: int, model: str, title: str = "Neuer Chat") -> int:
    now = time.time()
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO chats (user_id, title, model, created, updated) VALUES (?, ?, ?, ?, ?)",
            (user_id, title, model, now, now),
        )
        return cur.lastrowid


def get_chat(user_id: int, chat_id: int) -> dict | None:
    with connect() as conn:
        chat = conn.execute(
            "SELECT id, title, model, updated FROM chats WHERE id = ? AND user_id = ?",
            (chat_id, user_id),
        ).fetchone()
        if not chat:
            return None
        msgs = conn.execute(
            "SELECT id, role, content, created FROM messages WHERE chat_id = ? ORDER BY id",
            (chat_id,),
        )
        return {**dict(chat), "messages": [dict(m) for m in msgs]}


def update_chat(user_id: int, chat_id: int, title: str | None = None, model: str | None = None) -> bool:
    with connect() as conn:
        if title is not None:
            conn.execute("UPDATE chats SET title = ? WHERE id = ? AND user_id = ?", (title, chat_id, user_id))
        if model is not None:
            conn.execute("UPDATE chats SET model = ? WHERE id = ? AND user_id = ?", (model, chat_id, user_id))
        return conn.execute("SELECT 1 FROM chats WHERE id = ? AND user_id = ?", (chat_id, user_id)).fetchone() is not None


def delete_chat(user_id: int, chat_id: int) -> bool:
    with connect() as conn:
        return conn.execute("DELETE FROM chats WHERE id = ? AND user_id = ?", (chat_id, user_id)).rowcount > 0


def add_message(chat_id: int, role: str, content: str) -> int:
    now = time.time()
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO messages (chat_id, role, content, created) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, now),
        )
        conn.execute("UPDATE chats SET updated = ? WHERE id = ?", (now, chat_id))
        return cur.lastrowid


def delete_messages_from(chat_id: int, message_id: int) -> None:
    """Löscht eine Nachricht und alle danach (für 'Antwort neu generieren')."""
    with connect() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id = ? AND id >= ?", (chat_id, message_id))
