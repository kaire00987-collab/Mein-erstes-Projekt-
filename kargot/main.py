"""Kargot: Web-Server für den eigenen KI-Chat (Claude über die API, optional Ollama)."""
import json
import os
import time
from pathlib import Path

import anthropic
import httpx
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db

# Als Home-Assistant-Add-on stehen die Einstellungen in /data/options.json
HA_OPTIONS = Path("/data/options.json")
if HA_OPTIONS.exists():
    _opts = json.loads(HA_OPTIONS.read_text())
    for _key, _env in {"api_key": "ANTHROPIC_API_KEY", "ai_name": "AI_NAME",
                       "model": "DEFAULT_MODEL", "effort": "CLAUDE_EFFORT"}.items():
        if _opts.get(_key):
            os.environ.setdefault(_env, str(_opts[_key]))
    os.environ.setdefault("HA_INGRESS", "true")

# Anfragen über Home Assistant (Ingress) kommen immer von dieser Adresse
HA_INGRESS = os.environ.get("HA_INGRESS", "false").lower() == "true"
HA_PROXY_IP = os.environ.get("HA_PROXY_IP", "172.30.32.2")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "").rstrip("/")  # leer = keine Offline-Modelle
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODELS = [m.strip() for m in os.environ.get(
    "CLAUDE_MODELS", "claude-opus-5-5,claude-sonnet-5-5,claude-haiku-5-5").split(",") if m.strip()]
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("CLAUDE_EFFORT", "medium")  # low / medium / high
AI_NAME = os.environ.get("AI_NAME", "Kargot")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
STATIC = Path(__file__).parent / "static"

BASE_PROMPT = (
    "Du bist {name}, ein hilfsbereiter, ehrlicher und kluger KI-Assistent. "
    "Du sprichst mit {user}. Antworte standardmäßig auf Deutsch, außer man schreibt dir in einer anderen Sprache. "
    "Sei klar und direkt, nutze Markdown (Listen, Überschriften, Codeblöcke), wenn es hilft. "
    "Wenn du etwas nicht weißt, sag es ehrlich, statt etwas zu erfinden. "
    "Heute ist der {date}. Du hast keinen Internetzugang und kannst keine Webseiten aufrufen. "
    "Wenn jemand fragt, auf welcher Technik du basierst: Du nutzt im Hintergrund Claude von Anthropic."
)

claude = anthropic.AsyncAnthropic(api_key=ANTHROPIC_KEY) if ANTHROPIC_KEY else None


def is_claude(model: str) -> bool:
    return model.startswith("claude-")

app = FastAPI(title=AI_NAME)
db.init()

# Konten aus INITIAL_USERS="name:passwort,name2:passwort2" anlegen (nur wenn noch nicht vorhanden)
for entry in os.environ.get("INITIAL_USERS", "").split(","):
    name, _, pw = entry.strip().partition(":")
    if name and pw and name not in db.list_users():
        db.add_user(name, pw)


# --- Anmeldung ---

COOKIE = "kargot_session"


def ha_username(request: Request) -> str | None:
    """Über Home Assistant angemeldete Person – nur vertrauen, wenn die Anfrage wirklich von HA kommt."""
    if HA_INGRESS and request.client and request.client.host == HA_PROXY_IP:
        name = request.headers.get("X-Remote-User-Name", "").strip()
        return name or None
    return None


def current_user(request: Request, session: str | None = Cookie(default=None, alias=COOKIE)):
    name = ha_username(request)
    if name:
        return db.get_or_create_user(name)
    user = db.user_for_token(session) if session else None
    if not user:
        raise HTTPException(401, "Nicht angemeldet")
    return user


class LoginIn(BaseModel):
    username: str
    password: str


@app.post("/api/login")
def login(data: LoginIn, response: Response):
    token = db.login(data.username.strip(), data.password)
    if not token:
        time.sleep(1)  # bremst Passwort-Raten
        raise HTTPException(401, "Benutzername oder Passwort falsch")
    response.set_cookie(
        COOKIE, token, httponly=True, samesite="lax", secure=COOKIE_SECURE, max_age=60 * 60 * 24 * 365
    )
    return {"ok": True}


@app.post("/api/logout")
def logout(response: Response, session: str | None = Cookie(default=None, alias=COOKIE)):
    if session:
        db.logout(session)
    response.delete_cookie(COOKIE)
    return {"ok": True}


