"""Unsere eigene KI: Web-Server, der mit Ollama (lokales Sprachmodell) spricht."""
import json
import os
import time
from pathlib import Path

import httpx
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434").rstrip("/")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "qwen2.5:7b")
AI_NAME = os.environ.get("AI_NAME", "Unsere KI")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
STATIC = Path(__file__).parent / "static"

BASE_PROMPT = (
    "Du bist {name}, ein hilfsbereiter, ehrlicher und kluger KI-Assistent. "
    "Du sprichst mit {user}. Antworte standardmäßig auf Deutsch, außer man schreibt dir in einer anderen Sprache. "
    "Sei klar und direkt, nutze Markdown (Listen, Überschriften, Codeblöcke), wenn es hilft. "
    "Wenn du etwas nicht weißt, sag es ehrlich, statt etwas zu erfinden. "
    "Heute ist der {date}. Du läufst komplett offline auf einem privaten Server und hast keinen Internetzugang."
)

app = FastAPI(title=AI_NAME)
db.init()


# --- Anmeldung ---

def current_user(session: str | None = Cookie(default=None)):
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
        "session", token, httponly=True, samesite="lax", secure=COOKIE_SECURE, max_age=60 * 60 * 24 * 365
    )
    return {"ok": True}


@app.post("/api/logout")
def logout(response: Response, session: str | None = Cookie(default=None)):
    if session:
        db.logout(session)
    response.delete_cookie("session")
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return {
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


# --- Modelle ---

@app.get("/api/models")
async def models(user=Depends(current_user)):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            r.raise_for_status()
            names = [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return {"models": [], "error": "Ollama ist nicht erreichbar"}
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
    payload = {
        "model": chat["model"],
        "stream": True,
        "messages": [{"role": "system", "content": build_system_prompt(user)}]
        + [{"role": m["role"], "content": m["content"]} for m in history],
    }

    async def stream():
        answer = []
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10)) as client:
                async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as r:
                    if r.status_code != 200:
                        body = (await r.aread()).decode(errors="ignore")
                        yield json.dumps({"error": f"Ollama-Fehler ({r.status_code}): {body[:300]}"}) + "\n"
                        return
                    async for line in r.aiter_lines():
                        if not line.strip():
                            continue
                        part = json.loads(line)
                        if part.get("error"):
                            yield json.dumps({"error": part["error"]}) + "\n"
                            return
                        text = part.get("message", {}).get("content", "")
                        if text:
                            answer.append(text)
                            yield json.dumps({"t": text}) + "\n"
                        if part.get("done"):
                            break
        except httpx.ConnectError:
            yield json.dumps({"error": "Ollama ist nicht erreichbar. Läuft der Ollama-Container?"}) + "\n"
        finally:
            # Auch bei Abbruch speichern, was schon da ist
            if answer:
                db.add_message(chat_id, "assistant", "".join(answer))
        yield json.dumps({"done": True}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


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
        "start_url": "/",
        "display": "standalone",
        "background_color": "#1f1e1d",
        "theme_color": "#1f1e1d",
        "icons": [{"src": "/static/icon.svg", "sizes": "any", "type": "image/svg+xml"}],
    }
