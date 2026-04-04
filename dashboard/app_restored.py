#!/usr/bin/env python3
"""
Peak Overwatch - RESTORED Dashboard
Original working dashboard with all Phase 1-5 features
Login: demo@peakoverwatch.com / password123
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
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'restored-secret-key-' + secrets.token_hex(16))

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
            {'id': 1, 'username': 'ourviralpicks', 'niche': 'Home & Lifestyle', 'fyp_score': 95, 'last_fyp': 95, 'profit': 12412, 'growth': 24.7},
            {'id': 2, 'username': 'homegadgetfinds', 'niche': 'Gadgets & Tech', 'fyp_score': 88, 'last_fyp': 88, 'profit': 8923, 'growth': 18.2},
            {'id': 3, 'username': 'beautytrends', 'niche': 'Beauty & Skincare', 'fyp_score': 92, 'last_fyp': 92, 'profit': 15678, 'growth': 32.1}
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
demo_hash = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
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
    """Login page - matches peakoverwatch.com design"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login - Peak Overwatch</title>
        <style>
            :root {
                --red: #FF0050;
                --cyan: #00F2EA;
                --dark: #0a0a0a;
                --surface: #161616;
                --border: rgba(255,255,255,0.07);
                --text: #e8e8e8;
                --muted: #888;
            }
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
                background: var(--dark); 
                color: var(--text);
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .login-container {
                width: 100%;
                max-width: 400px;
                padding: 1rem;
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
                background: linear-gradient(135deg, var(--cyan), var(--red));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 0.5rem;
            }
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
                    <div class="logo-main">Peak<span style="margin-left: -4px; color: var(--red);">Overwatch</span></div>
                    <div class="logo-subtitle">Dashboard Restored <span class="status-badge">Original</span></div>
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
            
            // Auto-focus email field
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
    """Main dashboard - matches our original design"""
    user = request.user
    unread_alerts = user.get_unread_alerts()
    
    # Generate analytics data
    analytics = []
    for i in range(30):
        date = datetime.now() - timedelta(days=29-i)
        gmv = 3000 + i * 10 + random.randint(-200, 200)
        analytics.append({
            'date': date.strftime('%m-%d'),
            'gmv': gmv,
            'fyp': random.randint(75, 98)
        })
    
    dates = [a['date'] for a in analytics]
    gmv_data = [a['gmv'] for a in analytics]
    fyp_data = [a['fyp'] for a in analytics]
    
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
            
            .chart-container { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.5rem; margin: 2rem 0; }
            .chart-wrapper { height: 300px; }
            
            .alerts-panel { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.5rem; margin: 2rem 0; }
            .alert-item { background: var(--dark); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; border-left: 4px solid var(--info); }
            .alert-item.critical { border-left-color: var(--critical); }
            .alert-item.warning { border-left-color: var(--warning); }
            .alert-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
            .alert-title { font-weight: 600; }
            .alert-time { font-size: 0.8rem; color: var(--muted); }
            .alert-message { color: var(--muted); font-size: 0.9rem; }
            
            .notification-badge { background: var(--red); color: white; border-radius: 50%; width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 600; margin-left: 0.5rem; }
            
            .notification-toast { position: fixed; top: 20px; right: 20px; width: 300px; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3); border-left: 4px solid var(--info); }
            .notification-toast.critical { border-left-color: var(--critical); }
            .notification-toast.warning { border-left-color: var(--warning); }
            
            .btn { background: linear-gradient(135deg, var(--red), #ff3366); color: white; border: none; padding: 0.5rem 1rem; border-radius: 8px; font-weight: 600; cursor: pointer; }
            
            .account-health { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.5rem; }
            .account-row { background: var(--dark); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; }
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
                <h1>Dashboard Restored</h1>
                <p style="color: var(--muted);">Original working dashboard with real-time alerts</p>
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
                    <div style="color: var(--muted); font-size: 0.9rem;">Status</div>
                    <div class="metric-value" style="color: #10b981;">Live</div>
                </div>
            </div>
            
            <div class="chart-container">
                <h3 style="margin-bottom: 1rem;">Performance Trends</h3>
                <div class="chart-wrapper">
                    <canvas id="performanceChart"></canvas>
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
                        ✅ No alerts. All systems normal!
                    </div>
                {% endif %}
            </div>
            
            <div class="account-health">
                <h3 style="margin-bottom: 1rem;">Account Health</h3>
                {% for profile in user.profiles %}
                <div class="account-row">
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
            const ctx = document.getElementById('performanceChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: {{ dates|tojson }},
                    datasets: [
                        {
                            label: 'GMV',
                            data: {{ gmv_data|tojson }},
                            borderColor: '#FF0050',
                            backgroundColor: 'rgba(255,0,80,0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: 'FYP Score',
                            data: {{ fyp_data|tojson }},
                            borderColor: '#00F2EA',
                            backgroundColor: 'rgba(0,242,234,0.1)',
                            borderWidth: 2,
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#888' } } },
                    scales: {
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#888' } },
                        x: { grid: { display: false }, ticks: { color: '#888', maxRotation: 0 } }
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
                const metric = document.querySelector('.metric-card:nth-child(3) .metric-value');
                if (metric) {
                    const current = parseInt(metric.textContent) || 0;
                    metric.textContent = current + 1;
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
        </script>
    </body>
    </html>
    ''', user=user, unread_alerts=unread_alerts, dates=dates, gmv_data=gmv_data, fyp_data=fyp_data)

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'message': 'Original dashboard restored'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5009))
    print(f"🚀 Peak Overwatch RESTORED")
    print(f"📡 Running on port {port}")
    print(f"👤 Demo: demo@peakoverwatch.com / password123")
    print(f"🔔 Real-time monitoring: ACTIVE")
    print(f"✅ Original dashboard with all features restored")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)