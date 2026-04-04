# Peak Overwatch

Strategic oversight platform for TikTok affiliate operations.

## Project Structure

```text
peak-overwatch/
├── landing/            # Marketing site for peakoverwatch.com
└── dashboard/          # Flask prototype for app.peakoverwatch.com
```

## Current Dashboard Status

The dashboard repo went through several rapid prototype phases. The current
maintained runnable entrypoint is:

- `dashboard/phase4_simple.py`

That file currently contains the best working combination of:
- phase 1 UI direction
- phase 2 auth flow
- phase 3 settings/history flow
- phase 4 in-app alert prototype

Older milestone files that became stale or syntactically broken were reduced to
archive stubs so the repository stays honest and healthy.

## Deployment

### Landing Page
- Folder: `landing/`
- URL: `https://peakoverwatch.com`

### Dashboard
- Folder: `dashboard/`
- URL: `https://app.peakoverwatch.com`
- Procfile entry: `gunicorn phase4_simple:app`

## Local Development

```bash
cd dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 phase4_simple.py
```

Open:
- `http://localhost:5006`

Demo account:
- `demo@peakoverwatch.com`
- `password123`

## Important Reality Check

This dashboard is still a prototype. The app shell and flows are real, but much of
the metrics/alerting logic is still mock data until full TikTok API-backed data is
wired in.

## License

© 2026 Peak Medium / Revler Inc.
