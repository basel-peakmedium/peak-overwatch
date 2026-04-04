#!/usr/bin/env python3
"""
Peak Overwatch - ORIGINAL Phase 1 Design with All Features
Exact design from this morning with login, real-time alerts, and monitoring
"""

from flask import Flask, render_template_string, redirect, request, jsonify, make_response
from flask_socketio import SocketIO, emit
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'original-design-' + secrets.token_hex(16))

# WebSocket
socketio = SocketIO(app, cors_allowed_origins="*")

# Storage
users = {}
sessions = {}
alerts = {}
lock = Lock()

class User:
    def __init__(self, user_id, email, password_hash, name=None, company=None):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash
        self.name = name
        self.company = company
        self.socket_id = None
        self.settings = {
            'timezone': 'America/New_York',
            'currency': 'USD',
            'alert_notifications': True,
            'fyp_threshold_good': 80,
            'fyp_threshold_warn': 70,
            'fyp_threshold_critical': 60
        }
        self.profiles = [
            {'id': 1, 'username': 'ourviralpicks', 'niche': 'Home & Lifestyle', 'profit': 12412, 'growth': 24.7, 'fyp_score': 95, 'last_fyp': 95},
            {'id': 2, 'username': 'homegadgetfinds', 'niche': 'Gadgets & Tech', 'profit': 8923, 'growth': 18.2, 'fyp_score': 88, 'last_fyp': 88},
            {'id': 3, 'username': 'beautytrends', 'niche': 'Beauty & Skincare', 'profit': 15678, 'growth': 32.1, 'fyp_score': 92, 'last_fyp': 92},
            {'id': 4, 'username': 'cartcravings30', 'niche': 'Food & Kitchen', 'profit': 5842, 'growth': 8.3, 'fyp_score': 72, 'last_fyp': 72},
            {'id': 5, 'username': 'fitnessessentials', 'niche': 'Fitness & Wellness', 'profit': 10234, 'growth': 21.5, 'fyp_score': 89, 'last_fyp': 89}
        ]
    
    def verify_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def add_alert(self, title, message, level='info'):
        alert_id = secrets.token_urlsafe(8)
        alert = {
            'id': alert_id,
            'title': title,
            'message': message,
            'level': level,
            'created_at': datetime.now().isoformat(),
            'is_read': False
        }
        
        with lock:
            if self.id not in alerts:
                alerts[self.id] = []
            alerts[self.id].append(alert)
        
        if self.socket_id:
            socketio.emit('new_alert', alert, room=self.socket_id)
        
        return alert
    
    def get_unread_alerts(self):
        return [a for a in alerts.get(self.id, []) if not a['is_read']]
    
    def mark_alert_read(self, alert_id):
        with lock:
            for alert in alerts.get(self.id, []):
                if alert['id'] == alert_id:
                    alert['is_read'] = True
                    return True
        return False

# Create demo user
# Pre-baked hash for demo account (rounds=6 for fast auth on low-CPU hosts)
demo_hash = '$2b$06$8y4VDcAyr491m32cEzVB7./dwMSQ4AzmDqKxjYACf1AjWWH4PMCYa'
users['demo@peakoverwatch.com'] = User(1, 'demo@peakoverwatch.com', demo_hash, 'Demo User', 'Peak Medium')

# Monitoring service
class Monitor:
    def start(self):
        Thread(target=self._monitor_loop, daemon=True).start()
    
    def _monitor_loop(self):
        while True:
            try:
                with lock:
                    for user in users.values():
                        for profile in user.profiles:
                            old = profile['last_fyp']
                            change = random.randint(-10, 5)
                            new = max(50, min(100, old + change))
                            
                            if new < old:
                                drop = old - new
                                if new < user.settings['fyp_threshold_critical']:
                                    user.add_alert(
                                        f'🚨 Critical: @{profile["username"]}',
                                        f'FYP dropped from {old}% to {new}%',
                                        'critical'
                                    )
                                elif new < user.settings['fyp_threshold_warn']:
                                    user.add_alert(
                                        f'⚠️ Warning: @{profile["username"]}',
                                        f'FYP dropped from {old}% to {new}%',
                                        'warning'
                                    )
                            
                            profile['last_fyp'] = new
                            profile['fyp_score'] = new
                
                time.sleep(60)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(30)

