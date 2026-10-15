"""Copy the SQLite database to a dated backup file and keep the newest 14.

Run daily as a PythonAnywhere scheduled task:
    /home/<you>/game-night/.venv/bin/python /home/<you>/game-night/scripts/backup_db.py
"""

import datetime
import os
import sqlite3
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("DJANGO_DB_PATH", PROJECT / "db.sqlite3"))
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", PROJECT / "backups"))
KEEP = 14


def main():
    if not DB_PATH.exists():
        print(f"No database at {DB_PATH} yet; nothing to back up")
        return
    BACKUP_DIR.mkdir(exist_ok=True)
    target = BACKUP_DIR / f"db-{datetime.date.today():%Y-%m-%d}.sqlite3"
    # sqlite3's backup API gives a consistent copy even while the app is writing.
    with sqlite3.connect(DB_PATH) as source, sqlite3.connect(target) as dest:
        source.backup(dest)
    backups = sorted(BACKUP_DIR.glob("db-*.sqlite3"))
    for old in backups[:-KEEP]:
        old.unlink()
    print(f"Backed up to {target}")


if __name__ == "__main__":
    main()
