# Peak Overwatch

Strategic oversight platform for TikTok affiliate operations. Provides eagle-eye view of performance metrics, FYP health monitoring, and optimization tools for TikTok Shop affiliates.

## Project Structure

```
peak-overwatch/
├── landing/           # Landing page for peakoverwatch.com
│   ├── index.html    # Main landing page
│   ├── terms.html    # Terms of Service
│   ├── privacy.html  # Privacy Policy
│   └── vercel.json   # Vercel deployment config
├── dashboard/         # Dashboard app for app.peakoverwatch.com
│   ├── app.py        # Flask application
│   ├── requirements.txt
│   ├── Procfile
│   ├── runtime.txt
│   └── README.md
└── README.md          # This file
```

## Deployment

### Landing Page (peakoverwatch.com)
**Platform:** Vercel
**Folder:** `landing/`
**URL:** https://peakoverwatch.com

### Dashboard (app.peakoverwatch.com)
**Platform:** Render/Railway
**Folder:** `dashboard/`
**URL:** https://app.peakoverwatch.com

## TikTok Developer Portal Application

**App Name:** Peak Overwatch
**Status:** Draft/Production
**URL:** developers.tiktok.com/app/7624568636699412496/pending

## Features

### Landing Page
- Professional design with dark mode
- Mobile-responsive layout
- Terms of Service and Privacy Policy
- TikTok integration messaging

### Dashboard
- FYP health monitoring with color-coded alerts
- Profit tracking (Commission % × GMV)
- Multi-account portfolio management
- Interactive charts with metric switching
- TikTok API integration ready

## Setup

### Local Development
```bash
# Landing page
cd landing
# Open index.html in browser

# Dashboard
cd dashboard
pip install -r requirements.txt
python app.py
```

### Production Deployment
See individual README files in `landing/` and `dashboard/` folders.

## Environment Variables

### Dashboard
```
FLASK_ENV=production
SECRET_KEY=[generate with: python -c 'import secrets; print(secrets.token_hex(16))']
PORT=5000
```

## TikTok API Integration
- Login Kit for authentication
- Display API for data visualization
- Content Posting API (future)
- Analytics APIs for performance data

## License
© 2026 Peak Medium / Revler Inc