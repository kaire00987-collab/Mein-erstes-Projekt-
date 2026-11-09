# Kargot – eure private KI

**Kargot** ist euer eigener KI-Chat für zwei. Er läuft auf **eurer Synology NAS**:

- 🧠 Im Hintergrund arbeitet **Claude** von Anthropic (über die offizielle API) – Kargot ist euer eigener Name und eure eigene Oberfläche dafür
- 💾 **Alle Chats und Konten werden nur auf eurer NAS gespeichert**, nicht in einer Cloud
- 👥 Ein eigenes Konto für jede Person – keiner sieht die Chats des anderen
- 💬 Chat-Verlauf, Suche, Umbenennen, Löschen, Live-Antworten, Stopp- und „Neu“-Knopf
- 📝 Schöne Formatierung (Listen, Tabellen, Code mit Kopieren-Knopf)
- 🙋 „Persönliche Anweisungen“: Jeder sagt der KI, was sie über ihn wissen soll
- 📱 Läuft im Browser am Handy und PC (lässt sich als App auf den Homescreen legen)

## Was passiert mit euren Daten?

| | Wo? |
|---|---|
| Chat-Verlauf, Konten, Passwörter (verschlüsselt), Einstellungen | **Nur auf eurer NAS** (`data/ki.db`) |
| Die Nachrichten des aktuellen Chats | Werden zum Beantworten an Anthropic (die Firma hinter Claude) geschickt |

