#!/usr/bin/env python3
"""
Peak Overwatch - FINAL COMPLETE VERSION
All 5 tabs working: Dashboard, Accounts, Analytics, Alerts, Settings
"""

from flask import Flask, render_template_string, redirect, request, jsonify, make_response
import os
import bcrypt
import secrets
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'final-' + secrets.token_hex(16))

# Storage
users = {}
sessions = {}

class User:
    def __init__(self, user_id, email, password_hash):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash

# Create demo user
demo_hash = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
users['demo@peakoverwatch.com'] = User(1, 'demo@peakoverwatch.com', demo_hash)

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
    if not user or not bcrypt.checkpw(data['password'].encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({'success': False, 'message': 'Invalid credentials'})
    
    token = secrets.token_urlsafe(32)
    sessions[token] = {'user_id': user.id}
    
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
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Peak Overwatch • {{ active_tab }}</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
        <style>
            :root { 
                --red: #FF0050; 
                --cyan: #00F2EA; 
                --dark: #0a0a0a; 
                --surface: #161616; 
                --border: rgba(255,255,255,0.07); 
                --text: #e8e8e8; 
                --muted: #888888; 
            }
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
                background: var(--dark); 
                color: var(--text); 
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
            .main-content { 
                margin-left: 260px; 
                padding: 2rem; 
                min-height: 100vh; 
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
            }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="logo">Peak<span>Overwatch</span></div>
            <nav>
                <a href="/dashboard" class="nav-link {{ 'active' if active_tab == 'dashboard' else '' }}">
                    <i class="bi bi-speedometer2"></i><span>Dashboard</span>
                </a>
                <a href="/accounts" class="nav-link {{ 'active' if active_tab == 'accounts' else '' }}">
                    <i class="bi bi-person-badge"></i><span>Accounts</span>
                </a>
                <a href="/analytics" class="nav-link {{ 'active' if active_tab == 'analytics' else '' }}">
                    <i class="bi bi-graph-up"></i><span>Analytics</span>
                </a>
                <a href="/alerts" class="nav-link {{ 'active' if active_tab == 'alerts' else '' }}">
                    <i class="bi bi-bell"></i><span>Alerts</span>
                </a>
                <a href="/settings" class="nav-link {{ 'active' if active_tab == 'settings' else '' }}">
                    <i class="bi bi-gear"></i><span>Settings</span>
                </a>
            </nav>
            <div style="position: absolute; bottom: 1.5rem; left: 1.5rem; right: 1.5rem;">
                <div style="padding: 1rem; background: var(--dark); border-radius: 8px; margin-bottom: 0.5rem;">
                    <div style="font-weight: 600; margin-bottom: 0.25rem;">Demo User</div>
                    <div style="font-size: 0.85rem; color: var(--muted);">{{ user.email }}</div>
                </div>
                <a href="/logout" style="display: block; padding: 0.75rem 1rem; color: var(--muted); text-decoration: none; border-radius: 8px;">
                    <i class="bi bi-box-arrow-right"></i><span>Sign Out</span>
                </a>
            </div>
        </div>
        <div class="main-content">
            {{ content|safe }}
        </div>
    </body>
    </html>
    ''', user=user, active_tab=active_tab, content=content)

@app.route('/dashboard')
@login_required
def dashboard():
    user = request.user
    
    content = '''
    <div class="page-header">
        <h1>Dashboard Overview</h1>
        <p>Monitor your TikTok affiliate performance across all accounts</p>
    </div>
    
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; margin-bottom: 2rem;">
        <div class="card">
            <div style="color: var(--muted); font-size: 0.9rem; margin-bottom: 0.5rem;">Total GMV</div>
            <div style="font-size: 2rem; font-weight: 800; color: var(--cyan);">$372,360</div>
            <div style="color: #10b981; font-size: 0.85rem; margin-top: 0.5rem;">
                <i class="bi bi-arrow-up-right"></i> +12.4% from last month
            </div>
        </div>
        
        <div class="card">
            <div style="color: var(--muted); font-size: 0.9rem; margin-bottom: 0.5rem;">Commission Earned</div>
            <div style="font-size: 2rem; font-weight: 800; color: var(--cyan);">$55,854</div>
            <div style="color: #10b981; font-size: 0.85rem; margin-top: 0.5rem;">
                <i class="bi bi-arrow-up-right"></i> +8.7% from last month
            </div>
        </div>
        
        <div class="card">
            <div style="color: var(--muted); font-size: 0.9rem; margin-bottom: 0.5rem;">FYP Health Score</div>
            <div style="font-size: 2rem; font-weight: 800; color: var(--cyan);">87%</div>
            <div style="color: #10b981; font-size: 0.85rem; margin-top: 0.5rem;">
                <i class="bi bi-arrow-up-right"></i> +3.2% from last week
            </div>
        </div>
        
        <div class="card">
            <div style="color: var(--muted); font-size: 0.9rem; margin-bottom: 0.5rem;">Active Accounts</div>
            <div style="font-size: 2rem; font-weight: 800; color: var(--cyan);">5</div>
            <div style="color: #10b981; font-size: 0.85rem; margin-top: 0.5rem;">
                <i class="bi bi-plus-circle"></i> +2 new this month
            </div>
        </div>
    </div>
    
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
            <h2 style="font-size: 1.25rem; font-weight: 600;">Account Performance</h2>
            <button class="btn" onclick="alert('Connect TikTok feature coming soon!')">
                <i class="bi bi-plus"></i> Add Account
            </button>
        </div>
        
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr>
                    <th style="text-align: left; padding: 0.75rem 1rem; color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--border);">Account</th>
                    <th style="text-align: left; padding: 0.75rem 1rem; color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--border);">Niche</th>
                    <th style="text-align: left; padding: 0.75rem 1rem; color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--border);">Profit</th