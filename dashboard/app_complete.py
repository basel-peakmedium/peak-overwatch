#!/usr/bin/env python3
"""
Peak Overwatch - COMPLETE DASHBOARD WITH ALL 5 TABS
All tabs functional with mock data for demo video
"""

from flask import Flask, render_template_string, redirect, request, jsonify, make_response, send_file
from flask_socketio import SocketIO, emit
import os
import json
import csv
import io
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
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'complete-dashboard-' + secrets.token_hex(16))

# WebSocket
socketio = SocketIO(app, cors_allowed_origins="*")

# Storage
users = {}
sessions = {}
alerts = {}
user_settings = {}
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
            'email_notifications': True,
            'fyp_threshold_good': 80,
            'fyp_threshold_warn': 70,
            'fyp_threshold_critical': 60,
            'daily_summary': True,
            'weekly_report': True
        }
        self.profiles = [
            {'id': 1, 'username': 'ourviralpicks', 'niche': 'Home & Lifestyle', 'profit': 12412, 'growth': 24.7, 'fyp_score': 95, 'last_fyp': 95, 'status': 'active', 'last_active': '2026-04-07 08:45:00', 'followers': 125000, 'videos': 342},
            {'id': 2, 'username': 'homegadgetfinds', 'niche': 'Gadgets & Tech', 'profit': 8923, 'growth': 18.2, 'fyp_score': 88, 'last_fyp': 88, 'status': 'active', 'last_active': '2026-04-07 09:15:00', 'followers': 89000, 'videos': 215},
            {'id': 3, 'username': 'beautytrends', 'niche': 'Beauty & Skincare', 'profit': 15678, 'growth': 32.1, 'fyp_score': 92, 'last_fyp': 92, 'status': 'active', 'last_active': '2026-04-07 07:30:00', 'followers': 210000, 'videos': 489},
            {'id': 4, 'username': 'cartcravings30', 'niche': 'Food & Kitchen', 'profit': 5842, 'growth': 8.3, 'fyp_score': 72, 'last_fyp': 72, 'status': 'warning', 'last_active': '2026-04-06 22:15:00', 'followers': 45000, 'videos': 128},
            {'id': 5, 'username': 'fitnessessentials', 'niche': 'Fitness & Wellness', 'profit': 10234, 'growth': 21.5, 'fyp_score': 89, 'last_fyp': 89, 'status': 'active', 'last_active': '2026-04-07 10:00:00', 'followers': 167000, 'videos': 312}
        ]
        self.analytics_data = self._generate_analytics_data()
    
    def _generate_analytics_data(self):
        """Generate 30 days of mock analytics data"""
        data = []
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(30):
            date = base_date + timedelta(days=i)
            base_gmv = 4000 + (i * 200) + random.randint(-300, 300)
            base_views = 50000 + (i * 1500) + random.randint(-5000, 5000)
            base_engagement = 4.2 + (i * 0.05) + random.uniform(-0.2, 0.2)
            
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'gmv': base_gmv,
                'commission': base_gmv * 0.15 + random.randint(-200, 200),
                'views': base_views,
                'engagement_rate': round(base_engagement, 2),
                'new_followers': random.randint(150, 800),
                'video_count': random.randint(3, 12)
            })
        
        return data
    
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
    
    def get_all_alerts(self, limit=50):
        return alerts.get(self.id, [])[:limit]
    
    def mark_alert_read(self, alert_id):
        with lock:
            for alert in alerts.get(self.id, []):
                if alert['id'] == alert_id:
                    alert['is_read'] = True
                    return True
        return False
    
    def mark_all_alerts_read(self):
        with lock:
            for alert in alerts.get(self.id, []):
                alert['is_read'] = True
        return True
    
    def update_settings(self, new_settings):
        self.settings.update(new_settings)
        return True
    
    def get_analytics_summary(self):
        """Calculate summary metrics from analytics data"""
        if not self.analytics_data:
            return {}
        
        recent = self.analytics_data[-7:]  # Last 7 days
        previous = self.analytics_data[-14:-7]  # 7 days before that
        
        recent_gmv = sum(d['gmv'] for d in recent)
        previous_gmv = sum(d['gmv'] for d in previous)
        gmv_growth = ((recent_gmv - previous_gmv) / previous_gmv * 100) if previous_gmv > 0 else 0
        
        recent_commission = sum(d['commission'] for d in recent)
        previous_commission = sum(d['commission'] for d in previous)
        commission_growth = ((recent_commission - previous_commission) / previous_commission * 100) if previous_commission > 0 else 0
        
        return {
            'total_gmv': sum(d['gmv'] for d in self.analytics_data[-30:]),
            'total_commission': sum(d['commission'] for d in self.analytics_data[-30:]),
            'avg_engagement': round(sum(d['engagement_rate'] for d in recent) / len(recent), 2),
            'total_followers_growth': sum(d['new_followers'] for d in self.analytics_data[-30:]),
            'gmv_growth': round(gmv_growth, 1),
            'commission_growth': round(commission_growth, 1)
        }

