# Peak Overwatch Dashboard

TikTok affiliate analytics platform with beautiful design and full authentication system.

## Features

### ✅ Phase 1: Dashboard Design
- Beautiful dark theme matching peakoverwatch.com
- Sidebar navigation with sections
- Interactive charts with cyan→red gradient
- Account performance tables
- Responsive design

### ✅ Phase 2: Authentication System
- User registration/login with bcrypt hashing
- Session management with secure cookies
- Protected routes (login required)
- Demo user: `demo@peakoverwatch.com` / `password123`
- Database schema ready for PostgreSQL

### ✅ Phase 3: Settings & Profile Management
- User settings page (timezone, currency, notifications)
- Profile management (update info, change password)
- Mock TikTok connection/disconnect system
- Data export (CSV, summary reports)
- FYP threshold configuration

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/basel-peakmedium/peak-overwatch.git
   cd peak-overwatch/dashboard
   ```

2. **Install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements-redesign.txt
   ```

3. **Run the application:**
   ```bash
   python3 app_simple_auth.py
   ```

4. **Access the dashboard:**
   - Open `http://localhost:5004`
   - Login with demo credentials or create new account

## File Structure

```
dashboard/
├── app_simple_auth.py          # Main application with authentication
├── app-final-redesign.py       # Final dashboard design (no auth)
├── phase3_complete.py          # Complete Phase 3 implementation
├── models.py                   # Database models
├── database_schema.sql         # PostgreSQL schema
├── database_setup.py           # Database setup script
├── requirements-redesign.txt   # Python dependencies
├── .env.example               # Environment variables template
├── Procfile-redesign          # Deployment configuration
└── runtime-redesign.txt       # Python runtime version
```

## Deployment

### Local Development
```bash
python3 app_simple_auth.py
```

### Production (Render)
1. Fork the repository
2. Create new Web Service on Render
3. Set build command: `pip install -r requirements-redesign.txt`
4. Set start command: `gunicorn app_simple_auth:app`
5. Add environment variables from `.env.example`

### Production (Vercel)
1. Deploy landing page to Vercel (`peakoverwatch.com`)
2. Deploy dashboard to Render (`app.peakoverwatch.com`)
3. Configure CORS and environment variables

## Environment Variables

Copy `.env.example` to `.env` and update:

```env
FLASK_ENV=production
SECRET_KEY=your-secret-key
DB_HOST=localhost
DB_PORT=5432
DB_NAME=peakoverwatch
DB_USER=postgres
DB_PASSWORD=your-password
```

## Database Setup (PostgreSQL)

1. Install PostgreSQL
2. Create database:
   ```bash
   python3 database_setup.py
   ```
3. Update `.env` with database credentials

## Features Roadmap

### Phase 4 (Next)
- Real TikTok API integration (when approved)
- Email notifications system
- Advanced analytics and reporting
- Team collaboration features

### Phase 5
- Mobile app (React Native)
- Real-time WebSocket updates
- Advanced alert system (Slack, Telegram)
- Payment integration (Stripe)

## Design Notes

- Color scheme: `#FF0050` (red), `#00F2EA` (cyan), `#0a0a0a` (dark)
- Font: Inter, system fonts fallback
- Charts: Chart.js with custom gradients
- Responsive: Mobile-first design

## License

© 2026 Peak Medium / Revler Inc. All rights reserved.