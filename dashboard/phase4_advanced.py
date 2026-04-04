#!/usr/bin/env python3
"""
Peak Overwatch Dashboard - Phase 4: Advanced Features
Email notifications, real-time updates, and alert system
"""

from flask import Flask, render_template_string, redirect, request, jsonify, make_response
from flask_socketio import SocketIO, emit
import os
import json
from datetime import datetime, timedelta
import random
import bcrypt
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread, Lock
import time
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-phase4')
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory storage with thread safety
users = {}
sessions = {}
alerts = {}
user_lock = Lock()

class User:
    def __init__(self, user_id, email, password_hash, name=None, company=None):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash
        self.name = name
        self.company = company
        self.created_at = datetime.now()
        self.last_login = None
        self.subscription_tier = 'free'
        self.socket_id = None
        
        # Settings with defaults
        self.settings = {
            'timezone': 'America/New_York',
            'currency': 'USD',
            'daily_email_reports': True,
            'weekly_summary_email': True,
            'alert_notifications': True,
            'alert_email': True,
            'alert_slack': False,
            'alert_telegram': False,
            'fyp_threshold_good': 80,
            'fyp_threshold_warn': 70,
            'fyp_threshold_critical': 60,
            'gmv_drop_threshold': 20,  # percentage
            'commission_drop_threshold': 15  # percentage
        }
        
        # Mock TikTok profiles
        self.profiles = [
            {
                'id': 1,
                'username': 'ourviralpicks',
                'niche': 'Home & Lifestyle',
                'profit': 12412,
                'growth': 24.7,
                'fyp_score': 95,
                'connected_at': datetime.now() - timedelta(days=30),
                'last_fyp_score': 95,
                'last_gmv': 5200,
                'last_commission': 780
            },
            {
                'id': 2,
                'username': 'homegadgetfinds',
                'niche': 'Gadgets & Tech',
                'profit': 8923,
                'growth': 18.2,
                'fyp_score': 88,
                'connected_at': datetime.now() - timedelta(days=25),
                'last_fyp_score': 88,
                'last_gmv': 3800,
                'last_commission': 570
            },
            {
                'id': 3,
                'username': 'beautytrends',
                'niche': 'Beauty & Skincare',
                'profit': 15678,
                'growth': 32.1,
                'fyp_score': 92,
                'connected_at': datetime.now() - timedelta(days=20),
                'last_fyp_score': 92,
                'last_gmv': 6200,
                'last_commission': 930
            }
        ]
        
        # Analytics history
        self.analytics_history = self._generate_analytics_history()
    
    def _generate_analytics_history(self):
        """Generate 90 days of analytics history"""
        history = []
        for i in range(90):
            date = datetime.now() - timedelta(days=89-i)
            base_gmv = 3000 + i * 10 + random.randint(-200, 200)
            history.append({
                'date': date.strftime('%Y-%m-%d'),
                'gmv': base_gmv,
                'commission': base_gmv * 0.15,
                'fyp_score': random.randint(75, 98),
                'views': random.randint(50000, 150000),
                'likes': random.randint(5000, 20000),
                'shares': random.randint(200, 800),
                'products_sold': random.randint(40, 120)
            })
        return history
    
    def verify_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def update_settings(self, new_settings):
        with user_lock:
            for key, value in new_settings.items():
                if key in self.settings:
                    if isinstance(value, str) and value.lower() in ['true', 'false']:
                        value = value.lower() == 'true'
                    self.settings[key] = value
    
    def add_alert(self, alert_type, title, message, level='info', data=None):
        """Add an alert for the user"""
        alert_id = secrets.token_urlsafe(8)
        alert = {
            'id': alert_id,
            'type': alert_type,
            'title': title,
            'message': message,
            'level': level,  # info, warning, critical
            'data': data or {},
            'created_at': datetime.now().isoformat(),
            'is_read': False,
            'is_resolved': False
        }
        
        if self.id not in alerts:
            alerts[self.id] = []
        alerts[self.id].append(alert)
        
        # Limit to 100 alerts per user
        if len(alerts[self.id]) > 100:
            alerts[self.id] = alerts[self.id][-100:]
        
        # Send real-time notification via WebSocket
        if self.socket_id:
            socketio.emit('new_alert', alert, room=self.socket_id)
        
        # Send email if enabled
        if self.settings['alert_email'] and level in ['warning', 'critical']:
            self._send_alert_email(alert)
        
        return alert
    
    def _send_alert_email(self, alert):
        """Send alert email (mock implementation)"""
        # In production, this would send actual emails
        print(f"[EMAIL] Would send alert to {self.email}: {alert['title']} - {alert['message']}")
        # Actual email implementation would go here:
        # msg = MIMEMultipart()
        # msg['From'] = 'alerts@peakoverwatch.com'
        # msg['To'] = self.email
        # msg['Subject'] = f"[Peak Overwatch] {alert['title']}"
        # msg.attach(MIMEText(alert['message'], 'plain'))
        # Send via SMTP...
    
    def get_unread_alerts(self):
        """Get unread alerts for the user"""
        user_alerts = alerts.get(self.id, [])
        return [a for a in user_alerts if not a['is_read']]
    
    def mark_alert_read(self, alert_id):
        """Mark an alert as read"""
        user_alerts = alerts.get(self.id, [])
        for alert in user_alerts:
            if alert['id'] == alert_id:
                alert['is_read'] = True
                return True
        return False
    
    def resolve_alert(self, alert_id):
        """Mark an alert as resolved"""
        user_alerts = alerts.get(self.id, [])
        for alert in user_alerts:
            if alert['id'] == alert_id:
                alert['is_resolved'] = True
                alert['resolved_at'] = datetime.now().isoformat()
                return True
        return False

