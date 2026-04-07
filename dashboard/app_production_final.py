#!/usr/bin/env python3
"""
Peak Overwatch - Production Final Version (Spec v1.0 Rebuild)
Full UI rebuild: GMV hero, toggleable chart, animations
"""

from flask import Flask, render_template_string, redirect, request, jsonify, make_response
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
# Mock account data (spec v1.0)
# ---------------------------------------------------------------------------
MOCK_ACCOUNTS = [
    {
        'handle': '@trendvault_us',
        'name': 'Trend Vault US',
        'color': '#00C9A7',
        'gmv': 22600,
        'commission': 13.2,
        'videos': 847,
        'views': 2100000,
        'earnings': 2983,
        'status': 'Active',
        'fyp_score': 94,
    },
    {
        'handle': '@pickoftheday_co',
        'name': 'Pick of the Day',
        'color': '#8B5CF6',
        'gmv': 4200,
        'commission': 11.8,
        'videos': 312,
        'views': 480000,
        'earnings': 496,
        'status': 'Active',
        'fyp_score': 81,
    },
    {
        'handle': '@dailyfinds_hub',
        'name': 'Daily Finds Hub',
        'color': '#F59E0B',
        'gmv': 890,
        'commission': 14.5,
        'videos': 89,
        'views': 95000,
        'earnings': 129,
        'status': 'Warning',
        'fyp_score': 67,
    },
]

MOCK_PRODUCTS = [
    {'name': 'Stainless Steel Chef Knife Set', 'account': '@trendvault_us', 'color': '#00C9A7', 'units': 312, 'gmv': 8400, 'commission': 13.2},
    {'name': 'LED Strip Lights 32ft RGB', 'account': '@trendvault_us', 'color': '#00C9A7', 'units': 547, 'gmv': 6200, 'commission': 13.2},
    {'name': 'Wireless Earbuds Pro Max', 'account': '@pickoftheday_co', 'color': '#8B5CF6', 'units': 189, 'gmv': 2800, 'commission': 11.8},
    {'name': 'Bamboo Cutting Board Set', 'account': '@trendvault_us', 'color': '#00C9A7', 'units': 234, 'gmv': 2600, 'commission': 13.2},
    {'name': 'Portable Blender USB', 'account': '@trendvault_us', 'color': '#00C9A7', 'units': 178, 'gmv': 2100, 'commission': 13.2},
    {'name': 'Silicone Cooking Utensil Set', 'account': '@pickoftheday_co', 'color': '#8B5CF6', 'units': 145, 'gmv': 870, 'commission': 11.8},
    {'name': 'Yoga Mat Non-Slip Pro', 'account': '@dailyfinds_hub', 'color': '#F59E0B', 'units': 67, 'gmv': 540, 'commission': 14.5},
    {'name': 'Wall Art Canvas Prints', 'account': '@dailyfinds_hub', 'color': '#F59E0B', 'units': 43, 'gmv': 350, 'commission': 14.5},
]

MOCK_VIRAL_VIDEOS = [
    {'title': 'Chef Knife Set Full Review', 'account': '@trendvault_us', 'color': '#00C9A7', 'total_views': 1200000, 'views_this_month': 890000, 'date': '2026-03-12'},
    {'title': 'Home Decor Haul 2026', 'account': '@trendvault_us', 'color': '#00C9A7', 'total_views': 780000, 'views_this_month': 620000, 'date': '2026-03-18'},
    {'title': 'Best LED Lights Setup Ever', 'account': '@trendvault_us', 'color': '#00C9A7', 'total_views': 450000, 'views_this_month': 380000, 'date': '2026-03-22'},
    {'title': 'Top Kitchen Gadgets 2026', 'account': '@pickoftheday_co', 'color': '#8B5CF6', 'total_views': 210000, 'views_this_month': 180000, 'date': '2026-03-25'},
]