Damit Kargot antworten kann, muss Claude im Hintergrund den Chat lesen. Das geht technisch nicht anders. Laut Anthropic werden
Daten aus der API standardmäßig **nicht zum Training** der KI verwendet. Einzelheiten stehen in den
[Datenschutzbestimmungen von Anthropic](https://www.anthropic.com/legal/privacy).
Es wird immer nur der gerade offene Chat gesendet – nie eure anderen Chats oder die Daten der anderen Person.

## Was kostet das?

Die App selbst ist kostenlos. Für die KI im Hintergrund (Claude) bezahlt ihr nach Verbrauch bei Anthropic (Guthaben vorher aufladen, z. B. 10 €):

| Modell | Wofür | Grobe Kosten |
|---|---|---|
| **Kargot Max** (Standard, = Claude Opus 5.5) | Am klügsten | ca. 1–5 Cent pro Nachricht, bei sehr langen Chats mehr |
| Kargot Schnell (= Claude Sonnet 5.5) | Fast genauso gut, schneller | etwa die Hälfte |
| Kargot Mini (= Claude Haiku 5.5) | Einfache Fragen | Bruchteile eines Cents |

Oben rechts im Chat könnt ihr jederzeit das Modell wechseln. **Tipp:** Legt im Anthropic-Konto unter
„Limits“ eine monatliche Obergrenze fest, dann gibt es keine Überraschungen.

---

## Einrichtung auf der Synology (ca. 20 Minuten)

### Voraussetzung

Eure NAS braucht den **Container Manager** (früher „Docker“). Öffnet das **Paket-Zentrum** und sucht nach
„Container Manager“. Wird er angezeigt → installieren. Wird er nicht angezeigt, kann euer NAS-Modell leider
keine Container ausführen (meist die „j“-Modelle); dann meldet euch, es gibt Alternativen.
2 GB Arbeitsspeicher reichen für die App völlig aus.

### Schritt 1: API-Schlüssel holen

1. Auf **https://platform.claude.com** ein Konto anlegen
2. Unter **Billing** Guthaben aufladen
3. Unter **API Keys** → **Create Key** einen Schlüssel erstellen und kopieren (beginnt mit `sk-ant-`)
   – der Schlüssel ist wie ein Passwort, nicht weitergeben!

### Schritt 2: Dateien auf die NAS kopieren

1. Auf GitHub bei diesem Projekt auf **Code → Download ZIP** klicken
2. In der **File Station** im Ordner `docker` einen Ordner `kargot` anlegen
   (gibt es `docker` nicht, einfach anlegen)
3. Die ZIP hochladen, rechtsklicken → **Hier entpacken**. Danach muss direkt in `docker/kargot`
   die Datei `docker-compose.yml` liegen (eventuell den Inhalt eines Unterordners eine Ebene nach oben verschieben)

### Schritt 3: Einstellungen eintragen

1. Die Datei `einstellungen.beispiel.env` kopieren und die Kopie in **`einstellungen.env`** umbenennen
2. Mit dem **Texteditor** (aus dem Paket-Zentrum) öffnen und ausfüllen:
   ```
   ANTHROPIC_API_KEY=sk-ant-…euer-schlüssel…
   INITIAL_USERS=lena:startpasswort1,max:startpasswort2
   ```
   (Namen und Passwörter natürlich anpassen.)
3. Speichern

### Schritt 4: Starten

1. **Container Manager** öffnen → **Projekt** → **Erstellen**
2. Projektname: `kargot`, Pfad: `docker/kargot` auswählen
3. Es wird erkannt, dass eine `docker-compose.yml` vorhanden ist → **Weiter** → **Fertig**
4. Warten, bis der Build fertig ist (ein paar Minuten)

### Schritt 5: Loslegen

Im Browser öffnen: **http://IP-EURER-NAS:3000**
(Die IP findet ihr in der Synology-Systemsteuerung unter *Netzwerk*, z. B. `192.168.178.20`.)

Mit dem Namen und Startpasswort anmelden und dann über **⚙︎** (unten links) ein eigenes Passwort setzen.

**Am Handy als App:** Seite öffnen → Teilen/Menü → **„Zum Home-Bildschirm“**.

---

## Weitere Einstellungen

In `einstellungen.env`:

| Einstellung | Bedeutung |
|---|---|
| `AI_NAME` | Name eurer KI (Standard: „Kargot“) |
| `DEFAULT_MODEL` | Modell für neue Chats: `claude-opus-5-5` (Max), `claude-sonnet-5-5` (Schnell) oder `claude-haiku-5-5` (Mini) |
| `CLAUDE_EFFORT` | Wie gründlich Kargot nachdenkt: `low` (schnell, günstig), `medium`, `high` (gründlich, teurer) |

Nach einer Änderung im Container Manager das Projekt **stoppen und neu starten**.

## Backup

Alles Wichtige liegt in `docker/kargot/data/`. Diesen Ordner in **Hyper Backup** aufnehmen, fertig.

## Von unterwegs zugreifen (optional)

Standardmäßig klappt es nur im Heimnetz – das ist am sichersten. Für unterwegs ist
**[Tailscale](https://tailscale.com/)** am einfachsten: Es gibt Tailscale direkt im Synology-Paket-Zentrum
und als App fürs Handy (kostenlos, verschlüsselt, keine Router-Einstellungen nötig).
Wer die Seite stattdessen öffentlich über HTTPS betreibt (Synology *Reverse Proxy* + Let's-Encrypt-Zertifikat),
setzt in `einstellungen.env` `COOKIE_SECURE=true`.

## Für Technik-Fans

**Per SSH statt Oberfläche:**
```bash
cd /volume1/docker/kargot
cp einstellungen.beispiel.env einstellungen.env   # ausfüllen
sudo docker compose up -d --build
sudo docker compose exec app python manage.py add-user NAME      # weiteres Konto
sudo docker compose exec app python manage.py set-password NAME  # Passwort zurücksetzen
```

**Komplett offline (ohne Internet):** Auf einem Rechner mit mindestens 16 GB RAM (nicht die NAS) kann zusätzlich ein
lokales Open-Source-Modell laufen: `docker compose --profile offline up -d`, dann
`docker compose exec ollama ollama pull qwen2.5:7b` und in `einstellungen.env` `OLLAMA_URL=http://ollama:11434`.
Lokale Modelle erscheinen dann zusätzlich in der Modellauswahl.

**Aufbau:**
```
docker-compose.yml   startet die App (und optional Ollama)
app/main.py          Webserver (Python/FastAPI): Login, Chats, Anbindung an Claude bzw. Ollama
app/db.py            Datenbank (SQLite)
app/manage.py        Benutzerverwaltung per Kommandozeile
app/static/          Oberfläche (HTML, CSS, JavaScript – ohne externe Dateien)
```