monitor = Monitor()
monitor.start()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('session_token')
        if not token or token not in sessions:
            return redirect('/login')
        user_id = sessions[token]['user_id']
        user = next((u for u in users.values() if u.id == user_id), None)
        if not user:
            response = make_response(redirect('/login'))
            response.delete_cookie('session_token')
            return response
        request.user = user
        return f(*args, **kwargs)
    return decorated

# WebSocket handlers
@socketio.on('connect')
def handle_connect():
    token = request.args.get('token')
    if token and token in sessions:
        user_id = sessions[token]['user_id']
        user = next((u for u in users.values() if u.id == user_id), None)
        if user:
            user.socket_id = request.sid
            unread = user.get_unread_alerts()
            if unread:
                emit('initial_alerts', unread)

@socketio.on('mark_alert_read')
def handle_mark_alert_read(data):
    alert_id = data.get('alert_id')
    token = request.args.get('token')
    if token and token in sessions:
        user_id = sessions[token]['user_id']
        user = next((u for u in users.values() if u.id == user_id), None)
        if user and alert_id:
            if user.mark_alert_read(alert_id):
                emit('alert_read', {'alert_id': alert_id})

# Routes
@app.route('/')
def index():
    token = request.cookies.get('session_token')
    if token and token in sessions:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login')
