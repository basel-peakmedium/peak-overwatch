#!/usr/bin/env python3
"""
Peak Overwatch Dashboard - Simple Authentication Version
Works without PostgreSQL for local testing
"""

from flask import Flask, render_template_string, session, redirect, url_for, request, jsonify, make_response
import os
import json
from datetime import datetime, timedelta
import random
import bcrypt
import secrets
from functools import wraps

app = Flask(__name__)

# Production settings
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['ENV'] = os.environ.get('FLASK_ENV', 'production')

# In-memory database for testing (replace with PostgreSQL in production)
users_db = {}
sessions_db = {}

class SimpleUser:
    """Simple user model for testing"""
    
    def __init__(self, user_id, email, password_hash, full_name=None, company=None):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name
        self.company = company
        self.created_at = datetime.now()
        self.last_login = None
        self.subscription_tier = 'free'
    
    def verify_password(self, password):
        """Verify user password"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

class SimpleAuth:
    """Simple authentication for testing"""
    
    @staticmethod
    def create_user(email, password, full_name=None, company=None):
        """Create a new user"""
        if email in users_db:
            return None
        
        user_id = len(users_db) + 1
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user = SimpleUser(user_id, email, password_hash, full_name, company)
        users_db[email] = user
        
        # Create demo data for new user
        SimpleAuth._create_demo_data(user_id)
        
        return user
    
    @staticmethod
    def authenticate_user(email, password):
        """Authenticate user"""
        user = users_db.get(email)
        if not user:
            return None
        
        if not user.verify_password(password):
            return None
        
        user.last_login = datetime.now()
        return user
    
    @staticmethod
    def _create_demo_data(user_id):
        """Create demo data for new user"""
        # This would create mock profiles and analytics in a real database
        pass

class SimpleSessionManager:
    """Simple session management for testing"""
    
    @staticmethod
    def create_session(user_id):
        """Create a new session"""
        session_token = secrets.token_urlsafe(32)
        sessions_db[session_token] = {
            'user_id': user_id,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(days=7)
        }
        return session_token
    
    @staticmethod
    def validate_session(session_token):
        """Validate session token"""
        session_data = sessions_db.get(session_token)
        if not session_data:
            return None
        
        if datetime.now() > session_data['expires_at']:
            del sessions_db[session_token]
            return None
        
        # Find user by ID
        for user in users_db.values():
            if user.id == session_data['user_id']:
                return user
        
        return None
    
    @staticmethod
    def delete_session(session_token):
        """Delete session"""
        if session_token in sessions_db:
            del sessions_db[session_token]

# Create a demo user for testing
demo_user = SimpleAuth.create_user('demo@peakoverwatch.com', 'password123', 'Demo User', 'Peak Medium')

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.cookies.get('session_token')
        
        if not session_token:
            return redirect('/login')
        
        user = SimpleSessionManager.validate_session(session_token)
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
        user = SimpleSessionManager.validate_session(session_token)
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
    
    user = SimpleAuth.authenticate_user(email, password)
    if not user:
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
    
    # Create session
    session_token = SimpleSessionManager.create_session(user.id)
    
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
        secure=False,  # Set to True in production with HTTPS
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
    
    user = SimpleAuth.create_user(email, password, full_name, company)
    if not user:
        return jsonify({'success': False, 'message': 'User already exists'}), 409
    
    # Create session
    session_token = SimpleSessionManager.create_session(user.id)
    
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
        secure=False,
        samesite='Lax',
        max_age=7*24*60*60  # 7 days
    )
    
    return response

@app.route('/logout')
def logout():
    """Logout endpoint"""
    session_token = request.cookies.get('session_token')
    if session_token:
        SimpleSessionManager.delete_session(session_token)
    
    response = make_response(redirect('/login'))
    response.delete_cookie('session_token')
    return response

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard route"""
    user = request.user
    
    # Generate mock data
    time_series = generate_mock_time_series()
    accounts = generate_mock_profiles()
    
    # Calculate summary from mock data
    total_gmv = sum(day['gmv'] for day in time_series[-30:])
    total_commission = sum(day['commission'] for day in time_series[-30:])
    avg_fyp = sum(day['fyp_score'] for day in time_series[-7:]) / min(7, len(time_series[-7:]))
    
    return render_template_string(
        DASHBOARD_TEMPLATE, 
        user=user,
        total_gmv=int(total_gmv),
        commission_earned=int(total_commission),
        fyp_health_score=int(avg_fyp),
        active_accounts=len(accounts),
        time_series=json.dumps(time_series),
        accounts=accounts
    )

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

def generate_mock_profiles():
    """Generate mock profile data"""
    return [
        {'username': 'ourviralpicks', 'niche': 'Home & Lifestyle', 'profit': 12412, 'growth': 24.7, 'fyp_score': 95},
        {'username': 'homegadgetfinds', 'niche': 'Gadgets & Tech', 'profit': 8923, 'growth': 18.2, 'fyp_score': 88},
        {'username': 'beautytrends', 'niche': 'Beauty & Skincare', 'profit': 15678, 'growth': 32.1, 'fyp_score': 92},
        {'username': 'cartcravings30', 'niche': 'Food & Kitchen', 'profit': 5842, 'growth': 8.3, 'fyp_score': 72},
        {'username': 'fitnessessentials', 'niche': 'Fitness & Wellness', 'profit': 10234, 'growth': 21.5, 'fyp_score': 89}
    ]

