# Kargot

Eure private KI direkt in Home Assistant. Ihr meldet euch automatisch mit eurem Home-Assistant-Konto an,
jede Person hat ihre eigenen Chats. Alle Chats werden nur auf eurem Home-Assistant-Rechner gespeichert.

## Einrichtung

1. Auf **https://platform.claude.com** ein Konto anlegen, unter **Billing** Guthaben aufladen
   und unter **API Keys** einen Schlüssel erstellen (beginnt mit `sk-ant-`).
2. Hier im Add-on auf **Konfiguration** gehen, den Schlüssel bei **API-Schlüssel** einfügen und speichern.
3. Auf **Info** → **Starten**. „In Seitenleiste anzeigen“ einschalten.
4. Links in der Seitenleiste auf **Kargot** tippen – fertig.

## Wichtig

- Damit Kargot antworten kann, wird der gerade offene Chat an Anthropic (Claude) geschickt.
  Gespeichert wird der Verlauf nur bei euch.
- Die Kosten laufen über euer Guthaben bei Anthropic. Am besten dort ein monatliches Limit setzen.
- Backup: Die Chats sind in den normalen Home-Assistant-Backups enthalten.
