# Kargot in Home Assistant – Schritt für Schritt

Diese Anleitung hat zwei Teile:

- **Teil A:** Kargot als Chat in Home Assistant (wie die Claude-App) – ca. 15 Minuten
- **Teil B:** Sprachsteuerung „Kargot, mach das Licht aus“ – ca. 20 Minuten

Ihr braucht: Home Assistant OS (habt ihr), Handy oder PC, eine Bank- oder Kreditkarte für das Guthaben.

> Hinweis: Die Namen der Menüpunkte können je nach Home-Assistant-Version leicht abweichen.
> In neueren Versionen heißen „Add-ons“ zum Beispiel teilweise „Apps“.

---

## Teil A: Kargot-Chat installieren

### A1 – Kargot auf GitHub freigeben (einmalig, 1 Minute)

1. Diesen Link öffnen: https://github.com/kaire00987-collab/Mein-erstes-Projekt-/pull/1
2. Ganz unten auf den grünen Knopf **„Merge pull request“** tippen
3. Dann **„Confirm merge“**
4. Fertig – es erscheint „Merged“ in Lila.

### A2 – API-Schlüssel besorgen (5 Minuten)

Der Schlüssel ist eure „Eintrittskarte“ für Claude, das Gehirn hinter Kargot.

1. **https://platform.claude.com** öffnen und ein Konto anlegen (mit E-Mail)
2. Links auf **Billing** (Abrechnung) → **Add credits** → z. B. **10 $** aufladen
3. Empfehlung: Unter **Limits** eine monatliche Obergrenze setzen, z. B. 20 $
4. Links auf **API Keys** → **Create Key**
5. Name: `Kargot` → **Create**
6. Den Schlüssel (beginnt mit `sk-ant-…`) **kopieren** und kurz in einer Notiz zwischenspeichern
   – er wird nur einmal angezeigt! Nicht weitergeben, er ist wie ein Passwort.

### A3 – Kargot in Home Assistant installieren (5 Minuten)

1. Home Assistant öffnen → **Einstellungen** → **Add-ons**
2. Unten rechts **Add-on Store**
3. Oben rechts auf **⋮** (drei Punkte) → **Repositories**
4. Diese Adresse einfügen:
   ```
   https://github.com/kaire00987-collab/Mein-erstes-Projekt-
   ```
5. **Hinzufügen** → Fenster schließen
6. Seite neu laden (nach unten ziehen bzw. F5). Ganz unten erscheint der Bereich **„Kargot Add-ons“**
7. Auf **Kargot** tippen → **Installieren** → warten (2–5 Minuten)

### A4 – Kargot einrichten und starten (2 Minuten)

1. Oben auf den Reiter **Konfiguration**
2. Bei **API-Schlüssel** euren `sk-ant-…`-Schlüssel einfügen → **Speichern**
3. Zurück zum Reiter **Info**
4. Diese Schalter einschalten:
   - **Beim Booten starten**
   - **In Seitenleiste anzeigen**
5. **Starten** tippen

### A5 – Loslegen

1. Links in der Seitenleiste ist jetzt **Kargot** – antippen
2. Schreibt etwas, z. B. „Hallo Kargot, wer bist du?“
3. Über **⚙︎** unten links könnt ihr Kargot sagen, was es über euch wissen soll

**Für die zweite Person:** Sie braucht ein eigenes Home-Assistant-Konto
(**Einstellungen → Personen → Person hinzufügen**, „Anmelden erlauben“ einschalten).
Dann bekommt sie in Kargot automatisch eigene, private Chats.

**Am Handy:** Kargot ist in der Home-Assistant-App ebenfalls in der Seitenleiste (☰).

---

## Teil B: Sprachsteuerung mit „Kargot“

Der Kargot-Chat aus Teil A ist zum Schreiben da. Für Sprache und das Steuern von Licht & Co. nutzt man den
eingebauten Sprachassistenten von Home Assistant („Assist“) und gibt ihm Claude als Gehirn und den Namen Kargot.

### B1 – Claude mit Home Assistant verbinden

1. **Einstellungen** → **Geräte & Dienste** → unten rechts **Integration hinzufügen**
2. Nach **Anthropic** suchen und auswählen
3. Denselben API-Schlüssel wie in A2 einfügen → **Absenden**
4. Bei der neuen Anthropic-Integration auf **Konfigurieren** (bzw. beim Gesprächsagenten auf das Zahnrad) tippen:
   - **Anweisungen** – diesen Text hineinkopieren:
     ```
     Du bist Kargot, der Sprachassistent von unserem Zuhause.
     Antworte immer auf Deutsch, kurz und freundlich, in ein bis zwei Sätzen.
     ```
   - **Home Assistant steuern**: **Assist** auswählen (sonst darf Kargot keine Geräte schalten)
   - **Absenden**

