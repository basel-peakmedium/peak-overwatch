#!/usr/bin/env python3
"""
Peak Overwatch Dashboard - Phase 5: Production Ready
Simplified version with production features, ready for testing
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

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Production configuration
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(32)),
    ENV=os.environ.get('FLASK_ENV', 'production'),
    DEBUG=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true',
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)

# WebSocket with production settings
socketio = SocketIO(
    app,
    cors_allowed_origins=os.environ.get('CORS_ALLOWED_ORIGINS', '*'),
    logger=os.environ.get('SOCKETIO_LOGGING', 'false').lower() == 'true',
    engineio_logger=os.environ.get('ENGINEIO_LOGGING', 'false').lower() == 'true',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e8  # 100MB
)

# In-memory storage with thread safety (production would use Redis/PostgreSQL)
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
        
        # Production settings with defaults
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
            'gmv_drop_threshold': 20,
            'commission_drop_threshold': 15
        }
        
        # Production profiles with more realistic data
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
                'last_commission': 780,
                'status': 'active',
                'last_updated': datetime.now()
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
                'last_commission': 570,
                'status': 'active',
                'last_updated': datetime.now()
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
                'last_commission': 930,
                'status': 'active',
                'last_updated': datetime.now()
            }
        ]
        
        # Analytics cache
        self._analytics_cache = None
        self._analytics_cache_time = None
    
    def verify_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def update_settings(self, new_settings):
        with user_lock:
            for key, value in new_settings.items():
                if key in self.settings:
                    if isinstance(value, str) and value.lower() in ['true', 'false']:
                        value = value.lower() == 'true'
                    self.settings[key] = value
            logger.info(f"User {self.email} updated settings")
    
    def add_alert(self, alert_type, title, message, level='info', data=None):
        """Add alert with production logging"""
        alert_id = secrets.token_urlsafe(8)
        alert = {
            'id': alert_id,
            'type': alert_type,
            'title': title,
            'message': message,
            'level': level,
            'data': data or {},
            'created_at': datetime.now().isoformat(),
            'is_read': False,
            'is_resolved': False
        }
        
        with user_lock:
            if self.id not in alerts:
                alerts[self.id] = []
            alerts[self.id].append(alert)
            
            # Production: Keep only last 100 alerts
            if len(alerts[self.id]) > 100:
                alerts[self.id] = alerts[self.id][-100:]
        
        # Production WebSocket delivery
        if self.socket_id:
            try:
                socketio.emit('new_alert', alert, room=self.socket_id)
                logger.debug(f"Alert sent via WebSocket to user {self.email}")
            except Exception as e:
                logger.error(f"Failed to send WebSocket alert: {e}")
        
        # Production logging
        logger.info(f"ALERT {level.upper()}: {title} - User: {self.email}")
        
        return alert
    
    def get_unread_alerts(self):
        return [a for a in alerts.get(self.id, []) if not a['is_read']]
    
    def mark_alert_read(self, alert_id):
        with user_lock:
            for alert in alerts.get(self.id, []):
                if alert['id'] == alert_id:
                    alert['is_read'] = True
                    logger.debug(f"Alert {alert_id} marked as read for user {self.email}")
                    return True
        return False
    
    def get_analytics(self, days=30):
        """Get analytics with caching for production performance"""
        cache_key = f"analytics_{self.id}_{days}"
        
        # Check cache (in production would use Redis)
        if self._analytics_cache and self._analytics_cache_time:
            cache_age = (datetime.now() - self._analytics_cache_time).total_seconds()
            if cache_age < 300:  # 5 minute cache
                return self._analytics_cache
        
        # Generate analytics
        analytics = []
        for i in range(days):
            date = datetime.now() - timedelta(days=days - i - 1)
            base_gmv = 3000 + i * 10 + random.randint(-200, 200)
            analytics.append({
                'date': date.strftime('%Y-%m-%d'),
                'gmv': base_gmv,
                'commission': int(base_gmv * 0.15),
                'fyp_score': random.randint(75, 98),
                'views': random.randint(50000, 150000),
                'likes': random.randint(5000, 20000),
                'shares': random.randint(200, 800),
                'products_sold': random.randint(40, 120)
            })
        
        # Update cache
        self._analytics_cache = analytics
        self._analytics_cache_time = datetime.now()
        
        return analytics

# Create demo user for production testing
demo_hash = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
users['demo@peakoverwatch.com'] = User(1, 'demo@peakoverwatch.com', demo_hash, 'Demo User', 'Peak Medium')

# Production monitoring service
class ProductionMonitor:
    def __init__(self):
        self.running = False
        self.thread = None
        self.check_interval = 60  # Check every minute
    
    def start(self):
        """Start production monitoring"""
        if self.running:
            return
        
        self.running = True
        self.thread = Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("Production monitoring service started")
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Production monitoring service stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop with production error handling"""
        while self.running:
            try:
                self._check_all_users()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(30)  # Backoff on error
    
    def _check_all_users(self):
        """Check all users with production logging"""
        with user_lock:
            user_count = len(users)
            if user_count == 0:
                return
            
            logger.debug(f"Monitoring {user_count} users")
            
            for user in users.values():
                try:
                    self._check_user_profiles(user)
                except Exception as e:
                    logger.error(f"Error monitoring user {user.email}: {e}")
    
    def _check_user_profiles(self, user):
        """Check user profiles with realistic simulation"""
        for profile in user.profiles:
            # Realistic FYP score simulation
            old_score = profile['last_fyp_score']
            
            # More realistic score changes
            trend = random.choice(['up', 'down', 'stable'])
            if trend == 'up':
                new_score = min(100, old_score + random.randint(1, 8))
            elif trend == 'down':
                new_score = max(50, old_score - random.randint(1, 12))
            else:
                new_score = old_score + random.randint(-3, 3)
                new_score = max(50, min(100, new_score))
            
            # Check thresholds
            if new_score < old_score:
                drop = old_score - new_score
                
                if new_score < user.settings['fyp_threshold_critical']:
                    user.add_alert(
                        'fyp_drop_critical',
                        f'🚨 Critical: @{profile["username"]} FYP Score',
                        f'FYP score dropped from {old_score}% to {new_score}% - Immediate attention needed!',
                        'critical',
                        {
                            'profile_id': profile['id'],
                            'username': profile['username'],
                            'old_score': old_score,
                            'new_score': new_score,
                            'drop': drop,
                            'threshold': user.settings['fyp_threshold_critical']
                        }
                    )
                elif new_score < user.settings['fyp_threshold_warn']:
                    user.add_alert(
                        'fyp_drop_warning',
                        f'⚠️ Warning: @{profile["username"]} FYP Score',
                        f'FYP score dropped from {old_score}% to {new_score}% - Monitor closely',
                        'warning',
                        {
                            'profile_id': profile['id'],
                            'username': profile['username'],
                            'old_score': old_score,
                            'new_score': new_score
                        }
                    )
                elif drop >= 8:
                    user.add_alert(
                        'fyp_drop_info',
                        f'📉 Notice: @{profile["username"]} FYP Score',
                        f'FYP score dropped from {old_score}% to {new_score}%',
                        'info',
                        {
                            'profile_id': profile['id'],
                            'username': profile['username'],
                            'old_score': old_score,
                            'new_score': new_score
                        }
                    )
            
            # Update profile
            profile['last_fyp_score'] = new_score
            profile['fyp_score'] = new_score
            profile['last_updated'] = datetime.now()
            
            # Simulate GMV changes
            old_gmv = profile['last_gmv']
            gmv_change = random.randint(-15, 20)  # -15% to +20%
            new_gmv = int(old_gmv * (1 + gmv_change / 100))
            
            if gmv_change < -user.settings['gmv_drop_threshold']:
                user.add_alert(
                    'gmv_drop',
                    f'📊 GMV Alert: @{profile["username"]}',
                    f'GMV dropped by {abs(gmv_change)}% (${old_gmv:,} → ${new_gmv:,})',
                    'warning' if gmv_change < -10 else 'info',
                    {
                        'profile_id': profile['id'],
                        'username': profile['username'],
                        'old_gmv': old_gmv,
                        'new_gmv': new_gmv,
                        'change_percent': gmv_change
                    }
                )
            
            profile['last_gmv'] = new_gmv
            profile['profit'] = int(profile['profit'] * (1 + random.randint(-5, 10) / 100))

