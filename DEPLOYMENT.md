# Deployment

The app is a single FastAPI service (`backend/app.py`) that also serves the
static frontend — one deploy gives you one public HTTPS URL that works from
a phone, tablet, or desktop, same as any website.

It was **not** deployed to Vercel: Vercel's serverless functions have an
ephemeral filesystem, and this app writes to a SQLite file
(`backend/db.py`) and to disk for uploaded governance documents/survey
exports — none of that survives between requests on Vercel without also
swapping in an external database and object storage.

Two options are set up, both giving the app a persistent disk and a
long-running server so it runs basically unchanged:

| | Fly.io | Render |
|---|---|---|
| Cost | Free allowance (small always-on-ish VM + ~3GB volume) | Persistent disks need a **paid** plan |
| Setup | Docker build via `flyctl` CLI | Native Python buildpack via Blueprint (no Docker knowledge needed) |
| Config file | [`fly.toml`](fly.toml) + [`Dockerfile`](Dockerfile) | [`render.yaml`](render.yaml) |

If cost is the deciding factor, use Fly.io. If you'd rather not deal with
Docker/CLI at all and don't mind paying, Render's Blueprint flow is more
hands-off.

## Option A: Fly.io (free)

1. Install `flyctl`: https://fly.io/docs/flyctl/install/, then `fly auth login`
   (this asks for a credit card for identity verification — you won't be
   charged while staying within the free allowance).
2. From the repo root, create the app (pick a name if `mechatronics-academic-ms`
   is taken — edit the `app = "..."` line in [`fly.toml`](fly.toml) to match):
   ```
   fly apps create mechatronics-academic-ms
   ```
3. Create the persistent volume `fly.toml` mounts at `/data` (same region as
   `primary_region` in `fly.toml`, default `iad`):
   ```
   fly volumes create accreditation_data --region iad --size 1
   ```
4. Optional: set the Google Sheet default and any CORS origin before deploying:
   ```
   fly secrets set DEFAULT_INDICATORS_SHEET_URL="https://docs.google.com/spreadsheets/d/..."
   ```
5. Deploy:
   ```
   fly deploy
   ```
6. `fly open` (or visit `https://<your-app-name>.fly.dev`) once it's up.

`fly.toml` sets `min_machines_running = 0`, so the app scales to zero and
stops billing/using resources when idle, then cold-starts on the next
request — a good fit for a low-traffic accreditation tool and it keeps you
comfortably inside the free allowance.

## Option B: Render (paid, for persistent disks)

1. Push this repo to GitHub (or GitLab).
2. In Render: **New > Blueprint**, point it at the repo. Render reads
   [`render.yaml`](render.yaml) and creates the web service + a 1 GB
   persistent disk mounted at `/var/data`.
3. **Persistent disks require a paid Render plan** (`render.yaml` sets
   `plan: starter`) — Render's free tier doesn't support them. Without a
   disk, the SQLite database and uploaded documents would be wiped on
   every redeploy.
4. Set the `ALLOWED_ORIGINS` env var if you'll ever call the API from a
   different origin than the deployed site itself (same-origin page loads,
   which is how this app is normally used, don't need it — CORS only
   matters for cross-origin `fetch` calls).
5. Optional: set `DEFAULT_INDICATORS_SHEET_URL` to your team's Google
   Sheet link so the "Sync from Google Sheet" box on the indicators
   tracker is pre-filled for every visitor, not just whoever last typed it
   into their own browser.
6. Deploy. Render assigns a URL like `https://academic-analytics-accreditation.onrender.com`.

## What's on the persistent disk/volume

Both options point these at their persistent storage via env vars already
read by `backend/config.py`:

- `ACCREDITATION_DB_PATH` — the SQLite file backing indicators, curriculum
  mapping, governance, and faculty data.
- `EXPORTS_DIR` — uploaded governance documents and generated survey
  dashboard exports (PPTX/PNG/ZIP).

Both default to paths under `backend/` when unset (unchanged local-dev
behavior) — see `backend/config.py`.

## Google Sheet sync

The "Sync from Google Sheet" button on `indicators-tracker.html` needs no
server-side credentials — it reads the sheet's public XLSX export, so the
sheet must be shared as **"Anyone with the link can view."** See
`backend/sheets_sync.py` for the sync logic and `ARCHITECTURE.md` for the
matching rules.

## Local development is unaffected

Running `uvicorn app:app` from `backend/` with no env vars set behaves
exactly as before — none of the files above change behavior unless their
env vars are actually set.
