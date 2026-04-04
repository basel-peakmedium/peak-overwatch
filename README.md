# Peak Overwatch

Strategic oversight platform for TikTok affiliate operations.

## Project Structure

```text
peak-overwatch/
├── landing/            # Marketing site for peakoverwatch.com
└── dashboard/          # Flask prototype for app.peakoverwatch.com
```

## Current Dashboard Status

The repo went through a lot of rapid prototype branching. The single maintained
runnable dashboard entrypoint is now:

- `dashboard/app_production_final.py`

That file is the best current working combination of:
- upgraded dashboard UI
- auth flow
- health check / production-oriented app shell
- real-time in-app alerts

Older milestone files and broken prototype forks are retained only as archived
stubs where useful for history, not as active app paths.

## Deployment

### Landing Page
- Folder: `landing/`
- URL: `https://peakoverwatch.com`

### Dashboard
- Folder: `dashboard/`
- URL: `https://app.peakoverwatch.com`
- Procfile entry: `gunicorn app_production_final:app`

## Local Development

```bash
cd dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app_production_final.py
```

Open:
- `http://localhost:5008`

Demo account:
- `demo@peakoverwatch.com`
- `password123`

## Important Reality Check

This is still a prototype. The app shell and monitoring UX are real, but much of
the metrics/alerting logic is still mock data until full TikTok API-backed data is
wired in.

## License

© 2026 Peak Medium / Revler Inc.
