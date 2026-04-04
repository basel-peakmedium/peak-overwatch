# Peak Overwatch Dashboard

Current runnable dashboard prototype for `app.peakoverwatch.com`.

## Current source of truth

Use:
- `phase4_simple.py` — current app entrypoint

This file currently contains the most complete runnable prototype from phases 1-4:
- dashboard UI
- authentication
- settings
- alert history
- real-time in-app alert prototype

Older milestone files are still present only as archived stubs where needed to keep
repo history understandable and compile checks clean.

## Quick Start

```bash
cd dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 phase4_simple.py
```

Then open:
- `http://localhost:5006`

Demo login:
- `demo@peakoverwatch.com`
- `password123`

## Deployment

`Procfile` now points at:
- `gunicorn phase4_simple:app`

Recommended env vars:

```env
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=replace-me
PORT=5000
SESSION_COOKIE_SECURE=true
CORS_ALLOWED_ORIGINS=https://app.peakoverwatch.com
```

## Notes

- Current analytics and alerting data are still mock/demo data.
- Real TikTok-backed analytics should be layered in after app approval / API access.
- For now, prioritize code clarity and a single maintained app path over more prototype forks.