# Create demo user
demo_hash = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
users['demo@peakoverwatch.com'] = User(1, 'demo@peakoverwatch.com', demo_hash, 'Demo User', 'Peak Medium')

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

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    token = request.args.get('token')
    if token and token in sessions:
        user_id = sessions[token]['user_id']
        user = next((u for u in users.values() if u.id == user_id), None)
        if user:
            user.socket_id = request.sid
            print(f"User {user.email} connected via WebSocket")
            # Send any pending alerts
            unread_alerts = user.get_unread_alerts()
            if unread_alerts:
                emit('initial_alerts', unread_alerts)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    for user in users.values():
        if user.socket_id == request.sid:
            user.socket_id = None
            print(f"User {user.email} disconnected from WebSocket")

@socketio.on('mark_alert_read')
def handle_mark_alert_read(data):
    """Mark an alert as read via WebSocket"""
    alert_id = data.get('alert_id')
    token = request.args.get('token')
    if token and token in sessions:
        user_id = sessions[token]['user_id']
        user = next((u for u in users.values() if u.id == user_id), None)
        if user and alert_id:
            user.mark_alert_read(alert_id)
            emit('alert_read', {'alert_id': alert_id})

# Background task for monitoring and alerts
def monitor_task():
    """Background task to monitor accounts and generate alerts"""
    while True:
        try:
            with user_lock:
                for user in users.values():
                    # Check each profile for issues
                    for profile in user.profiles:
                        # Simulate random FYP score changes
                        old_score = profile['last_fyp_score']
                        new_score = random.randint(
                            max(50, old_score - 10),
                            min(100, old_score + 10)
                        )
                        
                        # Check for FYP drops
                        if new_score < old_score:
                            drop_amount = old_score - new_score
                            threshold = user.settings['fyp_threshold_critical']
                            
                            if new_score < threshold:
                                user.add_alert(
                                    'fyp_drop_critical',
                                    f'Critical FYP Drop: @{profile["username"]}',
                                    f'FYP score dropped to {new_score}% (below critical threshold of {threshold}%)',
                                    'critical',
                                    {
                                        'profile_id': profile['id'],
                                        'profile_username': profile['username'],
                                        'old_score': old_score,
                                        'new_score': new_score,
                                        'drop_amount': drop_amount,
                                        'threshold': threshold
                                    }
                                )
                            elif new_score < user.settings['fyp_threshold_warn']:
                                user.add_alert(
                                    'fyp_drop_warning',
                                    f'FYP Warning: @{profile["username"]}',
                                    f'FYP score dropped to {new_score}% (below warning threshold)',
                                    'warning',
                                    {
                                        'profile_id': profile['id'],
                                        'profile_username': profile['username'],
                                        'old_score': old_score,
                                        'new_score': new_score
                                    }
                                )
                        
                        profile['last_fyp_score'] = new_score
                        profile['fyp_score'] = new_score
                        
                        # Simulate GMV changes
                        old_gmv = profile['last_gmv']
                        new_gmv = random.randint(
                            max(1000, int(old_gmv * 0.8)),
                            int(old_gmv * 1.2)
                        )
                        
                        # Check for significant GMV drops
                        if new_gmv < old_gmv * (1 - user.settings['gmv_drop_threshold'] / 100):
                            drop_percent = ((old_gmv - new_gmv) / old_gmv) * 100
                            user.add_alert(
                                'gmv_drop',
                                f'GMV Drop: @{profile["username"]}',
                                f'GMV dropped by {drop_percent:.1f}% (from ${old_gmv:,} to ${new_gmv:,})',
                                'warning',
                                {
                                    'profile_id': profile['id'],
                                    'profile_username': profile['username'],
                                    'old_gmv': old_gmv,
                                    'new_gmv': new_gmv,
                                    'drop_percent': drop_percent
                                }
                            )
                        
                        profile['last_gmv'] = new_gmv
                        
                        # Update profit based on new GMV
                        profile['profit'] = int(profile['profit'] * (new_gmv / max(1, old_gmv)))
            
            # Sleep for 30 seconds before next check
            time.sleep(30)
            
        except Exception as e:
            print(f"Error in monitor task: {e}")
            time.sleep(60)

