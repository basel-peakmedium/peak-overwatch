# Peak Overwatch Dashboard

Current maintained dashboard app for `app.peakoverwatch.com`.

## Current source of truth

Use:
- `app_production_final.py` — maintained app entrypoint

This is the best current runnable path in the repo and now serves as the single
maintained app file for active development.

It currently includes:
- dashboard UI
- authentication
- health check endpoint
- real-time alert prototype
- production-oriented cookie/session config

Older milestone files and broken prototype forks are being kept only as archived
stubs so the repository stays understandable without pretending they are healthy.

## Quick Start

```bash
cd dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app_production_final.py
```

Then open:
- `http://localhost:5008`

Demo login:
- `demo@peakoverwatch.com`
- `password123`

## Deployment

`Procfile` now points at:
- `gunicorn app_production_final:app`

Recommended env vars:

```env
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=replace-me
PORT=5008
SESSION_COOKIE_SECURE=true
CORS_ALLOWED_ORIGINS=https://app.peakoverwatch.com
```

## Notes

- Current analytics and alerting data are still mock/demo data.
- Real TikTok-backed analytics should be layered in after app approval / API access.
- The repo previously accumulated too many copied app variants; this file is now the
  one maintained path.