# Start production monitoring
monitor = ProductionMonitor()
monitor.start()

# Production authentication decorator
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('session_token')
        if not token or token not in sessions:
            logger.warning(f"Unauthorized access attempt from {request.remote_addr}")
            return redirect('/login')
        
        user_id = sessions[token]['user_id']
        user = next((u for u in users.values() if u.id == user_id), None)
        if not user:
            logger.warning(f"Invalid session token from {request.remote_addr}")
            response = make_response(redirect('/login'))
            response.delete_cookie('session_token')
            return response
        
        request.user = user
        return f(*args, **kwargs)
    return decorated

# Production WebSocket handlers
@socketio.on('connect')
def handle_connect():
    """Production WebSocket connection handler"""
    token = request.args.get('token')
    if token and token in sessions:
        user_id = sessions[token]['user_id']
        user = next((u for u in users.values() if u.id == user_id), None)
        if user:
            user.socket_id = request.sid
            logger.info(f"User {user.email} connected via WebSocket")
            
            # Send initial data
            unread_alerts = user.get_unread_alerts()
            if unread_alerts:
                emit('initial_alerts', unread_alerts[:10])  # Limit for performance
            
            # Send connection confirmation
            emit('connection_established', {
                'timestamp': datetime.now().isoformat(),
                'user': user.email,
                'alert_count': len(unread_alerts)
            })