# Start monitoring thread
monitor_thread = Thread(target=monitor_task, daemon=True)
monitor_thread.start()

# Routes
@app.route('/')
def index():
    token = request.cookies.get('session_token')
    if token and token in sessions:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login')
def login_page():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login - Peak Overwatch</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0a0a0a; color: #e8e8e8; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .login-box { background: #161616; border: 1px solid rgba(255,255,255,0.07); border-radius: 16px; padding: 2rem; width: 300px; }
            .logo { font-size: 1.5rem; font-weight: 800; margin-bottom: 1rem; }
            .logo span:first-child { color: #fff; }
            .logo span:last-child { color: #FF0050; margin-left: -4px; }
            input { width: 100%; padding: 0.75rem; margin: 0.5rem 0; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; color: #e8e8e8; }
            button { width: 100%; padding: 0.75rem; background: linear-gradient(135deg, #FF0050, #ff3366); color: white; border: none; border-radius: 8px; font-weight: 600; margin-top: 1rem; cursor: pointer; }
            .demo { font-size: 0.8rem; color: #888; margin-top: 1rem; text-align: center; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <div class="logo"><span>Peak</span><span>Overwatch</span></div>
            <form id="loginForm">
                <input type="email" id="email" placeholder="Email" value="demo@peakoverwatch.com" required>
                <input type="password" id="password" placeholder="Password" value="password123" required>
                <button type="submit">Sign In</button>
            </form>
            <div class="demo">Demo: demo@peakoverwatch.com / password123</div>
        </div>
        <script>
            document.getElementById('loginForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        email: document.getElementById('email').value,
                        password: document.getElementById('password').value
                    })
                });
                const data = await res.json();
                if (data.success) {
                    window.location.href = '/dashboard';
                } else {
                    alert('Login failed: ' + data.message);
                }
            });
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
    user.last_login = datetime.now()
    
    resp = jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'company': user.company
        }
    })
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
    user = request.user
    
    # Generate recent data for charts
    recent_data = user.analytics_history[-30:]
    dates = [d['date'][5:] for d in recent_data]  # MM-DD format
    gmv_data = [d['gmv'] for d in recent_data]
    fyp_data = [d['fyp_score'] for d in recent_data]
    
    # Get unread alerts
    unread_alerts = user.get_unread_alerts()
    
    # Calculate metrics
    total_gmv = sum(d['gmv'] for d in recent_data)
    total_commission = sum(d['commission'] for d in recent_data)
    avg_fyp = sum(d['fyp_score'] for d in recent_data[-7:]) / min(7, len(recent_data[-7:]))
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - Peak Overwatch</title>
        <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root {
                --red: #FF0050;
                --cyan: #00F2EA;
                --dark: #0a0a0a;
                --surface: #161616;
                --border: rgba(255,255,255,0.07);
                --text: #e8e8e8;
                --muted: #888;
                --success: #10b981;
                --warning: #f59e0b;
                --critical: #ef4444;
            }
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: var(--dark); color: var(--text); }
            
            /* Sidebar */
            .sidebar { position: fixed; top: 0; left: 0; bottom: 0; width: 260px; background: var(--surface); border-right: 1px solid var(--border); padding: 1.5rem; }
            .logo { font-size: 1.25rem; font-weight: 800; margin-bottom: 2rem; }
            .logo span:first-child { color: #fff; }
            .logo span:last-child { color: var(--red); margin-left: -4px; }
            .nav-link { display: block; padding: 0.75rem 1rem; color: var(--text); text-decoration: none; border-radius: 8px; margin-bottom: 0.25rem; }
            .nav-link:hover { background: rgba(255,255,255,0.05); }
            .nav-link.active { background: rgba(255,0,80,0.1); color: var(--cyan); border-left: 3px solid var(--red); }
            
            /* Main Content */
            .main { margin-left: 260px; padding: 2rem; }
            .header h1 { font-size: 2rem; font-weight: 800; margin-bottom: 0.5rem; background: linear-gradient(135deg, var(--cyan), var(--red)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            
            /* Metrics Grid */
            .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; margin: 2rem 0; }
            .metric-card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.5rem; }
            .metric-value { font-size: 2rem; font-weight: 800; background: linear-gradient(135deg, var(--cyan), var(--red)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            
            /* Charts */
            .chart-container { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.5rem; margin: 2rem 0; }
            .chart-wrapper { height: 300px; position: relative; }
            
            /* Alerts Panel */
            .alerts-panel { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.5rem; margin: 2rem 0; }
            .alert-item { background: var(--dark); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; }
            .alert-item.critical { border-left: 4px solid var(--critical); }
            .alert-item.warning { border-left: 4px solid var(--warning); }
            .alert-item.info { border-left: 4px solid var(--cyan); }
            .alert-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
            .alert-title { font-weight: 600; }
            .alert-time { font-size: 0.8rem; color: var(--muted); }
            .alert-message { color: var(--muted); font-size: 0.9rem; }
            
            /* Accounts */
            .accounts { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.5rem; }
            .account-row { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 1.5rem; padding: 1rem 0; border-bottom: 1px solid var(--border); }
            
            /* Buttons */
            .btn { background: linear-gradient(135deg, var(--red), #ff3366); color: white; border: none; padding: 0.5rem 1rem; border-radius: 8px; font-weight: 600; cursor: pointer; }
            
            /* User Menu */
            .user-menu { position: absolute; bottom: 1.5rem; left: 1.5rem; right: 1.5rem; }
            .logout-link { color: var(--muted); text-decoration: none; font-size: 0.85rem; }
            
            /* Notification Badge */
            .notification-badge { background: var(--red); color: white; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 600; }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="logo"><span>Peak</span><span>Overwatch</span></div>
            <a href="/dashboard" class="nav-link active">Dashboard</a>
            <a href="/alerts" class="nav-link">
                Alerts
                {% if unread_alerts %}
                <span class="notification-badge" style="float: right;">{{ unread_alerts|length }}</span>
                {% endif %}
            </a>
            <a href="/settings" class="nav-link">Settings</a>
            <div class="user-menu">
                <div style="margin-bottom: 0.5rem;">{{ user.name or user.email }}</div>
                <a href="/logout" class="logout-link">Sign Out</a>
            </div>
        </div>
        
        <div class="main">
            <!-- Header -->
            <div class="header">
                <h1>Portfolio Overview</h1>
                <p style="color: var(--muted);">Real-time monitoring of your TikTok affiliate performance</p>
            </div>
            
            <!-- Metrics -->
            <div class="metrics">
                <div class="metric-card">
                    <div style="color: var(--muted); font-size: 0.9rem;">Total GMV</div>
                    <div class="metric-value">${{ "{:,}".format(total_gmv|int) }}</div>
                </div>
                <div class="metric-card">
                    <div style="color: var(--muted); font-size: 0.9rem;">Commission</div>
                    <div class="metric-value">${{ "{:,}".format(total_commission|int) }}</div>
                </div>
                <div class="metric-card">
                    <div style="color: var(--muted); font-size: 0.9rem;">Avg FYP Score</div>
                    <div class="metric-value">{{ avg_fyp|int }}%</div>
                </div>
                <div class="metric-card">
                    <div style="color: var(--muted); font-size: 0.9rem;">Active Alerts</div>
                    <div class="metric-value">{{ unread_alerts|length }}</div>
                </div>
            </div>
            
            <!-- Charts -->
            <div class="chart-container">
                <h3 style="margin-bottom: 1rem;">Performance Trends</h3>
                <div class="chart-wrapper">
                    <canvas id="performanceChart"></canvas>
                </div>
            </div>
            
            <!-- Recent Alerts -->
            <div class="alerts-panel">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                    <h3>Recent Alerts</h3>
                    <button class="btn" onclick="window.location.href='/alerts'">View All</button>
                </div>
                {% if unread_alerts %}
                    {% for alert in unread_alerts[:3] %}
                    <div class="alert-item {{ alert.level }}">
                        <div class="alert-header">
                            <div class="alert-title">{{ alert.title }}</div>
                            <div class="alert-time">{{ alert.created_at[:10] }}</div>
                        </div>
                        <div class="alert-message">{{ alert.message }}</div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div style="text-align: center; color: var(--muted); padding: 2rem;">
                        No recent alerts. Everything looks good! ✅
                    </div>
                {% endif %}
            </div>
            
            <!-- Accounts -->
            <div class="accounts">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                    <h3>Account Performance</h3>
                    <button class="btn" onclick="alert('Connect TikTok feature coming soon!')">+ Add Account</button>
                </div>
                <div class="account-row" style="font-weight: 600; color: var(--muted);">
                    <div>Account</div>
                    <div>Profit</div>
                    <div>Growth</div>
                    <div>FYP Score</div>
                </div>
                {% for profile in user.profiles %}
                <div class="account-row">
                    <div>@{{ profile.username }}</div>
                    <div>${{ "{:,}".format(profile.profit) }}</div>
                    <div>{{ profile.growth }}%</div>
                    <div>
                        <span style="color: {% if profile.fyp_score >= user.settings.fyp_threshold_good %}var(--success){% elif profile.fyp_score >= user.settings.fyp_threshold_warn %}var(--warning){% else %}var(--critical){% endif %};">
                            {{ profile.fyp_score }}%
                        </span>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <script>
            // Initialize WebSocket connection
            const socket = io({
                query: {
                    token: getCookie('session_token')
                }
            });
            
            // Handle new alerts
            socket.on('new_alert', (alert) => {
                showAlertNotification(alert);
                updateAlertBadge();
            });
            
            socket.on('initial_alerts', (alerts) => {
                console.log('Initial alerts:', alerts);
            });
            
            socket.on('alert_read', (data) => {
                console.log('Alert marked as read:', data.alert_id);
            });
            
            // Chart initialization
            const ctx = document.getElementById('performanceChart').getContext('2d');
            const dates = {{ dates|tojson }};
            const gmvData = {{ gmv_data|tojson }};
            const fypData = {{ fyp_data|tojson }};
            
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
                            label: 'FYP Score',
                            data: fypData,
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
                                color: '#888'
                            }
                        }
                    },
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            grid: { color: 'rgba(255,255,255,0.05)' },
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
                            grid: { drawOnChartArea: false },
                            ticks: { 
                                color: '#888',
                                callback: function(value) {
                                    return value + '%';
                                }
                            },
                            min: 0,
                            max: 100
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#888', maxRotation: 0 }
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
            
            function showAlertNotification(alert) {
                // Create notification element
                const notification = document.createElement('div');
                notification.className = `alert-item ${alert.level}`;
                notification.style.position = 'fixed';
                notification.style.top = '20px';
                notification.style.right = '20px';
                notification.style.width = '300px';
                notification.style.zIndex = '1000';
                notification.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
                
                notification.innerHTML = `
                    <div class="alert-header">
                        <div class="alert-title">${alert.title}</div>
                        <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; cursor: pointer;">×</button>
                    </div>
                    <div class="alert-message">${alert.message}</div>
                `;
                
                document.body.appendChild(notification);
                
                // Auto-remove after 10 seconds
                setTimeout(() => {
                    if (notification.parentElement) {
                        notification.remove();
                    }
                }, 10000);
            }
            
            function updateAlertBadge() {
                // Update the alert badge count
                const badge = document.querySelector('.notification-badge');
                if (badge) {
                    const currentCount = parseInt(badge.textContent) || 0;
                    badge.textContent = currentCount + 1;
                }
            }
            
            // Mark alert as read when clicked
            document.addEventListener('click', (e) => {
                const alertItem = e.target.closest('.alert-item');
                if (alertItem) {
                    // In a real implementation, you would send the alert ID to the server
                    console.log('Alert clicked, would mark as read');
                }
            });
        </script>
    </body>
    </html>
    ''', user=user, dates=dates, gmv_data=gmv_data, fyp_data=fyp_data, 
         total_gmv=total_gmv, total_commission=total_commission, avg_fyp=avg_fyp,
         unread_alerts=unread_alerts)

@app.route('/alerts')
@login_required
def alerts_page():
    user = request.user
    user_alerts = alerts.get(user.id, [])
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Alerts - Peak Overwatch</title>
        <style>
            :root {
                --red: #FF0050;
                --cyan: #00F2EA;
                --dark: #0a0a0a;
                --surface: #161616;
                --border: rgba(255,255,255,0.07);
                --text: #e8e8e8;
                --muted: #888;
                --success: #10b981;
                --warning: #f59e0b;
                --critical: #ef4444;
            }
            * { margin: 0; padding: 0;