### B2 – Den Sprachassistenten „Kargot“ anlegen

1. **Einstellungen** → **Sprachassistenten** → **Assistent hinzufügen**
2. **Name:** `Kargot`
3. **Sprache:** Deutsch
4. **Gesprächsagent:** den Claude-/Anthropic-Agenten aus B1 auswählen
5. **Sprache-zu-Text** und **Text-zu-Sprache** (damit Kargot hört und spricht):
   - Am einfachsten und besten auf Deutsch: **Home Assistant Cloud** (Nabu Casa, ca. 7,50 €/Monat,
     unterstützt nebenbei auch die Entwicklung von Home Assistant)
   - Kostenlos und lokal: Add-ons **Whisper** (Hören) und **Piper** (Sprechen) aus dem Add-on Store
     installieren, dann hier auswählen. Funktioniert, klingt aber etwas roboterhafter.
6. **Erstellen**
7. Beim neuen Assistenten **Kargot** auf **⋮ → Als bevorzugt festlegen**

### B3 – Festlegen, was Kargot steuern darf

1. **Einstellungen** → **Sprachassistenten** → Reiter **Entitäten freigeben** (bzw. „Freigeben“)
2. Lichter, Steckdosen usw. einschalten, die Kargot steuern darf
3. Tipp: Gebt den Geräten verständliche Namen und Räume (z. B. „Wohnzimmerlicht“ im Raum „Wohnzimmer“),
   dann versteht Kargot euch besser.

### B4 – Testen

1. In der Home-Assistant-App oben rechts auf das **Assist-Symbol** (Sprechblase) tippen
2. Schreiben oder aufs Mikrofon tippen und sagen: **„Mach das Licht im Wohnzimmer aus“**
3. Kargot schaltet das Licht und antwortet.

### B5 – Per Sprache vom Handy starten

- **iPhone:** In der App **Kurzbefehle** einen neuen Kurzbefehl anlegen → Aktion **„Assist“** (von Home Assistant)
  hinzufügen → Kurzbefehl **„Kargot“** nennen. Dann sagt ihr:
  **„Hey Siri, Kargot“** → und danach z. B. „Mach das Licht aus“.
- **Android:** **Einstellungen → Apps → Standard-Apps → Digitaler Assistent** → **Home Assistant** auswählen.
  Dann startet langes Drücken auf die Home-Taste direkt Kargot.

### Und Alexa?

- **Das Wort „Alexa“ lässt sich nicht durch „Kargot“ ersetzen.** Amazon erlaubt nur feste Aktivierungswörter
  (Alexa, Echo, Computer, Amazon, Ziggy).
- Was geht: Mit **Home Assistant Cloud** könnt ihr eure Home-Assistant-Geräte mit Alexa verbinden
  (**Einstellungen → Home Assistant Cloud → Alexa**). Dann klappt „Alexa, Licht aus“ – das ist dann aber Alexa, nicht Kargot.
- Ein eigener Alexa-Skill („Alexa, frag Kargot …“) ist möglich, aber aufwendig. Das können wir später angehen.

### Ein Lautsprecher, der auf „Kargot“ hört (später)

Wer ohne Handy sprechen möchte, kann sich das **Home Assistant Voice Preview Edition** holen (ca. 60 €).
Das ist ein kleiner Lautsprecher mit Mikrofon wie ein Echo, nur für Home Assistant. Er hört ab Werk auf
„Okay Nabu“ oder „Hey Jarvis“ und benutzt dann euren Assistenten Kargot. Ein eigenes Aktivierungswort
„Kargot“ kann man trainieren – das ist etwas für später.

---

## Hilfe, etwas klappt nicht

| Problem | Lösung |
|---|---|
| Kargot erscheint nicht im Add-on Store | Prüfen, ob Schritt A1 erledigt ist. Dann im Store **⋮ → Nach Updates suchen** und Seite neu laden |
| „Kein Modell eingerichtet“ im Chat | API-Schlüssel fehlt: Add-on → Konfiguration → Schlüssel eintragen → Add-on neu starten |
| „API-Schlüssel ist ungültig“ | Schlüssel neu kopieren (ohne Leerzeichen) oder in A2 einen neuen erstellen |
| „Guthaben aufgebraucht“ | Auf platform.claude.com unter Billing aufladen |
| Kargot schaltet kein Licht | B1: „Home Assistant steuern = Assist“ prüfen, und B3: Gerät freigegeben? |

Bei anderen Fehlern: Add-on → Reiter **Protokoll** öffnen, Screenshot machen und schicken.
