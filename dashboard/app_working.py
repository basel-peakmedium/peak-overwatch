#!/usr/bin/env python3
"""
Peak Overwatch Dashboard - Working Version
Complete with authentication, settings, and mock TikTok integration
"""

from flask import Flask, render_template_string, redirect, request, jsonify, make_response
import os
import json
from datetime import datetime, timedelta
import random
import bcrypt
import secrets
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Simple in-memory storage
users = {}
sessions = {}

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
            'daily_emails': True,
            'weekly_summary': True
        }
        self.profiles = [
            {'id': 1, 'username': 'ourviralpicks', 'niche': 'Home & Lifestyle', 'profit': 12412, 'growth': 24.7, 'fyp': 95},
            {'id': 2, 'username': 'homegadgetfinds', 'niche': 'Gadgets & Tech', 'profit': 8923, 'growth': 18.2, 'fyp': 88},
            {'id': 3, 'username': 'beautytrends', 'niche': 'Beauty & Skincare', 'profit': 15678, 'growth': 32.1, 'fyp': 92}
        ]
    
    def verify_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

# Create demo user
demo_hash = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
users['demo@peakoverwatch.com'] = User(1, 'demo@peakoverwatch.com', demo_hash, 'Demo User', 'Peak Medium')

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
    user = request.user
    
    # Generate mock data
    dates = []
    gmv_data = []
    for i in range(30):
        date = datetime.now() - timedelta(days=29-i)
        dates.append(date.strftime('%b %d'))
        gmv_data.append(4000 + i*200 + random.randint(-300, 300))
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - Peak Overwatch</title>
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
            .accounts { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.5rem; }
            .account-row { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 1.5rem; padding: 1rem 0; border-bottom: 1px solid var(--border); }
            .btn { background: linear-gradient(135deg, var(--red), #ff3366); color: white; border: none; padding: 0.5rem 1rem; border-radius: 8px; font-weight: 600; cursor: pointer; }
            .user-menu { position: absolute; bottom: 1.5rem; left: 1.5rem; right: 1.5rem; }
            .logout-link { color: var(--muted); text-decoration: none; font-size: 0.85rem; }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="logo"><span>Peak</span><span>Overwatch</span></div>
            <a href="/dashboard" class="nav-link active">Dashboard</a>
            <a href="/settings" class="nav-link">Settings</a>
            <div class="user-menu">
                <div style="margin-bottom: 0.5rem;">{{ user.name or user.email }}</div>
                <a href="/logout" class="logout-link">Sign Out</a>
            </div>
        </div>
        <div class="main">
            <div class="header">
                <h1>Portfolio Overview</h1>
                <p style="color: var(--muted);">Monitor your TikTok affiliate performance</p>
            </div>
            
            <div class="metrics">
                <div class="metric-card">
                    <div style="color: var(--muted); font-size: 0.9rem;">Total GMV</div>
                    <div class="metric-value">$186,420</div>
                </div>
                <div class="metric-card">
                    <div style="color: var(--muted); font-size: 0.9rem;">Commission</div>
                    <div class="metric-value">$27,963</div>
                </div>
                <div class="metric-card">
                    <div style="color: var(--muted); font-size: 0.9rem;">FYP Score</div>
                    <div class="metric-value">94%</div>
                </div>
                <div class="metric-card">
                    <div style="color: var(--muted); font-size: 0.9rem;">Accounts</div>
                    <div class="metric-value">{{ user.profiles|length }}</div>
                </div>
            </div>
            
            <div class="chart-container">
                <h3 style="margin-bottom: 1rem;">Daily GMV - Last 30 Days</h3>
                <div style="height: 200px; position: relative;">
                    <canvas id="chart"></canvas>
                </div>
            </div>
            
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
                    <div>{{ profile.fyp }}%</div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            const ctx = document.getElementById('chart').getContext('2d');
            const dates = {{ dates|tojson }};
            const gmvData = {{ gmv_data|tojson }};
            
            // Create gradient
            const gradient = ctx.createLinearGradient(0, 0, 0, 200);
            gradient.addColorStop(0, 'rgba(255, 0, 80, 0.35)');
            gradient.addColorStop(0.5, 'rgba(255, 50, 120, 0.25)');
            gradient.addColorStop(1, 'rgba(0, 242, 234, 0.08)');
            
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        data: gmvData,
                        borderColor: '#FF0050',
                        backgroundColor: gradient,
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#888' } },
                        x: { grid: { display: false }, ticks: { color: '#888', maxRotation: 0 } }
                    }
                }
            });
        </script>
    </body>
    </html>
    ''', user=user, dates=dates, gmv_data=gmv_data)

@app.route('/settings')
@login_required
def settings():
    user = request.user
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Settings - Peak Overwatch</title>
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
            .settings-card {{ background: #161616; border: 1px solid rgba(255,255,255,0.07); border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem; }}
            h2 {{ margin-bottom: 1rem; }}
            .form-group {{ margin-bottom: 1rem; }}
            label {{ display: block; margin-bottom: 0.5rem; color: #888; }}
            input, select {{ width: 100%; padding: 0.75rem; background: rgba(255,255,255,0.05); border: 1px solid rgba(255