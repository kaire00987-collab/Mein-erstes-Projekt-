# Unsere KI – eure eigene, private KI

Ein eigener KI-Chat für euch zwei – sieht aus und funktioniert ähnlich wie die Claude-App:

- 💬 Chats mit Verlauf, Suche, Umbenennen, Löschen
- ⚡ Antworten erscheinen live Wort für Wort, mit Stopp- und „Neu generieren“-Knopf
- 📝 Schöne Formatierung (Listen, Tabellen, Code mit Kopieren-Knopf)
- 👥 Eigenes Konto für jede Person – keiner sieht die Chats des anderen
- 🧠 „Persönliche Anweisungen“: Jeder kann der KI sagen, was sie über ihn wissen soll
- 📱 Läuft im Browser am PC und am Handy (lässt sich als App auf den Homescreen legen)
- 🌙 Heller und dunkler Modus
- 🔒 **Alles bleibt auf eurem Server** – Chats, Konten und das KI-Modell selbst
- ✈️ **Funktioniert komplett offline**, sobald das Modell einmal heruntergeladen ist

> **Ehrlicher Hinweis:** Das „Gehirn“ ist ein freies Open-Source-Modell (z. B. Qwen, Llama, Gemma),
> das auf eurem Server läuft. Claude selbst kann man nicht herunterladen. Die freien Modelle sind gut
> für Alltag, Texte, Erklärungen und einfachen Code, aber nicht ganz so stark wie Claude.
> Je stärker euer Server, desto größer und klüger das Modell, das ihr nutzen könnt.

---

## Was ihr braucht

- Einen Server oder PC mit **Linux, Windows oder Mac**, auf dem **[Docker](https://docs.docker.com/get-docker/)** installiert ist
- Mindestens **8 GB RAM** (16 GB empfohlen) und ca. **10 GB freien Speicher**
- Optional: eine **NVIDIA-Grafikkarte** – dann antwortet die KI viel schneller

## Einrichtung (einmalig, ca. 15 Minuten)

```bash
# 1. Projekt holen
git clone https://github.com/kaire00987-collab/Mein-erstes-Projekt-.git
cd Mein-erstes-Projekt-

# 2. Einstellungen anlegen (Name der KI usw. kann man in .env ändern)
cp .env.example .env

# 3. Starten
docker compose up -d --build

# 4. KI-Modell herunterladen (einmalig, ca. 5 GB – braucht Internet)
docker compose exec ollama ollama pull qwen2.5:7b

# 5. Eure beiden Konten anlegen (fragt jeweils nach einem Passwort)
docker compose exec app python manage.py add-user lena
docker compose exec app python manage.py add-user max
```

Fertig! Öffnet im Browser: **http://IP-EURES-SERVERS:3000**
(auf dem Server selbst: http://localhost:3000)

Ab jetzt braucht ihr **kein Internet mehr** – nur noch das Heimnetz bzw. die Verbindung zum Server.

## Welches Modell passt zu eurem Server?

| Euer Server | Modell | Befehl |
|---|---|---|
| 8 GB RAM, keine Grafikkarte | Qwen 2.5 3B (schnell, einfacher) | `docker compose exec ollama ollama pull qwen2.5:3b` |
| 16 GB RAM **(Empfehlung)** | Qwen 2.5 7B (sehr gut auf Deutsch) | `docker compose exec ollama ollama pull qwen2.5:7b` |
| 16 GB RAM | Llama 3.1 8B | `docker compose exec ollama ollama pull llama3.1:8b` |
| 32 GB RAM oder Grafikkarte mit 16 GB+ | Gemma 3 27B / Qwen 2.5 32B (deutlich klüger) | `docker compose exec ollama ollama pull gemma3:27b` |

Ihr könnt mehrere Modelle laden und oben rechts im Chat zwischen ihnen wechseln.
Das Standard-Modell für neue Chats stellt ihr in `.env` bei `DEFAULT_MODEL` ein.
Alle Modelle: https://ollama.com/library

**Grafikkarte nutzen (NVIDIA):** In `docker-compose.yml` die Zeilen unter „Für NVIDIA-Grafikkarte“ einkommentieren,
das [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
installieren und `docker compose up -d` ausführen.

## Wo wird was gespeichert?

Alles im Ordner `data/` auf eurem Server:

- `data/ki.db` – Konten (Passwörter verschlüsselt), alle Chats und Einstellungen
- `data/ollama/` – die heruntergeladenen KI-Modelle

**Backup:** Einfach den Ordner `data/` kopieren.

## Nützliche Befehle

```bash
docker compose exec app python manage.py list-users          # Konten anzeigen
docker compose exec app python manage.py set-password lena   # Passwort ändern
docker compose exec app python manage.py delete-user max     # Konto löschen
docker compose logs -f app                                   # Protokoll ansehen
docker compose down                                          # stoppen
git pull && docker compose up -d --build                     # aktualisieren
```

## Von unterwegs zugreifen (optional)

Standardmäßig ist die KI nur in eurem Heimnetz erreichbar – das ist am sichersten.
Wenn ihr auch unterwegs chatten wollt, ist **[Tailscale](https://tailscale.com/)** am einfachsten
(kostenlos, verschlüsselt, kein Port-Freigeben am Router nötig).
Wer die Seite stattdessen öffentlich über HTTPS (z. B. mit Caddy) betreibt, setzt in `.env` `COOKIE_SECURE=true`.

## Aufbau (für Neugierige)

```
docker-compose.yml   startet zwei Container: "ollama" (die KI) und "app" (die Webseite)
app/main.py          Webserver (Python/FastAPI): Login, Chats, Weiterleitung an Ollama
app/db.py            Datenbank (SQLite)
app/manage.py        Benutzerverwaltung
app/static/          Oberfläche (HTML, CSS, JavaScript – ohne externe Dateien, also offline-fähig)
```
