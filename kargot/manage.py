"""Benutzerverwaltung über die Kommandozeile.

  python manage.py add-user NAME        # neuen Benutzer anlegen (fragt nach Passwort)
  python manage.py set-password NAME    # Passwort ändern
  python manage.py delete-user NAME     # Benutzer samt Chats löschen
  python manage.py list-users
"""
import getpass
import sqlite3
import sys

import db


def ask_password() -> str:
    while True:
        pw = getpass.getpass("Passwort: ")
        if len(pw) < 6:
            print("Bitte mindestens 6 Zeichen.")
            continue
        if pw != getpass.getpass("Passwort wiederholen: "):
            print("Passwörter stimmen nicht überein.")
            continue
        return pw


def main() -> int:
    db.init()
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd, args = sys.argv[1], sys.argv[2:]

    if cmd == "list-users":
        for name in db.list_users():
            print(name)
        return 0
    if not args:
        print(__doc__)
        return 1
    name = args[0]

    if cmd == "add-user":
        try:
            db.add_user(name, ask_password())
        except sqlite3.IntegrityError:
            print(f"Benutzer '{name}' gibt es schon.")
            return 1
        print(f"Benutzer '{name}' angelegt.")
    elif cmd == "set-password":
        print("Passwort geändert." if db.set_password(name, ask_password()) else "Benutzer nicht gefunden.")
    elif cmd == "delete-user":
        print("Gelöscht." if db.delete_user(name) else "Benutzer nicht gefunden.")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