@app.get("/api/me")
def me(request: Request, user=Depends(current_user)):
    return {
        "ha_login": ha_username(request) is not None,
        "username": user["username"],
        "system_prompt": user["system_prompt"],
        "ai_name": AI_NAME,
        "default_model": DEFAULT_MODEL,
    }


class SettingsIn(BaseModel):
    system_prompt: str


@app.put("/api/settings")
def save_settings(data: SettingsIn, user=Depends(current_user)):
    db.set_system_prompt(user["id"], data.system_prompt[:8000])
    return {"ok": True}


class PasswordIn(BaseModel):
    old: str
    new: str


@app.put("/api/password")
def change_password(data: PasswordIn, response: Response, user=Depends(current_user)):
    if not db.login(user["username"], data.old):
        raise HTTPException(400, "Altes Passwort stimmt nicht")
    if len(data.new) < 6:
        raise HTTPException(400, "Neues Passwort: mindestens 6 Zeichen")
    db.set_password(user["username"], data.new)  # meldet alle Geräte ab
    token = db.login(user["username"], data.new)
    response.set_cookie(
        COOKIE, token, httponly=True, samesite="lax", secure=COOKIE_SECURE, max_age=60 * 60 * 24 * 365
    )
    return {"ok": True}


# --- Modelle ---

@app.get("/api/models")
async def models(user=Depends(current_user)):
    names = list(CLAUDE_MODELS) if claude else []
    if OLLAMA_URL:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{OLLAMA_URL}/api/tags")
                r.raise_for_status()
                names += [m["name"] for m in r.json().get("models", [])]
        except Exception:
            pass
    if not names:
        return {"models": [], "error": "Kein Modell eingerichtet (API-Schlüssel fehlt?)"}
    return {"models": names}


# --- Chats ---

@app.get("/api/chats")
def chats(user=Depends(current_user)):
    return db.list_chats(user["id"])


class NewChatIn(BaseModel):
    model: str | None = None


@app.post("/api/chats")
def new_chat(data: NewChatIn, user=Depends(current_user)):
    chat_id = db.create_chat(user["id"], data.model or DEFAULT_MODEL)
    return db.get_chat(user["id"], chat_id)


@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: int, user=Depends(current_user)):
    chat = db.get_chat(user["id"], chat_id)
    if not chat:
        raise HTTPException(404, "Chat nicht gefunden")
    return chat


class ChatUpdateIn(BaseModel):
    title: str | None = None
    model: str | None = None


@app.patch("/api/chats/{chat_id}")
def update_chat(chat_id: int, data: ChatUpdateIn, user=Depends(current_user)):
    title = data.title.strip()[:200] if data.title else None
    if not db.update_chat(user["id"], chat_id, title=title, model=data.model):
        raise HTTPException(404, "Chat nicht gefunden")
    return {"ok": True}


@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: int, user=Depends(current_user)):
    if not db.delete_chat(user["id"], chat_id):
        raise HTTPException(404, "Chat nicht gefunden")
    return {"ok": True}


class MessageIn(BaseModel):
    content: str | None = None  # None = letzte Antwort neu generieren


def build_system_prompt(user) -> str:
    prompt = BASE_PROMPT.format(name=AI_NAME, user=user["username"], date=time.strftime("%d.%m.%Y"))
    if user["system_prompt"].strip():
        prompt += "\n\nWas du über diese Person wissen sollst und wie du antworten sollst:\n" + user["system_prompt"].strip()
    return prompt