def fmt_views(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


def generate_gmv_series(days=30):
    """Generate per-account daily GMV for the last N days."""
    base = datetime.now() - timedelta(days=days)
    # Daily targets (monthly / days with some ramp-up)
    targets = [753, 140, 30]  # trendvault, pickoftheday, dailyfinds
    series = []
    rng = random.Random(42)  # seeded for consistency
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


def generate_90d_series():
    return generate_gmv_series(90)


def generate_monthly_bar_data():
    """Generate views per account per month for last 3 months."""
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
    """Generate videos posted per account per month for last 3 months."""
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


# ---------------------------------------------------------------------------
# User class
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
            # Commission rates per account (overrideable)
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
                user_list = list(users.values())
                for user in user_list:
                    s = user.settings
                    warn = s.get('fyp_threshold_warn', 70)
                    for acc in MOCK_ACCOUNTS:
                        score = acc['fyp_score']
                        if score < warn:
                            user.add_alert(
                                f'⚠️ Warning: {acc["handle"]}',
                                f'FYP score at {score}% — below warning threshold',
                                'warning'
                            )
                time.sleep(3600)  # Check hourly
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
# Shared UI pieces
# ---------------------------------------------------------------------------
COMMON_CSS = '''
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
    --bg: #0a0a0a;
    --surface: #111317;
    --surface2: #181b20;
    --border: rgba(255,255,255,0.07);
    --text: #e8eaed;
    --muted: #7a8090;
    --teal: #00C9A7;
    --purple: #8B5CF6;
    --orange: #F59E0B;
    --total-line: #E5E7EB;
    --success: #10b981;
    --warning: #f59e0b;
    --critical: #ef4444;
    --info: #60a5fa;
    --red: #FF0050;
    --accent: #00C9A7;
}
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: var(--bg);
    color: var(--text);
    opacity: 0;
    animation: fadeIn 0.35s ease forwards;
}
@keyframes fadeIn { to { opacity: 1; } }
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(18px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes staggerIn {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
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
    background: linear-gradient(135deg, var(--teal), #0080ff);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.85rem; font-weight: 900; color: #000; flex-shrink: 0;
}
.logo-text span { color: var(--teal); }
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
    background: rgba(0,201,167,0.1);
    color: var(--teal);
}
.nav-item.active::before {
    content: '';
    position: absolute; left: 0; top: 20%; bottom: 20%;
    width: 3px; border-radius: 0 3px 3px 0;
    background: var(--teal);
    transition: top 0.2s, bottom 0.2s;
}
.nav-icon { width: 18px; text-align: center; font-size: 0.95rem; }
.notif-badge {
    background: var(--red); color: #fff; border-radius: 10px;
    padding: 1px 6px; font-size: 0.7rem; font-weight: 700;
    margin-left: auto; min-width: 18px; text-align: center;
}
.sidebar-footer {
    padding: 1rem 1.25rem; border-top: 1px solid var(--border);
    font-size: 0.85rem;
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
.card:hover { transform: translateY(-3px); box-shadow: 0 8px 32px rgba(0,0,0,0.35); }
.metric-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.25rem; margin-bottom: 2rem; }
.metric-label { color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.5rem; }
.metric-value {
    font-size: 2.1rem; font-weight: 800; color: var(--text); line-height: 1;
    font-variant-numeric: tabular-nums;
}
.metric-sub { color: var(--muted); font-size: 0.8rem; margin-top: 0.4rem; }

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
    transition: opacity 0.2s, transform 0.1s;
    background: rgba(255,255,255,0.05);
}
.toggle-btn:hover { transform: scale(1.04); }
.toggle-btn.off { opacity: 0.35; }
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
.data-table tbody tr { transition: background 0.15s; }
.data-table tbody tr:hover { background: rgba(255,255,255,0.025); }

/* Account dot */
.acc-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.acc-cell { display: flex; align-items: center; gap: 0.5rem; }

/* Badges */
.badge {
    display: inline-block; padding: 0.2rem 0.6rem; border-radius: 20px;
    font-size: 0.75rem; font-weight: 700; letter-spacing: 0.02em;
}
.badge-active { background: rgba(16,185,129,0.15); color: #10b981; }
.badge-warning { background: rgba(245,158,11,0.15); color: #f59e0b; }
.badge-critical { background: rgba(239,68,68,0.15); color: #ef4444; }
.badge-info { background: rgba(96,165,250,0.15); color: var(--info); }
.badge-good { background: rgba(16,185,129,0.15); color: #10b981; }
.badge-warn { background: rgba(245,158,11,0.15); color: #f59e0b; }

/* Buttons */
.btn {
    display: inline-flex; align-items: center; gap: 0.4rem;
    padding: 0.55rem 1.1rem; border-radius: 8px; font-size: 0.875rem;
    font-weight: 600; cursor: pointer; border: none; text-decoration: none;
    transition: background 0.2s, transform 0.1s;
}
.btn:hover { transform: translateY(-1px); }
.btn-primary { background: var(--teal); color: #000; }
.btn-primary:hover { background: #00b396; }
.btn-outline {
    background: transparent; color: var(--muted);
    border: 1px solid var(--border);
}
.btn-outline:hover { color: var(--text); border-color: rgba(255,255,255,0.2); }

/* KPI card */
.kpi-card {
    background: linear-gradient(135deg, rgba(0,201,167,0.1), rgba(0,128,255,0.05));
    border: 1px solid rgba(0,201,167,0.2); border-radius: 14px;
    padding: 1.25rem 1.5rem; margin-bottom: 1.5rem;
    display: inline-flex; align-items: center; gap: 1rem;
}
.kpi-number { font-size: 2.5rem; font-weight: 800; color: var(--teal); line-height: 1; }
.kpi-label { font-size: 0.9rem; color: var(--muted); }

/* Two-col layout */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
.three-col { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1.5rem; }

/* Alert items */
.alert-row {
    background: rgba(255,255,255,0.02); border: 1px solid var(--border);
    border-left: 3px solid var(--muted); border-radius: 10px;
    padding: 1rem 1.25rem; margin-bottom: 0.75rem;
}
.alert-row.critical { border-left-color: var(--critical); }
.alert-row.warning { border-left-color: var(--warning); }
.alert-row.info { border-left-color: var(--info); }
.alert-row.read { opacity: 0.45; }

/* Form */
.form-group { margin-bottom: 1.25rem; }
.form-label { display: block; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-bottom: 0.5rem; }
.form-input {
    width: 100%; padding: 0.65rem 0.85rem;
    background: rgba(255,255,255,0.04); border: 1px solid var(--border);
    border-radius: 8px; color: var(--text); font-size: 0.9rem;
    transition: border-color 0.2s;
}
.form-input:focus { outline: none; border-color: var(--teal); }
.form-input[type=number] { -moz-appearance: textfield; }
.form-input[type=number]::-webkit-inner-spin-button { opacity: 0.3; }
.checkbox-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.4rem 0; cursor: pointer; }
input[type=checkbox] { width: 15px; height: 15px; accent-color: var(--teal); }
.slider-row { display: flex; align-items: center; gap: 1rem; }
.slider-val { font-weight: 700; color: var(--teal); min-width: 3rem; text-align: right; }
input[type=range] { flex: 1; -webkit-appearance: none; height: 5px; border-radius: 3px; background: rgba(255,255,255,0.1); cursor: pointer; }
input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 16px; height: 16px; border-radius: 50%; background: var(--teal); }

/* Responsive */
@media (max-width: 1100px) { .metric-cards { grid-template-columns: repeat(2, 1fr); } .two-col, .three-col { grid-template-columns: 1fr; } }
@media (max-width: 768px) { .sidebar { display: none; } .main { margin-left: 0; padding: 1rem; } .metric-cards { grid-template-columns: 1fr 1fr; } }
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


def sidebar_html(active_page, user, unread_count=0):
    pages = [
        ('dashboard', '/dashboard', '⊞', 'Dashboard'),
        ('accounts', '/accounts', '◈', 'Accounts'),
        ('analytics', '/analytics', '▦', 'Analytics'),
        ('alerts', '/alerts', '◎', 'Alerts'),
        ('settings', '/settings', '⚙', 'Settings'),
    ]
    links = ''
    for key, href, icon, label in pages:
        active_cls = ' active' if key == active_page else ''
        badge = ''
        if key == 'alerts' and unread_count > 0:
            badge = f'<span class="notif-badge">{unread_count}</span>'
        links += f'''<a href="{href}" class="nav-item{active_cls}">
            <span class="nav-icon">{icon}</span>
            <span>{label}</span>
            {badge}
        </a>\n'''
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
    <title>Peak Overwatch • {title}</title>
    {chartjs_tag}
    <style>
        {COMMON_CSS}
        {extra_css}
    </style>
</head>
<body>
    {sidebar_html(active_page, user, unread_count)}
    <main class="main">
        {body_html}
    </main>
    <script>
        {COUNTER_JS}
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
    <title>Peak Overwatch — Sign In</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #0a0a0a; color: #e8eaed;
            display: flex; align-items: center; justify-content: center;
            min-height: 100vh;
            opacity: 0; animation: f 0.4s ease forwards;
        }
        @keyframes f { to { opacity: 1; } }
        .box {
            background: #111317; border: 1px solid rgba(255,255,255,0.07);
            border-radius: 18px; padding: 2.25rem; width: 340px;
        }
        .logo { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.5rem; }
        .logo-mark { width: 30px; height: 30px; border-radius: 8px; background: linear-gradient(135deg, #00C9A7, #0080ff); display: flex; align-items: center; justify-content: center; font-weight: 900; color: #000; font-size: 0.9rem; }
        .logo-text { font-size: 1.15rem; font-weight: 800; }
        .logo-text span { color: #00C9A7; }
        .tagline { color: #7a8090; font-size: 0.85rem; margin-bottom: 2rem; }
        label { display: block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; color: #7a8090; margin-bottom: 0.4rem; }
        input { width: 100%; padding: 0.7rem 0.9rem; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); border-radius: 9px; color: #e8eaed; font-size: 0.9rem; margin-bottom: 1rem; transition: border-color 0.2s; }
        input:focus { outline: none; border-color: #00C9A7; }
        .submit { width: 100%; padding: 0.8rem; background: #00C9A7; color: #000; font-weight: 700; font-size: 0.95rem; border: none; border-radius: 9px; cursor: pointer; margin-top: 0.5rem; transition: background 0.2s; }
        .submit:hover { background: #00b396; }
        .hint { font-size: 0.78rem; color: #7a8090; margin-top: 1.25rem; text-align: center; }
        .err { color: #ef4444; font-size: 0.85rem; margin-top: 0.5rem; display: none; }
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
            btn.textContent = 'Signing in...';
            btn.disabled = true;
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

    total_gmv = 27690
    total_commission = 3608
    total_views_m = 2.675
    active_accounts = 3

    # GMV series (30d)
    series = generate_gmv_series(30)
    labels = [d['date'] for d in series]
    ds_tv = [d['@trendvault_us'] for d in series]
    ds_po = [d['@pickoftheday_co'] for d in series]
    ds_dh = [d['@dailyfinds_hub'] for d in series]
    ds_total = [d['total'] for d in series]

    # Hero products
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
                <div style="font-weight:700;font-size:0.9rem;color:var(--teal);">{fmt_views(v['views_this_month'])}</div>
                <div style="color:var(--muted);font-size:0.75rem;">this month</div>
            </div>
        </div>'''

    body = f'''
    <div class="page-header">
        <div class="page-title">Dashboard</div>
        <div class="page-sub">Portfolio overview · {datetime.now().strftime("%B %Y")}</div>
    </div>

    <div class="metric-cards">
        <div class="card">
            <div class="metric-label">Total GMV</div>
            <div class="metric-value" data-counter="{total_gmv}" data-prefix="$">$0</div>
            <div class="metric-sub">↑ 14% vs last month</div>
        </div>
        <div class="card">
            <div class="metric-label">Est. Commission</div>
            <div class="metric-value" data-counter="{total_commission}" data-prefix="$">$0</div>
            <div class="metric-sub">Across 3 accounts</div>
        </div>
        <div class="card">
            <div class="metric-label">Total Views</div>
            <div class="metric-value" data-counter="{total_views_m}" data-suffix="M">0M</div>
            <div class="metric-sub">847 videos this month</div>
        </div>
        <div class="card">
            <div class="metric-label">Active Accounts</div>
            <div class="metric-value" data-counter="{active_accounts}">0</div>
            <div class="metric-sub">All monitored</div>
        </div>
    </div>

    <!-- Main chart -->
    <div class="panel" style="margin-bottom:1.5rem;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
            <div class="panel-title" style="margin-bottom:0;">GMV Trend · Last 30 Days</div>
        </div>
        <div class="chart-toggles" id="gmvToggles">
            <button class="toggle-btn" data-idx="0" style="color:#00C9A7;border-color:#00C9A7;background:rgba(0,201,167,0.1);">
                <span class="toggle-dot" style="background:#00C9A7;"></span>@trendvault_us
            </button>
            <button class="toggle-btn" data-idx="1" style="color:#8B5CF6;border-color:#8B5CF6;background:rgba(139,92,246,0.1);">
                <span class="toggle-dot" style="background:#8B5CF6;"></span>@pickoftheday_co
            </button>
            <button class="toggle-btn" data-idx="2" style="color:#F59E0B;border-color:#F59E0B;background:rgba(245,158,11,0.1);">
                <span class="toggle-dot" style="background:#F59E0B;"></span>@dailyfinds_hub
            </button>
            <button class="toggle-btn" data-idx="3" style="color:#E5E7EB;border-color:rgba(229,231,235,0.3);background:rgba(229,231,235,0.05);">
                <span class="toggle-dot" style="background:#E5E7EB;"></span>Total
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
            <div style="color:var(--muted);font-size:0.8rem;margin-bottom:0.5rem;">≥50K views delta</div>
            {viral_html}
        </div>
    </div>
    '''

    extra_js = f'''
    const gmvLabels = {json.dumps(labels)};
    const gmvData = [
        {{ label: '@trendvault_us', data: {json.dumps(ds_tv)}, borderColor: '#00C9A7', backgroundColor: 'rgba(0,201,167,0.08)', tension: 0.4, pointRadius: 0, pointHoverRadius: 4, borderWidth: 2 }},
        {{ label: '@pickoftheday_co', data: {json.dumps(ds_po)}, borderColor: '#8B5CF6', backgroundColor: 'rgba(139,92,246,0.08)', tension: 0.4, pointRadius: 0, pointHoverRadius: 4, borderWidth: 2 }},
        {{ label: '@dailyfinds_hub', data: {json.dumps(ds_dh)}, borderColor: '#F59E0B', backgroundColor: 'rgba(245,158,11,0.08)', tension: 0.4, pointRadius: 0, pointHoverRadius: 4, borderWidth: 2 }},
        {{ label: 'Total', data: {json.dumps(ds_total)}, borderColor: '#E5E7EB', backgroundColor: 'rgba(229,231,235,0.04)', tension: 0.4, pointRadius: 0, pointHoverRadius: 4, borderWidth: 1.5, borderDash: [4,3] }},
    ];
    const gmvChart = new Chart(document.getElementById('gmvChart').getContext('2d'), {{
        type: 'line',
        data: {{ labels: gmvLabels, datasets: gmvData }},
        options: {{
            maintainAspectRatio: false,
            animation: {{ duration: 1000, easing: 'easeInOutQuart' }},
            interaction: {{ intersect: false, mode: 'index' }},
            plugins: {{
                legend: {{ display: false }},
                tooltip: {{
                    backgroundColor: '#181b20',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {{
                        label: ctx => ' ' + ctx.dataset.label + ': $' + ctx.parsed.y.toLocaleString()
                    }}
                }}
            }},
            scales: {{
                x: {{ ticks: {{ color: '#7a8090', maxTicksLimit: 10 }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }},
                y: {{
                    ticks: {{ color: '#7a8090', callback: v => '$' + (v >= 1000 ? (v/1000).toFixed(0)+'k' : v) }},
                    grid: {{ color: 'rgba(255,255,255,0.04)' }}
                }}
            }}
        }}
    }});

    document.querySelectorAll('.toggle-btn').forEach(btn => {{
        btn.addEventListener('click', function() {{
            const idx = parseInt(this.dataset.idx);
            const meta = gmvChart.getDatasetMeta(idx);
            meta.hidden = !meta.hidden;
            this.classList.toggle('off', meta.hidden);
            gmvChart.update();
        }});
    }});
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
            return f'<span class="badge badge-good">{score}%</span>'
        elif score >= 70:
            return f'<span class="badge badge-warn">{score}%</span>'
        return f'<span class="badge badge-critical">{score}%</span>'

    def status_badge(status):
        cls = {'Active': 'badge-active', 'Warning': 'badge-warning', 'Inactive': 'badge-critical'}.get(status, 'badge-info')
        return f'<span class="badge {cls}">{status}</span>'

    rows = ''
    for i, acc in enumerate(MOCK_ACCOUNTS):
        commission = user.get_commission(acc['handle'])
        earnings = int(acc['gmv'] * commission / 100)
        delay = i * 0.08
        rows += f'''
        <tr style="animation: staggerIn 0.4s ease {delay:.2f}s both;">
            <td>
                <div class="acc-cell">
                    <div class="acc-dot" style="background:{acc['color']};width:12px;height:12px;"></div>
                    <div>
                        <div style="font-weight:600;">{acc['handle']}</div>
                        <div style="color:var(--muted);font-size:0.78rem;">{acc['name']}</div>
                    </div>
                </div>
            </td>
            <td style="font-weight:700;">${acc['gmv']:,}</td>
            <td>{commission:.1f}%</td>
            <td style="color:var(--teal);font-weight:600;">${earnings:,}</td>
            <td>{acc['videos']:,}</td>
            <td>{fmt_views(acc['views'])}</td>
            <td>{status_badge(acc['status'])}</td>
            <td>{fyp_badge(acc['fyp_score'])}</td>
        </tr>'''

    body = f'''
    <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div>
            <div class="page-title">Accounts</div>
            <div class="page-sub">TikTok Shop accounts and performance metrics</div>
        </div>
    </div>

    <div class="panel">
        <table class="data-table">
            <thead>
                <tr>
                    <th>Account</th>
                    <th>GMV (Month)</th>
                    <th>Avg Commission</th>
                    <th>Est. Earnings</th>
                    <th>Videos Posted</th>
                    <th>Total Views</th>
                    <th>Status</th>
                    <th>FYP Score</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>

    <div class="two-col">
        <div class="panel">
            <div class="panel-title">GMV by Account</div>
            <div style="position:relative;height:220px;"><canvas id="accGmvChart"></canvas></div>
        </div>
        <div class="panel">
            <div class="panel-title">Views by Account</div>
            <div style="position:relative;height:220px;"><canvas id="accViewsChart"></canvas></div>
        </div>
    </div>
    '''

    gmvs = [acc['gmv'] for acc in MOCK_ACCOUNTS]
    views = [acc['views'] for acc in MOCK_ACCOUNTS]
    handles = [acc['handle'] for acc in MOCK_ACCOUNTS]
    colors = [acc['color'] for acc in MOCK_ACCOUNTS]

    extra_js = f'''
    const accLabels = {json.dumps(handles)};
    const accColors = {json.dumps(colors)};
    new Chart(document.getElementById('accGmvChart'), {{
        type: 'bar',
        data: {{ labels: accLabels, datasets: [{{ data: {json.dumps(gmvs)}, backgroundColor: accColors, borderRadius: 6 }}] }},
        options: {{
            maintainAspectRatio: false,
            animation: {{ duration: 1000, easing: 'easeInOutQuart' }},
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
                x: {{ ticks: {{ color: '#7a8090', font: {{size: 11}} }}, grid: {{ display: false }} }},
                y: {{ ticks: {{ color: '#7a8090', callback: v => '$' + v.toLocaleString() }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }}
            }}
        }}
    }});
    new Chart(document.getElementById('accViewsChart'), {{
        type: 'bar',
        data: {{ labels: accLabels, datasets: [{{ data: {json.dumps(views)}, backgroundColor: accColors, borderRadius: 6 }}] }},
        options: {{
            maintainAspectRatio: false,
            animation: {{ duration: 1000, easing: 'easeInOutQuart' }},
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
                x: {{ ticks: {{ color: '#7a8090', font: {{size: 11}} }}, grid: {{ display: false }} }},
                y: {{ ticks: {{ color: '#7a8090', callback: v => v >= 1000000 ? (v/1000000).toFixed(1)+'M' : v >= 1000 ? (v/1000).toFixed(0)+'K' : v }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }}
            }}
        }}
    }});
    '''

    return page_shell('Accounts', 'accounts', user, unread_count, body, extra_js=extra_js, load_chartjs=True)


# ---------------------------------------------------------------------------
# /analytics
# ---------------------------------------------------------------------------
@app.route('/analytics')
@login_required
def analytics():
    user = request.user
    unread_count = len(user.get_unread_alerts())

    # 90-day GMV series
    series90 = generate_gmv_series(90)
    labels90 = [d['date'] for d in series90]
    ds90_tv = [d['@trendvault_us'] for d in series90]
    ds90_po = [d['@pickoftheday_co'] for d in series90]
    ds90_dh = [d['@dailyfinds_hub'] for d in series90]
    ds90_total = [d['total'] for d in series90]

    months, views_data = generate_monthly_bar_data()
    _, videos_data = generate_monthly_video_data()

    handles = [acc['handle'] for acc in MOCK_ACCOUNTS]
    colors = [acc['color'] for acc in MOCK_ACCOUNTS]

    views_datasets = json.dumps([
        {'label': acc['handle'], 'data': views_data[acc['handle']], 'backgroundColor': acc['color'], 'borderRadius': 5}
        for acc in MOCK_ACCOUNTS
    ])
    videos_datasets = json.dumps([
        {'label': acc['handle'], 'data': videos_data[acc['handle']], 'backgroundColor': acc['color'], 'borderRadius': 5}
        for acc in MOCK_ACCOUNTS
    ])

    # Products table
    product_rows = ''
    for p in MOCK_PRODUCTS:
        product_rows += f'''<tr>
            <td>
                <div class="acc-cell">
                    <div class="acc-dot" style="background:{p['color']};"></div>
                    {p['name']}
                </div>
            </td>
            <td style="color:var(--muted);">{p['account']}</td>
            <td>{p['units']:,}</td>
            <td style="font-weight:600;">${p['gmv']:,}</td>
            <td>{p['commission']}%</td>
        </tr>'''

    # Viral videos table
    viral_rows = ''
    for v in MOCK_VIRAL_VIDEOS:
        viral_rows += f'''<tr>
            <td style="max-width:260px;">{v['title']}</td>
            <td>
                <div class="acc-cell">
                    <div class="acc-dot" style="background:{v['color']};"></div>
                    {v['account']}
                </div>
            </td>
            <td>{fmt_views(v['total_views'])}</td>
            <td style="color:var(--teal);font-weight:600;">{fmt_views(v['views_this_month'])}</td>
            <td style="color:var(--muted);">{v['date']}</td>
        </tr>'''

    body = f'''
    <div class="page-header">
        <div class="page-title">Analytics</div>
        <div class="page-sub">Deep-dive performance across all accounts · 90-day window</div>
    </div>

    <!-- Section 1: GMV Trend 90d -->
    <div class="panel">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
            <div class="panel-title" style="margin-bottom:0;">GMV Trend · Last 90 Days</div>
        </div>
        <div class="chart-toggles" id="gmvToggles90">
            <button class="toggle-btn" data-idx="0" style="color:#00C9A7;border-color:#00C9A7;background:rgba(0,201,167,0.1);">
                <span class="toggle-dot" style="background:#00C9A7;"></span>@trendvault_us
            </button>
            <button class="toggle-btn" data-idx="1" style="color:#8B5CF6;border-color:#8B5CF6;background:rgba(139,92,246,0.1);">
                <span class="toggle-dot" style="background:#8B5CF6;"></span>@pickoftheday_co
            </button>
            <button class="toggle-btn" data-idx="2" style="color:#F59E0B;border-color:#F59E0B;background:rgba(245,158,11,0.1);">
                <span class="toggle-dot" style="background:#F59E0B;"></span>@dailyfinds_hub
            </button>
            <button class="toggle-btn" data-idx="3" style="color:#E5E7EB;border-color:rgba(229,231,235,0.3);background:rgba(229,231,235,0.05);">
                <span class="toggle-dot" style="background:#E5E7EB;"></span>Total
            </button>
        </div>
        <div class="chart-wrap" style="height:280px;"><canvas id="gmv90Chart"></canvas></div>
    </div>

    <!-- Section 2 & 3: Views + Videos bar charts -->
    <div class="two-col">
        <div class="panel">
            <div class="panel-title">Views per Account · Monthly</div>
            <div style="position:relative;height:240px;"><canvas id="viewsBarChart"></canvas></div>
        </div>
        <div class="panel">
            <div class="panel-title">Videos Posted · Monthly</div>
            <div style="position:relative;height:240px;"><canvas id="videosBarChart"></canvas></div>
        </div>
    </div>

    <!-- Section 4: Revenue source donut -->
    <div class="panel" style="max-width:500px;">
        <div class="panel-title">Revenue Source Breakdown</div>
        <div style="display:flex;align-items:center;gap:2rem;">
            <div style="position:relative;height:200px;width:200px;flex-shrink:0;"><canvas id="donutChart"></canvas></div>
            <div>
                <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.75rem;">
                    <div style="width:12px;height:12px;border-radius:2px;background:#00C9A7;"></div>
                    <div>Videos <strong>78%</strong></div>
                </div>
                <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.75rem;">
                    <div style="width:12px;height:12px;border-radius:2px;background:#8B5CF6;"></div>
                    <div>Shop Ads <strong>19%</strong></div>
                </div>
                <div style="display:flex;align-items:center;gap:0.6rem;">
                    <div style="width:12px;height:12px;border-radius:2px;background:#F59E0B;"></div>
                    <div>LIVE <strong>3%</strong></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Section 5: Products -->
    <div class="panel">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.25rem;">
            <div class="panel-title" style="margin-bottom:0;">Products</div>
            <div style="background:rgba(0,201,167,0.1);border:1px solid rgba(0,201,167,0.2);padding:0.4rem 1rem;border-radius:20px;font-size:0.85rem;">
                <strong style="color:var(--teal);">47</strong> <span style="color:var(--muted);">unique products this month</span>
            </div>
        </div>
        <div class="section-label">Top 3 Hero Products</div>
        <div style="display:flex;gap:1rem;margin-bottom:1.5rem;flex-wrap:wrap;">
            {' '.join([f'''<div style="flex:1;min-width:180px;background:rgba(255,255,255,0.03);border:1px solid var(--border);border-radius:10px;padding:1rem;">
                <div class="acc-cell" style="margin-bottom:0.4rem;">
                    <div class="acc-dot" style="background:{MOCK_PRODUCTS[i]['color']};"></div>
                    <div style="font-size:0.75rem;color:var(--muted);">{MOCK_PRODUCTS[i]['account']}</div>
                </div>
                <div style="font-size:0.85rem;font-weight:600;margin-bottom:0.5rem;line-height:1.3;">{MOCK_PRODUCTS[i]['name']}</div>
                <div style="font-size:1.25rem;font-weight:800;color:var(--teal);">${MOCK_PRODUCTS[i]['gmv']:,}</div>
                <div style="color:var(--muted);font-size:0.78rem;">{MOCK_PRODUCTS[i]['units']} units</div>
            </div>''' for i in range(3)])}
        </div>
        <div class="section-label">All Products</div>
        <table class="data-table">
            <thead>
                <tr><th>Product</th><th>Account</th><th>Units</th><th>GMV</th><th>Commission</th></tr>
            </thead>
            <tbody>{product_rows}</tbody>
        </table>
    </div>

    <!-- Section 6: Viral Videos -->
    <div class="panel">
        <div class="kpi-card" style="margin-bottom:1.25rem;">
            <div class="kpi-number">4</div>
            <div>
                <div style="font-weight:700;font-size:1rem;">Viral Videos This Month</div>
                <div class="kpi-label">Videos with ≥50K views delta</div>
            </div>
        </div>
        <table class="data-table">
            <thead>
                <tr><th>Video</th><th>Account</th><th>Total Views</th><th>Views This Month</th><th>Date</th></tr>
            </thead>
            <tbody>{viral_rows}</tbody>
        </table>
    </div>
    '''

    extra_js = f'''
    // GMV 90-day chart
    const gmv90Chart = new Chart(document.getElementById('gmv90Chart'), {{
        type: 'line',
        data: {{
            labels: {json.dumps(labels90)},
            datasets: [
                {{ label: '@trendvault_us', data: {json.dumps(ds90_tv)}, borderColor: '#00C9A7', backgroundColor: 'rgba(0,201,167,0.06)', tension: 0.4, pointRadius: 0, borderWidth: 2 }},
                {{ label: '@pickoftheday_co', data: {json.dumps(ds90_po)}, borderColor: '#8B5CF6', backgroundColor: 'rgba(139,92,246,0.06)', tension: 0.4, pointRadius: 0, borderWidth: 2 }},
                {{ label: '@dailyfinds_hub', data: {json.dumps(ds90_dh)}, borderColor: '#F59E0B', backgroundColor: 'rgba(245,158,11,0.06)', tension: 0.4, pointRadius: 0, borderWidth: 2 }},
                {{ label: 'Total', data: {json.dumps(ds90_total)}, borderColor: '#E5E7EB', backgroundColor: 'rgba(229,231,235,0.03)', tension: 0.4, pointRadius: 0, borderWidth: 1.5, borderDash: [4,3] }},
            ]
        }},
        options: {{
            maintainAspectRatio: false,
            animation: {{ duration: 1000, easing: 'easeInOutQuart' }},
            interaction: {{ intersect: false, mode: 'index' }},
            plugins: {{
                legend: {{ display: false }},
                tooltip: {{ backgroundColor: '#181b20', borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1, padding: 10,
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

    // Views bar chart
    new Chart(document.getElementById('viewsBarChart'), {{
        type: 'bar',
        data: {{
            labels: {json.dumps(months)},
            datasets: {views_datasets}
        }},
        options: {{
            maintainAspectRatio: false,
            animation: {{ duration: 1000, easing: 'easeInOutQuart' }},
            plugins: {{
                legend: {{ labels: {{ color: '#7a8090', font: {{size: 11}}, boxWidth: 10 }} }}
            }},
            scales: {{
                x: {{ stacked: false, ticks: {{ color: '#7a8090' }}, grid: {{ display: false }} }},
                y: {{ ticks: {{ color: '#7a8090', callback: v => v >= 1000000 ? (v/1000000).toFixed(1)+'M' : v >= 1000 ? (v/1000).toFixed(0)+'K' : v }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }}
            }}
        }}
    }});

    // Videos bar chart
    new Chart(document.getElementById('videosBarChart'), {{
        type: 'bar',
        data: {{
            labels: {json.dumps(months)},
            datasets: {videos_datasets}
        }},
        options: {{
            maintainAspectRatio: false,
            animation: {{ duration: 1000, easing: 'easeInOutQuart' }},
            plugins: {{
                legend: {{ labels: {{ color: '#7a8090', font: {{size: 11}}, boxWidth: 10 }} }}
            }},
            scales: {{
                x: {{ stacked: false, ticks: {{ color: '#7a8090' }}, grid: {{ display: false }} }},
                y: {{ ticks: {{ color: '#7a8090' }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }}
            }}
        }}
    }});

    // Donut chart
    new Chart(document.getElementById('donutChart'), {{
        type: 'doughnut',
        data: {{
            labels: ['Videos', 'Shop Ads', 'LIVE'],
            datasets: [{{ data: [78, 19, 3], backgroundColor: ['#00C9A7', '#8B5CF6', '#F59E0B'], borderWidth: 0, hoverOffset: 6 }}]
        }},
        options: {{
            maintainAspectRatio: false,
            animation: {{ duration: 1000, easing: 'easeInOutQuart' }},
            plugins: {{ legend: {{ display: false }}, tooltip: {{ backgroundColor: '#181b20', borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1 }} }},
            cutout: '68%'
        }}
    }});
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
        user.add_alert('👋 Welcome', 'Your real-time performance alerts will appear here.', 'info')
        user.add_alert('📊 FYP Warning: @dailyfinds_hub', 'FYP score at 67% — below warning threshold of 70%.', 'warning')
        all_alerts = alerts_store.get(user.id, [])

    unread_count = len([a for a in all_alerts if not a['is_read']])

    alert_items = ''
    for alert in reversed(all_alerts):
        level = alert.get('level', 'info')
        is_read = alert.get('is_read', False)
        read_cls = ' read' if is_read else ''
        ts = alert.get('created_at', '')[:16].replace('T', ' ')
        badge_cls = {'critical': 'badge-critical', 'warning': 'badge-warn', 'info': 'badge-info'}.get(level, 'badge-info')
        read_btn = '' if is_read else f'<button onclick="markRead(\'{alert["id"]}\')" style="margin-top:0.6rem;background:none;border:1px solid var(--border);color:var(--muted);padding:0.25rem 0.6rem;border-radius:6px;cursor:pointer;font-size:0.78rem;transition:border-color 0.2s;">Mark read</button>'
        alert_items += f'''
        <div class="alert-row {level}{read_cls}" id="alert-{alert['id']}">
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
    fyp_good = s.get('fyp_threshold_good', 80)
    fyp_warn = s.get('fyp_threshold_warn', 70)
    fyp_crit = s.get('fyp_threshold_critical', 60)
    ae = 'checked' if s.get('alert_email', True) else ''
    ac = 'checked' if s.get('alert_critical', True) else ''
    aw = 'checked' if s.get('alert_warning', True) else ''
    ai = 'checked' if s.get('alert_info', False) else ''

    # Commission rows
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
                <div class="panel-title">FYP Score Thresholds</div>
                <div style="color:var(--muted);font-size:0.82rem;margin-bottom:1.5rem;">Set alert trigger levels for FYP score changes</div>
                <div class="form-group">
                    <label class="form-label">Good <span style="color:var(--success);">●</span></label>
                    <div class="slider-row">
                        <input type="range" name="fyp_threshold_good" min="50" max="100" value="{fyp_good}"
                            oninput="document.getElementById('vg').textContent=this.value+'%'">
                        <span class="slider-val" id="vg">{fyp_good}%</span>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Warning <span style="color:var(--warning);">●</span></label>
                    <div class="slider-row">
                        <input type="range" name="fyp_threshold_warn" min="50" max="100" value="{fyp_warn}"
                            oninput="document.getElementById('vw').textContent=this.value+'%'">
                        <span class="slider-val" id="vw">{fyp_warn}%</span>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Critical <span style="color:var(--critical);">●</span></label>
                    <div class="slider-row">
                        <input type="range" name="fyp_threshold_critical" min="50" max="100" value="{fyp_crit}"
                            oninput="document.getElementById('vc').textContent=this.value+'%'">
                        <span class="slider-val" id="vc">{fyp_crit}%</span>
                    </div>
                </div>
                <div style="margin-top:2rem;background:rgba(255,255,255,0.02);border-radius:10px;padding:1rem;border:1px solid var(--border);">
                    <div style="font-size:0.78rem;color:var(--muted);margin-bottom:0.75rem;text-transform:uppercase;letter-spacing:0.06em;">Account Colors</div>
                    {"".join([f'<div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.5rem;"><div style="width:14px;height:14px;border-radius:3px;background:{acc["color"]};"></div><span style="font-size:0.85rem;">{acc["handle"]}</span><span style="color:var(--muted);font-size:0.78rem;margin-left:auto;">{acc["color"]}</span></div>' for acc in MOCK_ACCOUNTS])}
                </div>
            </div>
        </div>

        <div style="margin-top:0.5rem;display:flex;align-items:center;gap:1rem;">
            <button type="submit" class="btn btn-primary">Save Settings</button>
            <span id="saveMsg" style="color:var(--success);font-weight:600;font-size:0.9rem;display:none;">✓ Saved</span>
        </div>
    </form>
    '''

    extra_js = '''
    document.getElementById('settingsForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const data = {
            notification_email: form.notification_email.value,
            fyp_threshold_good: parseInt(form.fyp_threshold_good.value),
            fyp_threshold_warn: parseInt(form.fyp_threshold_warn.value),
            fyp_threshold_critical: parseInt(form.fyp_threshold_critical.value),
            alert_email: form.alert_email.checked,
            alert_critical: form.alert_critical.checked,
            alert_warning: form.alert_warning.checked,
            alert_info: form.alert_info.checked,
        };
        // Commission rates
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
# API routes
# ---------------------------------------------------------------------------
@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat(), 'version': '1.0.0'})


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
        'notification_email', 'fyp_threshold_good', 'fyp_threshold_warn',
        'fyp_threshold_critical', 'alert_email', 'alert_critical', 'alert_warning', 'alert_info',
        'commission_trendvault_us', 'commission_pickoftheday_co', 'commission_dailyfinds_hub',
    ]
    for key in allowed:
        if key in data:
            user.settings[key] = data[key]
    return jsonify({'success': True})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5008))
    print(f"🚀 Peak Overwatch v1.0 — Spec Rebuild")
    print(f"📡 Running on port {port}")
    print(f"👤 Demo: demo@peakoverwatch.com / password123")
    app.run(host='0.0.0.0', port=port, debug=False)