# Create demo user
demo_hash = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
users['demo@peakoverwatch.com'] = User(1, 'demo@peakoverwatch.com', demo_hash, 'Demo User', 'Peak Medium')

# Add some initial alerts
demo_user = users['demo@peakoverwatch.com']
demo_user.add_alert('🚨 Critical FYP Drop', '@cartcravings30 FYP score dropped from 78% to 72%', 'critical')
demo_user.add_alert('⚠️ Performance Warning', '@homegadgetfinds growth rate below threshold', 'warning')
demo_user.add_alert('📈 Strong Performance', '@beautytrends achieved 32.1% growth this week', 'info')
demo_user.add_alert('✅ Account Connected', 'Successfully connected @fitnessessentials', 'success')
demo_user.add_alert('📊 Weekly Report Ready', 'Your weekly performance summary is available', 'info')

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
    """Login page"""
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
                    <div class="logo-subtitle">Complete Dashboard v1.0</div>
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

# Helper function to render dashboard with active tab
def render_dashboard(template, user, active_tab='dashboard', **kwargs):
    unread_alerts = user.get_unread_alerts()
    analytics_summary = user.get_analytics_summary()
    
    # Calculate metrics for dashboard
    total_gmv = sum(profile['profit'] * 3 for profile in user.profiles)
    commission_earned = int(total_gmv * 0.15)
    fyp_health_score = int(sum(profile['fyp_score'] for profile in user.profiles) / len(user.profiles))
    active_accounts = len(user.profiles)
    
    base_context = {
        'user': user,
        'unread_alerts': unread_alerts,
        'active_tab': active_tab,
        'total_gmv': total_gmv,
        'commission_earned': commission_earned,
        'fyp_health_score': fyp_health_score,
        'active_accounts': active_accounts,
        'analytics_summary': analytics_summary,
        'time_series': json.dumps(user.analytics_data[-30:])  # Last 30 days
    }
    base_context.update(kwargs)
    
    return render_template_string(template, **base_context)

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard tab"""
    user = request.user
    return render_dashboard(DASHBOARD_TEMPLATE, user, active_tab='dashboard')

@app.route('/accounts')
@login_required
def accounts():
    """Accounts management tab"""
    user = request.user
    return render_dashboard(ACCOUNTS_TEMPLATE, user, active_tab='accounts')

@app.route('/analytics')
@login_required
def analytics():
    """Analytics tab"""
    user = request.user
    return render_dashboard(ANALYTICS_TEMPLATE, user, active_tab='analytics')

@app.route('/alerts')
@login_required
def alerts_page():
    """Alerts tab"""
    user = request.user
    all_alerts = user.get_all_alerts(limit=50)
    return render_dashboard(ALERTS_TEMPLATE, user, active_tab='alerts', all_alerts=all_alerts)

@app.route('/settings')
@login_required
def settings():
    """Settings tab"""
    user = request.user
    return render_dashboard(SETTINGS_TEMPLATE, user, active_tab='settings')

# API endpoints
@app.route('/api/settings/update', methods=['POST'])
@login_required
def update_settings():
    user = request.user
    data = request.json
    
    if user.update_settings(data):
        return jsonify({'success': True, 'message': 'Settings updated'})
    return jsonify({'success': False, 'message': 'Failed to update settings'}), 400

@app.route('/api/alerts/mark-all-read', methods=['POST'])
@login_required
def mark_all_alerts_read():
    user = request.user
    if user.mark_all_alerts_read():
        return jsonify({'success': True, 'message': 'All alerts marked as read'})
    return jsonify({'success': False, 'message': 'Failed to mark alerts as read'}), 400

@app.route('/api/export/csv')
@login_required
def export_csv():
    """Export analytics data as CSV"""
    user = request.user
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Date', 'GMV', 'Commission', 'Views', 'Engagement Rate', 'New Followers', 'Video Count'])
    
    # Write data
    for row in user.analytics_data:
        writer.writerow([
            row['date'],
            row['gmv'],
            row['commission'],
            row['views'],
            row['engagement_rate'],
            row['new_followers'],
            row['video_count']
        ])
    
    # Create response
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'peak-overwatch-analytics-{datetime.now().strftime("%Y-%m-%d")}.csv'
    )

@app.route('/api/export/json')
@login_required
def export_json():
    """Export analytics data as JSON"""
    user = request.user
    
    return jsonify({
        'export_date': datetime.now().isoformat(),
        'user': user.email,
        'data': user.analytics_data,
        'accounts': user.profiles,
        'summary': user.get_analytics_summary()
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'message': 'Complete dashboard with all 5 tabs functional'
    })

# Templates
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Peak Overwatch • {{ active_tab|title }}</title>
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    
    <style>
        /* Base styles from original design */
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
            line-height: 1.6;
        }
        
        .sidebar {
            position: fixed;
            top: 0;
            left: 0;
            bottom: 0;
            width: 260px;
            background: var(--surface);
            border-right: 1px solid var(--border);
            padding: 1.5rem;
            z-index: 100;
        }
        
        .logo {
            font-size: 1.25rem;
            font-weight: 800;
            margin-bottom: 2rem;
        }
        .logo span:first-child { color: #fff; }
        .logo span:last-child { color: var(--red); margin-left: -4px; }
        
        .nav-link {
            display: block;
            padding: 0.75rem 1rem;
            color: #e8e8e8;
            text-decoration: none;
            border-radius: 8px;
            margin-bottom: 0.25rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .nav-link.active {
            background: rgba(255,0,80,0.1);
            color: #00F2EA;
        }
        .nav-link:hover:not(.active) {
            background: rgba(255,255,255,0.05);
        }
        
        .main-content {
            margin-left: 260px;
            padding: 2rem;
            min-height: 100vh;
        }
        
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        
        .page-header {
            margin-bottom: 2rem;
        }
        .page-header h1 {
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--cyan), var(--red));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .page-header p {
            color: var(--muted);
            font-size: 1.1rem;
        }
        
        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }
        
        .btn {
            background: linear-gradient(135deg, var(--red), #ff3366);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255,0,80,0.2);
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
            margin-left: auto;
        }
        
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
        }
        .logout-link:hover {
            background: rgba(255,255,255,0.05);
            color: var(--text);
        }
    </style>
</head>
<body>
    <!-- Sidebar -->
    <div class="sidebar">
        <div class="logo">Peak<span>Overwatch</span></div>
        
        <nav>
            <a href="/dashboard" class="nav-link {% if active_tab == 'dashboard' %}active{% endif %}">
                <i class="bi bi-speedometer2"></i>
                <span>Dashboard</span>
            </a>
            
            <a href="/accounts" class="nav-link {% if active_tab == 'accounts' %}active{% endif %}">
                <i class="bi bi-person-badge"></i>
                <span>Accounts</span>
            </a>
            
            <a href="/analytics" class="nav-link {% if active_tab == 'analytics' %}active{% endif %}">
                <i class="bi bi-graph-up"></i>
                <span>Analytics</span>
            </a>
            
            <a href="/alerts" class="nav-link {% if active_tab == 'alerts' %}active{% endif %}">
                <i class="bi bi-bell"></i>
                <span>Alerts</span>
                {% if unread_alerts %}
                <span class="notification-badge">{{ unread_alerts|length }}</span>
                {% endif %}
            </a>
            
            <a href="/settings" class="nav-link {% if active_tab == 'settings' %}active{% endif %}">
                <i class="bi bi-gear"></i>
                <span>Settings</span>
            </a>
        </nav>
        
        <div class="user-menu">
            <div class="user-info">
                <div class="user-name">{{ user.name or user.email }}</div>
                <div class="user-email">{{ user.email }}</div>
            </div>
            <a href="/logout" class="logout-link">
                <i class="bi bi-box-arrow-right"></i>
                <span>Sign Out</span>
            </a>
        </div>
    </div>
    
    <!-- Main Content -->
    <div class="main-content">
        {% block content %}{% endblock %}
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
            updateAlertCount();
        });
        
        socket.on('alert_read', (data) => {
            console.log('Alert marked as read:', data);
        });
        
        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        }
        
        function showNotification(alert) {
            const toast = document.createElement('div');
            toast.className = 'notification-toast';
            toast.innerHTML = `
                <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; border-left: 4px solid ${alert.level === 'critical' ? '#ef4444' : alert.level === 'warning' ? '#f59e0b' : '#3b82f6'};">
                    <div style="font-weight: 600; margin-bottom: 0.25rem;">${alert.title}</div>
                    <div style="color: #888; font-size: 0.9rem;">${alert.message}</div>
                </div>
            `;
            
            const container = document.querySelector('.notification-container');
            if (container) {
                container.prepend(toast);
                setTimeout(() => toast.remove(), 5000);
            }
        }
        
        function updateAlertCount() {
            const badge = document.querySelector('.notification-badge');
            if (badge) {
                const current = parseInt(badge.textContent) || 0;
                badge.textContent = current + 1;
            }
        }
    </script>
</body>
</html>
'''

DASHBOARD_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
<div class="page-header">
    <h1>Dashboard Overview</h1>
    <p>Monitor your TikTok affiliate performance across all accounts</p>
</div>

<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; margin-bottom: 2rem;">
    <div class="card">
        <div style="color: var(--muted); font-size: 0.9rem; margin-bottom: 0.5rem;">Total GMV</div>
        <div style="font-size: 2rem; font-weight: 800; color: var(--cyan);">${{ "{:,}".format(total_gmv) }}</div>
        <div style="color: #10b981; font-size: 0.85rem; margin-top: 0.5rem;">
            <i class="bi bi-arrow-up-right"></i> +12.4% from last month
        </div>
    </div>
    
    <div class="card">
        <div style="color: var(--muted); font