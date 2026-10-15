# Game Night Arranger

A small Django + HTMX app for a single board game night. Players list the games they're bringing and tick what they'd like to play. The event page ranks games by interest and shows who can run each one. Vote counts are shown, but voter names never are.

## Run locally (Windows)

```powershell
py -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py runserver
```

Open http://127.0.0.1:8000 and create an event.

## Test on a phone

With the server running, start a Cloudflare quick tunnel in a second terminal:

```powershell
cloudflared tunnel --url http://localhost:8000
```

It prints a `https://….trycloudflare.com` address you can open on any phone. Install `cloudflared` with `winget install Cloudflare.cloudflared`.

## Tests

```powershell
.\.venv\Scripts\python manage.py test events
```

## Deploy

See [DEPLOY.md](DEPLOY.md).
