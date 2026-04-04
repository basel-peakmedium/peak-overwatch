#!/usr/bin/env python3
"""
Peak Overwatch Dashboard - Phase 3 Complete
Settings, Profile Management, Mock TikTok Connection, Data Export
"""

from flask import Flask, render_template_string, session, redirect, url_for, request, jsonify, make_response
import os
import json
from datetime import datetime, timedelta
import random
import bcrypt
import secrets
import csv
import io
from functools import wraps

app = Flask(__name__)

# Production settings
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['ENV'] = os.environ.get('FLASK_ENV', 'production')

# In-memory database for testing
users_db = {}
sessions_db = {}

class User:
    """User model with settings and profiles"""
    
    def __init__(self, user_id, email, password_hash, full_name=None, company=None):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name
        self.company = company
        self.created_at = datetime.now()
        self.last_login = None
        self.subscription_tier = 'free'
        
        # Default settings
        self.settings = {
            'timezone': 'America/New_York',
            'currency': 'USD',
            'fyp_threshold_good': 80,
            'fyp_threshold_warn': 70,
            'fyp_threshold_critical': 60,
            'daily_email_reports': True,
            'weekly_summary_email': True,
            'alert_notifications': True,
            'alert_email': True,
            'alert_slack': False,
            'alert_telegram': False
        }
        
        # Mock TikTok profiles
        self.mock_profiles = [
            {
                'id': 1,
                'username': 'ourviralpicks',
                'niche': 'Home & Lifestyle',
                'profit': 12412,
                'growth': 24.7,
                'fyp_score': 95,
                'connected_at': datetime.now() - timedelta(days=30)
            },
            {
                'id': 2,
                'username': 'homegadgetfinds',
                'niche': 'Gadgets & Tech',
                'profit': 8923,
                'growth': 18.2,
                'fyp_score': 88,
                'connected_at': datetime.now() - timedelta(days=25)
            },
            {
                'id': 3,
                'username': 'beautytrends',
                'niche': 'Beauty & Skincare',
                'profit': 15678,
                'growth': 32.1,
                'fyp_score': 92,
                'connected_at': datetime.now() - timedelta(days=20)
            }
        ]
    
    def verify_password(self, password):
        """Verify user password"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def update_settings(self, new_settings):
        """Update user settings"""
        for key, value in new_settings.items():
            if key in self.settings:
                # Convert string booleans to actual booleans
                if isinstance(value, str) and value.lower() in ['true', 'false']:
                    value = value.lower() == 'true'
                self.settings[key] = value
    
    def add_mock_profile(self, username, niche='General'):
        """Add a mock TikTok profile"""
        new_profile = {
            'id': len(self.mock_profiles) + 1,
            'username': username,
            'niche': niche,
            'profit': random.randint(5000, 20000),
            'growth': random.uniform(5, 35),
            'fyp_score': random.randint(70, 98),
            'connected_at': datetime.now()
        }
        self.mock_profiles.append(new_profile)
        return new_profile
    
    def remove_mock_profile(self, profile_id):
        """Remove a mock TikTok profile"""
        self.mock_profiles = [p for p in self.mock_profiles if p['id'] != profile_id]
        return len([p for p in self.mock_profiles if p['id'] == profile_id]) == 0

class Auth:
    """Authentication manager"""
    
    @staticmethod
    def create_user(email, password, full_name=None, company=None):
        """Create a new user"""
        if email in users_db:
            return None
        
        user_id = len(users_db) + 1
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user = User(user_id, email, password_hash, full_name, company)
        users_db[email] = user
        
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

class SessionManager:
    """Session management"""
    
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
demo_user = Auth.create_user('demo@peakoverwatch.com', 'password123', 'Demo User', 'Peak Medium')

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

# Helper functions
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

# Routes
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
    session_token = SessionManager.create_session(user.id)
    
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
        secure=False,
        samesite='Lax',
        max_age=7*24*60*60
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
    
    # Generate mock data
    time_series = generate_mock_time_series()
    
    # Calculate summary
    total_gmv = sum(day['gmv'] for day in time_series[-30:])
    total_commission = sum(day['commission'] for day in time_series[-30:])
    avg_fyp = sum(day['fyp_score'] for day in time_series[-7:]) / min(7, len(time_series[-7:]))
    
    return render_template_string(
        DASHBOARD_TEMPLATE, 
        user=user,
        total_gmv=int(total_gmv),
        commission_earned=int(total_commission),
        fyp_health_score=int(avg_fyp),
        active_accounts=len(user.mock_profiles),
        time_series=json.dumps(time_series),
        accounts=user.mock_profiles
    )

@app.route('/settings')
@login_required
def settings_page():
    """Settings page"""
    user = request.user
    return render_template_string(SETTINGS_TEMPLATE, user=user, settings=user.settings)

# API Endpoints
@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    """Get user settings API"""
    user = request.user
    return jsonify({'success': True, 'settings': user.settings})

@app.route('/api/settings', methods=['PUT'])
@login_required
def update_settings():
    """Update user settings API"""
    user = request.user
    data = request.json
    
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    user.update_settings(data)
    return jsonify({'success': True, 'message': 'Settings updated', 'settings': user.settings})

@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    """Update user profile API"""
    user = request.user
    data = request.json
    
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    # Update user profile
    if 'full_name' in data:
        user.full_name = data['full_name']
    if 'company' in data:
        user.company = data['company']
    
    return jsonify({
        'success': True, 
        'message': 'Profile updated',
        'user': {
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'company': user.company
        }
    })

@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    """Change password API"""
    user = request.user
    data = request.json
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    if not current_password or not new_password or not confirm_password:
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    
    if new_password != confirm_password:
        return jsonify({'success': False, 'message': 'New passwords do not match'}), 400
    
    if len(new_password) < 8:
        return jsonify({'success': False, 'message': 'New password must be at least 8 characters'}), 400
    
    if not user.verify_password(current_password):
        return jsonify({'success': False, 'message': 'Current password is incorrect'}), 401
    
    # Update password
    user.password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    return jsonify({'success': True, 'message': 'Password updated successfully'})

@app.route('/api/tiktok/mock-connect', methods=['POST'])
@login_required
def mock_tiktok_connect():
    """Mock TikTok connection API"""
    user = request.user
    data = request.json
    
    username = data.get('username')
    niche = data.get('niche', 'General')
    
    if not username:
        return jsonify({'success': False, 'message': 'Username is required'}), 400
    
    # Check if profile already exists
    for profile in user.mock_profiles:
        if profile['username'] == username:
            return jsonify({'success': False, 'message': 'Account already connected'}), 409
    
    # Create new mock profile
    new_profile = user.add_mock_profile(username, niche)
    
    return jsonify({
        'success': True, 
        'message': 'TikTok account connected successfully',
        'profile': new_profile
    })

@app.route('/api/tiktok/mock-disconnect', methods=['POST'])
@login_required
def mock_tiktok_disconnect():
    """Mock TikTok disconnect API"""
    user = request.user
    data = request.json
    
    profile_id = data.get('profile_id')
    
    if not profile_id:
        return jsonify({'success': False, 'message': 'Profile ID is required'}), 400
    
    # Remove profile
    success = user.remove_mock_profile(profile_id)
    
    if not success:
        return jsonify({'success': False, 'message': 'Profile not found'}), 404
    
    return jsonify({'success': True, 'message': 'Account disconnected successfully'})

@app.route('/api/export/data', methods=['GET'])
@login_required
def export_data():
    """Export user data as CSV"""
    user = request.user
    
    # Generate CSV data
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Date', 'GMV', 'Commission', 'FYP Score', 'Account', 'Niche'])
    
    # Write data
    time_series = generate_mock_time_series(90)
    for day in time_series:
        for profile in user.mock_profiles:
            writer.writerow([
                day['date'],
                day['gmv'],
                day['commission'],
                day['fyp_score'],
                profile['username'],
                profile['niche']
            ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename=peakoverwatch_export_{datetime.now().strftime("%Y%m%d")}.csv'
    response.headers['Content-Type'] = 'text/csv'
    
    return response

@app.route('/api/export/summary', methods=['GET'])
@login_required
def export_summary():
    """Export user summary as PDF (mock)"""
    user = request.user
    
    # Generate mock PDF content (in production, use a PDF library)
    summary_data = f"""
    Peak Overwatch Analytics Summary
    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    User: {user.email}
    
    Account Summary:
    - Total Accounts: {len(user.mock_profiles)}
    - Subscription Tier: {user.subscription_tier}
    
    Connected Accounts:
    """
    
    for profile in user.mock_profiles:
        summary_data += f"- @{profile['username']} ({profile['niche']}): ${profile['profit']} profit, {profile['growth']}% growth, {profile['fyp_score']}% FYP\n"
    
    summary_data += f"""
    
    Settings:
    - Timezone: {user.settings['timezone']}
    - Currency: {user.settings['currency']}
    - FYP Thresholds: Good ({user.settings['fyp_threshold_good']}%), Warn ({user.settings['fyp_threshold_warn']}%), Critical ({user.settings['fyp_threshold_critical']}%)
    
    © 2026 Peak Overwatch. All rights reserved.
    """
    
    response = make_response(summary_data)
    response.headers['Content-Disposition'] = f'attachment; filename=peakoverwatch_summary_{datetime.now().strftime("%Y%m%d")}.txt'
    response.headers['Content-Type'] = 'text/plain'
    
    return response

# HTML Templates (simplified for brevity)
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

        * { margin: 0; padding: 0;