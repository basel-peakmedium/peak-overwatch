#!/usr/bin/env python3
"""
Peak Overwatch Dashboard - Phase 4 Simple
Real-time alerts and notification system
"""

from flask import Flask, render_template_string, redirect, request, jsonify, make_response
from flask_socketio import SocketIO, emit
import os
import json
from datetime import datetime, timedelta
import random
import bcrypt
import secrets
from threading import Thread, Lock
import time
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-phase4')
app.config['ENV'] = os.environ.get('FLASK_ENV', 'production')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
socketio = SocketIO(app, cors_allowed_origins=os.environ.get('CORS_ALLOWED_ORIGINS', '*'))

# Simple in-memory storage
users = {}
sessions = {}
alerts = {}
lock = Lock()
SESSION_LIFETIME = timedelta(days=7)

class User:
    def __init__(self, user_id, email, password_hash, name=None, company=None):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash
        self.name = name
        self.company = company
        self.socket_id = None
        self.settings = {
            'alert_email': True,
            'alert_notifications': True,
            'fyp_threshold_good': 80,
            'fyp_threshold_warn': 70,
            'fyp_threshold_critical': 60
        }
        self.profiles = [
            {'id': 1, 'username': 'ourviralpicks', 'niche': 'Home & Lifestyle', 'fyp_score': 95, 'last_fyp': 95},
            {'id': 2, 'username': 'homegadgetfinds', 'niche': 'Gadgets & Tech', 'fyp_score': 88, 'last_fyp': 88},
            {'id': 3, 'username': 'beautytrends', 'niche': 'Beauty & Skincare', 'fyp_score': 92, 'last_fyp': 92}
        ]
    
    def verify_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def add_alert(self, alert_type, title, message, level='info'):
        alert_id = secrets.token_urlsafe(8)
        alert = {
            'id': alert_id,
            'type': alert_type,
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
            
            # Keep only last 50 alerts
            if len(alerts[self.id]) > 50:
                alerts[self.id] = alerts[self.id][-50:]
        
        # Send via WebSocket if connected
        if self.socket_id:
            socketio.emit('new_alert', alert, room=self.socket_id)
        
        print(f"[ALERT] {level.upper()} for {self.email}: {title}")
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
demo_hash = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
users['demo@peakoverwatch.com'] = User(1, 'demo@peakoverwatch.com', demo_hash, 'Demo User', 'Peak Medium')

# WebSocket handlers
@socketio.on('connect')
def handle_connect():
    token = request.args.get('token')
    if token and token in sessions:
        user_id = sessions[token]['user_id']
        user = next((u for u in users.values() if u.id == user_id), None)
        if user:
            user.socket_id = request.sid
            print(f"User {user.email} connected via WebSocket")
            # Send any unread alerts
            unread = user.get_unread_alerts()
            if unread:
                emit('initial_alerts', unread)

@socketio.on('disconnect')
def handle_disconnect():
    for user in users.values():
        if user.socket_id == request.sid:
            user.socket_id = None
            print(f"User {user.email} disconnected")

@socketio.on('mark_alert_read')
def handle_mark_alert_read(data):
    alert_id = data.get('alert_id')
    token = request.args.get('token')
    if token and token in sessions:
        user_id = sessions[token]['user_id']
        user = next((u for u in users.values() if u.id == user_id), None)
        if user and alert_id:
            user.mark_alert_read(alert_id)
            emit('alert_read', {'alert_id': alert_id})

# Background monitoring
def monitor_accounts():
    """Simulate account monitoring and alert generation"""
    while True:
        try:
            with lock:
                for user in users.values():
                    # Check each profile
                    for profile in user.profiles:
                        old_score = profile['last_fyp']
                        # Simulate score change
                        change = random.randint(-15, 10)
                        new_score = max(50, min(100, old_score + change))
                        
                        # Check for significant drops
                        if new_score < old_score:
                            drop = old_score - new_score
                            
                            if new_score < user.settings['fyp_threshold_critical']:
                                user.add_alert(
                                    'fyp_drop_critical',
                                    f'Critical FYP Drop: @{profile["username"]}',
                                    f'FYP score dropped from {old_score}% to {new_score}% (below critical threshold)',
                                    'critical'
                                )
                            elif new_score < user.settings['fyp_threshold_warn']:
                                user.add_alert(
                                    'fyp_drop_warning',
                                    f'FYP Warning: @{profile["username"]}',
                                    f'FYP score dropped from {old_score}% to {new_score}%',
                                    'warning'
                                )
                            elif drop >= 10:
                                user.add_alert(
                                    'fyp_drop_info',
                                    f'FYP Drop: @{profile["username"]}',
                                    f'FYP score dropped from {old_score}% to {new_score}%',
                                    'info'
                                )
                        
                        # Update profile
                        profile['last_fyp'] = new_score
                        profile['fyp_score'] = new_score
            
            # Sleep before next check
            time.sleep(45)  # Check every 45 seconds
            
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(60)

# Start monitor thread
Thread(target=monitor_accounts, daemon=True).start()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('session_token')
        session = sessions.get(token) if token else None
        if not token or not session:
            return redirect('/login')
        if session['expires'] < datetime.now():
            del sessions[token]
            response = make_response(redirect('/login'))
            response.delete_cookie('session_token')
            return response
        user_id = session['user_id']
        user = next((u for u in users.values() if u.id == user_id), None)
        if not user:
            response = make_response(redirect('/login'))
            response.delete_cookie('session_token')
            return response
        request.user = user
        return f(*args, **kwargs)
    return decorated

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
            <div class="demo" style="margin-top: 0.5rem;">Phase 4: Real-time alerts enabled</div>
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
    sessions[token] = {'user_id': user.id, 'expires': datetime.now() + SESSION_LIFETIME}
    
    resp = jsonify({'success': True})
    resp.set_cookie(
        'session_token',
        token,
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

@app.route('/dashboard')
@login_required
def dashboard():
    user = request.user
    unread_alerts = user.get_unread_alerts()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - Peak Overwatch</title>
        <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
        <style>
            :root {
                --red: #FF0050;
                --cyan: #00F2EA;
                --dark: #0a0a0a;
                --surface: #161616;
                --border: rgba(255,255,255,0.07);
                --text: #e8e8e8;
                --muted: #888;
                --critical: #ef4444;
                --warning: #f59e0b;
                --info: #3b82f6;
            }
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: var(--dark); color: var(--text); }
            
            .sidebar { position: fixed; top: 0; left: 0; bottom: 0; width: 260px; background: var(--surface); border-right: 1px solid var(--border); padding: 1.5rem; }
            .logo { font-size: 1.25rem; font-weight: 800; margin-bottom: 2rem; }
            .logo span:first-child { color: #fff; }
            .logo span:last-child { color: var(--red); margin-left: -4px; }
            .nav-link { display: block; padding: 0.75rem 1rem; color: var(--text); text-decoration: none; border-radius: 8px; margin-bottom: 0.25rem; }
            .nav-link:hover { background: rgba(255,255,255,0.05); }
            .nav-link.active { background: rgba(255,0,80,0.1); color: var(--cyan); border-left: 3px solid var(--red); }
            
            .main { margin-left: 260px; padding: 2rem; }
            .header h1 { font-size: 2rem; font-weight: 800; margin-bottom: 0.5rem; background: linear-gradient(135deg, var(--cyan), var(--red)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            
            .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; margin: 2rem 0; }
            .metric-card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.5rem; }
            .metric-value { font-size: 2rem; font-weight: 800; background: linear-gradient(135deg, var(--cyan), var(--red)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            
            .alerts-panel { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.5rem; margin: 2rem 0; }
            .alert-item { background: var(--dark); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; border-left: 4px solid var(--info); }
            .alert-item.critical { border-left-color: var(--critical); }
            .alert-item.warning { border-left-color: var(--warning); }
            .alert-item.info { border-left-color: var(--cyan); }
            .alert-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
            .alert-title { font-weight: 600; }
            .alert-time { font-size: 0.8rem; color: var(--muted); }
            .alert-message { color: var(--muted); font-size: 0.9rem; }
            
            .notification-badge { background: var(--red); color: white; border-radius: 50%; width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 600; margin-left: 0.5rem; }
            
            .notification-toast { position: fixed; top: 20px; right: 20px; width: 300px; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3); border-left: 4px solid var(--info); }
            .notification-toast.critical { border-left-color: var(--critical); }
            .notification-toast.warning { border-left-color: var(--warning); }
            .notification-toast.info { border-left-color: var(--cyan); }
            
            .btn { background: linear-gradient(135deg, var(--red), #ff3366); color: white; border: none; padding: 0.5rem 1rem; border-radius: 8px; font-weight: 600; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="logo"><span>Peak</span><span>Overwatch</span></div>
            <a href="/dashboard" class="nav-link active">Dashboard</a>
            <a href="/alerts" class="nav-link">
                Alerts
                {% if unread_alerts %}
                <span class="notification-badge">{{ unread_alerts|length }}</span>
                {% endif %}
            </a>
            <a href="/settings" class="nav-link">Settings</a>
            <div style="position: absolute; bottom: 1.5rem; left: 1.5rem; right: 1.5rem;">
                <div style="margin-bottom: 0.5rem;">{{ user.name or user.email }}</div>
                <a href="/logout" style="color: #888; text-decoration: none; font-size: 0.85rem;">Sign Out</a>
            </div>
        </div>
        
        <div class="main">
            <div class="header">
                <h1>Real-Time Dashboard</h1>
                <p style="color: var(--muted);">Live monitoring with real-time alerts</p>
            </div>
            
            <div class="metrics">
                <div class="metric-card">
                    <div style="color: var(--muted); font-size: 0.9rem;">Active Accounts</div>
                    <div class="metric-value">{{ user.profiles|length }}</div>
                </div>
                <div class="metric-card">
                    <div style="color: var(--muted); font-size: 0.9rem;">Avg FYP Score</div>
                    <div class="metric-value">
                        {{ (user.profiles|sum(attribute='fyp_score') / user.profiles|length)|int }}%
                    </div>
                </div>
                <div class="metric-card">
                    <div style="color: var(--muted); font-size: 0.9rem;">Unread Alerts</div>
                    <div class="metric-value">{{ unread_alerts|length }}</div>
                </div>
                <div class="metric-card">
                    <div style="color: var(--muted); font-size: 0.9rem;">Monitoring</div>
                    <div class="metric-value" style="color: #10b981;">Active</div>
                </div>
            </div>
            
            <div class="alerts-panel">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
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
                        No alerts. All systems normal! ✅
                    </div>
                {% endif %}
            </div>
            
            <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.5rem;">
                <h3 style="margin-bottom: 1rem;">Account Health</h3>
                {% for profile in user.profiles %}
                <div style="background: var(--dark); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-weight: 600;">@{{ profile.username }}</div>
                            <div style="color: var(--muted); font-size: 0.9rem;">{{ profile.niche }}</div>
                        </div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: {% if profile.fyp_score >= user.settings.fyp_threshold_good %}#10b981{% elif profile.fyp_score >= user.settings.fyp_threshold_warn %}#f59e0b{% else %}#ef4444{% endif %};">
                            {{ profile.fyp_score }}%
                        </div>
                    </div>
                    <div style="margin-top: 0.5rem; height: 4px; background: var(--border); border-radius: 2px; overflow: hidden;">
                        <div style="height: 100%; width: {{ profile.fyp_score }}%; background: {% if profile.fyp_score >= user.settings.fyp_threshold_good %}#10b981{% elif profile.fyp_score >= user.settings.fyp_threshold_warn %}#f59e0b{% else %}#ef4444{% endif %};"></div>
                    </div>
                </div>
                {% endfor %}
            </div>
            
            <div style="margin-top: 2rem; color: var(--muted); font-size: 0.9rem; text-align: center;">
                Real-time monitoring active. Alerts will appear automatically when detected.
            </div>
        </div>
        
        <script>
            // Connect to WebSocket
            const socket = io({
                query: {
                    token: getCookie('session_token')
                }
            });
            
            // Handle new alerts
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

                const badge = document.querySelector('.notification-badge');
                if (badge) {
                    const currentBadgeCount = Math.max((parseInt(badge.textContent) || 0) - 1, 0);
                    if (currentBadgeCount === 0) {
                        badge.remove();
                    } else {
                        badge.textContent = currentBadgeCount;
                    }
                }

                const metric = document.querySelector('.metric-card:nth-child(3) .metric-value');
                if (metric) {
                    const currentMetricCount = Math.max((parseInt(metric.textContent) || 0) - 1, 0);
                    metric.textContent = currentMetricCount;
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
                
                // Auto-remove after 8 seconds
                setTimeout(() => {
                    if (toast.parentElement) {
                        toast.remove();
                    }
                }, 8000);
            }
            
            function addAlertToList(alert) {
                const alertsPanel = document.querySelector('.alerts-panel');
                const noAlerts = alertsPanel.querySelector('div[style*="text-align: center"]');
                if (noAlerts) {
                    noAlerts.remove();
                }
                
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
                let badge = document.querySelector('.notification-badge');
                if (!badge) {
                    const alertsLink = document.querySelector('a[href="/alerts"]');
                    badge = document.createElement('span');
                    badge.className = 'notification-badge';
                    badge.textContent = '0';
                    alertsLink.appendChild(badge);
                }
                const currentBadgeCount = parseInt(badge.textContent) || 0;
                badge.textContent = currentBadgeCount + 1;
                
                const metric = document.querySelector('.metric-card:nth-child(3) .metric-value');
                if (metric) {
                    const currentMetricCount = parseInt(metric.textContent) || 0;
                    metric.textContent = currentMetricCount + 1;
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
            
            // Simulate a test alert after 5 seconds
            setTimeout(() => {
                console.log('Test alert system ready');
            }, 5000);
        </script>
    </body>
    </html>
    ''', user=user, unread_alerts=unread_alerts)

@app.route('/alerts')
@login_required
def alerts_page():
    user = request.user
    user_alerts = alerts.get(user.id, [])
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Alerts - Peak Overwatch</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0a0a0a; color: #e8e8e8; }}
            .sidebar {{ position: fixed; top: 0; left: 0; bottom: 0; width: 260px; background: #161616; border-right: 1px solid rgba(255,255,255,0.07); padding: 1.5rem; }}
            .logo {{ font-size: 1.25rem; font-weight: 800; margin-bottom: 2rem; }}
            .logo span:first-child {{ color: #fff; }}
            .logo span:last-child {{ color: #FF0050; margin-left: -4px; }}
            .nav-link {{ display: block; padding: 0.75rem 1rem; color: #e8e8e8; text-decoration: none; border-radius: 8px; margin-bottom: 0.25rem; }}
            .nav-link:hover {{ background: rgba(255,255,255,0.05); }}
            .nav-link.active {{ background: rgba(255,0,80,0.1); color: #00F2EA; border-left: 3px solid #FF0050; }}
            .main {{ margin-left: 260px; padding: 2rem; }}
            .alert-card {{ background: #161616; border: 1px solid rgba(255,255,255,0.07); border-radius: 16px; padding: 1.5rem; margin-bottom: 1rem; }}
            h1 {{ font-size: 2rem; font-weight: 800; margin-bottom: 0.5rem; background: linear-gradient(135deg, #00F2EA, #FF0050); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="logo"><span>Peak</span><span>Overwatch</span></div>
            <a href="/dashboard" class="nav-link">Dashboard</a>
            <a href="/alerts" class="nav-link active">Alerts</a>
            <a href="/settings" class="nav-link">Settings</a>
            <div style="position: absolute; bottom: 1.5rem; left: 1.5rem; right: 1.5rem;">
                <div style="margin-bottom: 0.5rem;">{user.name or user.email}</div>
                <a href="/logout" style="color: #888; text-decoration: none; font-size: 0.85rem;">Sign Out</a>
            </div>
        </div>
        <div class="main">
            <h1>Alert History</h1>
            <p style="color: #888; margin-bottom: 2rem;">All alerts for your account</p>
            
            {''.join([f'''
            <div class="alert-card" style="border-left: 4px solid {'#ef4444' if a['level'] == 'critical' else '#f59e0b' if a['level'] == 'warning' else '#3b82f6'};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div style="font-weight: 600;">{a['title']}</div>
                    <div style="color: #888; font-size: 0.9rem;">{a['created_at'][:10]} {a['created_at'][11:16]}</div>
                </div>
                <div style="color: #888; margin-bottom: 0.5rem;">{a['message']}</div>
                <div style="display: flex; gap: 0.5rem;">
                    <span style="background: {'rgba(239,68,68,0.1)' if a['level'] == 'critical' else 'rgba(245,158,11,0.1)' if a['level'] == 'warning' else 'rgba(59,130,246,0.1)'}; color: {'#ef4444' if a['level'] == 'critical' else '#f59e0b' if a['level'] == 'warning' else '#3b82f6'}; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem; text-transform: uppercase;">
                        {a['level']}
                    </span>
                    <span style="background: rgba(255,255,255,0.05); color: #888; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">
                        {a['type']}
                    </span>
                    {'<span style="background: rgba(16,185,129,0.1); color: #10b981; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">Read</span>' if a['is_read'] else '<span style="background: rgba(239,68,68,0.1); color: #ef4444; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">Unread</span>'}
                </div>
            </div>
            ''' for a in reversed(user_alerts)]) or '<div style="text-align: center; color: #888; padding: 3rem;">No alerts yet</div>'}
        </div>
    </body>
    </html>
    '''

@app.route('/settings')
@login_required
def settings():
    user = request.user
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Settings - Peak Overwatch</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0a0a0a; color: #e8e8e8; }
            .sidebar { position: fixed; top: 0; left: 0; bottom: 0; width: 260px; background: #161616; border-right: 1px solid rgba(255,255,255,0.07); padding: 1.5rem; }
            .logo { font-size: 1.25rem; font-weight: 800; margin-bottom: 2rem; }
            .logo span:first-child { color: #fff; }
            .logo span:last-child { color: #FF0050; margin-left: -4px; }
            .nav-link { display: block; padding: 0.75rem 1rem; color: #e8e8e8; text-decoration: none; border-radius: 8px; margin-bottom: 0.25rem; }
            .nav-link:hover { background: rgba(255,255,255,0.05); }
            .nav-link.active { background: rgba(255,0,80,0.1); color: #00F2EA; border-left: 3px solid #FF0050; }
            .main { margin-left: 260px; padding: 2rem; }
            .settings-card { background: #161616; border: 1px solid rgba(255,255,255,0.07); border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem; }
            h1 { font-size: 2rem; font-weight: 800; margin-bottom: 0.5rem; background: linear-gradient(135deg, #00F2EA, #FF0050); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .form-group { margin-bottom: 1rem; }
            label { display: block; margin-bottom: 0.5rem; color: #888; }
            input, select { width: 100%; padding: 0.75rem; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; color: #e8e8e8; }
            .btn { background: linear-gradient(135deg, #FF0050, #ff3366); color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 600; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="logo"><span>Peak</span><span>Overwatch</span></div>
            <a href="/dashboard" class="nav-link">Dashboard</a>
            <a href="/alerts" class="nav-link">Alerts</a>
            <a href="/settings" class="nav-link active">Settings</a>
            <div style="position: absolute; bottom: 1.5rem; left: 1.5rem; right: 1.5rem;">
                <div style="margin-bottom: 0.5rem;">{{ user.name or user.email }}</div>
                <a href="/logout" style="color: #888; text-decoration: none; font-size: 0.85rem;">Sign Out</a>
            </div>
        </div>
        <div class="main">
            <h1>Alert Settings</h1>
            <p style="color: #888; margin-bottom: 2rem;">Configure your alert preferences</p>

            <div class="settings-card">
                <h3 style="margin-bottom: 1rem;">FYP Score Thresholds</h3>
                <div class="form-group">
                    <label>Good Threshold (Green)</label>
                    <input type="number" value="{{ user.settings['fyp_threshold_good'] }}" min="0" max="100" id="goodThreshold">
                </div>
                <div class="form-group">
                    <label>Warning Threshold (Yellow)</label>
                    <input type="number" value="{{ user.settings['fyp_threshold_warn'] }}" min="0" max="100" id="warnThreshold">
                </div>
                <div class="form-group">
                    <label>Critical Threshold (Red)</label>
                    <input type="number" value="{{ user.settings['fyp_threshold_critical'] }}" min="0" max="100" id="criticalThreshold">
                </div>
                <button class="btn" onclick="saveThresholds()">Save Thresholds</button>
            </div>

            <div class="settings-card">
                <h3 style="margin-bottom: 1rem;">Notification Channels</h3>
                <div style="margin-bottom: 1rem;">
                    <label style="display: flex; align-items: center; gap: 0.5rem;">
                        <input type="checkbox" {% if user.settings['alert_email'] %}checked{% endif %} id="emailAlerts">
                        Email Alerts
                    </label>
                </div>
                <div style="margin-bottom: 1rem;">
                    <label style="display: flex; align-items: center; gap: 0.5rem;">
                        <input type="checkbox" {% if user.settings['alert_notifications'] %}checked{% endif %} id="inAppAlerts">
                        In-App Notifications
                    </label>
                </div>
                <button class="btn" onclick="saveNotifications()">Save Preferences</button>
            </div>

            <div class="settings-card">
                <h3 style="margin-bottom: 1rem;">Real-Time Monitoring</h3>
                <p style="color: #888; margin-bottom: 1rem;">
                    The system automatically monitors your TikTok accounts and generates alerts when:
                </p>
                <ul style="color: #888; margin-bottom: 1rem; padding-left: 1.5rem;">
                    <li>FYP score drops below configured thresholds</li>
                    <li>Significant changes in account performance</li>
                    <li>System detects potential issues</li>
                </ul>
                <div style="background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); color: #10b981; padding: 1rem; border-radius: 8px;">
                    <div style="font-weight: 600; margin-bottom: 0.25rem;">✅ Monitoring Active</div>
                    <div style="font-size: 0.9rem;">Real-time alerts are enabled and working</div>
                </div>
            </div>
        </div>

        <script>
            function saveThresholds() {
                const good = document.getElementById('goodThreshold').value;
                const warn = document.getElementById('warnThreshold').value;
                const critical = document.getElementById('criticalThreshold').value;
                alert('Thresholds saved:\nGood: ' + good + '%\nWarning: ' + warn + '%\nCritical: ' + critical + '%');
            }

            function saveNotifications() {
                const email = document.getElementById('emailAlerts').checked;
                const inApp = document.getElementById('inAppAlerts').checked;
                alert('Notifications saved:\nEmail: ' + (email ? 'ON' : 'OFF') + '\nIn-App: ' + (inApp ? 'ON' : 'OFF'));
            }
        </script>
    </body>
    </html>
    ''', user=user)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5006))
    print(f"🚀 Peak Overwatch Phase 4: Real-time Alerts")
    print(f"📡 WebSocket server starting on port {port}")
    print(f"👤 Demo: demo@peakoverwatch.com / password123")
    print(f"🔔 Real-time monitoring active")
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    socketio.run(app, host='0.0.0.0', port=port, debug=debug, allow_unsafe_werkzeug=True)