@socketio.on('disconnect')
def handle_disconnect():
    """Production WebSocket disconnection handler"""
    for user in users.values():
        if user.socket_id == request.sid:
            user.socket_id = None
            logger.info(f"User {user.email} disconnected from WebSocket")
            break

@socketio.on('mark_alert_read')
def handle_mark_alert_read(data):
    """Production alert read handler"""
    alert_id = data.get('alert_id')
    token = request.args.get('token')
    if token and token in sessions:
        user_id = sessions[token]['user_id']
        user = next((u for u in users.values() if u.id == user_id), None)
        if user and alert_id:
            if user.mark_alert_read(alert_id):
                emit('alert_read', {'alert_id': alert_id})
                logger.debug(f"Alert {alert_id} marked read via WebSocket")

# Production routes
@app.route('/')
def index():
    """Production home page with proper redirects"""
    token = request.cookies.get('session_token')
    if token and token in sessions:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login')
def login_page():
    """Production login page"""
    return render_template_string(PRODUCTION_LOGIN_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def api_login():
    """Production login API with security logging"""
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    user = users.get(email)
    if not user or not user.verify_password(password):
        logger.warning(f"Failed login attempt for email: {email}")
        return jsonify({
            'success': False, 
            'message': 'Invalid email or password',
            'code': 'AUTH_FAILED'
        }), 401
    
    # Create production session
    token = secrets.token_urlsafe(32)
    sessions[token] = {
        'user_id': user.id,
        'created_at': datetime.now().isoformat(),
        'expires': datetime.now() + timedelta(days=7),
        'user_agent': request.headers.get('User-Agent'),
        'ip_address': request.remote_addr
    }
    
    user.last_login = datetime.now()
    
    logger.info(f"User {email} logged in successfully")
    
    resp = jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'company': user.company,
            'subscription_tier': user.subscription_tier
        }
    })
    
    # Production cookie settings
    resp.set_cookie(
        'session_token',
        token,
        httponly=True,
        secure=app.config['SESSION_COOKIE_SECURE'],
        samesite=app.config['SESSION_COOKIE_SAMESITE'],
        max_age=7*24*60*60,
        path='/'
    )
    
    return resp

@app.route('/api/register', methods=['POST'])
def api_register():
    """Production registration API"""
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    company = data.get('company', '').strip()
    
    # Validation
    if not email or '@' not in email:
        return jsonify({
            'success': False,
            'message': 'Valid email required',
            'code': 'INVALID_EMAIL'
        }), 400
    
    if len(password) < 8:
        return jsonify({
            'success': False,
            'message': 'Password must be at least 8 characters',
            'code': 'PASSWORD_TOO_SHORT'
        }), 400
    
    if email in users:
        return jsonify({
            'success': False,
            'message': 'Email already registered',
            'code': 'EMAIL_EXISTS'
        }), 409
    
    # Create user
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user_id = max([u.id for u in users.values()] or [0]) + 1
    user = User(user_id, email, password_hash, name, company)
    users[email] = user
    
    # Create session
    token = secrets.token_urlsafe(32)
    sessions[token] = {
        'user_id': user.id,
        'created_at': datetime.now().isoformat(),
        'expires': datetime.now() + timedelta(days=7)
    }
    
    logger.info(f"New user registered: {email}")
    
    resp = jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'company': user.company
        }
    })
    
    resp.set_cookie(
        'session_token',
        token,
        httponly=True,
        secure=app.config['SESSION_COOKIE_SECURE'],
        samesite=app.config['SESSION_COOKIE_SAMESITE'],
        max_age=7*24*60*60,
        path='/'
    )
    
    return resp

@app.route('/logout')
def logout():
    """Production logout with proper session cleanup"""
    token = request.cookies.get('session_token')
    if token in sessions:
        user_id = sessions[token]['user_id']
        user = next((u for u in users.values() if u.id == user_id), None)
        if user:
            logger.info(f"User {user.email} logged out")
        del sessions[token]
    
    resp = make_response(redirect('/login'))
    resp.delete_cookie('session_token', path='/')
    return resp

