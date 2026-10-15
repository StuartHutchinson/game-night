# Deploying to PythonAnywhere

Replace `<you>` with your PythonAnywhere username and `<github-user>` with your GitHub username throughout.

## One-time setup

1. **Create the account.** Sign up for the free Beginner plan at pythonanywhere.com. Your app will live at `https://<you>.pythonanywhere.com`.

2. **Clone the repo.** Open a **Bash console** (Consoles tab) and run:

   ```bash
   git clone https://github.com/<github-user>/game-night.git ~/game-night
   cd ~/game-night
   python3.12 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

   If the repo is private, GitHub will ask for a username and a personal access token instead of a password.

3. **Make a secret key.** Still in the console:

   ```bash
   .venv/bin/python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

   Copy the output for step 5. Don't commit it or paste it anywhere else.

4. **Create the web app.** On the **Web** tab: *Add a new web app* → *Manual configuration* → *Python 3.12*. Then set:

   | Setting | Value |
   | --- | --- |
   | Source code | `/home/<you>/game-night` |
   | Working directory | `/home/<you>/game-night` |
   | Virtualenv | `/home/<you>/game-night/.venv` |
   | Static files: URL `/static/` | Directory `/home/<you>/game-night/staticfiles` |
   | Force HTTPS | On |

5. **Edit the WSGI file.** On the Web tab, click the WSGI configuration file link. Replace everything in it with:

   ```python
   import os
   import sys

   path = "/home/<you>/game-night"
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
   os.environ["DJANGO_DEBUG"] = "0"
   os.environ["DJANGO_ALLOWED_HOSTS"] = "<you>.pythonanywhere.com"
   os.environ["DJANGO_SECRET_KEY"] = "<paste the key from step 3>"

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

6. **First deploy.** In the Bash console:

   ```bash
   chmod +x ~/game-night/scripts/deploy.sh
   ~/game-night/scripts/deploy.sh
   ```

   Then click **Reload** on the Web tab and open `https://<you>.pythonanywhere.com`.

7. **Daily backups.** On the **Tasks** tab, add a daily scheduled task:

   ```
   /home/<you>/game-night/.venv/bin/python /home/<you>/game-night/scripts/backup_db.py
   ```

   It keeps the last 14 daily copies in `~/game-night/backups/`.

8. **Link from github.io.** Add a link or redirect on your github.io site pointing to `https://<you>.pythonanywhere.com`.

## Every update after that

```bash
~/game-night/scripts/deploy.sh
```

Then click **Reload** on the Web tab. The script backs up the database before migrating.

## Keeping the free app alive

Free web apps are switched off after 3 months unless you click **Run until 3 months from today** on the Web tab. PythonAnywhere emails you before that happens.

## If something breaks

The Web tab links to the **error log** and **server log**. Most first-deploy problems are a typo in the WSGI file or a missing `DJANGO_ALLOWED_HOSTS` value.
