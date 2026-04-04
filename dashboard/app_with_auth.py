#!/usr/bin/env python3
"""
Peak Overwatch Dashboard - With Authentication
Complete dashboard with user accounts, database, and authentication
"""

from flask import Flask, render_template_string, session, redirect, url_for, request, jsonify, make_response
import os
import json
from datetime import datetime, timedelta
import random
from models import User, Auth, SessionManager
from functools import wraps

app = Flask(__name__)

# Production settings
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['ENV'] = os.environ.get('FLASK_ENV', 'production')
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.cookies.get('session_token')
        
        if not session_token:
            return redirect('/login')
        
        user = SessionManager.validate_session(session_token)
        if not user:
            response = make_response(redirect('/login'))
            response.delete_cookie('session_token')
            return response
        
        # Store user in request context
        request.user = user
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Home page - redirect to login or dashboard"""
    session_token = request.cookies.get('session_token')
    
    if session_token:
        user = SessionManager.validate_session(session_token)
        if user:
            return redirect('/dashboard')
    
    return redirect('/login')

@app.route('/login', methods=['GET'])
def login_page():
    """Login page"""
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def api_login():
    """Login API endpoint"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password required'}), 400
    
    user = Auth.authenticate_user(email, password)
    if not user:
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
    
    # Create session
    user_agent = request.headers.get('User-Agent')
    ip_address = request.remote_addr
    session_token = SessionManager.create_session(user.id, user_agent, ip_address)
    
    response = jsonify({
        'success': True, 
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'company': user.company
        }
    })
    
    # Set session cookie
    response.set_cookie(
        'session_token',
        session_token,
        httponly=True,
        secure=app.config['SESSION_COOKIE_SECURE'],
        samesite='Lax',
        max_age=7*24*60*60  # 7 days
    )
    
    return response

@app.route('/register', methods=['GET'])
def register_page():
    """Registration page"""
    return render_template_string(REGISTER_TEMPLATE)

@app.route('/api/register', methods=['POST'])
def api_register():
    """Registration API endpoint"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')
    company = data.get('company')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password required'}), 400
    
    if len(password) < 8:
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters'}), 400
    
    user = Auth.register_user(email, password, full_name, company)
    if not user:
        return jsonify({'success': False, 'message': 'User already exists'}), 409
    
    # Create session
    user_agent = request.headers.get('User-Agent')
    ip_address = request.remote_addr
    session_token = SessionManager.create_session(user.id, user_agent, ip_address)
    
    response = jsonify({
        'success': True, 
        'message': 'Registration successful',
        'user': {
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'company': user.company
        }
    })
    
    # Set session cookie
    response.set_cookie(
        'session_token',
        session_token,
        httponly=True,
        secure=app.config['SESSION_COOKIE_SECURE'],
        samesite='Lax',
        max_age=7*24*60*60  # 7 days
    )
    
    return response

@app.route('/logout')
def logout():
    """Logout endpoint"""
    session_token = request.cookies.get('session_token')
    if session_token:
        SessionManager.delete_session(session_token)
    
    response = make_response(redirect('/login'))
    response.delete_cookie('session_token')
    return response

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard route"""
    user = request.user
    
    # Get user data
    settings = user.get_settings()
    mock_profiles = user.get_mock_profiles()
    daily_analytics = user.get_daily_analytics(30)
    account_summary = user.get_account_summary()
    
    # Prepare time series data for chart
    time_series = []
    for day in daily_analytics:
        time_series.append({
            'date': day['date'].strftime('%Y-%m-%d'),
            'gmv': float(day['gmv']),
            'commission': float(day['commission']),
            'fyp_score': float(day['fyp_score'])
        })
    
    # If no data yet, generate mock
    if not time_series:
        time_series = generate_mock_time_series()
        account_summary = generate_mock_summary()
        mock_profiles = generate_mock_profiles()
    
    return render_template_string(
        DASHBOARD_TEMPLATE, 
        user=user,
        total_gmv=int(account_summary['total_gmv']),
        commission_earned=int(account_summary['total_commission']),
        fyp_health_score=int(account_summary['avg_fyp_score']),
        active_accounts=account_summary['active_accounts'] or len(mock_profiles),
        time_series=json.dumps(time_series),
        accounts=mock_profiles
    )

@app.route('/api/user/data')
@login_required
def user_data():
    """Get user data API"""
    user = request.user
    
    settings = user.get_settings()
    mock_profiles = user.get_mock_profiles()
    daily_analytics = user.get_daily_analytics(30)
    account_summary = user.get_account_summary()
    
    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'company': user.company,
            'subscription_tier': user.subscription_tier
        },
        'settings': settings,
        'mock_profiles': mock_profiles,
        'daily_analytics': [
            {
                'date': day['date'].strftime('%Y-%m-%d'),
                'gmv': float(day['gmv']),
                'commission': float(day['commission']),
                'fyp_score': float(day['fyp_score'])
            }
            for day in daily_analytics
        ],
        'summary': account_summary
    })

@app.route('/api/user/settings', methods=['PUT'])
@login_required
def update_settings():
    """Update user settings"""
    user = request.user
    data = request.json
    
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    user.update_settings(data)
    
    return jsonify({'success': True, 'message': 'Settings updated'})