@app.route('/dashboard')
@login_required
def dashboard():
    """Production dashboard with performance optimizations"""
    user = request.user
    
    # Get analytics with caching
    analytics = user.get_analytics(30)
    dates = [a['date'][5:] for a in analytics]
    gmv_data = [a['gmv'] for a in analytics]
    fyp_data = [a['fyp_score'] for a in analytics]
    
    # Calculate production metrics
    total_gmv = sum(a['gmv'] for a in analytics)
    total_commission = sum(a['commission'] for a in analytics)
    avg_fyp = sum(a['fyp_score'] for a in analytics[-7:]) / min(7, len(analytics[-7:]))
    
    # Get alerts
    unread_alerts = user.get_unread_alerts()
    
    # Production dashboard template
    return render_template_string(PRODUCTION_DASHBOARD_TEMPLATE,
        user=user,
        dates=dates,
        gmv_data=gmv_data,
        fyp_data=fyp_data,
        total_gmv=total_gmv,
        total_commission=total_commission,
        avg_fyp=avg_fyp,
        unread_alerts=unread_alerts,
        profiles=user.profiles,
        settings=user.settings
    )

@app.route('/api/alerts')
@login_required
def api_alerts():
    """Production alerts API with pagination"""
    user = request.user
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    
    with user_lock:
        user_alerts = alerts.get(user.id, [])
        paginated_alerts = user_alerts[offset:offset + limit]
        
        return jsonify({
            'success': True,
            'alerts': paginated_alerts,
            'total': len(user_alerts),
            'unread': len([a for a in user_alerts if not a['is_read']]),
            'has_more': offset + limit < len(user_alerts)
        })

@app.route('/api/alerts/<alert_id>/read', methods=['POST'])
@login_required
def api_mark_alert_read(alert_id):
    """Production alert read API"""
    user = request.user
    if user.mark_alert_read(alert_id):
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Alert not found'}), 404

@app.route('/api/settings', methods=['GET', 'PUT'])
@login_required
def api_settings():
    """Production settings API"""
    user = request.user
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'settings': user.settings
        })
    
    # PUT - Update settings
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    user.update_settings(data)
    return jsonify({'success': True, 'settings': user.settings})

@app.route('/health')
def health_check():
    """Production health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'services': {
            'web': 'up',
            'websocket': 'up',
            'monitoring': 'up' if monitor.running else 'down',
            'users': len(users),
            'sessions': len(sessions)
        }
    })

@app.route('/metrics')
def metrics():
    """Production metrics endpoint (for monitoring)"""
    with user_lock:
        return jsonify({
            'users_total': len(users),
            'sessions_active': len(sessions),
            'alerts_total': sum(len(alerts.get(uid, [])) for uid in alerts),
            'alerts_unread': sum(len([a for a in alerts.get(uid, []) if not a['is_read']]) for uid in alerts),
            'monitoring_running': monitor.running,
            'uptime': int((datetime.now() - app_start_time).total_seconds())
        })

# Production templates
PRODUCTION_LOGIN_TEMPLATE = '''
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
            --dark: #0a0a0a;
            --surface: #161616;
            --border: rgba(255,255,255,0.07);
            --text: #e8e8e8;
            --muted: #888;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: var(--dark); 
            color: var(--text);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
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
        .btn-secondary {
            width: 100%;
            padding: 1rem;
            background: transparent;
            color: var(--muted);
            border: 1px solid var(--border);
            border-radius: 10px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            margin-top: 1rem;
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
                <div class="logo-subtitle">Production Ready <span class="status-badge">v1.0</span></div>
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
            
            <button class="btn-secondary" onclick="showRegister()">Create Account</button>
            
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
        
        function showRegister() {
            alert('Registration feature coming soon! For now, use the demo account.');
        }
        
        // Auto-focus email field
        document.getElementById('email').focus();
    </script>
</body>
</html>
'''

PRODUCTION_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: var(--dark); 
            color: var(--text);
            overflow-x: hidden;
        }
        
        /* Sidebar */
        .sidebar {
            position: fixed;
            top: 0;
            left: 0;
            bottom: 0;
            width: 280px;
            background: var(--surface);
            border-right: 1px solid var(--border);
            padding: 2rem;
            display: flex;
            flex-direction: column;
        }
        .logo {
            font-size: 1.5rem;
            font-weight: 800;
            margin-bottom: 2.5rem;
        }
        .logo span:first-child { color: #fff; }
        .logo span:last-child { color: var(--red); margin-left: -4px; }
        .nav {
            flex: 1;
        }
        .nav-link {
            display: flex;
            align-items: center;
            padding: 0.875rem 1rem;
            color: var(--text);
            text-decoration: none;
            border-radius: 10px;
            margin-bottom: 0.5rem;
            transition: all 0.2s;
        }
        .nav-link:hover {
            background: rgba(255,255,255,0.05);
        }
        .nav-link.active {
            background: rgba(255,0,80,0.1);
            color: var(--cyan);
            font-weight: 600;
        }
        .nav-icon {
            margin-right: 0.75rem;
            font-size: 1.2rem;
        }
        .notification-badge {
            margin-left: auto;
            background: var(--red);
            color: white;
            border-radius: 50%;
            width: 22px;
            height: 22px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 600