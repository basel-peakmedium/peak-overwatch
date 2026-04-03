# Peak Overwatch Dashboard

Production-ready TikTok affiliate analytics dashboard for deployment to `app.peakoverwatch.com`.

## Features
- Real-time FYP health monitoring
- Multi-account portfolio management
- Profit tracking (Commission % × GMV)
- Interactive charts with metric switching
- Dark mode professional design
- TikTok API integration ready

## Deployment

### Render.com (Recommended)
1. Connect GitHub repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `gunicorn app:app`
4. Add environment variable: `FLASK_ENV=production`

### Railway.app
1. Deploy from GitHub
2. Automatic Python detection
3. Add `PORT` environment variable

### Local Development
```bash
pip install -r requirements.txt
python app.py
```

## Environment Variables
- `FLASK_ENV`: Set to `production` for production
- `SECRET_KEY`: Flask secret key (generate with `python -c 'import secrets; print(secrets.token_hex(16))'`)
- `PORT`: Server port (default: 5000)

## Project Structure
```
peakoverwatch-dashboard/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── Procfile           # Process file for PaaS
├── runtime.txt        # Python version
└── README.md          # This file
```

## TikTok API Integration
This dashboard is designed to integrate with TikTok's official APIs:
- Login Kit for authentication
- Display API for data visualization
- Content Posting API (future)
- Analytics APIs for performance data

## License
© 2026 Peak Medium / Revler Inc