# Helper functions for mock data
def generate_mock_time_series(days=30):
    """Generate mock time series data"""
    time_series = []
    base_date = datetime.now() - timedelta(days=days)
    
    for i in range(days):
        date = base_date + timedelta(days=i)
        base_gmv = 4000 + (i * 200) + random.randint(-300, 300)
        time_series.append({
            'date': date.strftime('%Y-%m-%d'),
            'gmv': base_gmv,
            'commission': base_gmv * 0.15 + random.randint(-200, 200),
            'fyp_score': random.randint(70, 95)
        })
    
    return time_series

def generate_mock_summary():
    """Generate mock summary data"""
    return {
        'total_gmv': 186420,
        'total_commission': 27963,
        'avg_fyp_score': 94,
        'active_accounts': 12
    }

def generate_mock_profiles():
    """Generate mock profile data"""
    return [
        {'username': 'ourviralpicks', 'niche': 'Home & Lifestyle', 'profit': 12412, 'growth': 24.7, 'fyp_score': 95},
        {'username': 'homegadgetfinds', 'niche': 'Gadgets & Tech', 'profit': 8923, 'growth': 18.2, 'fyp_score': 88},
        {'username': 'beautytrends', 'niche': 'Beauty & Skincare', 'profit': 15678, 'growth': 32.1, 'fyp_score': 92},
        {'username': 'cartcravings30', 'niche': 'Food & Kitchen', 'profit': 5842, 'growth': 8.3, 'fyp_score': 72},
        {'username': 'fitnessessentials', 'niche': 'Fitness & Wellness', 'profit': 10234, 'growth': 21.5, 'fyp_score': 89}
    ]

# HTML Templates
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign In — Peak Overwatch</title>
    <style>
        :root {
            --red: #FF0050;
            --cyan: #00F2EA;
            --dark: #0a0a0a;
            --surface: #161616;
            --border: rgba(255,255,255,0.07);
            --text: #e8e8e8;
            --muted: #888888;
            --font: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: var(--font);
            background: var(--dark);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .login-container {
            width: 100%;
            max-width: 400px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 2.5rem;
            text-align: center;
        }

        .logo {
            font-size: 1.5rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }

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
            color: white;
        }

        .logo span:first-child { color: #fff; }
        .logo span:last-child { color: var(--red); margin-left: -4px; }

        .subtitle {
            color: var(--muted);
            margin-bottom: 2rem;
            font-size: 0.95rem;
        }

        .form-group {
            margin-bottom: 1.5rem;
            text-align: left;
        }

        label {
            display: block;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
            font-weight: 500;
        }

        input {
            width: 100%;
            padding: 0.75rem 1rem;
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-size: 0.95rem;
            transition: all 0.2s;
        }

        input:focus {
            outline: none;
            border-color: var(--cyan);
            background: rgba(0, 242, 234, 0.05);
        }

        .btn {
            width: 100%;
            padding: 0.75rem;
            background: linear-gradient(135deg, var(--red), #ff3366);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(255, 0, 80, 0.3);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .divider {
            margin: 2rem 0;
            position: relative;
            text-align: center;
            color: var(--muted);
            font-size: 0.85rem;
        }

        .divider::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 1px;
            background: var(--border);
        }

        .divider span {
            background: var(--surface);
            padding: 0 1rem;
            position: relative;
        }

        .footer-links {
            margin-top: 2rem;
            font-size: 0.85rem;
            color: var(--muted);
        }

        .footer-links a {
            color: var(--cyan);
            text-decoration: none;
        }

        .footer-links a:hover {
            text-decoration: underline;
        }

        .error-message {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #ef4444;
            padding: 0.75rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
            display: none;
        }

        .success-message {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #10b981;
            padding: 0.75rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
            display: none;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <div class="logo-icon">P</div>
            <span>Peak</span><span>Overwatch</span>
        </div>
        <div class="subtitle">Sign in to access your TikTok affiliate dashboard</div>
        
        <div class="error-message" id="errorMessage"></div>
        <div class="success-message" id="successMessage"></div>
        
        <form id="loginForm">
            <div class="form-group">
                <label for="email">Email Address</label>
                <input type="email" id="email" placeholder="you@example.com" required>
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" placeholder="••••••••" required>
            </div>
            
            <button type="submit" class="btn" id="submitBtn">Sign In</button>
        </form>
        
        <div class="divider"><span>New to Peak Overwatch?</span></div>
        
        <a href="/register" class="btn" style="background: transparent; border: 1px solid var(--border);">
            Create Account
        </a>
        
        <div class="footer-links">
            <p><a href="https://peakoverwatch.com">← Back to Homepage</a></p>
        </div>
    </div>

    <script>
        const loginForm = document.getElementById('loginForm');
        const errorMessage = document.getElementById('errorMessage');
        const successMessage = document.getElementById('successMessage');
        const submitBtn = document.getElementById('submitBtn');
        
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            // Clear messages
            errorMessage.style.display = 'none';
            successMessage.style.display = 'none';
            
            // Disable button
            submitBtn.disabled = true;
            submitBtn.textContent = 'Signing in...';
            
            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: