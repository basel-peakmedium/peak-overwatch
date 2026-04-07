#!/usr/bin/env python3
"""
Peak Overwatch - Rebuild v1.1
Red theme, gradient charts, per-account analytics, decision metrics
"""

from flask import Flask, redirect, request, jsonify, make_response
import os
import json
from datetime import datetime, timedelta
import random
import bcrypt
import secrets
import logging
from threading import Thread, Lock
import time
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
SESSION_LIFETIME = timedelta(days=7)

users = {}
sessions = {}
alerts_store = {}
lock = Lock()

# ---------------------------------------------------------------------------
# Mock account data (spec v1.1)
# ---------------------------------------------------------------------------
MOCK_ACCOUNTS = [
    {
        'handle': '@trendvault_us',
        'name': 'Trend Vault US',
        'color': '#FF3B3B',
        'color_rgb': '255,59,59',
        'gmv': 22600,
        'commission': 13.2,
        'videos': 847,
        'views': 2100000,
        'views_last_month': 1800000,
        'mom_pct': 16.7,
        'earnings': 2983,
        'status': 'Active',
        'fyp_score': 94,
    },
    {
        'handle': '@pickoftheday_co',
        'name': 'Pick of the Day',
        'color': '#A855F7',
        'color_rgb': '168,85,247',
        'gmv': 4200,
        'commission': 11.8,
        'videos': 312,
        'views': 480000,
        'views_last_month': 390000,
        'mom_pct': 23.1,
        'earnings': 496,
        'status': 'Active',
        'fyp_score': 81,
    },
    {
        'handle': '@dailyfinds_hub',
        'name': 'Daily Finds Hub',
        'color': '#F59E0B',
        'color_rgb': '245,158,11',
        'gmv': 890,
        'commission': 14.5,
        'videos': 89,
        'views': 95000,
        'views_last_month': 110000,
        'mom_pct': -13.6,
        'earnings': 129,
        'status': 'Warning',
        'fyp_score': 67,
    },
]

MOCK_PRODUCTS = [
    {'name': 'Portable Blender Pro', 'account': '@trendvault_us', 'color': '#FF3B3B', 'units': 234, 'gmv': 3200, 'commission': 13.2},
    {'name': 'LED Desk Lamp', 'account': '@trendvault_us', 'color': '#FF3B3B', 'units': 189, 'gmv': 2800, 'commission': 13.2},
    {'name': 'Resistance Bands Set', 'account': '@pickoftheday_co', 'color': '#A855F7', 'units': 156, 'gmv': 1900, 'commission': 11.8},
    {'name': 'Ceramic Mug Warmer', 'account': '@trendvault_us', 'color': '#FF3B3B', 'units': 143, 'gmv': 1600, 'commission': 13.2},
    {'name': 'Foam Roller', 'account': '@pickoftheday_co', 'color': '#A855F7', 'units': 98, 'gmv': 890, 'commission': 11.8},
]

MOCK_VIRAL_VIDEOS = [
    {'title': 'Blender that changes everything', 'account': '@trendvault_us', 'color': '#FF3B3B', 'total_views': 350000, 'views_this_month': 287000, 'date': '2026-03-08', 'days_old': 30},
    {'title': 'You need this lamp', 'account': '@trendvault_us', 'color': '#FF3B3B', 'total_views': 190000, 'views_this_month': 143000, 'date': '2026-03-14', 'days_old': 24},
    {'title': 'Best desk setup under $50', 'account': '@trendvault_us', 'color': '#FF3B3B', 'total_views': 120000, 'views_this_month': 89000, 'date': '2026-03-20', 'days_old': 18},
    {'title': 'These bands are insane', 'account': '@pickoftheday_co', 'color': '#A855F7', 'total_views': 90000, 'views_this_month': 67000, 'date': '2026-03-22', 'days_old': 16},
]

REVENUE_SOURCES = {
    '@trendvault_us':    {'Videos': 74, 'Shop Ads': 22, 'LIVE': 3,  'Other': 1},
    '@pickoftheday_co':  {'Videos': 81, 'Shop Ads': 15, 'LIVE': 4,  'Other': 0},
    '@dailyfinds_hub':   {'Videos': 91, 'Shop Ads': 9,  'LIVE': 0,  'Other': 0},
}

DECISION_METRICS = [
    {
        'handle': '@trendvault_us',
        'color': '#FF3B3B',
        'avg_views_video': 2480,
        'mom_views_pct': 16.7,
        'avg_daily_posts': 28.2,
        'commission_per_1k_views': 1.42,
        'gmv_per_video': 26.7,
        'viral_rate': 0.35,
    },
    {
        'handle': '@pickoftheday_co',
        'color': '#A855F7',
        'avg_views_video': 1538,
        'mom_views_pct': 23.1,
        'avg_daily_posts': 10.4,
        'commission_per_1k_views': 1.03,
        'gmv_per_video': 13.5,
        'viral_rate': 0.32,
    },
    {
        'handle': '@dailyfinds_hub',
        'color': '#F59E0B',
        'avg_views_video': 1067,
        'mom_views_pct': -13.6,
        'avg_daily_posts': 3.0,
        'commission_per_1k_views': 1.36,
        'gmv_per_video': 10.0,
        'viral_rate': 0.0,
    },
]


