#!/usr/bin/env python3
"""
Peak Overwatch - COMPLETE WITH ALL 5 TABS
Dashboard, Accounts, Analytics, Alerts, Settings - All functional
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
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'complete-' + secrets.token_hex(16))

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
            {'id': 1, 'username': 'ourviralpicks', 'niche': 'Home & Lifestyle', 'profit': 12412, 'growth': 24.7, 'fyp_score': 95, 'status': 'active', 'last_active': '2026-04-07 08:45:00', 'followers': 125000, 'videos': 342},
            {'id': 2, 'username': 'homegadgetfinds', 'niche': 'Gadgets & Tech', 'profit': 8923, 'growth': 18.2, 'fyp_score': 88, 'status': 'active', 'last_active': '2026-04-07 09:15:00', 'followers': 89000, 'videos': 215},
            {'id': 3, 'username': 'beautytrends', 'niche': 'Beauty & Skincare', 'profit': 15678, 'growth': 32.1, 'fyp_score': 92, 'status': 'active', 'last_active': '2026-04-07 07:30:00', 'followers': 210000, 'videos': 489},
            {'id': 4, 'username': 'cartcravings30', 'niche': 'Food & Kitchen', 'profit': 5842, 'growth': 8.3, 'fyp_score': 72, 'status': 'warning', 'last_active': '2026-04-06 22:15:00', 'followers': 45000, 'videos': 128},
            {'id': 5, 'username': 'fitnessessentials', 'niche': 'Fitness & Wellness', 'profit': 10234, 'growth': 21.5, 'fyp_score': 89, 'status': 'active', 'last_active': '2026-04-07 10:00:00', 'followers': 167000, 'videos': 312}
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

# Create demo user
demo_hash = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
users['demo@peakoverwatch.com'] = User(1, 'demo@peakoverwatch.com', demo_hash, 'Demo User', 'Peak Medium')

# Add initial alerts
demo_user = users['demo@peakoverwatch.com']
demo_user.add_alert('🚨 Critical FYP Drop', '@cartcravings30 FYP score dropped from 78% to 72%', 'critical')
demo_user.add_alert('⚠️ Performance Warning', '@homegadgetfinds growth rate below threshold', 'warning')
demo_user.add_alert('📈 Strong Performance', '@beautytrends achieved 32.1% growth this week', 'info')
demo_user.add_alert('✅ Account Connected', 'Successfully connected @fitnessessentials', 'success')
demo_user.add_alert('📊 Weekly Report Ready', 'Your weekly performance summary is available', 'info')

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

# Routes
@app.route('/')
def index():
    token = request.cookies.get('session_token')
    if token and token in sessions:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login')
def login():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - Peak Overwatch</title>
        <style>
            :root { --red: #FF0050; --cyan: #00F2EA; --dark: #0a0a0a; --surface: #161616; --border: rgba(255,255,255,0.07); --text: #e8e8e8; --muted: #888888; }
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: var(--dark); color: var(--text); display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 1rem; }
            .login-container { width: 100%; max-width: 400px; }
            .login-card { background: var(--surface); border: 1px solid var(--border); border-radius: 20px; padding: 2.5rem; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
            .logo { text-align: center; margin-bottom: 2rem; }
            .logo-main { font-size: 2rem; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 0.5rem; }
            .logo-main span:first-child { color: #fff; }
            .logo-main span:last-child { color: var(--red); margin-left: -4px; }
            .logo-subtitle { color: var(--muted); font-size: 0.9rem; }
            .form-group { margin-bottom: 1.5rem; }
            label { display: block; margin-bottom: 0.5rem; color: var(--muted); font-size: 0.9rem; font-weight: 500; }
            input { width: 100%; padding: 1rem; background: rgba(255,255,255,0.05); border: 1px solid var(--border); border-radius: 10px; color: var(--text); font-size: 1rem; }
            input:focus { outline: none; border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(0,242,234,0.1); }
            .btn-primary { width: 100%; padding: 1rem; background: linear-gradient(135deg, var(--red), #ff3366); color: white; border: none; border-radius: 10px; font-size: 1rem; font-weight: 600; cursor: pointer; }
            .demo-info { text-align: center; margin-top: 1.5rem; padding: 1rem; background: rgba(255,0,80,0.05); border: 1px solid rgba(255,0,80,0.1); border-radius: 10px; color: var(--muted); font-size: 0.9rem; }
            .error-message { color: #ef4444; font-size: 0.9rem; margin-top: 0.5rem; display: none; }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-card">
                <div class="logo">
                    <div class="logo-main"><span>Peak</span><span>Overwatch</span></div>
                    <div class="logo-subtitle">All 5 Tabs Complete</div>
                </div>
                <form id="loginForm">
                    <div class="form-group">
                        <label for="email">Email</label>
                        <input type="email" id="email" value="demo@peakoverwatch.com" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" value="password123" required>
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
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ 
                        email: document.getElementById('email').value,
                        password: document.getElementById('password').value 
                    })
                });
                const data = await response.json();
                if (data.success) window.location.href = '/dashboard';
                else document.getElementById('errorMessage').textContent = data.message || 'Login failed';
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

# Helper to render pages
def render_page(user, active_tab, content):
    unread_alerts = user.get_unread_alerts()
    total_gmv = sum(p['profit'] * 3 for p in user.profiles)
    commission_earned = int(total_gmv * 0.15)
    fyp_health_score = int(sum(p['fyp_score'] for p in user.profiles) / len(user.profiles))
    
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Peak Overwatch • {active_tab.title()}</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root {{ --red: #FF0050; --cyan: #00F2EA; --dark: #0a0a0a; --surface: #161616; --border: rgba(255,255,255,0.07); --text: #e8e8e8; --muted: #888888; }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: var(--dark); color: var(--text); }}
            .sidebar {{ position: fixed; top: 0; left: 0; bottom: 0; width: 260px; background: var(--surface); border-right: 1px solid var(--border); padding: 1.5rem; }}
            .logo {{ font-size: 1.25rem; font-weight: 800; margin-bottom: 2rem; }}
            .logo span:first-child {{ color: #fff; }}
            .logo span:last-child {{ color: var(--red); margin-left: -4px; }}
            .nav-link {{ display: block; padding: 0.75rem 1rem; color: #e8e8e8; text-decoration: none; border-radius: 8px; margin-bottom: 0.25rem; display: flex; align-items: center; gap: 0.75rem; }}
            .nav-link.active {{ background: rgba(255,0,80,0.1); color: #00F2EA; }}
            .nav-link:hover:not(.active) {{ background: rgba(255,255,255,0.05); }}
            .main-content {{ margin-left: 260px; padding: 2rem; min-height: 100vh; }}
            .page-header {{ margin-bottom: 2rem; }}
            .page-header h1 {{ font-size: 2rem; font-weight: 800; margin-bottom: 0.5rem; background: linear-gradient(135deg, var(--cyan), var(--red)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
            .page-header p {{ color: var(--muted); font-size: 1.1rem; }}
            .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem; }}
            .btn {{ background: linear-gradient(135deg, var(--red), #ff3366); color: white; border: none; padding: 0.5rem 1rem; border-radius: 8px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-block; }}
            .notification-badge {{ background: var(--red); color: white; border-radius: 50%; width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 600; margin-left: auto; }}
            .user-menu {{ position: absolute; bottom: 1.5rem; left: 1.5rem; right: 1.5rem; }}
            .user-info {{ padding: 1rem; background: var(--dark); border-radius: 8px; margin-bottom: 0.5rem; }}
            .user-name {{ font-weight: 600; margin-bottom: 0.25rem; }}
            .user-email {{ font-size: 0.85rem; color: var(--muted); }}
            .logout-link {{ display: block; padding: 0.75rem 1rem; color: var(--muted); text-decoration: none; border-radius: 8px; }}
            .logout-link:hover {{ background: rgba(255,255,255,0.05); color: var(--text); }}
            .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; margin-bottom: 2rem; }}
            .metric-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.5rem; }}
            .metric-label {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 0.5rem; }}
            .metric-value {{ font-size: 2rem; font-weight: 800; color: var(--cyan); }}
            .