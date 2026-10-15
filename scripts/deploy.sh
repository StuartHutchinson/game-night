#!/usr/bin/env bash
# Update the live app on PythonAnywhere. Run from a PythonAnywhere Bash console:
#   ~/game-night/scripts/deploy.sh
# then click Reload on the Web tab.
set -euo pipefail

cd "$(dirname "$0")/.."
git pull --ff-only
.venv/bin/pip install --quiet -r requirements.txt
.venv/bin/python scripts/backup_db.py
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
echo "Done. Now click Reload on the PythonAnywhere Web tab."
