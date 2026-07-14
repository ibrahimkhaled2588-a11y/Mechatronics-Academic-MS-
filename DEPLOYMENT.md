# Deployment (Render)

The app is a single FastAPI service (`backend/app.py`) that also serves the
static frontend — one deploy gives you one public HTTPS URL that works from
a phone, tablet, or desktop, same as any website.

It was **not** deployed to Vercel: Vercel's serverless functions have an
ephemeral filesystem, and this app writes to a SQLite file
(`backend/db.py`) and to disk for uploaded governance documents/survey
exports — none of that survives between requests on Vercel without also
swapping in an external database and object storage. Render (or Railway,
which works the same way) gives a persistent disk and a long-running
server, so the app runs basically unchanged.

## Deploy via the Render Blueprint

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

## What's on the persistent disk

`render.yaml` points these at `/var/data` via env vars already read by
`backend/config.py`:

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
exactly as before — `render.yaml` only changes behavior when those env
vars are actually set.
