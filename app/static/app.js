// Logik der Weboberfläche
const $ = (id) => document.getElementById(id);
const state = { me: null, chats: [], chatId: null, models: [], controller: null };

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (res.status === 401 && path !== "/api/login") { showLogin(); throw new Error("401"); }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Fehler ${res.status}`);
  }
  return res;
}
const json = async (path, opts) => (await api(path, opts)).json();

const MODEL_LABELS = {
  "claude-opus-5-5": "Kargot Max",
  "claude-sonnet-5-5": "Kargot Schnell",
  "claude-haiku-5-5": "Kargot Mini",
};

// ---------- Anmeldung ----------
function showLogin() {
  $("app-view").classList.add("hidden");
  $("login-view").classList.remove("hidden");
  $("login-user").focus();
}

$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("login-error").textContent = "";
  try {
    await api("/api/login", { method: "POST", body: { username: $("login-user").value, password: $("login-pass").value } });
    $("login-pass").value = "";
    start();
  } catch (err) {
    $("login-error").textContent = err.message;
  }
});

$("logout").onclick = async () => { await api("/api/logout", { method: "POST" }); location.hash = ""; showLogin(); };

// ---------- Start ----------
async function start() {
  try { state.me = await json("/api/me"); } catch { return showLogin(); }
  $("login-view").classList.add("hidden");
  $("app-view").classList.remove("hidden");
  document.querySelectorAll(".ai-name").forEach((el) => (el.textContent = state.me.ai_name));
  document.title = state.me.ai_name;
  $("username").textContent = state.me.username;
  $("welcome-text").textContent = `Hallo ${state.me.username}!`;
  await Promise.all([loadModels(), loadChats()]);
  const fromHash = parseInt(location.hash.slice(1));
  if (fromHash && state.chats.some((c) => c.id === fromHash)) openChat(fromHash);
  else newChatView();
}

async function loadModels() {
  const data = await json("/api/models");
  state.models = data.models;
  const sel = $("model-select");
  sel.innerHTML = "";
  if (!data.models.length) {
    sel.innerHTML = `<option value="">${data.error || "Kein Modell installiert"}</option>`;
    return;
  }
  for (const m of data.models) sel.add(new Option(MODEL_LABELS[m] || m, m));
  sel.value = data.models.includes(state.me.default_model) ? state.me.default_model : data.models[0];
}

$("model-select").onchange = async () => {
  if (state.chatId) await api(`/api/chats/${state.chatId}`, { method: "PATCH", body: { model: $("model-select").value } });
};

// ---------- Chat-Liste ----------
async function loadChats() {
  state.chats = await json("/api/chats");
  renderChatList();
}

function renderChatList() {
  const q = $("search").value.toLowerCase();
  const list = $("chat-list");
  list.innerHTML = "";
  for (const c of state.chats.filter((c) => c.title.toLowerCase().includes(q))) {
    const el = document.createElement("div");
    el.className = "chat-item" + (c.id === state.chatId ? " active" : "");
    el.innerHTML = `<span></span><button class="icon-btn" title="Umbenennen">✎</button><button class="icon-btn" title="Löschen">🗑</button>`;
    el.querySelector("span").textContent = c.title;
    el.onclick = () => openChat(c.id);
    const [rename, del] = el.querySelectorAll("button");
    rename.onclick = async (e) => {
      e.stopPropagation();
      const title = prompt("Neuer Name:", c.title);
      if (title && title.trim()) {
        await api(`/api/chats/${c.id}`, { method: "PATCH", body: { title } });
        await loadChats();
        if (c.id === state.chatId) $("chat-title").textContent = title;
      }
    };
    del.onclick = async (e) => {
      e.stopPropagation();
      if (!confirm(`„${c.title}“ löschen?`)) return;
      await api(`/api/chats/${c.id}`, { method: "DELETE" });
      if (c.id === state.chatId) newChatView();
      await loadChats();
    };
    list.appendChild(el);
  }
}
$("search").oninput = renderChatList;

// ---------- Chat anzeigen ----------
function newChatView() {
  stopStreaming();
  state.chatId = null;
  location.hash = "";
  $("chat-title").textContent = "";
  $("messages").innerHTML = "";
  $("messages").appendChild(welcomeEl);
  if (state.models.includes(state.me.default_model)) $("model-select").value = state.me.default_model;
  renderChatList();
  closeSidebar();
  $("input").focus();
}
const welcomeEl = $("welcome");
$("new-chat").onclick = newChatView;

async function openChat(id) {
  stopStreaming();
  const chat = await json(`/api/chats/${id}`);
  state.chatId = id;
  location.hash = id;
  $("chat-title").textContent = chat.title;
  if (state.models.includes(chat.model)) $("model-select").value = chat.model;
  const box = $("messages");
  box.innerHTML = "";
  chat.messages.forEach((m, idx) => addMessage(m.role, m.content, idx === chat.messages.length - 1));
  renderChatList();
  closeSidebar();
  box.scrollTop = box.scrollHeight;
}

function addMessage(role, content, isLast = false) {
  welcomeEl.remove();
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  wrap.appendChild(bubble);
  setContent(bubble, role, content);
  if (role === "assistant") addActions(wrap, bubble, isLast);
  $("messages").appendChild(wrap);
  return bubble;
}

function setContent(bubble, role, content) {
  bubble.dataset.raw = content;
  if (role === "user") bubble.textContent = content;
  else bubble.innerHTML = window.renderMarkdown(content);
}

function addActions(wrap, bubble, showRegenerate) {
  const bar = document.createElement("div");
  bar.className = "msg-actions";
  const copy = document.createElement("button");
  copy.className = "icon-btn";
  copy.textContent = "Kopieren";
  copy.onclick = () => copyText(bubble.dataset.raw, copy);
  bar.appendChild(copy);
  if (showRegenerate) {
    const regen = document.createElement("button");
    regen.className = "icon-btn regen";
    regen.textContent = "↻ Neu";
    regen.onclick = () => { wrap.remove(); send(null); };
    bar.appendChild(regen);
  }
  wrap.appendChild(bar);
}

function copyText(text, btn) {
  const done = () => { const old = btn.textContent; btn.textContent = "Kopiert ✓"; setTimeout(() => (btn.textContent = old), 1200); };
  if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done);
  else {
    const ta = document.createElement("textarea");
    ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); done();
  }
}

// Kopier-Knopf in Codeblöcken
$("messages").addEventListener("click", (e) => {
  if (e.target.classList.contains("copy")) copyText(e.target.nextElementSibling.textContent, e.target);
});

// ---------- Senden & Streaming ----------
const input = $("input");
input.addEventListener("input", autosize);
function autosize() { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 220) + "px"; }
input.addEventListener("keydown", (e) => {
  // Enter = senden, Shift+Enter = neue Zeile (am Handy: Knopf benutzen)
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing && window.matchMedia("(pointer: fine)").matches) {
    e.preventDefault();
    $("composer").requestSubmit();
  }
});
$("composer").addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text || state.controller) return;
  input.value = "";
  autosize();
  send(text);
});
$("stop").onclick = stopStreaming;

function stopStreaming() {
  if (state.controller) state.controller.abort();
}

async function send(text) {
  if (!$("model-select").value) { alert("Es ist noch kein KI-Modell installiert. Siehe Anleitung (README)."); return; }
  try {
    if (!state.chatId) {
      const chat = await json("/api/chats", { method: "POST", body: { model: $("model-select").value } });
      state.chatId = chat.id;
      location.hash = chat.id;
    }
  } catch (err) { return alert(err.message); }
  const chatId = state.chatId;
  document.querySelectorAll(".regen").forEach((b) => b.remove());
  if (text !== null) addMessage("user", text);

  const bubble = addMessage("assistant", "");
  bubble.innerHTML = '<span class="thinking">Denkt nach…</span>';
  const box = $("messages");
  const stick = () => { if (box.scrollHeight - box.scrollTop - box.clientHeight < 120) box.scrollTop = box.scrollHeight; };
  box.scrollTop = box.scrollHeight;

  state.controller = new AbortController();
  $("send").classList.add("hidden");
  $("stop").classList.remove("hidden");
  let answer = "";
  let pending = false;
  let finished = false;
  const paint = () => { pending = false; if (finished) return; setContent(bubble, "assistant", answer); bubble.classList.add("cursor"); stick(); };

  try {
    const res = await api(`/api/chats/${chatId}/messages`, {
      method: "POST", body: { content: text }, signal: state.controller.signal,
    });
    if (text !== null) loadChats().then(() => {
      const c = state.chats.find((c) => c.id === chatId);
      if (c && state.chatId === chatId) $("chat-title").textContent = c.title;
    });
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop();
      for (const line of lines) {
        if (!line.trim()) continue;
        const ev = JSON.parse(line);
        if (ev.error) throw new Error(ev.error);
        if (ev.t) {
          answer += ev.t;
          if (!pending) { pending = true; requestAnimationFrame(paint); }
        }
      }
    }
  } catch (err) {
    if (err.name !== "AbortError" && err.message !== "401") {
      if (!answer) bubble.parentElement.classList.add("error");
      answer += (answer ? "\n\n" : "") + "⚠️ " + err.message;
    }
  } finally {
    finished = true;
    state.controller = null;
    $("send").classList.remove("hidden");
    $("stop").classList.add("hidden");
    if (state.chatId === chatId) {
      setContent(bubble, "assistant", answer || "_(keine Antwort)_");
      bubble.classList.remove("cursor");
      const wrap = bubble.parentElement;
      wrap.querySelector(".msg-actions")?.remove();
      addActions(wrap, bubble, true);
      stick();
    }
    await loadChats();
    const c = state.chats.find((c) => c.id === state.chatId);
    if (c) $("chat-title").textContent = c.title;
  }
}

// ---------- Einstellungen ----------
$("open-settings").onclick = () => {
  $("system-prompt").value = state.me.system_prompt || "";
  $("settings").showModal();
};
$("settings-form").addEventListener("submit", async (e) => {
  if (e.submitter?.value !== "save") return;
  e.preventDefault();
  $("settings-error").textContent = "";
  try {
    const system_prompt = $("system-prompt").value;
    await api("/api/settings", { method: "PUT", body: { system_prompt } });
    state.me.system_prompt = system_prompt;
    if ($("pw-new").value) {
      await api("/api/password", { method: "PUT", body: { old: $("pw-old").value, new: $("pw-new").value } });
      $("pw-old").value = $("pw-new").value = "";
    }
    $("settings").close();
  } catch (err) {
    $("settings-error").textContent = err.message;
  }
});

// ---------- Handy-Seitenleiste ----------
function closeSidebar() { $("sidebar").classList.remove("open"); $("backdrop").classList.remove("open"); }
$("open-sidebar").onclick = () => { $("sidebar").classList.add("open"); $("backdrop").classList.add("open"); };
$("close-sidebar").onclick = closeSidebar;
$("backdrop").onclick = closeSidebar;

start();