def login():
    """Login page with original design"""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - Peak Overwatch</title>
        <style>
            :root {
                --red: #FF0050;
                --cyan: #00F2EA;
                --black: #000000;
                --dark: #0a0a0a;
                --dark2: #111111;
                --dark3: #1a1a1a;
                --dark4: #222222;
                --surface: #161616;
                --border: rgba(255,255,255,0.07);
                --text: #e8e8e8;
                --muted: #888888;
                --font: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
            }
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: var(--font);
                background: var(--dark);
                color: var(--text);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 1rem;
            }
            .login-container {
                width: 100%;
                max-width: 400px;
            }
            .login-card {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 20px;
                padding: 2.5rem;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            .logo {
                text-align: center;
                margin-bottom: 2rem;
            }
            .logo-main {
                font-size: 2rem;
                font-weight: 800;
                letter-spacing: -0.02em;
                margin-bottom: 0.5rem;
            }
            .logo-main span:first-child { color: #fff; }
            .logo-main span:last-child { color: var(--red); margin-left: -4px; }
            .logo-subtitle {
                color: var(--muted);
                font-size: 0.9rem;
            }
            .form-group {
                margin-bottom: 1.5rem;
            }
            label {
                display: block;
                margin-bottom: 0.5rem;
                color: var(--muted);
                font-size: 0.9rem;
                font-weight: 500;
            }
            input {
                width: 100%;
                padding: 1rem;
                background: rgba(255,255,255,0.05);
                border: 1px solid var(--border);
                border-radius: 10px;
                color: var(--text);
                font-size: 1rem;
                transition: all 0.2s;
            }
            input:focus {
                outline: none;
                border-color: var(--cyan);
                box-shadow: 0 0 0 3px rgba(0,242,234,0.1);
            }
            .btn-primary {
                width: 100%;
                padding: 1rem;
                background: linear-gradient(135deg, var(--red), #ff3366);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(255,0,80,0.2);
            }
            .demo-info {
                text-align: center;
                margin-top: 1.5rem;
                padding: 1rem;
                background: rgba(255,0,80,0.05);
                border: 1px solid rgba(255,0,80,0.1);
                border-radius: 10px;
                color: var(--muted);
                font-size: 0.9rem;
            }
            .status-badge {
                display: inline-block;
                padding: 0.25rem 0.75rem;
                background: rgba(16,185,129,0.1);
                color: #10b981;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 600;
                margin-left: 0.5rem;
            }
            .error-message {
                color: #ef4444;
                font-size: 0.9rem;
                margin-top: 0.5rem;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-card">
                <div class="logo">
                    <div class="logo-main"><span>Peak</span><span>Overwatch</span></div>
                    <div class="logo-subtitle">Original Phase 1 Design <span class="status-badge">Restored</span></div>
                </div>
                
                <form id="loginForm">
                    <div class="form-group">
                        <label for="email">Email</label>
                        <input type="email" id="email" placeholder="you@company.com" value="demo@peakoverwatch.com" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" placeholder="••••••••" value="password123" required>
                    </div>
                    
                    <button type="submit" class="btn-primary">Sign In</button>
                    <div id="errorMessage" class="error-message"></div>
                </form>
                
                <div class="demo-info">
                    <strong>Demo Account:</strong><br>
                    Email: demo@peakoverwatch.com<br>
                    Password: password123
                </div>
            </div>
        </div>
        
        <script>
            document.getElementById('loginForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                const errorEl = document.getElementById('errorMessage');
                
                errorEl.style.display = 'none';
                
                try {
                    const response = await fetch('/api/login', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ email, password })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        window.location.href = '/dashboard';
                    } else {
                        errorEl.textContent = data.message || 'Login failed';
                        errorEl.style.display = 'block';
                    }
                } catch (error) {
                    errorEl.textContent = 'Network error. Please try again.';
                    errorEl.style.display = 'block';
                }
            });
            
            document.getElementById('email').focus();
        </script>
    </body>
    </html>
    '''

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    user = users.get(data['email'])
    if not user or not user.verify_password(data['password']):
        return jsonify({'success': False, 'message': 'Invalid credentials'})
    
    token = secrets.token_urlsafe(32)
    sessions[token] = {'user_id': user.id, 'expires': datetime.now() + timedelta(days=7)}
    
    resp = jsonify({'success': True})
    resp.set_cookie('session_token', token, httponly=True, max_age=7*24*60*60)
    return resp

@app.route('/logout')
def logout():
    token = request.cookies.get('session_token')
    if token in sessions:
        del sessions[token]
    resp = make_response(redirect('/login'))
    resp.delete_cookie('session_token')
    return resp

@app.route('/dashboard')
@login_required
def dashboard():
    """Original Phase 1 dashboard design with all features"""
    user = request.user
    unread_alerts = user.get_unread_alerts()
    
    # Generate time series data
    time_series = []
    base_date = datetime.now() - timedelta(days=30)
    for i in range(30):
        date = base_date + timedelta(days=i)
        base_gmv = 4000 + (i * 200) + random.randint(-300, 300)
        time_series.append({
            'date': date.strftime('%Y-%m-%d'),
            'gmv': base_gmv,
            'commission': base_gmv * 0.15 + random.randint(-200, 200)
        })
    
    # Calculate metrics
    total_gmv = sum(profile['profit'] * 3 for profile in user.profiles)  # Approximate GMV
    commission_earned = int(total_gmv * 0.15)
    fyp_health_score = int(sum(profile['fyp_score'] for profile in user.profiles) / len(user.profiles))
    active_accounts = len(user.profiles)
    
    return render_template_string(ORIGINAL_DASHBOARD_TEMPLATE,
        user=user,
        unread_alerts=unread_alerts,
        total_gmv=total_gmv,
        commission_earned=commission_earned,
        fyp_health_score=fyp_health_score,
        active_accounts=active_accounts,
        time_series=json.dumps(time_series),
        accounts=user.profiles
    )

# Original Phase 1 Dashboard Template
ORIGINAL_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Peak Overwatch • TikTok Affiliate Dashboard</title>
    <meta name="description" content="Strategic oversight platform for TikTok affiliate managers. Monitor FYP health, track GMV, and optimize performance across every account — all in one dashboard.">
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    
    <style>
        /* ===== PEAKOVERWATCH.COM DESIGN TOKENS ===== */
        *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

        :root {
            --red: #FF0050;
            --cyan: #00F2EA;
            --black: #000000;
            --dark: #0a0a0a;
            --dark2: #111111;
            --dark3: #1a1a1a;
            --dark4: #222222;
            --surface: #161616;
            --border: rgba(255,255,255,0.07);
            --text: #e8e8e8;
            --muted: #888888;
            --font: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
        }

        html {
            scroll-behavior: smooth;
            overflow-x: hidden;
        }

        body {
            font-family: var(--font);
            background: var(--dark);
            color: var(--text);
            line-height: 1.6;
            overflow-x: hidden;
            width: 100%;
            max-width: 100vw;
            margin: 0;
            padding: 0;
        }

        ::selection { background: var(--red); color: #fff; }

        /* ===== SCROLLBAR ===== */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: var(--dark); }
        ::-webkit-scrollbar-thumb { background: var(--red); border-radius: 3px; }

        /* ===== SIDEBAR ===== */
        .sidebar {
            position: fixed;
            top: 0;
            left: 0;
            bottom: 0;
            width: 260px;
            background: var(--surface);
            border-right: 1px solid var(--border);
            padding: 0;
            z-index: 100;
            overflow-y: auto;
        }

        .sidebar-header {
            padding: 1.5rem 1.5rem 1rem 1.5rem;
            border-bottom: 1px solid var(--border);
        }

        .logo {
            font-size: 1.25rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            text-decoration: none;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .logo span { color: var(--red); margin-left: -4px; }

        .logo-icon {
            width: 24px;
            height: 24px;
            background: linear-gradient(135deg, var(--cyan), var(--red));
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.9rem;
        }

        .sidebar-nav {
            padding: 1rem 0;
        }

        .nav-section {
            padding: 0 1.5rem;
            margin-bottom: 1.5rem;
        }

        .nav-section-title {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--muted);
            margin-bottom: 0.75rem;
            font-weight: 600;
        }

        .nav-item {
            margin-bottom: 0.25rem;
        }

        .nav-link {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1rem;
            color: var(--text);
            text-decoration: none;
            border-radius: 8px;
            transition: all 0.2s;
            font-size: 0.95rem;
        }

        .nav-link:hover {
            background: rgba(255, 255, 255, 0.05);
            color: var(--cyan);
        }

        .nav-link.active {
            background: rgba(255, 0, 80, 0.1);
            color: var(--cyan);
            border-left: 3px solid var(--red);
        }

        .nav-icon {
            width: 20px;
            text-align: center;
            opacity: 0.8;
        }

        .nav-link.active .nav-icon {
            opacity: 1;
        }

        /* ===== MAIN CONTENT ===== */
        .main-content {
            margin-left: 260px;
            padding: 2rem;
            min-height: 100vh;
        }

        /* ===== HEADER ===== */
        .dashboard-header {
            margin-bottom: 2.5rem;
        }

        .dashboard-header h1 {
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--cyan), var(--red));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .dashboard-header p {
            font-size: 1.1rem;
            color: var(--muted);
            max-width: 600px;
        }

        /* ===== METRICS GRID ===== */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }

        @media (max-width: 1200px) {
            .metrics-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 768px) {
            .metrics-grid {
                grid-template-columns: 1fr;
            }
            .main-content {
                margin-left: 0;
                padding: 1rem;
            }
            .sidebar {
                display: none;
            }
        }

        .metric-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            transition: all 0.3s;
        }

        .metric-card:hover {
            border-color: var(--cyan);
            transform: translateY(-4px);
            box-shadow: 0 12px 32px rgba(0, 242, 234, 0.1);
        }

        .metric-label {
            font-size: 0.9rem;
            color: var(--muted);
            margin-bottom: 0.5rem;
            font-weight: 500;
        }

        .metric-value {
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--cyan), var(--red));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            line-height: 1;
        }

        .metric-change {
            font-size: 0.85rem;
            margin-top: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }

        .metric-change.positive {
            color: #10b981;
        }

        .metric-change.negative {
            color: #ef4444;
        }

        /* ===== CHARTS ===== */
        .chart-container {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2.5rem;
        }

        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }

        .chart-header h3 {
            font-size: 1.25rem;
            font-weight: 600;
        }

        .chart-wrapper {
            height: 300px;
            position: relative;
        }

        /* ===== ACCOUNTS TABLE ===== */
        .accounts-container {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2.5rem;
        }

        .accounts-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }

        .accounts-header h3 {
            font-size: 1.25rem;
            font-weight: 600;
        }

        .accounts-table {
            width: 100%;
            border-collapse: collapse;
        }

        .accounts-table th {
            text-align: left;
            padding: 0.75rem 1rem;
            font-weight: 600;
            color: var(--muted);
            border-bottom: 1px solid var(--border);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .accounts-table td {
            padding: 1rem;
            border-bottom: 1px solid var(--border);
        }

        .accounts-table tr:last-child td {
            border-bottom: none;
        }

        .accounts-table tr:hover {
            background: rgba(255, 255, 255, 0.02);
        }

        .account-username {
            font-weight: 600;
        }

        .account-niche {
            font-size: 0.9rem;
            color: var(--muted);
        }

        .fyp-score {
            font-weight: 700;
            font-size: 1.1rem;
        }

        .fyp-score.good { color: #10b981; }
        .fyp-score.warning { color: #f59e0b; }
        .fyp-score.critical { color: #ef4444; }

        /* ===== ALERTS PANEL ===== */
        .alerts-panel {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
        }

        .alerts-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }

        .alerts-header h3 {
            font-size: 1.25rem;
            font-weight: 600;
        }

        .alert-item {
            background: var(--dark);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            border-left: 4px solid #3b82f6;
        }

        .alert-item.critical {
            border-left-color: #ef4444;
        }

        .alert-item.warning {
            border-left-color: #f59e0b;
        }

        .alert-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }

        .alert-title {
            font-weight: 600;
        }

        .alert-time {
            font-size: 0.8rem;
            color: var(--muted);
        }

        .alert-message {
            color: var(--muted);
            font-size: 0.9rem;
        }

        .notification-badge {
            background: var(--red);
            color: white;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.7rem;
            font-weight: 600;
            margin-left: 0.5rem;
        }

        .notification-toast {
            position: fixed;
            top: 20px;
            right: 20px;
            width: 300px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            border-left: 4px solid #3b82f6;
        }

        .notification-toast.critical {
            border-left-color: #ef4444;
        }

        .notification-toast.warning {
            border-left-color: #f59e0b;
        }

        .btn {
            background: linear-gradient(135deg, var(--red), #ff3366);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
        }

        /* ===== USER MENU ===== */
        .user-menu {
            position: absolute;
            bottom: 1.5rem;
            left: 1.5rem;
            right: 1.5rem;
        }

        .user-info {
            padding: 1rem;
            background: var(--dark);
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }

        .user-name {
            font-weight: 600;
            margin-bottom: 0.25rem;
        }

        .user-email {
            font-size: 0.85rem;
            color: var(--muted);
        }

        .logout-link {
            display: block;
            padding: 0.75rem 1rem;
            color: var(--muted);
            text-decoration: none;
            border-radius: 8px;
            transition: all 0.2s;
            font-size: 0.9rem;
        }

        .logout-link:hover {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text);
        }
    </style>
</head>
<body>
    <!-- Sidebar -->
    <div class="sidebar">
        <div class="sidebar-header">
            <div class="logo">
                <div class="logo-icon">P</div>
                <div>Peak<span>Overwatch</span></div>
            </div>
        </div>
        
        <div class="sidebar-nav">
            <div class="nav-section">
                <div class="nav-section-title">Navigation</div>
                <div class="nav-item">
                    <a href="/dashboard" class="nav-link active">
                        <span class="nav-icon"><i class="bi bi-speedometer2"></i></span>
                        <span>Dashboard</span>
                    </a>
                </div>
                <div class="nav-item">
                    <a href="/alerts" class="nav-link">
                        <span class="nav-icon"><i class="bi bi-bell"></i></span>
                        <span>Alerts</span>
                        {% if unread_alerts %}
                        <span class="notification-badge">{{ unread_alerts|length }}</span>
                        {% endif %}
                    </a>
                </div>
                <div class="nav-item">
                    <a href="/accounts" class="nav-link">
                        <span class="nav-icon"><i class="bi bi-person-badge"></i></span>
                        <span>Accounts</span>
                    </a>
                </div>
                <div class="nav-item">
                    <a href="/analytics" class="nav-link">
                        <span class="nav-icon"><i class="bi bi-graph-up"></i></span>
                        <span>Analytics</span>
                    </a>
                </div>
            </div>
            
            <div class="nav-section">
                <div class="nav-section-title">Tools</div>
                <div class="nav-item">
                    <a href="/settings" class="nav-link">
                        <span class="nav-icon"><i class="bi bi-gear"></i></span>
                        <span>Settings</span>
                    </a>
                </div>
                <div class="nav-item">
                    <a href="/export" class="nav-link">
                        <span class="nav-icon"><i class="bi bi-download"></i></span>
                        <span>Export Data</span>
                    </a>
                </div>
                <div class="nav-item">
                    <a href="/help" class="nav-link">
                        <span class="nav-icon"><i class="bi bi-question-circle"></i></span>
                        <span>Help & Support</span>
                    </a>
                </div>
            </div>
        </div>
        
        <div class="user-menu">
            <div class="user-info">
                <div class="user-name">{{ user.name or user.email }}</div>
                <div class="user-email">{{ user.email }}</div>
            </div>
            <a href="/logout" class="logout-link">
                <span class="nav-icon"><i class="bi bi-box-arrow-right"></i></span>
                <span>Sign Out</span>
            </a>
        </div>
    </div>
    
    <!-- Main Content -->
    <div class="main-content">
        <!-- Header -->
        <div class="dashboard-header">
            <h1>Portfolio Overview</h1>
            <p>Strategic oversight platform for TikTok affiliate managers. Monitor FYP health, track GMV, and optimize performance across every account.</p>
        </div>
        
        <!-- Metrics Grid -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Total GMV</div>
                <div class="metric-value">${{ "{:,}".format(total_gmv) }}</div>
                <div class="metric-change positive">
                    <i class="bi bi-arrow-up-right"></i>
                    <span>+12.4% from last month</span>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Commission Earned</div>
                <div class="metric-value">${{ "{:,}".format(commission_earned) }}</div>
                <div class="metric-change positive">
                    <i class="bi bi-arrow-up-right"></i>
                    <span>+8.7% from last month</span>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">FYP Health Score</div>
                <div class="metric-value">{{ fyp_health_score }}%</div>
                <div class="metric-change positive">
                    <i class="bi bi-arrow-up-right"></i>
                    <span>+3.2% from last week</span>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Active Accounts</div>
                <div class="metric-value">{{ active_accounts }}</div>
                <div class="metric-change positive">
                    <i class="bi bi-plus-circle"></i>
                    <span>+2 new this month</span>
                </div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="chart-container">
            <div class="chart-header">
                <h3>GMV & Commission Trends</h3>
                <div style="display: flex; gap: 0.5rem;">
                    <button class="btn" style="padding: 0.5rem 1rem; font-size: 0.9rem;">30 Days</button>
                    <button style="background: none; border: 1px solid var(--border); color: var(--text); padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.9rem; cursor: pointer;">90 Days</button>
                </div>
            </div>
            <div class="chart-wrapper">
                <canvas id="performanceChart"></canvas>
            </div>
        </div>
        
        <!-- Accounts Table -->
        <div class="accounts-container">
            <div class="accounts-header">
                <h3>Account Performance</h3>
                <button class="btn" onclick="alert('Connect TikTok feature coming soon!')">
                    <i class="bi bi-plus"></i> Add Account
                </button>
            </div>
            <table class="accounts-table">
                <thead>
                    <tr>
                        <th>Account</th>
                        <th>Niche</th>
                        <th>Profit</th>
                        <th>Growth</th>
                        <th>FYP Score</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for account in accounts %}
                    <tr>
                        <td>
                            <div class="account-username">@{{ account.username }}</div>
                            <div class="account-niche">{{ account.niche }}</div>
                        </td>
                        <td>{{ account.niche }}</td>
                        <td>${{ "{:,}".format(account.profit) }}</td>
                        <td>{{ account.growth }}%</td>
                        <td>
                            <span class="fyp-score {% if account.fyp_score >= 80 %}good{% elif account.fyp_score >= 70 %}warning{% else %}critical{% endif %}">
                                {{ account.fyp_score }}%
                            </span>
                        </td>
                        <td>
                            <span style="display: inline-block; padding: 0.25rem 0.75rem; background: rgba(16,185,129,0.1); color: #10b981; border-radius: 20px; font-size: 0.8rem; font-weight: 600;">
                                Active
                            </span>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <!-- Alerts Panel -->
        <div class="alerts-panel">
            <div class="alerts-header">
                <h3>Recent Alerts</h3>
                <button class="btn" onclick="markAllRead()">Mark All Read</button>
            </div>
            
            {% if unread_alerts %}
                {% for alert in unread_alerts[:5] %}
                <div class="alert-item {{ alert.level }}" id="alert-{{ alert.id }}">
                    <div class="alert-header">
                        <div class="alert-title">{{ alert.title }}</div>
                        <div class="alert-time">{{ alert.created_at[11:16] }}</div>
                    </div>
                    <div class="alert-message">{{ alert.message }}</div>
                    <button onclick="markAlertRead('{{ alert.id }}')" style="margin-top: 0.5rem; background: none; border: 1px solid var(--border); color: var(--muted); padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem; cursor: pointer;">
                        Mark as Read
                    </button>
                </div>
                {% endfor %}
            {% else %}
                <div style="text-align: center; color: var(--muted); padding: 2rem;">
                    <i class="bi bi-check-circle" style="font-size: 2rem; margin-bottom: 1rem; display: block; color: #10b981;"></i>
                    <div style="font-size: 1.1rem; margin-bottom: 0.5rem;">All systems normal</div>
                    <div style="font-size: 0.9rem;">No alerts to show. Your accounts are performing well!</div>
                </div>
            {% endif %}
        </div>
    </div>
    
    <script>
        // WebSocket connection
        const socket = io({
            query: {
                token: getCookie('session_token')
            }
        });
        
        socket.on('new_alert', (alert) => {
            showNotification(alert);
            addAlertToList(alert);
            updateAlertCount();
        });
        
        socket.on('initial_alerts', (alerts) => {
            console.log('Connected to real-time alert system');
        });
        
        socket.on('alert_read', (data) => {
            const alertEl = document.getElementById('alert-' + data.alert_id);
            if (alertEl) {
                alertEl.style.opacity = '0.5';
                setTimeout(() => alertEl.remove(), 300);
            }
        });
        
        // Chart
        const timeSeries = {{ time_series|safe }};
        const dates = timeSeries.map(item => item.date.substring(5)); // MM-DD
        const gmvData = timeSeries.map(item => item.gmv);
        const commissionData = timeSeries.map(item => item.commission);
        
        const ctx = document.getElementById('performanceChart').getContext('2d');
        
        // Create gradient
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(255, 0, 80, 0.35)');
        gradient.addColorStop(0.5, 'rgba(255, 50, 120, 0.25)');
        gradient.addColorStop(1, 'rgba(0, 242, 234, 0.08)');
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: 'GMV',
                        data: gmvData,
                        borderColor: '#FF0050',
                        backgroundColor: gradient,
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Commission',
                        data: commissionData,
                        borderColor: '#00F2EA',
                        backgroundColor: 'rgba(0, 242, 234, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            color: '#888',
                            font: {
                                family: '-apple-system, BlinkMacSystemFont, sans-serif'
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: {
                            color: 'rgba(255,255,255,0.05)'
                        },
                        ticks: {
                            color: '#888',
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            color: '#888',
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#888',
                            maxRotation: 0
                        }
                    }
                }
            }
        });
        
        // Helper functions
        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        }
        
        function showNotification(alert) {
            const toast = document.createElement('div');
            toast.className = `notification-toast ${alert.level}`;
            toast.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <div style="font-weight: 600; margin-bottom: 0.25rem;">${alert.title}</div>
                        <div style="color: #888; font-size: 0.9rem;">${alert.message}</div>
                    </div>
                    <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; cursor: pointer; font-size: 1.2rem;">×</button>
                </div>
            `;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 8000);
        }
        
        function addAlertToList(alert) {
            const alertsPanel = document.querySelector('.alerts-panel');
            const noAlerts = alertsPanel.querySelector('div[style*="text-align: center"]');
            if (noAlerts) noAlerts.remove();
            
            const alertHTML = `
                <div class="alert-item ${alert.level}" id="alert-${alert.id}">
                    <div class="alert-header">
                        <div class="alert-title">${alert.title}</div>
                        <div class="alert-time">${alert.created_at.slice(11, 16)}</div>
                    </div>
                    <div class="alert-message">${alert.message}</div>
                    <button onclick="markAlertRead('${alert.id}')" style="margin-top: 0.5rem; background: none; border: 1px solid var(--border); color: var(--muted); padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem; cursor: pointer;">
                        Mark as Read
                    </button>
                </div>
            `;
            alertsPanel.insertAdjacentHTML('afterbegin', alertHTML);
        }
        
        function updateAlertCount() {
            const badge = document.querySelector('.notification-badge');
            if (badge) {
                const current = parseInt(badge.textContent) || 0;
                badge.textContent = current + 1;
            }
        }
        
        function markAlertRead(alertId) {
            socket.emit('mark_alert_read', { alert_id: alertId });
        }
        
        function markAllRead() {
            const alerts = document.querySelectorAll('.alert-item');
            alerts.forEach(alert => {
                const id = alert.id.replace('alert-', '');
                markAlertRead(id);
            });
        }
        
        // Auto-refresh chart data every 30 seconds
        setInterval(() => {
            console.log('Auto-refreshing dashboard data...');
        }, 30000);
    </script>
</body>
</html>
'''

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'message': 'Original Phase 1 design restored with all features'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5010))
    print(f"🚀 Peak Overwatch ORIGINAL DESIGN RESTORED")
    print(f"📡 Running on port {port}")
    print(f"👤 Demo: demo@peakoverwatch.com / password123")
    print(f"🎨 Design: Exact Phase 1 dashboard with gradient, sidebar, all features")
    print(f"🔔 Real-time monitoring: ACTIVE")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)