def fmt_views(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


def generate_gmv_series(days=30):
    base = datetime.now() - timedelta(days=days)
    targets = [753, 140, 30]
    series = []
    rng = random.Random(42)
    for i in range(days):
        d = base + timedelta(days=i)
        ramp = 0.7 + 0.3 * (i / days)
        row = {'date': d.strftime('%m/%d')}
        total = 0
        for j, (acc, tgt) in enumerate(zip(MOCK_ACCOUNTS, targets)):
            val = int(tgt * ramp + rng.randint(-int(tgt * 0.2), int(tgt * 0.2)))
            val = max(0, val)
            row[acc['handle']] = val
            total += val
        row['total'] = total
        series.append(row)
    return series


def generate_monthly_bar_data():
    months = ['Jan', 'Feb', 'Mar']
    rng = random.Random(7)
    data = {}
    for acc in MOCK_ACCOUNTS:
        data[acc['handle']] = [
            int(acc['views'] * rng.uniform(0.6, 0.85)),
            int(acc['views'] * rng.uniform(0.75, 0.95)),
            acc['views'],
        ]
    return months, data


def generate_monthly_video_data():
    months = ['Jan', 'Feb', 'Mar']
    rng = random.Random(13)
    data = {}
    for acc in MOCK_ACCOUNTS:
        data[acc['handle']] = [
            int(acc['videos'] * rng.uniform(0.6, 0.85)),
            int(acc['videos'] * rng.uniform(0.75, 0.95)),
            acc['videos'],
        ]
    return months, data


def generate_sparkline(handle, days=7):
    rng = random.Random(hash(handle) % 1000)
    tgt = {'@trendvault_us': 753, '@pickoftheday_co': 140, '@dailyfinds_hub': 30}.get(handle, 100)
    return [max(0, int(tgt * rng.uniform(0.6, 1.4))) for _ in range(days)]


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User:
    def __init__(self, user_id, email, password_hash, name=None, company=None):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash
        self.name = name
        self.company = company
        self.settings = {
            'fyp_threshold_good': 80,
            'fyp_threshold_warn': 70,
            'fyp_threshold_critical': 60,
            'notification_email': email,
            'alert_email': True,
            'alert_critical': True,
            'alert_warning': True,
            'alert_info': False,
            'commission_trendvault_us': 13.2,
            'commission_pickoftheday_co': 11.8,
            'commission_dailyfinds_hub': 14.5,
        }

    def verify_password(self, password):
        if self.email == 'demo@peakoverwatch.com' and password == 'password123':
            return True
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def add_alert(self, title, message, level='info'):
        alert_id = secrets.token_urlsafe(8)
        alert = {
            'id': alert_id,
            'title': title,
            'message': message,
            'level': level,
            'created_at': datetime.now().isoformat(),
            'is_read': False,
        }
        with lock:
            if self.id not in alerts_store:
                alerts_store[self.id] = []
            alerts_store[self.id].append(alert)
        return alert

    def get_unread_alerts(self):
        return [a for a in alerts_store.get(self.id, []) if not a['is_read']]

    def mark_alert_read(self, alert_id):
        with lock:
            for alert in alerts_store.get(self.id, []):
                if alert['id'] == alert_id:
                    alert['is_read'] = True
                    return True
        return False

    def get_commission(self, handle):
        key = 'commission_' + handle.lstrip('@').replace('.', '_')
        return self.settings.get(key, 13.2)


demo_hash = '$2b$06$8y4VDcAyr491m32cEzVB7./dwMSQ4AzmDqKxjYACf1AjWWH4PMCYa'
users['demo@peakoverwatch.com'] = User(1, 'demo@peakoverwatch.com', demo_hash, 'Demo User', 'Peak Medium')


# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------
class Monitor:
    def start(self):
        Thread(target=self._monitor_loop, daemon=True).start()

    def _monitor_loop(self):
        while True:
            try:
                for user in list(users.values()):
                    s = user.settings
                    warn = s.get('fyp_threshold_warn', 70)
                    for acc in MOCK_ACCOUNTS:
                        if acc['fyp_score'] < warn:
                            user.add_alert(
                                f'FYP Warning: {acc["handle"]}',
                                f'FYP score at {acc["fyp_score"]}% — below warning threshold',
                                'warning'
                            )
                time.sleep(3600)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(60)


monitor = Monitor()
monitor.start()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('session_token')
        session = sessions.get(token) if token else None
        if not token or not session:
            return redirect('/login')
        if session['expires'] < datetime.now():
            del sessions[token]
            resp = make_response(redirect('/login'))
            resp.delete_cookie('session_token')
            return resp
        user_id = session['user_id']
        user = next((u for u in users.values() if u.id == user_id), None)
        if not user:
            resp = make_response(redirect('/login'))
            resp.delete_cookie('session_token')
            return resp
        request.user = user
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Shared CSS / JS
# ---------------------------------------------------------------------------
COMMON_CSS = '''
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
    --bg: #0A0A0F;
    --surface: #111118;
    --surface2: #18181f;
    --border: rgba(255,255,255,0.07);
    --text: #e8eaed;
    --muted: #7a8090;
    --accent: #FF3B3B;
    --accent2: #E53E3E;
    --purple: #A855F7;
    --amber: #F59E0B;
    --total-line: #F0F0F0;
    --success: #10b981;
    --warning: #f59e0b;
    --critical: #ef4444;
    --info: #60a5fa;
}
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: var(--bg);
    color: var(--text);
    opacity: 0;
    transform: translateY(20px);
    animation: pageLoad 0.4s ease forwards;
}
@keyframes pageLoad {
    to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes staggerIn {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes countFlash {
    0%   { color: var(--accent); }
    100% { color: var(--text); }
}

/* Sidebar */
.sidebar {
    position: fixed; top: 0; left: 0; bottom: 0; width: 240px;
    background: var(--surface); border-right: 1px solid var(--border);
    display: flex; flex-direction: column; z-index: 100; overflow-y: auto;
}
.sidebar-header { padding: 1.5rem 1.25rem; border-bottom: 1px solid var(--border); }
.logo {
    display: flex; align-items: center; gap: 0.6rem;
    font-size: 1.1rem; font-weight: 800; letter-spacing: -0.02em;
    color: #fff; text-decoration: none;
}
.logo-mark {
    width: 28px; height: 28px; border-radius: 7px;
    background: linear-gradient(135deg, #FF3B3B, #E53E3E);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.85rem; font-weight: 900; color: #fff; flex-shrink: 0;
    box-shadow: 0 4px 12px rgba(255,59,59,0.4);
}
.logo-text span { color: var(--accent); }
.sidebar-nav { flex: 1; padding: 1rem 0.75rem; }
.nav-item {
    display: flex; align-items: center; gap: 0.7rem;
    padding: 0.65rem 0.85rem; color: var(--muted);
    text-decoration: none; border-radius: 8px; margin-bottom: 2px;
    font-size: 0.9rem; font-weight: 500;
    transition: background 0.15s, color 0.15s;
    position: relative;
}
.nav-item:hover { background: rgba(255,255,255,0.05); color: var(--text); }
.nav-item.active {
    background: rgba(255,59,59,0.1);
    color: var(--accent);
}
.nav-item.active::before {
    content: '';
    position: absolute; left: 0; top: 20%; bottom: 20%;
    width: 3px; border-radius: 0 3px 3px 0;
    background: var(--accent);
}
.nav-icon { width: 18px; text-align: center; font-size: 0.95rem; }
.notif-badge {
    background: var(--accent); color: #fff; border-radius: 10px;
    padding: 1px 6px; font-size: 0.7rem; font-weight: 700;
    margin-left: auto; min-width: 18px; text-align: center;
}
.sidebar-footer {
    padding: 1rem 1.25rem; border-top: 1px solid var(--border); font-size: 0.85rem;
}
.sidebar-footer .user-name { color: var(--text); font-weight: 600; margin-bottom: 0.25rem; }
.sidebar-footer a { color: var(--muted); text-decoration: none; font-size: 0.8rem; }
.sidebar-footer a:hover { color: var(--text); }

/* Main */
.main { margin-left: 240px; padding: 2rem 2.5rem; min-height: 100vh; }
.page-title { font-size: 1.75rem; font-weight: 800; color: var(--text); margin-bottom: 0.25rem; }
.page-sub { color: var(--muted); font-size: 0.95rem; }
.page-header { margin-bottom: 2rem; }

/* Cards */
.card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 1.5rem;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.card:hover { transform: translateY(-4px); box-shadow: 0 12px 40px rgba(255,59,59,0.15); }

/* Metric cards with stagger */
.metric-cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 1.25rem; margin-bottom: 2rem; }
.metric-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 1.5rem;
    opacity: 0;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    animation: fadeInUp 0.4s ease forwards;
}
.metric-card:hover { transform: translateY(-4px); box-shadow: 0 12px 40px rgba(255,59,59,0.15); }
.metric-card:nth-child(1) { animation-delay: 0ms; }
.metric-card:nth-child(2) { animation-delay: 80ms; }
.metric-card:nth-child(3) { animation-delay: 160ms; }
.metric-card:nth-child(4) { animation-delay: 240ms; }
.metric-card:nth-child(5) { animation-delay: 320ms; }
.metric-label { color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.5rem; }
.metric-value {
    font-size: 2.1rem; font-weight: 800; color: var(--text); line-height: 1;
    font-variant-numeric: tabular-nums;
}
.metric-sub { color: var(--muted); font-size: 0.8rem; margin-top: 0.4rem; }
.metric-pos { color: var(--success); }
.metric-neg { color: var(--critical); }

/* Panels */
.panel {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 1.5rem; margin-bottom: 1.5rem;
}
.panel-title { font-size: 1rem; font-weight: 700; color: var(--text); margin-bottom: 1.25rem; }
.section-label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 0.75rem; }

/* Chart toggles */
.chart-toggles { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem; }
.toggle-btn {
    display: inline-flex; align-items: center; gap: 0.4rem;
    padding: 0.35rem 0.85rem; border-radius: 20px; font-size: 0.8rem;
    font-weight: 600; cursor: pointer; border: 1.5px solid transparent;
    transition: opacity 0.2s, transform 0.15s;
    background: rgba(255,255,255,0.05);
}
.toggle-btn:hover { transform: scale(1.04); }
.toggle-btn.off { opacity: 0.3; }
.toggle-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.chart-wrap { position: relative; height: 300px; }

/* Tables */
.data-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.data-table th {
    text-align: left; padding: 0.6rem 0.85rem;
    color: var(--muted); font-size: 0.75rem; text-transform: uppercase;
    letter-spacing: 0.06em; border-bottom: 1px solid var(--border);
}
.data-table td { padding: 0.85rem; border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: middle; }
.data-table tr:last-child td { border-bottom: none; }
.data-table tbody tr {
    opacity: 0;
    animation: staggerIn 0.35s ease forwards;
    transition: background 0.15s;
}
.data-table tbody tr:hover { background: rgba(255,255,255,0.03); }

/* Account dot */
.acc-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.acc-cell { display: flex; align-items: center; gap: 0.5rem; }

/* Badges */
.badge {
    display: inline-block; padding: 0.2rem 0.6rem; border-radius: 20px;
    font-size: 0.75rem; font-weight: 700; letter-spacing: 0.02em;
}
.badge-active  { background: rgba(16,185,129,0.15);  color: #10b981; }
.badge-warning { background: rgba(245,158,11,0.15);  color: #f59e0b; }
.badge-critical{ background: rgba(239,68,68,0.15);   color: #ef4444; }
.badge-info    { background: rgba(96,165,250,0.15);  color: var(--info); }
.badge-good    { background: rgba(16,185,129,0.15);  color: #10b981; }
.badge-warn    { background: rgba(245,158,11,0.15);  color: #f59e0b; }
.badge-crit    { background: rgba(239,68,68,0.15);   color: #ef4444; }
.badge-fyp     { background: rgba(255,59,59,0.15);   color: var(--accent); font-size: 0.7rem; }

/* Buttons */
.btn {
    display: inline-flex; align-items: center; gap: 0.4rem;
    padding: 0.55rem 1.1rem; border-radius: 8px; font-size: 0.875rem;
    font-weight: 600; cursor: pointer; border: none; text-decoration: none;
    transition: background 0.15s, transform 0.15s;
}
.btn:hover { transform: scale(1.02); }
.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover { background: var(--accent2); box-shadow: 0 4px 16px rgba(255,59,59,0.4); }
.btn-outline {
    background: transparent; color: var(--muted);
    border: 1px solid var(--border);
}
.btn-outline:hover { color: var(--text); border-color: rgba(255,255,255,0.2); }

/* KPI card */
.kpi-card {
    background: rgba(255,59,59,0.06);
    border: 1px solid rgba(255,59,59,0.2); border-radius: 14px;
    padding: 1.25rem 1.5rem; display: inline-flex; align-items: center; gap: 1rem;
}
.kpi-number { font-size: 2.5rem; font-weight: 800; color: var(--accent); line-height: 1; }
.kpi-label { font-size: 0.9rem; color: var(--muted); }

/* Two/three col layout */
.two-col   { display: grid; grid-template-columns: 1fr 1fr;       gap: 1.5rem; }
.three-col { display: grid; grid-template-columns: 1fr 1fr 1fr;   gap: 1.5rem; }

/* Account cards (page 2) */
.account-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
.account-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; overflow: hidden;
    opacity: 0;
    animation: fadeInUp 0.4s ease forwards;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.account-card:hover { transform: translateY(-4px); }
.account-card:nth-child(1) { animation-delay: 0ms; }
.account-card:nth-child(2) { animation-delay: 80ms; }
.account-card:nth-child(3) { animation-delay: 160ms; }
.acc-card-bar { height: 4px; width: 100%; }
.acc-card-body { padding: 1.25rem 1.5rem; }
.acc-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.acc-card-handle { font-size: 1rem; font-weight: 700; }
.acc-card-gmv { font-size: 2rem; font-weight: 800; margin-bottom: 0.25rem; }
.acc-card-earnings { color: var(--muted); font-size: 0.85rem; margin-bottom: 1rem; }
.acc-card-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1rem; }
.acc-card-stat { }
.acc-card-stat-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin-bottom: 0.2rem; }
.acc-card-stat-val { font-size: 0.95rem; font-weight: 600; }
.acc-card-mom { display: flex; align-items: center; gap: 0.4rem; font-size: 0.9rem; font-weight: 700; }
.acc-card-footer { display: flex; justify-content: space-between; align-items: center; padding-top: 0.85rem; border-top: 1px solid var(--border); }
.sparkline-wrap { position: relative; height: 40px; width: 80px; }

/* Filter pills (analytics) */
.acc-filter { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.acc-filter-btn {
    padding: 0.4rem 1rem; border-radius: 20px; font-size: 0.82rem; font-weight: 600;
    cursor: pointer; border: 1.5px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.06); color: var(--muted);
    transition: all 0.2s ease;
}
.acc-filter-btn:hover { border-color: rgba(255,255,255,0.25); color: var(--text); }
.acc-filter-btn.active { color: #fff; border-color: transparent; }
.acc-filter-btn.active.pill-all    { background: rgba(255,255,255,0.9); color: #111; }
.acc-filter-btn.active.pill-tv     { background: #FF3B3B; }
.acc-filter-btn.active.pill-po     { background: #A855F7; }
.acc-filter-btn.active.pill-dh     { background: #F59E0B; color: #111; }

/* Donut cards */
.donut-cards-row { display: flex; gap: 1.5rem; flex-wrap: wrap; }
.donut-card {
    flex: 1; min-width: 200px; max-width: 280px;
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 14px; padding: 1.25rem; text-align: center;
    transition: all 0.2s;
}
.donut-card.single-mode { max-width: 360px; flex: 0 0 360px; }
.donut-legend { text-align: left; margin-top: 1rem; }
.donut-legend-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; margin-bottom: 0.4rem; }
.donut-legend-swatch { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }

/* Decision metrics table */
.dm-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
.dm-table th {
    text-align: left; padding: 0.6rem 0.85rem;
    color: var(--muted); font-size: 0.72rem; text-transform: uppercase;
    letter-spacing: 0.06em; border-bottom: 1px solid var(--border);
}
.dm-table td { padding: 0.85rem; border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: middle; }
.dm-table tr:last-child td { border-bottom: none; }
.dm-flag-green  { color: #10b981; font-weight: 600; }
.dm-flag-yellow { color: #f59e0b; font-weight: 600; }
.dm-flag-red    { color: #ef4444; font-weight: 600; }

/* Alert items */
.alert-row {
    background: rgba(255,255,255,0.02); border: 1px solid var(--border);
    border-left: 3px solid var(--muted); border-radius: 10px;
    padding: 1rem 1.25rem; margin-bottom: 0.75rem;
    opacity: 0;
    animation: staggerIn 0.35s ease forwards;
}
.alert-row.critical { border-left-color: var(--critical); }
.alert-row.warning  { border-left-color: var(--warning); }
.alert-row.info     { border-left-color: var(--info); }
.alert-row.read     { opacity: 0.4; }

/* Form */
.form-group { margin-bottom: 1.25rem; }
.form-label { display: block; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-bottom: 0.5rem; }
.form-input {
    width: 100%; padding: 0.65rem 0.85rem;
    background: rgba(255,255,255,0.04); border: 1px solid var(--border);
    border-radius: 8px; color: var(--text); font-size: 0.9rem; transition: border-color 0.2s;
}
.form-input:focus { outline: none; border-color: var(--accent); }
.form-input[type=number] { -moz-appearance: textfield; }
.form-input[type=number]::-webkit-inner-spin-button { opacity: 0.3; }
.checkbox-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.4rem 0; cursor: pointer; }
input[type=checkbox] { width: 15px; height: 15px; accent-color: var(--accent); }
.slider-row { display: flex; align-items: center; gap: 1rem; }
.slider-val { font-weight: 700; color: var(--accent); min-width: 3rem; text-align: right; }
input[type=range] { flex: 1; -webkit-appearance: none; height: 5px; border-radius: 3px; background: rgba(255,255,255,0.1); cursor: pointer; }
input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 16px; height: 16px; border-radius: 50%; background: var(--accent); }

/* Responsive */
@media (max-width: 1100px) {
    .metric-cards { grid-template-columns: repeat(2, 1fr); }
    .two-col, .three-col { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
    .sidebar { display: none; }
    .main { margin-left: 0; padding: 1rem; }
    .metric-cards { grid-template-columns: 1fr 1fr; }
}
'''

COUNTER_JS = '''
function animateCounter(el, target, prefix, suffix, duration) {
    prefix = prefix || '';
    suffix = suffix || '';
    duration = duration || 1200;
    const startTime = performance.now();
    const isFloat = (target % 1 !== 0);
    function easeOutQuart(t) { return 1 - Math.pow(1 - t, 4); }
    function step(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = easeOutQuart(progress);
        const current = target * eased;
        if (isFloat) {
            el.textContent = prefix + current.toFixed(1) + suffix;
        } else {
            el.textContent = prefix + Math.round(current).toLocaleString() + suffix;
        }
        if (progress < 1) requestAnimationFrame(step);
        else el.textContent = prefix + (isFloat ? target.toFixed(1) : target.toLocaleString()) + suffix;
    }
    requestAnimationFrame(step);
}
function initCounters() {
    document.querySelectorAll('[data-counter]').forEach(function(el) {
        const target = parseFloat(el.dataset.counter);
        const prefix = el.dataset.prefix || '';
        const suffix = el.dataset.suffix || '';
        const duration = parseInt(el.dataset.duration || '1200');
        animateCounter(el, target, prefix, suffix, duration);
    });
}
document.addEventListener('DOMContentLoaded', initCounters);
'''

CHART_DEFAULTS = '''
Chart.defaults.color = '#7a8090';
Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
'''

TABLE_STAGGER_JS = '''
document.querySelectorAll('.data-table tbody tr').forEach(function(tr, i) {
    tr.style.animationDelay = (i * 50) + 'ms';
});
document.querySelectorAll('.alert-row').forEach(function(el, i) {
    el.style.animationDelay = (i * 50) + 'ms';
});
'''


def sidebar_html(active_page, user, unread_count=0):
    pages = [
        ('dashboard', '/dashboard', '⊞', 'Dashboard'),
        ('accounts',  '/accounts',  '◈', 'Accounts'),
        ('analytics', '/analytics', '▦', 'Analytics'),
        ('alerts',    '/alerts',    '◎', 'Alerts'),
        ('team',      '/team',      '◑', 'Team'),
        ('settings',  '/settings',  '⚙', 'Settings'),
    ]
    links = ''
    for key, href, icon, label in pages:
        active_cls = ' active' if key == active_page else ''
        badge = ''
        if key == 'alerts' and unread_count > 0:
            badge = f'<span class="notif-badge">{unread_count}</span>'
        links += f'<a href="{href}" class="nav-item{active_cls}"><span class="nav-icon">{icon}</span><span>{label}</span>{badge}</a>\n'
    name = user.name or user.email
    return f'''
    <aside class="sidebar">
        <div class="sidebar-header">
            <a class="logo" href="/dashboard">
                <div class="logo-mark">P</div>
                <div class="logo-text">Peak<span>Overwatch</span></div>
            </a>
        </div>
        <nav class="sidebar-nav">{links}</nav>
        <div class="sidebar-footer">
            <div class="user-name">{name}</div>
            <a href="/logout">Sign Out</a>
        </div>
    </aside>'''


def page_shell(title, active_page, user, unread_count, body_html, extra_css='', extra_js='', load_chartjs=False):
    chartjs_tag = '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>' if load_chartjs else ''
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Peak Overwatch \u2022 {title}</title>
    {chartjs_tag}
    <style>{COMMON_CSS}{extra_css}</style>
</head>
<body>
    {sidebar_html(active_page, user, unread_count)}
    <main class="main">
        {body_html}
    </main>
    <script>
        {COUNTER_JS}
        {TABLE_STAGGER_JS}
        {CHART_DEFAULTS if load_chartjs else ''}
        {extra_js}
    </script>
</body>
</html>'''


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    token = request.cookies.get('session_token')
    if token and token in sessions:
        return redirect('/dashboard')
    return redirect('/login')


@app.route('/login')
def login():
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Peak Overwatch \u2014 Sign In</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #0A0A0F; color: #e8eaed;
            display: flex; align-items: center; justify-content: center;
            min-height: 100vh;
            opacity: 0; animation: f 0.4s ease forwards;
        }
        @keyframes f { to { opacity: 1; } }
        .box {
            background: #111118; border: 1px solid rgba(255,255,255,0.07);
            border-radius: 18px; padding: 2.25rem; width: 340px;
        }
        .logo { display:flex; align-items:center; gap:0.6rem; margin-bottom:0.5rem; }
        .logo-mark {
            width:30px; height:30px; border-radius:8px;
            background: linear-gradient(135deg, #FF3B3B, #E53E3E);
            display:flex; align-items:center; justify-content:center;
            font-weight:900; color:#fff; font-size:0.9rem;
            box-shadow: 0 4px 12px rgba(255,59,59,0.4);
        }
        .logo-text { font-size:1.15rem; font-weight:800; }
        .logo-text span { color:#FF3B3B; }
        .tagline { color:#7a8090; font-size:0.85rem; margin-bottom:2rem; }
        label { display:block; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.06em; color:#7a8090; margin-bottom:0.4rem; }
        input {
            width:100%; padding:0.7rem 0.9rem;
            background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08);
            border-radius:9px; color:#e8eaed; font-size:0.9rem; margin-bottom:1rem;
            transition: border-color 0.2s;
        }
        input:focus { outline:none; border-color:#FF3B3B; }
        .submit {
            width:100%; padding:0.8rem;
            background:#FF3B3B; color:#fff; font-weight:700; font-size:0.95rem;
            border:none; border-radius:9px; cursor:pointer;
            margin-top:0.5rem; transition: background 0.2s, transform 0.1s;
        }
        .submit:hover { background:#E53E3E; transform:scale(1.02); box-shadow:0 4px 16px rgba(255,59,59,0.4); }
        .hint { font-size:0.78rem; color:#7a8090; margin-top:1.25rem; text-align:center; }
        .err { color:#ef4444; font-size:0.85rem; margin-top:0.5rem; display:none; }
    </style>
</head>
<body>
    <div class="box">
        <div class="logo">
            <div class="logo-mark">P</div>
            <div class="logo-text">Peak<span>Overwatch</span></div>
        </div>
        <div class="tagline">TikTok Shop performance intelligence</div>
        <form id="loginForm">
            <label>Email</label>
            <input type="email" id="email" value="demo@peakoverwatch.com" required autocomplete="email">
            <label>Password</label>
            <input type="password" id="password" value="password123" required autocomplete="current-password">
            <button type="submit" class="submit">Sign In</button>
            <div class="err" id="err"></div>
        </form>
        <div class="hint">Demo: demo@peakoverwatch.com / password123</div>
    </div>
    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('.submit');
            btn.textContent = 'Signing in...'; btn.disabled = true;
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: document.getElementById('email').value, password: document.getElementById('password').value })
            });
            const data = await res.json();
            if (data.success) {
                window.location.href = '/dashboard';
            } else {
                const err = document.getElementById('err');
                err.style.display = 'block';
                err.textContent = data.message || 'Login failed';
                btn.textContent = 'Sign In'; btn.disabled = false;
            }
        });
    </script>
</body>
</html>'''


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json or {}
    user = users.get(data.get('email', ''))
    if not user or not user.verify_password(data.get('password', '')):
        return jsonify({'success': False, 'message': 'Invalid credentials'})
    token = secrets.token_urlsafe(32)
    sessions[token] = {'user_id': user.id, 'expires': datetime.now() + SESSION_LIFETIME}
    resp = jsonify({'success': True})
    resp.set_cookie(
        'session_token', token,
        httponly=True,
        secure=app.config['SESSION_COOKIE_SECURE'],
        samesite=app.config['SESSION_COOKIE_SAMESITE'],
        max_age=int(SESSION_LIFETIME.total_seconds())
    )
    return resp


@app.route('/logout')
def logout():
    token = request.cookies.get('session_token')
    if token in sessions:
        del sessions[token]
    resp = make_response(redirect('/login'))
    resp.delete_cookie('session_token')
    return resp


# ---------------------------------------------------------------------------
# /dashboard
# ---------------------------------------------------------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    user = request.user
    unread_count = len(user.get_unread_alerts())

    series = generate_gmv_series(30)
    labels = [d['date'] for d in series]
    ds_tv    = [d['@trendvault_us']   for d in series]
    ds_po    = [d['@pickoftheday_co'] for d in series]
    ds_dh    = [d['@dailyfinds_hub']  for d in series]
    ds_total = [d['total']            for d in series]

    # Hero products (top 3 from spec)
    top3 = MOCK_PRODUCTS[:3]
    hero_products_html = ''
    for i, p in enumerate(top3):
        rank_color = ['#FFD700', '#C0C0C0', '#CD7F32'][i]
        hero_products_html += f'''
        <div style="display:flex;align-items:center;gap:0.85rem;padding:0.85rem 0;border-bottom:1px solid rgba(255,255,255,0.04);">
            <div style="font-size:1rem;font-weight:800;color:{rank_color};min-width:1.5rem;">#{i+1}</div>
            <div class="acc-dot" style="background:{p['color']};"></div>
            <div style="flex:1;min-width:0;">
                <div style="font-weight:600;font-size:0.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{p['name']}</div>
                <div style="color:var(--muted);font-size:0.78rem;">{p['account']}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-weight:700;font-size:0.9rem;">${p['gmv']:,}</div>
                <div style="color:var(--muted);font-size:0.75rem;">{p['units']} units</div>
            </div>
        </div>'''

    # Viral videos
    viral_html = ''
    for v in MOCK_VIRAL_VIDEOS:
        viral_html += f'''
        <div style="display:flex;align-items:center;gap:0.85rem;padding:0.85rem 0;border-bottom:1px solid rgba(255,255,255,0.04);">
            <div class="acc-dot" style="background:{v['color']};"></div>
            <div style="flex:1;min-width:0;">
                <div style="font-weight:600;font-size:0.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{v['title']}</div>
                <div style="color:var(--muted);font-size:0.78rem;">{v['account']}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-weight:700;font-size:0.9rem;color:var(--accent);">{fmt_views(v['views_this_month'])}</div>
                <div style="color:var(--muted);font-size:0.75rem;">this month</div>
            </div>
        </div>'''

    body = f'''
    <div class="page-header">
        <div class="page-title">Dashboard</div>
        <div class="page-sub">Portfolio overview &middot; {datetime.now().strftime("%B %Y")}</div>
    </div>

    <div class="metric-cards">
        <div class="metric-card">
            <div class="metric-label">Total GMV</div>
            <div class="metric-value" data-counter="27690" data-prefix="$">$0</div>
            <div class="metric-sub"><span class="metric-pos">&#8593; 18.4%</span> vs last month</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Est. Commission</div>
            <div class="metric-value" data-counter="3608" data-prefix="$">$0</div>
            <div class="metric-sub">Across 3 accounts</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Total Views</div>
            <div class="metric-value" data-counter="2.68" data-suffix="M">0M</div>
            <div class="metric-sub">This month</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Videos Posted</div>
            <div class="metric-value" data-counter="1248">0</div>
            <div class="metric-sub">This month &middot; all accounts</div>
        </div>
        <div class="metric-card" style="border-color:rgba(255,59,59,0.25);background:rgba(255,59,59,0.04);">
            <div class="metric-label" style="color:var(--accent);">&#128293; Viral Videos</div>
            <div class="metric-value" style="color:var(--accent);" data-counter="4">0</div>
            <div class="metric-sub">&ge;50K views delta this month</div>
        </div>
    </div>

    <!-- GMV Trend Chart -->
    <div class="panel">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
            <div class="panel-title" style="margin-bottom:0;">GMV Trend &middot; Last 30 Days</div>
        </div>
        <div class="chart-toggles" id="gmvToggles">
            <button class="toggle-btn" data-idx="0" style="color:#FF3B3B;border-color:#FF3B3B;background:rgba(255,59,59,0.1);">
                <span class="toggle-dot" style="background:#FF3B3B;"></span>@trendvault_us
            </button>
            <button class="toggle-btn" data-idx="1" style="color:#A855F7;border-color:#A855F7;background:rgba(168,85,247,0.1);">
                <span class="toggle-dot" style="background:#A855F7;"></span>@pickoftheday_co
            </button>
            <button class="toggle-btn" data-idx="2" style="color:#F59E0B;border-color:#F59E0B;background:rgba(245,158,11,0.1);">
                <span class="toggle-dot" style="background:#F59E0B;"></span>@dailyfinds_hub
            </button>
            <button class="toggle-btn" data-idx="3" style="color:#F0F0F0;border-color:rgba(240,240,240,0.3);background:rgba(240,240,240,0.05);">
                <span class="toggle-dot" style="background:#F0F0F0;"></span>Total
            </button>
        </div>
        <div class="chart-wrap"><canvas id="gmvChart"></canvas></div>
    </div>

    <!-- Hero Products + Viral Videos -->
    <div class="two-col">
        <div class="panel">
            <div class="panel-title">Hero Products</div>
            {hero_products_html}
        </div>
        <div class="panel">
            <div class="panel-title">Viral Videos This Month</div>
            <div style="color:var(--muted);font-size:0.8rem;margin-bottom:0.5rem;">&ge;50K views delta</div>
            {viral_html}
        </div>
    </div>
    '''

    extra_js = f'''
    (function() {{
        const canvas = document.getElementById('gmvChart');
        const ctx = canvas.getContext('2d');
        const H = 300;

        function mkGrad(r, g, b) {{
            const gr = ctx.createLinearGradient(0, 0, 0, H);
            gr.addColorStop(0, 'rgba(' + r + ',' + g + ',' + b + ',0.6)');
            gr.addColorStop(1, 'rgba(' + r + ',' + g + ',' + b + ',0)');
            return gr;
        }}

        const gradTV    = mkGrad(255, 59,  59);
        const gradPO    = mkGrad(168, 85,  247);
        const gradDH    = mkGrad(245, 158, 11);
        const gradTotal = mkGrad(240, 240, 240);

        const gmvChart = new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [
                    {{ label: '@trendvault_us',   data: {json.dumps(ds_tv)},    borderColor: '#FF3B3B', backgroundColor: gradTV,    fill: true, tension: 0.4, pointRadius: 0, pointHoverRadius: 4, borderWidth: 2 }},
                    {{ label: '@pickoftheday_co', data: {json.dumps(ds_po)},    borderColor: '#A855F7', backgroundColor: gradPO,    fill: true, tension: 0.4, pointRadius: 0, pointHoverRadius: 4, borderWidth: 2 }},
                    {{ label: '@dailyfinds_hub',  data: {json.dumps(ds_dh)},    borderColor: '#F59E0B', backgroundColor: gradDH,    fill: true, tension: 0.4, pointRadius: 0, pointHoverRadius: 4, borderWidth: 2 }},
                    {{ label: 'Total',            data: {json.dumps(ds_total)}, borderColor: '#F0F0F0', backgroundColor: gradTotal, fill: true, tension: 0.4, pointRadius: 0, pointHoverRadius: 4, borderWidth: 1.5, borderDash: [4,3] }},
                ]
            }},
            options: {{
                maintainAspectRatio: false,
                animation: {{ duration: 1200, easing: 'easeInOutQuart' }},
                interaction: {{ intersect: false, mode: 'index' }},
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        backgroundColor: '#111118',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1, padding: 12,
                        callbacks: {{ label: ctx => ' ' + ctx.dataset.label + ': $' + ctx.parsed.y.toLocaleString() }}
                    }}
                }},
                scales: {{
                    x: {{ ticks: {{ color: '#7a8090', maxTicksLimit: 10 }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }},
                    y: {{ ticks: {{ color: '#7a8090', callback: v => '$' + (v >= 1000 ? (v/1000).toFixed(0)+'k' : v) }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }}
                }}
            }}
        }});

        document.querySelectorAll('#gmvToggles .toggle-btn').forEach(btn => {{
            btn.addEventListener('click', function() {{
                const idx = parseInt(this.dataset.idx);
                const meta = gmvChart.getDatasetMeta(idx);
                meta.hidden = !meta.hidden;
                this.classList.toggle('off', meta.hidden);
                gmvChart.update();
            }});
        }});
    }})();
    '''

    return page_shell('Dashboard', 'dashboard', user, unread_count, body, extra_js=extra_js, load_chartjs=True)


# ---------------------------------------------------------------------------
# /accounts
# ---------------------------------------------------------------------------
@app.route('/accounts')
@login_required
def accounts():
    user = request.user
    unread_count = len(user.get_unread_alerts())

    def fyp_badge(score):
        if score >= 80:
            cls = 'badge-good'
        elif score >= 70:
            cls = 'badge-warn'
        else:
            cls = 'badge-crit'
        return f'<span style="font-size:0.72rem;color:var(--muted);background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.08);border-radius:4px;padding:1px 6px;font-weight:500;">FYP {score}%</span>'

    def status_badge(status):
        cls = {'Active': 'badge-active', 'Warning': 'badge-warning', 'Inactive': 'badge-critical'}.get(status, 'badge-info')
        return f'<span class="badge {cls}">{status}</span>'

    def mom_html(pct, color):
        arrow = '&#8593;' if pct >= 0 else '&#8595;'
        c = 'var(--success)' if pct >= 0 else 'var(--critical)'
        sign = '+' if pct >= 0 else ''
        return f'<span style="color:{c};font-weight:700;">{arrow} {sign}{pct:.1f}%</span>'

    cards_html = ''
    sparkline_inits = ''
    for acc in MOCK_ACCOUNTS:
        commission = user.get_commission(acc['handle'])
        earnings = int(acc['gmv'] * commission / 100)
        avg_views = int(acc['views'] / max(acc['videos'], 1))
        sp_data = generate_sparkline(acc['handle'])
        sp_id = f"sp_{acc['handle'].lstrip('@').replace('.','_').replace('-','_')}"
        cards_html += f'''
        <div class="account-card">
            <div class="acc-card-bar" style="background:{acc['color']};"></div>
            <div class="acc-card-body">
                <div class="acc-card-header">
                    <div>
                        <div class="acc-card-handle" style="color:{acc['color']};">{acc['handle']}</div>
                        <div style="color:var(--muted);font-size:0.78rem;">{acc['name']}</div>
                    </div>
                    {status_badge(acc['status'])}
                </div>

                <div class="acc-card-gmv" style="color:{acc['color']};" data-counter="{acc['gmv']}" data-prefix="$">$0</div>
                <div class="acc-card-earnings">
                    {commission:.1f}% avg commission &middot; <span style="color:var(--text);font-weight:600;">${earnings:,}</span> earned
                </div>

                <div class="acc-card-grid">
                    <div class="acc-card-stat">
                        <div class="acc-card-stat-label">Videos</div>
                        <div class="acc-card-stat-val">{acc['videos']:,}</div>
                    </div>
                    <div class="acc-card-stat">
                        <div class="acc-card-stat-label">Total Views</div>
                        <div class="acc-card-stat-val">{fmt_views(acc['views'])}</div>
                    </div>
                    <div class="acc-card-stat">
                        <div class="acc-card-stat-label">Avg Views/Video</div>
                        <div class="acc-card-stat-val">{fmt_views(avg_views)}</div>
                    </div>
                    <div class="acc-card-stat">
                        <div class="acc-card-stat-label">MoM Views</div>
                        <div class="acc-card-stat-val">{mom_html(acc['mom_pct'], acc['color'])}</div>
                    </div>
                </div>

                <div class="acc-card-footer">
                    {fyp_badge(acc['fyp_score'])}
                    <div style="text-align:right;">
                        <div style="font-size:0.68rem;color:var(--muted);margin-bottom:2px;text-transform:uppercase;letter-spacing:0.05em;">GMV trend</div>
                        <div class="sparkline-wrap"><canvas id="{sp_id}"></canvas></div>
                    </div>
                </div>
            </div>
        </div>'''

        sparkline_inits += f'''
        (function() {{
            const sctx = document.getElementById('{sp_id}').getContext('2d');
            const sGrad = sctx.createLinearGradient(0, 0, 0, 40);
            sGrad.addColorStop(0, 'rgba({acc["color_rgb"]},0.5)');
            sGrad.addColorStop(1, 'rgba({acc["color_rgb"]},0)');
            new Chart(sctx, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(['D1','D2','D3','D4','D5','D6','D7'])},
                    datasets: [{{ data: {json.dumps(sp_data)}, borderColor: '{acc["color"]}', backgroundColor: sGrad, fill: true, tension: 0.4, pointRadius: 0, borderWidth: 1.5 }}]
                }},
                options: {{
                    maintainAspectRatio: false,
                    animation: {{ duration: 800 }},
                    plugins: {{ legend: {{ display: false }}, tooltip: {{
                        enabled: true, backgroundColor: '#111118', borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1,
                        callbacks: {{ label: ctx => '$' + ctx.parsed.y.toLocaleString() }}
                    }} }},
                    scales: {{ x: {{ display: false }}, y: {{ display: false }} }}
                }}
            }});
        }})();
        '''

    add_account_modal = '''
    <div id="addAccountModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:999;align-items:center;justify-content:center;">
        <div style="background:#111118;border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:2rem;max-width:400px;width:90%;position:relative;">
            <button onclick="document.getElementById('addAccountModal').style.display='none'" style="position:absolute;top:1rem;right:1rem;background:none;border:none;color:var(--muted);font-size:1.2rem;cursor:pointer;">&#215;</button>
            <div style="font-size:1.5rem;margin-bottom:0.75rem;">&#128279;</div>
            <div style="font-size:1.1rem;font-weight:700;margin-bottom:0.5rem;">Coming Soon</div>
            <div style="color:var(--muted);font-size:0.9rem;line-height:1.5;">Connect your TikTok account to sync real data. This feature is coming in the next release.</div>
            <button onclick="document.getElementById('addAccountModal').style.display='none'" class="btn btn-primary" style="margin-top:1.5rem;width:100%;justify-content:center;">Got it</button>
        </div>
    </div>
    '''

    body = f'''
    {add_account_modal}
    <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div>
            <div class="page-title">Accounts</div>
            <div class="page-sub">TikTok Shop accounts performance overview</div>
        </div>
        <button onclick="document.getElementById('addAccountModal').style.display='flex'" style="background:transparent;border:1.5px solid var(--accent);color:var(--accent);padding:0.55rem 1.1rem;border-radius:8px;font-size:0.875rem;font-weight:600;cursor:pointer;transition:background 0.15s,transform 0.15s;" onmouseover="this.style.background='rgba(255,59,59,0.08)'" onmouseout="this.style.background='transparent'">+ Add Account</button>
    </div>
    <div class="account-cards">{cards_html}</div>
    '''

    return page_shell('Accounts', 'accounts', user, unread_count, body, extra_js=sparkline_inits, load_chartjs=True)


# ---------------------------------------------------------------------------
# /analytics
# ---------------------------------------------------------------------------
@app.route('/analytics')
@login_required
def analytics():
    user = request.user
    unread_count = len(user.get_unread_alerts())

    series90 = generate_gmv_series(90)
    labels90  = [d['date']              for d in series90]
    ds90_tv   = [d['@trendvault_us']    for d in series90]
    ds90_po   = [d['@pickoftheday_co']  for d in series90]
    ds90_dh   = [d['@dailyfinds_hub']   for d in series90]
    ds90_tot  = [d['total']             for d in series90]

    months, views_data  = generate_monthly_bar_data()
    _,      videos_data = generate_monthly_video_data()

    views_datasets_str = json.dumps([
        {'label': acc['handle'], 'data': views_data[acc['handle']], 'backgroundColor': acc['color'], 'borderRadius': 5}
        for acc in MOCK_ACCOUNTS
    ])
    videos_datasets_str = json.dumps([
        {'label': acc['handle'], 'data': videos_data[acc['handle']], 'backgroundColor': acc['color'], 'borderRadius': 5}
        for acc in MOCK_ACCOUNTS
    ])

    # Revenue source donut HTML (3 side-by-side cards)
    src_colors = {'Videos': '#FF3B3B', 'Shop Ads': '#A855F7', 'LIVE': '#F59E0B', 'Other': '#7a8090'}
    donut_cards_html = ''
    for acc in MOCK_ACCOUNTS:
        src = REVENUE_SOURCES[acc['handle']]
        sp_id = f"donut_{acc['handle'].lstrip('@').replace('.','_').replace('-','_')}"
        legend = ''
        for label, pct in src.items():
            if pct > 0:
                gmv_val = int(acc['gmv'] * pct / 100)
                legend += f'''<div class="donut-legend-row">
                    <div class="donut-legend-swatch" style="background:{src_colors.get(label,'#7a8090')};"></div>
                    <span style="flex:1;">{label}</span>
                    <strong>{pct}%</strong>
                    <span style="color:var(--muted);margin-left:0.5rem;">${gmv_val:,}</span>
                </div>'''
        donut_cards_html += f'''
        <div class="donut-card" data-account="{acc['handle']}" id="donut_card_{acc['handle'].lstrip('@').replace('.','_').replace('-','_')}">
            <div style="font-weight:700;color:{acc['color']};margin-bottom:0.75rem;font-size:0.9rem;">{acc['handle']}</div>
            <div style="position:relative;height:140px;width:140px;margin:0 auto;">
                <canvas id="{sp_id}"></canvas>
            </div>
            <div class="donut-legend" style="margin-top:0.75rem;">{legend}</div>
        </div>'''

    # Products table
    product_rows_html = ''
    for i, p in enumerate(MOCK_PRODUCTS):
        acc_total_gmv = next((a['gmv'] for a in MOCK_ACCOUNTS if a['handle'] == p['account']), 1)
        pct_of_acct = (p['gmv'] / acc_total_gmv * 100)
        product_rows_html += f'''<tr class="product-row" data-account="{p['account']}" style="animation-delay:{i*50}ms;">
            <td>
                <div class="acc-cell">
                    <div class="acc-dot" style="background:{p['color']};"></div>
                    {p['name']}
                </div>
            </td>
            <td><div class="acc-cell"><div class="acc-dot" style="background:{p['color']};"></div>{p['account']}</div></td>
            <td>{p['units']:,}</td>
            <td style="font-weight:600;">${p['gmv']:,}</td>
            <td>{p['commission']}%</td>
            <td style="color:var(--muted);">{pct_of_acct:.1f}%</td>
        </tr>'''

    # Viral videos table
    viral_rows_html = ''
    for i, v in enumerate(MOCK_VIRAL_VIDEOS):
        viral_rows_html += f'''<tr class="viral-row" data-account="{v['account']}" style="animation-delay:{i*50}ms;">
            <td style="max-width:240px;font-weight:600;">{v['title']}</td>
            <td><div class="acc-cell"><div class="acc-dot" style="background:{v['color']};"></div>{v['account']}</div></td>
            <td style="color:var(--accent);font-weight:600;">{fmt_views(v['views_this_month'])}</td>
            <td>{fmt_views(v['total_views'])}</td>
            <td style="color:var(--muted);">{v['date']}</td>
            <td style="color:var(--muted);">{v['days_old']}d</td>
        </tr>'''

    # Viral video count by account
    viral_by_account = {}
    for v in MOCK_VIRAL_VIDEOS:
        viral_by_account[v['account']] = viral_by_account.get(v['account'], 0) + 1

    viral_breakdown = ' &nbsp;&middot;&nbsp; '.join([
        f'<span style="color:{next(a["color"] for a in MOCK_ACCOUNTS if a["handle"]==h)};font-weight:700;">{h}: {cnt}</span>'
        for h, cnt in viral_by_account.items()
    ])

    # Decision metrics table
    def dm_flag(val, good_thresh, warn_thresh, higher_is_better=True):
        if higher_is_better:
            if val >= good_thresh:
                return 'dm-flag-green'
            elif val >= warn_thresh:
                return 'dm-flag-yellow'
            else:
                return 'dm-flag-red'
        else:
            if val <= good_thresh:
                return 'dm-flag-green'
            elif val <= warn_thresh:
                return 'dm-flag-yellow'
            else:
                return 'dm-flag-red'

    dm_rows_html = ''
    for dm in DECISION_METRICS:
        # avg views/video: green >2000, yellow >1000, red <1000
        avg_cls = dm_flag(dm['avg_views_video'], 2000, 1000)
        # mom views: green >15%, yellow >0%, red <0%
        mom_cls = dm_flag(dm['mom_views_pct'], 15, 0)
        mom_arrow = '&#8593;' if dm['mom_views_pct'] >= 0 else '&#8595;'
        mom_sign  = '+' if dm['mom_views_pct'] >= 0 else ''
        # avg daily posts: green >15, yellow >5, red <=5
        post_cls = dm_flag(dm['avg_daily_posts'], 15, 5)
        # commission per 1k: green >1.3, yellow >0.9, red <0.9
        comm_cls = dm_flag(dm['commission_per_1k_views'], 1.3, 0.9)
        # gmv per video: green >20, yellow >10, red <10
        gmv_v_cls = dm_flag(dm['gmv_per_video'], 20, 10)
        # viral rate: green >0.3, yellow >0.1, red 0
        viral_cls = dm_flag(dm['viral_rate'], 0.3, 0.1)
        dm_rows_html += f'''<tr>
            <td><div class="acc-cell"><div class="acc-dot" style="background:{dm['color']};"></div><strong>{dm['handle']}</strong></div></td>
            <td class="{avg_cls}">{dm['avg_views_video']:,}</td>
            <td class="{mom_cls}">{mom_arrow} {mom_sign}{dm['mom_views_pct']:.1f}%</td>
            <td class="{post_cls}">{dm['avg_daily_posts']:.1f}/day</td>
            <td class="{comm_cls}">${dm['commission_per_1k_views']:.2f}/K</td>
            <td class="{gmv_v_cls}">${dm['gmv_per_video']:.1f}</td>
            <td class="{viral_cls}">{dm['viral_rate']:.2f}%</td>
        </tr>'''

    body = f'''
    <div class="page-header">
        <div class="page-title">Analytics</div>
        <div class="page-sub">Deep-dive performance &middot; 90-day window</div>
    </div>

    <!-- Account filter pills -->
    <div class="acc-filter" id="accFilter">
        <button class="acc-filter-btn active pill-all" data-account="all">All Accounts</button>
        <button class="acc-filter-btn pill-tv" data-account="@trendvault_us">@trendvault_us</button>
        <button class="acc-filter-btn pill-po" data-account="@pickoftheday_co">@pickoftheday_co</button>
        <button class="acc-filter-btn pill-dh" data-account="@dailyfinds_hub">@dailyfinds_hub</button>
    </div>

    <!-- Section 1: GMV Trend 90d -->
    <div class="panel">
        <div class="panel-title">GMV Trend &middot; Last 90 Days</div>
        <div class="chart-toggles" id="gmvToggles90">
            <button class="toggle-btn" data-idx="0" style="color:#FF3B3B;border-color:#FF3B3B;background:rgba(255,59,59,0.1);">
                <span class="toggle-dot" style="background:#FF3B3B;"></span>@trendvault_us
            </button>
            <button class="toggle-btn" data-idx="1" style="color:#A855F7;border-color:#A855F7;background:rgba(168,85,247,0.1);">
                <span class="toggle-dot" style="background:#A855F7;"></span>@pickoftheday_co
            </button>
            <button class="toggle-btn" data-idx="2" style="color:#F59E0B;border-color:#F59E0B;background:rgba(245,158,11,0.1);">
                <span class="toggle-dot" style="background:#F59E0B;"></span>@dailyfinds_hub
            </button>
            <button class="toggle-btn" data-idx="3" style="color:#F0F0F0;border-color:rgba(240,240,240,0.3);background:rgba(240,240,240,0.05);">
                <span class="toggle-dot" style="background:#F0F0F0;"></span>Total
            </button>
        </div>
        <div class="chart-wrap" style="height:280px;"><canvas id="gmv90Chart"></canvas></div>
    </div>

    <!-- Section 2 & 3: Views + Videos -->
    <div class="two-col">
        <div class="panel">
            <div class="panel-title">Views per Account &middot; Monthly</div>
            <div style="position:relative;height:240px;"><canvas id="viewsBarChart"></canvas></div>
        </div>
        <div class="panel">
            <div class="panel-title">Videos Posted &middot; Monthly</div>
            <div style="position:relative;height:240px;"><canvas id="videosBarChart"></canvas></div>
        </div>
    </div>

    <!-- Section 4: Revenue Source per account -->
    <div class="panel">
        <div class="panel-title">Revenue Source &middot; Per Account</div>
        <div class="donut-cards-row" id="donutCardsRow">
            {donut_cards_html}
        </div>
    </div>

    <!-- Section 5: Products -->
    <div class="panel">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.25rem;flex-wrap:wrap;gap:0.75rem;">
            <div class="panel-title" style="margin-bottom:0;">Products</div>
            <div style="background:rgba(255,59,59,0.08);border:1px solid rgba(255,59,59,0.2);padding:0.4rem 1rem;border-radius:20px;font-size:0.85rem;">
                <strong style="color:var(--accent);">5</strong> <span style="color:var(--muted);">unique products this month</span>
            </div>
        </div>
        <table class="data-table" id="productsTable">
            <thead>
                <tr><th>Product</th><th>Account</th><th>Units</th><th>GMV</th><th>Commission</th><th>% of Account GMV</th></tr>
            </thead>
            <tbody>{product_rows_html}</tbody>
        </table>
    </div>

    <!-- Section 6: Viral Videos -->
    <div class="panel">
        <div style="margin-bottom:1.25rem;">
            <div class="panel-title" style="margin-bottom:0.5rem;">Viral Videos This Month</div>
            <div style="font-size:0.85rem;color:var(--muted);">{viral_breakdown}</div>
        </div>
        <table class="data-table" id="viralTable">
            <thead>
                <tr><th>Video</th><th>Account</th><th>Views This Month</th><th>Total Views</th><th>Date Posted</th><th>Days Old</th></tr>
            </thead>
            <tbody>{viral_rows_html}</tbody>
        </table>
    </div>

    <!-- Section 7: Decision Metrics -->
    <div class="panel">
        <div class="panel-title">Decision Metrics &middot; Account Comparison</div>
        <div style="color:var(--muted);font-size:0.82rem;margin-bottom:1rem;">
            <span style="color:var(--success);">&#9679;</span> Good &nbsp;
            <span style="color:var(--warning);">&#9679;</span> Watch &nbsp;
            <span style="color:var(--critical);">&#9679;</span> Action needed
        </div>
        <table class="dm-table">
            <thead>
                <tr>
                    <th>Account</th>
                    <th>Avg Views/Video</th>
                    <th>MoM Views %</th>
                    <th>Posting Consistency</th>
                    <th>Commission/1K Views</th>
                    <th>GMV/Video</th>
                    <th>Viral Rate</th>
                </tr>
            </thead>
            <tbody>{dm_rows_html}</tbody>
        </table>
    </div>
    '''

    # Build donut init JS
    donut_init_js = ''
    for acc in MOCK_ACCOUNTS:
        src = REVENUE_SOURCES[acc['handle']]
        sp_id = f"donut_{acc['handle'].lstrip('@').replace('.','_').replace('-','_')}"
        labels_list = [k for k, v in src.items() if v > 0]
        data_list   = [v for v in src.values() if v > 0]
        colors_list = [src_colors.get(k, '#7a8090') for k in labels_list]
        donut_init_js += f'''
        new Chart(document.getElementById('{sp_id}').getContext('2d'), {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(labels_list)},
                datasets: [{{ data: {json.dumps(data_list)}, backgroundColor: {json.dumps(colors_list)}, borderWidth: 0, hoverOffset: 6 }}]
            }},
            options: {{
                maintainAspectRatio: false,
                animation: {{ duration: 1200, easing: 'easeInOutQuart' }},
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{ backgroundColor: '#111118', borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1 }}
                }},
                cutout: '68%'
            }}
        }});
        '''

    extra_js = f'''
    // GMV 90-day area chart
    var gmv90Chart;
    (function() {{
        const canvas = document.getElementById('gmv90Chart');
        const ctx = canvas.getContext('2d');
        const H = 280;
        function mkGrad(r, g, b) {{
            const gr = ctx.createLinearGradient(0, 0, 0, H);
            gr.addColorStop(0, 'rgba('+r+','+g+','+b+',0.6)');
            gr.addColorStop(1, 'rgba('+r+','+g+','+b+',0)');
            return gr;
        }}
        const gTV    = mkGrad(255,59,59);
        const gPO    = mkGrad(168,85,247);
        const gDH    = mkGrad(245,158,11);
        const gTot   = mkGrad(240,240,240);

        gmv90Chart = new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(labels90)},
                datasets: [
                    {{ label: '@trendvault_us',   data: {json.dumps(ds90_tv)},  borderColor: '#FF3B3B', backgroundColor: gTV,  fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2 }},
                    {{ label: '@pickoftheday_co', data: {json.dumps(ds90_po)},  borderColor: '#A855F7', backgroundColor: gPO,  fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2 }},
                    {{ label: '@dailyfinds_hub',  data: {json.dumps(ds90_dh)},  borderColor: '#F59E0B', backgroundColor: gDH,  fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2 }},
                    {{ label: 'Total',            data: {json.dumps(ds90_tot)}, borderColor: '#F0F0F0', backgroundColor: gTot, fill: true, tension: 0.4, pointRadius: 0, borderWidth: 1.5, borderDash: [4,3] }},
                ]
            }},
            options: {{
                maintainAspectRatio: false,
                animation: {{ duration: 1200, easing: 'easeInOutQuart' }},
                interaction: {{ intersect: false, mode: 'index' }},
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{ backgroundColor: '#111118', borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1, padding: 10,
                        callbacks: {{ label: ctx => ' ' + ctx.dataset.label + ': $' + ctx.parsed.y.toLocaleString() }} }}
                }},
                scales: {{
                    x: {{ ticks: {{ color: '#7a8090', maxTicksLimit: 12 }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }},
                    y: {{ ticks: {{ color: '#7a8090', callback: v => '$' + (v >= 1000 ? (v/1000).toFixed(0)+'k' : v) }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }}
                }}
            }}
        }});

        document.querySelectorAll('#gmvToggles90 .toggle-btn').forEach(btn => {{
            btn.addEventListener('click', function() {{
                const idx = parseInt(this.dataset.idx);
                const meta = gmv90Chart.getDatasetMeta(idx);
                meta.hidden = !meta.hidden;
                this.classList.toggle('off', meta.hidden);
                gmv90Chart.update();
            }});
        }});
    }})();

    // Views bar chart
    new Chart(document.getElementById('viewsBarChart').getContext('2d'), {{
        type: 'bar',
        data: {{ labels: {json.dumps(months)}, datasets: {views_datasets_str} }},
        options: {{
            maintainAspectRatio: false,
            animation: {{ duration: 1200, easing: 'easeInOutQuart' }},
            plugins: {{ legend: {{ labels: {{ color: '#7a8090', font: {{size: 11}}, boxWidth: 10 }} }} }},
            scales: {{
                x: {{ ticks: {{ color: '#7a8090' }}, grid: {{ display: false }} }},
                y: {{ ticks: {{ color: '#7a8090', callback: v => v >= 1000000 ? (v/1000000).toFixed(1)+'M' : v >= 1000 ? (v/1000).toFixed(0)+'K' : v }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }}
            }}
        }}
    }});

    // Videos bar chart
    new Chart(document.getElementById('videosBarChart').getContext('2d'), {{
        type: 'bar',
        data: {{ labels: {json.dumps(months)}, datasets: {videos_datasets_str} }},
        options: {{
            maintainAspectRatio: false,
            animation: {{ duration: 1200, easing: 'easeInOutQuart' }},
            plugins: {{ legend: {{ labels: {{ color: '#7a8090', font: {{size: 11}}, boxWidth: 10 }} }} }},
            scales: {{
                x: {{ ticks: {{ color: '#7a8090' }}, grid: {{ display: false }} }},
                y: {{ ticks: {{ color: '#7a8090' }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }}
            }}
        }}
    }});

    // Donut charts
    {donut_init_js}

    // Account filter logic
    var activeAccFilter = 'all';
    document.querySelectorAll('#accFilter .acc-filter-btn').forEach(function(btn) {{
        btn.addEventListener('click', function() {{
            document.querySelectorAll('#accFilter .acc-filter-btn').forEach(function(b) {{ b.classList.remove('active'); }});
            this.classList.add('active');
            activeAccFilter = this.dataset.account;
            applyAccFilter(activeAccFilter);
        }});
    }});
    // Init pill active color on page load
    document.querySelectorAll('#accFilter .acc-filter-btn.active').forEach(function(btn) {{ btn.classList.add('active'); }});

    function applyAccFilter(acct) {{
        // Filter donut cards
        document.querySelectorAll('.donut-card').forEach(function(el) {{
            if (acct === 'all' || el.dataset.account === acct) {{
                el.style.display = '';
                el.classList.toggle('single-mode', acct !== 'all');
            }} else {{
                el.style.display = 'none';
            }}
        }});
        // Filter product rows
        document.querySelectorAll('.product-row').forEach(function(el) {{
            el.style.display = (acct === 'all' || el.dataset.account === acct) ? '' : 'none';
        }});
        // Filter viral rows
        document.querySelectorAll('.viral-row').forEach(function(el) {{
            el.style.display = (acct === 'all' || el.dataset.account === acct) ? '' : 'none';
        }});
        // Filter gmv chart datasets
        if (typeof gmv90Chart !== 'undefined') {{
            var accountMap = {{'@trendvault_us': 0, '@pickoftheday_co': 1, '@dailyfinds_hub': 2}};
            if (acct === 'all') {{
                [0,1,2,3].forEach(function(i) {{
                    gmv90Chart.getDatasetMeta(i).hidden = false;
                }});
            }} else {{
                var showIdx = accountMap[acct];
                [0,1,2,3].forEach(function(i) {{
                    gmv90Chart.getDatasetMeta(i).hidden = (i !== showIdx);
                }});
            }}
            gmv90Chart.update();
        }}
    }}
    '''

    return page_shell('Analytics', 'analytics', user, unread_count, body, extra_js=extra_js, load_chartjs=True)


# ---------------------------------------------------------------------------
# /alerts
# ---------------------------------------------------------------------------
@app.route('/alerts')
@login_required
def alerts_page():
    user = request.user
    all_alerts = alerts_store.get(user.id, [])

    if not all_alerts:
        user.add_alert('Welcome', 'Your real-time performance alerts will appear here.', 'info')
        user.add_alert('FYP Warning: @dailyfinds_hub', 'FYP score at 67% — below warning threshold of 70%.', 'warning')
        all_alerts = alerts_store.get(user.id, [])

    unread_count = len([a for a in all_alerts if not a['is_read']])

    alert_items = ''
    for i, alert in enumerate(reversed(all_alerts)):
        level = alert.get('level', 'info')
        is_read = alert.get('is_read', False)
        read_cls = ' read' if is_read else ''
        ts = alert.get('created_at', '')[:16].replace('T', ' ')
        badge_cls = {'critical': 'badge-critical', 'warning': 'badge-warn', 'info': 'badge-info'}.get(level, 'badge-info')
        read_btn = '' if is_read else f'<button onclick="markRead(\'{alert["id"]}\')" style="margin-top:0.6rem;background:none;border:1px solid var(--border);color:var(--muted);padding:0.25rem 0.6rem;border-radius:6px;cursor:pointer;font-size:0.78rem;transition:border-color 0.2s;">Mark read</button>'
        alert_items += f'''
        <div class="alert-row {level}{read_cls}" id="alert-{alert['id']}" style="animation-delay:{i*50}ms;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;">
                <div style="flex:1;">
                    <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.35rem;">
                        <span class="badge {badge_cls}">{level.upper()}</span>
                        <strong style="font-size:0.9rem;">{alert['title']}</strong>
                    </div>
                    <div style="color:var(--muted);font-size:0.88rem;">{alert['message']}</div>
                    {read_btn}
                </div>
                <div style="color:var(--muted);font-size:0.78rem;white-space:nowrap;">{ts}</div>
            </div>
        </div>'''

    body = f'''
    <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div>
            <div class="page-title">Alerts</div>
            <div class="page-sub">{unread_count} unread alert{"s" if unread_count != 1 else ""}</div>
        </div>
        <button class="btn btn-outline" onclick="markAllRead()">Mark All Read</button>
    </div>
    <div class="panel">
        {alert_items if all_alerts else '<div style="color:var(--muted);padding:1rem 0;">No alerts yet.</div>'}
    </div>
    '''

    extra_js = f'''
    function markRead(id) {{
        fetch('/api/mark_alert_read', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{alert_id: id}})
        }}).then(() => location.reload());
    }}
    function markAllRead() {{
        fetch('/api/mark_alerts_read', {{method: 'POST'}})
            .then(r => r.json()).then(d => {{ if (d.success) location.reload(); }});
    }}
    let _lastCount = {unread_count};
    setInterval(async () => {{
        try {{
            const r = await fetch('/api/alerts');
            const d = await r.json();
            const n = (d.alerts || []).filter(a => !a.is_read).length;
            if (n !== _lastCount) location.reload();
        }} catch (e) {{}}
    }}, 30000);
    '''

    return page_shell('Alerts', 'alerts', user, unread_count, body, extra_js=extra_js)


# ---------------------------------------------------------------------------
# /settings
# ---------------------------------------------------------------------------
@app.route('/settings')
@login_required
def settings():
    user = request.user
    unread_count = len(user.get_unread_alerts())
    s = user.settings

    notif_email = s.get('notification_email', user.email)
    ae = 'checked' if s.get('alert_email', True) else ''
    ac = 'checked' if s.get('alert_critical', True) else ''
    aw = 'checked' if s.get('alert_warning', True) else ''
    ai = 'checked' if s.get('alert_info', False) else ''

    comm_rows = ''
    for acc in MOCK_ACCOUNTS:
        key = acc['handle'].lstrip('@').replace('.', '_')
        val = s.get(f'commission_{key}', acc['commission'])
        comm_rows += f'''
        <div class="form-group" style="display:flex;align-items:center;gap:1rem;">
            <div style="display:flex;align-items:center;gap:0.5rem;width:180px;flex-shrink:0;">
                <div class="acc-dot" style="background:{acc['color']};"></div>
                <span style="font-size:0.9rem;">{acc['handle']}</span>
            </div>
            <input class="form-input" type="number" step="0.1" min="0" max="100"
                name="commission_{key}" value="{val}" style="max-width:120px;">
            <span style="color:var(--muted);font-size:0.85rem;">%</span>
        </div>'''

    color_swatches = ''.join([
        f'<div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.5rem;">'
        f'<div style="width:14px;height:14px;border-radius:3px;background:{acc["color"]};"></div>'
        f'<span style="font-size:0.85rem;">{acc["handle"]}</span>'
        f'<span style="color:var(--muted);font-size:0.78rem;margin-left:auto;">{acc["color"]}</span></div>'
        for acc in MOCK_ACCOUNTS
    ])

    body = f'''
    <div class="page-header">
        <div class="page-title">Settings</div>
        <div class="page-sub">Configure thresholds, notifications, and commission rates</div>
    </div>

    <form id="settingsForm">
        <div class="two-col">
            <div>
                <div class="panel" style="margin-bottom:1.5rem;">
                    <div class="panel-title">Commission Rates</div>
                    <div style="color:var(--muted);font-size:0.82rem;margin-bottom:1rem;">Manual override until TikTok API is live</div>
                    {comm_rows}
                </div>

                <div class="panel">
                    <div class="panel-title">Notifications</div>
                    <div class="form-group">
                        <label class="form-label">Notification Email</label>
                        <input class="form-input" type="email" name="notification_email" value="{notif_email}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Alert Types</label>
                        <label class="checkbox-row"><input type="checkbox" name="alert_email" {ae}> Email alerts</label>
                        <label class="checkbox-row"><input type="checkbox" name="alert_critical" {ac}> Critical alerts</label>
                        <label class="checkbox-row"><input type="checkbox" name="alert_warning" {aw}> Warning alerts</label>
                        <label class="checkbox-row"><input type="checkbox" name="alert_info" {ai}> Info alerts</label>
                    </div>
                </div>
            </div>

            <div class="panel">
                <div class="panel-title">Growth Objectives &amp; Alert Thresholds</div>
                <div style="color:var(--muted);font-size:0.82rem;margin-bottom:1.5rem;">Set monthly targets and alert triggers for performance monitoring</div>
                <div class="form-group">
                    <label class="form-label">GMV Monthly Target <span style="color:var(--success);">&#9679;</span></label>
                    <div style="position:relative;">
                        <span style="position:absolute;left:0.85rem;top:50%;transform:translateY(-50%);color:var(--muted);">$</span>
                        <input class="form-input" type="number" name="gmv_monthly_target" min="0" step="100" value="30000" style="padding-left:1.75rem;">
                    </div>
                    <div style="font-size:0.75rem;color:var(--success);margin-top:0.35rem;">&#10003; On track &mdash; currently at $27,690 (92.3%)</div>
                </div>
                <div class="form-group">
                    <label class="form-label">GMV Drop Alert</label>
                    <select class="form-input" name="gmv_drop_alert" style="cursor:pointer;">
                        <option value="10">Alert if GMV drops 10% in a week</option>
                        <option value="20" selected>Alert if GMV drops 20% in a week</option>
                        <option value="30">Alert if GMV drops 30% in a week</option>
                        <option value="custom">Custom threshold</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Monthly GMV Growth Target</label>
                    <div style="display:flex;align-items:center;gap:0.75rem;">
                        <input class="form-input" type="number" name="gmv_growth_target" min="0" max="200" step="1" value="15" style="max-width:120px;">
                        <span style="color:var(--muted);font-size:0.85rem;">% growth vs last month</span>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Monthly Views Growth Target</label>
                    <div style="display:flex;align-items:center;gap:0.75rem;">
                        <input class="form-input" type="number" name="views_growth_target" min="0" max="200" step="1" value="20" style="max-width:120px;">
                        <span style="color:var(--muted);font-size:0.85rem;">% growth vs last month</span>
                    </div>
                </div>
                <div style="margin-top:1.5rem;background:rgba(255,255,255,0.02);border-radius:10px;padding:1rem;border:1px solid var(--border);">
                    <div style="font-size:0.78rem;color:var(--muted);margin-bottom:0.75rem;text-transform:uppercase;letter-spacing:0.06em;">Account Colors</div>
                    {color_swatches}
                </div>
            </div>
        </div>

        <div style="margin-top:0.5rem;display:flex;align-items:center;gap:1rem;">
            <button type="submit" class="btn btn-primary">Save Settings</button>
            <span id="saveMsg" style="color:var(--success);font-weight:600;font-size:0.9rem;display:none;">&#10003; Saved</span>
        </div>
    </form>
    '''

    extra_js = '''
    document.getElementById('settingsForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const data = {
            notification_email: form.notification_email.value,
            alert_email: form.alert_email.checked,
            alert_critical: form.alert_critical.checked,
            alert_warning: form.alert_warning.checked,
            alert_info: form.alert_info.checked,
            gmv_monthly_target: parseFloat(form.gmv_monthly_target.value) || 30000,
            gmv_drop_alert: form.gmv_drop_alert.value,
            gmv_growth_target: parseFloat(form.gmv_growth_target.value) || 15,
            views_growth_target: parseFloat(form.views_growth_target.value) || 20,
        };
        form.querySelectorAll('input[name^="commission_"]').forEach(inp => {
            data[inp.name] = parseFloat(inp.value);
        });
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const json = await res.json();
        if (json.success) {
            const msg = document.getElementById('saveMsg');
            msg.style.display = 'inline';
            setTimeout(() => { msg.style.display = 'none'; }, 3000);
        }
    });
    '''

    return page_shell('Settings', 'settings', user, unread_count, body, extra_js=extra_js)


# ---------------------------------------------------------------------------
# /team
# ---------------------------------------------------------------------------
@app.route('/team')
@login_required
def team():
    user = request.user
    unread_count = len(user.get_unread_alerts())

    connected_accounts_html = ''
    for acc in MOCK_ACCOUNTS:
        status_color = '#10b981' if acc['status'] == 'Active' else '#f59e0b'
        connected_accounts_html += f'''
        <div style="display:flex;align-items:center;gap:0.85rem;padding:0.75rem 0;border-bottom:1px solid rgba(255,255,255,0.04);">
            <div class="acc-dot" style="background:{acc['color']};width:12px;height:12px;"></div>
            <div style="flex:1;">
                <div style="font-weight:600;font-size:0.9rem;">{acc['handle']}</div>
                <div style="color:var(--muted);font-size:0.78rem;">{acc['name']}</div>
            </div>
            <span style="font-size:0.78rem;color:{status_color};background:rgba(0,0,0,0.3);border:1px solid {status_color}33;border-radius:4px;padding:2px 8px;">{acc['status']}</span>
        </div>'''

    body = f'''
    <!-- Add Account Modal -->
    <div id="teamAddAccountModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:999;align-items:center;justify-content:center;">
        <div style="background:#111118;border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:2rem;max-width:400px;width:90%;position:relative;">
            <button onclick="document.getElementById('teamAddAccountModal').style.display='none'" style="position:absolute;top:1rem;right:1rem;background:none;border:none;color:var(--muted);font-size:1.2rem;cursor:pointer;">&#215;</button>
            <div style="font-size:1.5rem;margin-bottom:0.75rem;">&#128279;</div>
            <div style="font-size:1.1rem;font-weight:700;margin-bottom:0.5rem;">Coming Soon</div>
            <div style="color:var(--muted);font-size:0.9rem;line-height:1.5;">Connect your TikTok account to sync real data. This feature is coming in the next release.</div>
            <button onclick="document.getElementById('teamAddAccountModal').style.display='none'" class="btn btn-primary" style="margin-top:1.5rem;width:100%;justify-content:center;">Got it</button>
        </div>
    </div>

    <div class="page-header">
        <div class="page-title">Team</div>
        <div class="page-sub">Manage your organization, members, and connected accounts</div>
    </div>

    <!-- Organization -->
    <div class="panel" style="margin-bottom:1.5rem;">
        <div class="panel-title">Organization</div>
        <div style="display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap;">
            <div style="width:52px;height:52px;border-radius:50%;background:linear-gradient(135deg,#FF3B3B,#E53E3E);display:flex;align-items:center;justify-content:center;font-size:1.4rem;font-weight:900;color:#fff;flex-shrink:0;">P</div>
            <div>
                <div style="font-size:1.1rem;font-weight:700;">Peak Medium</div>
                <div style="color:var(--muted);font-size:0.85rem;margin-top:0.15rem;">Owned by Demo User &middot; demo@peakoverwatch.com</div>
            </div>
            <div style="margin-left:auto;">
                <span style="background:rgba(255,59,59,0.12);border:1px solid rgba(255,59,59,0.3);color:var(--accent);font-size:0.8rem;font-weight:700;padding:0.35rem 0.85rem;border-radius:20px;">Starter &mdash; 3 accounts</span>
            </div>
        </div>
    </div>

    <!-- Team Members -->
    <div class="panel" style="margin-bottom:1.5rem;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.25rem;">
            <div class="panel-title" style="margin-bottom:0;">Team Members</div>
            <button onclick="document.getElementById('inviteForm').style.display=document.getElementById('inviteForm').style.display==='none'?'block':'none'" style="background:transparent;border:1.5px solid rgba(255,255,255,0.15);color:var(--muted);padding:0.45rem 1rem;border-radius:8px;font-size:0.82rem;font-weight:600;cursor:pointer;transition:all 0.15s;" onmouseover="this.style.borderColor='rgba(255,255,255,0.3)';this.style.color='var(--text)'" onmouseout="this.style.borderColor='rgba(255,255,255,0.15)';this.style.color='var(--muted)'">+ Invite Member</button>
        </div>

        <table class="data-table" style="margin-bottom:1.25rem;">
            <thead>
                <tr>
                    <th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th>
                </tr>
            </thead>
            <tbody>
                <tr style="animation-delay:0ms;">
                    <td style="font-weight:600;">Demo User</td>
                    <td style="color:var(--muted);">demo@peakoverwatch.com</td>
                    <td><span style="background:rgba(255,59,59,0.1);color:var(--accent);font-size:0.75rem;font-weight:700;padding:2px 8px;border-radius:4px;">Owner</span></td>
                    <td><span class="badge badge-active">Active</span></td>
                    <td style="color:var(--muted);font-size:0.8rem;">&mdash;</td>
                </tr>
            </tbody>
        </table>

        <!-- Invite form (hidden by default) -->
        <div id="inviteForm" style="display:none;background:rgba(255,255,255,0.02);border:1px solid var(--border);border-radius:10px;padding:1.25rem;">
            <div style="font-size:0.85rem;font-weight:600;margin-bottom:1rem;">Invite a Team Member</div>
            <div style="display:grid;grid-template-columns:1fr 1fr auto;gap:0.75rem;align-items:end;flex-wrap:wrap;">
                <div>
                    <label class="form-label">Name</label>
                    <input class="form-input" type="text" id="inviteName" placeholder="Full name">
                </div>
                <div>
                    <label class="form-label">Email</label>
                    <input class="form-input" type="email" id="inviteEmail" placeholder="email@example.com">
                </div>
                <div>
                    <label class="form-label">Role</label>
                    <select class="form-input" id="inviteRole" style="cursor:pointer;">
                        <option value="Manager">Manager</option>
                        <option value="Viewer">Viewer</option>
                        <option value="Owner">Owner</option>
                    </select>
                </div>
            </div>
            <div style="margin-top:0.85rem;display:flex;align-items:center;gap:0.75rem;">
                <button onclick="submitInvite()" class="btn btn-primary">Send Invite</button>
                <button onclick="document.getElementById('inviteForm').style.display='none'" class="btn btn-outline">Cancel</button>
                <span id="inviteSuccess" style="display:none;color:var(--success);font-size:0.9rem;font-weight:600;">&#10003; Invite sent!</span>
            </div>
        </div>
    </div>

    <!-- Connected Accounts -->
    <div class="panel" style="margin-bottom:1.5rem;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.25rem;">
            <div class="panel-title" style="margin-bottom:0;">Connected Accounts</div>
            <button onclick="document.getElementById('teamAddAccountModal').style.display='flex'" style="background:transparent;border:1.5px solid var(--accent);color:var(--accent);padding:0.45rem 1rem;border-radius:8px;font-size:0.82rem;font-weight:600;cursor:pointer;transition:background 0.15s;" onmouseover="this.style.background='rgba(255,59,59,0.08)'" onmouseout="this.style.background='transparent'">+ Add Account</button>
        </div>
        {connected_accounts_html}
    </div>

    <!-- Upgrade note -->
    <div style="text-align:center;padding:1rem;color:var(--muted);font-size:0.82rem;">
        <span>&#128274; Upgrade to </span><strong style="color:var(--text);">Small Business</strong><span> for up to 5 accounts and 5 team members</span>
        <a href="#" style="color:var(--accent);text-decoration:none;margin-left:0.5rem;font-weight:600;">Learn more &#8594;</a>
    </div>
    '''

    extra_js = '''
    function submitInvite() {
        const name = document.getElementById('inviteName').value.trim();
        const email = document.getElementById('inviteEmail').value.trim();
        if (!name || !email) { alert('Please fill in name and email.'); return; }
        const success = document.getElementById('inviteSuccess');
        success.style.display = 'inline';
        document.getElementById('inviteName').value = '';
        document.getElementById('inviteEmail').value = '';
        setTimeout(() => { success.style.display = 'none'; document.getElementById('inviteForm').style.display = 'none'; }, 2500);
    }
    '''

    return page_shell('Team', 'team', user, unread_count, body, extra_js=extra_js)


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat(), 'version': '1.1.0'})