# HTML Templates (same as before, but simplified)
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
            <p style="margin-top: 0.5rem; font-size: 0.8rem;">
                Demo: demo@peakoverwatch.com / password123
            </p>
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
                    body: JSON.stringify({ email, password })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    successMessage.textContent = 'Login successful! Redirecting...';
                    successMessage.style.display = 'block';
                    
                    // Redirect to dashboard after short delay
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 1000);
                } else {
                    errorMessage.textContent = result.message || 'Login failed';
                    errorMessage.style.display = 'block';
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Sign In';
                }
            } catch (error) {
                errorMessage.textContent = 'Network error. Please try again.';
                errorMessage.style.display = 'block';
                submitBtn.disabled = false;
                submitBtn.textContent = 'Sign In';
            }
        });
    </script>
</body>
</html>'''

REGISTER_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Create Account — Peak Overwatch</title>
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

        .register-container {
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
    <div class="register-container">
        <div class="logo">
            <div class="logo-icon">P</div>
            <span>Peak</span><span>Overwatch</span>
        </div>
        <div class="subtitle">Create your Peak Overwatch account</div>
        
        <div class="error-message" id="errorMessage"></div>
        <div class="success-message" id="successMessage"></div>
        
        <form id="registerForm">
            <div class="form-group">
                <label for="full_name">Full Name (Optional)</label>
                <input type="text" id="full_name" placeholder="John Doe">
            </div>
            
            <div class="form-group">
                <label for="company">Company (Optional)</label>
                <input type="text" id="company" placeholder="Your Company">
            </div>
            
            <div class="form-group">
                <label for="email">Email Address</label>
                <input type="email" id="email" placeholder="you@example.com" required>
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" placeholder="••••••••" required minlength="8">
                <small style="color: var(--muted); font-size: 0.8rem; margin-top: 0.25rem; display: block;">
                    Must be at least 8 characters
                </small>
            </div>
            
            <div class="form-group">
                <label for="confirm_password">Confirm Password</label>
                <input type="password" id="confirm_password" placeholder="••••••••" required>
            </div>
            
            <button type="submit" class="btn" id="submitBtn">Create Account</button>
        </form>
        
        <div class="divider"><span>Already have an account?</span></div>
        
        <a href="/login" class="btn" style="background: transparent; border: 1px solid var(--border);">
            Sign In Instead
        </a>
        
        <div class="footer-links">
            <p><a href="https://peakoverwatch.com">← Back to Homepage</a></p>
            <p style="margin-top: 0.5rem; font-size: 0.8rem;">
                By creating an account, you agree to our 
                <a href="https://peakoverwatch.com/terms">Terms</a> and 
                <a href="https://peakoverwatch.com/privacy">Privacy Policy</a>
            </p>
        </div>
    </div>

    <script>
        const registerForm = document.getElementById('registerForm');
        const errorMessage = document.getElementById('errorMessage');
        const successMessage = document.getElementById('successMessage');
        const submitBtn = document.getElementById('submitBtn');
        
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const full_name = document.getElementById('full_name').value;
            const company = document.getElementById('company').value;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const confirm_password = document.getElementById('confirm_password').value;
            
            // Clear messages
            errorMessage.style.display = 'none';
            successMessage.style.display = 'none';
            
            // Validate passwords match
            if (password !== confirm_password) {
                errorMessage.textContent = 'Passwords do not match';
                errorMessage.style.display = 'block';
                return;
            }
            
            // Validate password length
            if (password.length < 8) {
                errorMessage.textContent = 'Password must be at least 8 characters';
                errorMessage.style.display = 'block';
                return;
            }
            
            // Disable button
            submitBtn.disabled = true;
            submitBtn.textContent = 'Creating account...';
            
            try {
                const response = await fetch('/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password, full_name, company })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    successMessage.textContent = 'Account created! Redirecting...';
                    successMessage.style.display = 'block';
                    
                    // Redirect to dashboard after short delay
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 1000);
                } else {
                    errorMessage.textContent = result.message || 'Registration failed';
                    errorMessage.style.display = 'block';
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Create Account';
                }
            } catch (error) {
                errorMessage.textContent = 'Network error. Please try again.';
                errorMessage.style.display = 'block';
                submitBtn.disabled = false;
                submitBtn.textContent = 'Create Account';
            }
        });
    </script>
</body>
</html>'''

# DASHBOARD_TEMPLATE would be the same as in app-final-redesign.py
# For brevity, I'm including the template from the previous file
with open('dashboard_template.html', 'r') as f:
    DASHBOARD_TEMPLATE = f.read()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5004))  # Different port
    app.run(host='0.0.0.0', port=port, debug=(app.config['ENV'] == 'development'))