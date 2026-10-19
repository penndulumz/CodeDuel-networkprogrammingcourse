# Cloud Deployment — Render or Railway

> **Audience**: Tournament administrators hosting the arena on the public Internet.

The platform keeps its state on local disk: the SQLite database (`app.db`), uploaded
bots (`bots/`) and match replays (`replays/`). All three live under the directory named
by the `DATA_DIR` environment variable (default: the working directory). In the cloud,
`DATA_DIR` must point at a **persistent volume**, otherwise every redeploy wipes users,
bots and matches.

Serverless hosts such as Vercel are not supported: their file system is read-only and
short-lived, and background grading/match threads are killed after each request.

The repository ships a `Dockerfile` (sets `DATA_DIR=/data`), `render.yaml` and
`railway.json`. Run **exactly one instance** — SQLite and the in-process match queue
are not shared between replicas.

## Environment variables

| Variable | Value | Notes |
| --- | --- | --- |
| `DATA_DIR` | `/data` | Already set in the Dockerfile; mount the volume here. |
| `ADMIN_USERNAME` | `admin` | Single administrator account. |
| `ADMIN_PASSWORD` | *(secret)* | **Change it** — the default `admin123` is public. |
| `PUBLIC_URL` | `https://<your-app>.onrender.com` | Shown to players as the shareable link. |
| `ALLOWED_ORIGINS` | same as `PUBLIC_URL` | CORS allow-list (comma separated). |
| `COOKIE_SECURE` | `true` | Both hosts serve HTTPS. |
| `PORT` | *(injected by host)* | `main.py` reads it automatically. |

## Render

1. Push this branch to GitHub.
2. Render dashboard → **New → Blueprint** → pick the repository. Render reads
   `render.yaml` and creates the `codeduel` web service with a 1 GB disk at `/data`.
3. Fill in the secret values it prompts for (`ADMIN_PASSWORD`, `PUBLIC_URL`,
   `ALLOWED_ORIGINS`). You can set `PUBLIC_URL` after the first deploy once the
   `*.onrender.com` address is known, then redeploy.

Persistent disks require a paid instance (the blueprint uses `starter`). On the free
plan the service still runs, but data resets on every deploy or restart.

## Railway

1. Railway dashboard → **New Project → Deploy from GitHub repo** → pick the repository.
   Railway builds with the `Dockerfile` (configured in `railway.json`).
2. Service → **Settings → Volumes → Add Volume**, mount path `/data`.
3. Service → **Variables**: add the variables from the table above.
4. Service → **Settings → Networking → Generate Domain**, then set `PUBLIC_URL` and
   `ALLOWED_ORIGINS` to that domain and redeploy.

## Verifying

- Open the public URL and log in as the admin with the new password.
- Upload a bot, play a match, then trigger a redeploy: the account, bot and replay must
  still be there. If they are gone, the volume is not mounted at `DATA_DIR`.

## Local Docker run

```bash
docker build -t codeduel .
docker run -p 8000:8000 -v codeduel-data:/data -e ADMIN_PASSWORD=change-me codeduel
```