@app.post("/api/chats/{chat_id}/messages")
async def send_message(chat_id: int, data: MessageIn, user=Depends(current_user)):
    chat = db.get_chat(user["id"], chat_id)
    if not chat:
        raise HTTPException(404, "Chat nicht gefunden")

    if data.content is None:
        # Neu generieren: letzte KI-Antwort entfernen
        msgs = chat["messages"]
        if msgs and msgs[-1]["role"] == "assistant":
            db.delete_messages_from(chat_id, msgs[-1]["id"])
            msgs = msgs[:-1]
        if not msgs:
            raise HTTPException(400, "Nichts zum Neu-Generieren")
    else:
        content = data.content.strip()
        if not content:
            raise HTTPException(400, "Leere Nachricht")
        db.add_message(chat_id, "user", content)
        if not chat["messages"] and chat["title"] == "Neuer Chat":
            title = content.splitlines()[0][:60] + ("…" if len(content) > 60 else "")
            db.update_chat(user["id"], chat_id, title=title)

    history = db.get_chat(user["id"], chat_id)["messages"]
    messages = []
    for m in history:  # aufeinanderfolgende Nachrichten derselben Rolle zusammenfassen
        if messages and messages[-1]["role"] == m["role"]:
            messages[-1]["content"] += "\n\n" + m["content"]
        else:
            messages.append({"role": m["role"], "content": m["content"]})
    system = build_system_prompt(user)
    source = stream_claude if is_claude(chat["model"]) else stream_ollama

    async def stream():
        answer = []
        try:
            async for kind, text in source(chat["model"], system, messages):
                if kind == "error":
                    yield json.dumps({"error": text}) + "\n"
                    break
                answer.append(text)
                yield json.dumps({"t": text}) + "\n"
        finally:
            # Auch bei Abbruch speichern, was schon da ist
            if answer:
                db.add_message(chat_id, "assistant", "".join(answer))
        yield json.dumps({"done": True}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


# --- Modell-Anbindungen ---

async def stream_claude(model: str, system: str, messages: list[dict]):
    """Claude über die Anthropic-API. Nur die Nachrichten dieses Chats werden gesendet."""
    if not claude:
        yield "error", "Kein API-Schlüssel eingetragen (Add-on-Konfiguration bzw. einstellungen.env)."
        return
    try:
        async with claude.beta.messages.stream(
            model=model,
            max_tokens=64000,
            system=system,
            messages=messages,
            output_config={"effort": EFFORT},
            cache_control={"type": "ephemeral"},  # spart Kosten bei langen Chats
            # Lehnt das Modell aus Sicherheitsgründen ab, übernimmt automatisch ein anderes Claude-Modell
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            async for text in stream.text_stream:
                yield "text", text
            final = await stream.get_final_message()
        if final.stop_reason == "refusal":
            yield "text", "\n\n_(Diese Anfrage wurde abgelehnt.)_"
        elif final.stop_reason == "max_tokens":
            yield "text", "\n\n_(Antwort war zu lang und wurde abgeschnitten.)_"
    except anthropic.AuthenticationError:
        yield "error", "Der API-Schlüssel ist ungültig. Bitte neu kopieren und in der Add-on-Konfiguration (bzw. einstellungen.env) eintragen, dann neu starten."
    except anthropic.PermissionDeniedError as e:
        yield "error", f"Keine Berechtigung für dieses Modell: {e.message}"
    except anthropic.RateLimitError:
        yield "error", "Zu viele Anfragen oder Guthaben aufgebraucht. Kurz warten bzw. Guthaben aufladen."
    except anthropic.BadRequestError as e:
        yield "error", f"Anfrage abgelehnt: {e.message}"
    except anthropic.APIStatusError as e:
        yield "error", f"Fehler beim KI-Dienst ({e.status_code}). Bitte später nochmal versuchen."
    except anthropic.APIConnectionError:
        yield "error", "Keine Verbindung zum KI-Dienst. Ist der Server online?"


async def stream_ollama(model: str, system: str, messages: list[dict]):
    """Lokales Modell über Ollama (optional, komplett offline)."""
    if not OLLAMA_URL:
        yield "error", "Ollama ist nicht eingerichtet."
        return
    payload = {"model": model, "stream": True, "messages": [{"role": "system", "content": system}] + messages}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10)) as client:
            async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as r:
                if r.status_code != 200:
                    body = (await r.aread()).decode(errors="ignore")
                    yield "error", f"Ollama-Fehler ({r.status_code}): {body[:300]}"
                    return
                async for line in r.aiter_lines():
                    if not line.strip():
                        continue
                    part = json.loads(line)
                    if part.get("error"):
                        yield "error", part["error"]
                        return
                    text = part.get("message", {}).get("content", "")
                    if text:
                        yield "text", text
                    if part.get("done"):
                        return
    except httpx.ConnectError:
        yield "error", "Ollama ist nicht erreichbar. Läuft der Ollama-Container?"


# --- Weboberfläche ---

app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/manifest.webmanifest")
def manifest(request: Request):
    return {
        "name": AI_NAME,
        "short_name": AI_NAME,
        "start_url": "./",
        "display": "standalone",
        "background_color": "#10141c",
        "theme_color": "#10141c",
        "icons": [{"src": "static/icon.svg", "sizes": "any", "type": "image/svg+xml"}],
    }