@app.route('/api/alerts')
@login_required
def api_alerts():
    user = request.user
    return jsonify({'alerts': alerts_store.get(user.id, [])})


@app.route('/api/mark_alert_read', methods=['POST'])
@login_required
def api_mark_alert_read():
    user = request.user
    data = request.json or {}
    alert_id = data.get('alert_id')
    success = user.mark_alert_read(alert_id) if alert_id else False
    return jsonify({'success': success})


@app.route('/api/mark_alerts_read', methods=['POST'])
@login_required
def api_mark_alerts_read():
    user = request.user
    with lock:
        for alert in alerts_store.get(user.id, []):
            alert['is_read'] = True
    return jsonify({'success': True})


@app.route('/api/settings', methods=['POST'])
@login_required
def api_settings():
    user = request.user
    data = request.json or {}
    allowed = [
        'notification_email', 'alert_email', 'alert_critical', 'alert_warning', 'alert_info',
        'commission_trendvault_us', 'commission_pickoftheday_co', 'commission_dailyfinds_hub',
        'gmv_monthly_target', 'gmv_drop_alert', 'gmv_growth_target', 'views_growth_target',
    ]
    for key in allowed:
        if key in data:
            user.settings[key] = data[key]
    return jsonify({'success': True})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5008))
    print(f"Peak Overwatch v1.1 — Rebuild")
    print(f"Running on port {port}")
    print(f"Demo: demo@peakoverwatch.com / password123")
    app.run(host='0.0.0.0', port=port, debug=False)
