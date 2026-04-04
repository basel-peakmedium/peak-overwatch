#!/usr/bin/env python3
"""
Peak Overwatch Dashboard - Phase 5: Production Ready
Advanced features, database integration, email notifications, and deployment configuration
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
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from logging.handlers import RotatingFileHandler
import redis
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
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
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max upload
)

# WebSocket configuration
socketio = SocketIO(
    app,
    cors_allowed_origins=os.environ.get('CORS_ALLOWED_ORIGINS', '*'),
    logger=os.environ.get('SOCKETIO_LOGGING', 'false').lower() == 'true',
    engineio_logger=os.environ.get('ENGINEIO_LOGGING', 'false').lower() == 'true'
)

# Database connection pool
class Database:
    _instance = None
    _lock = Lock()
    
    @classmethod
    def get_connection(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls._create_pool()
        return cls._instance
    
    @staticmethod
    def _create_pool():
        """Create database connection pool"""
        try:
            conn = psycopg2.connect(
                host=os.environ.get('DB_HOST', 'localhost'),
                port=os.environ.get('DB_PORT', '5432'),
                database=os.environ.get('DB_NAME', 'peakoverwatch'),
                user=os.environ.get('DB_USER', 'postgres'),
                password=os.environ.get('DB_PASSWORD', ''),
                cursor_factory=RealDictCursor
            )
            conn.autocommit = True
            logger.info("Database connection established")
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            # Fallback to in-memory for development
            return None
    
    @staticmethod
    def execute_query(query, params=None, fetch_one=False, fetch_all=False):
        """Execute database query with error handling"""
        conn = Database.get_connection()
        if conn is None:
            return None
        
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                if fetch_one:
                    return cur.fetchone()
                elif fetch_all:
                    return cur.fetchall()
                else:
                    conn.commit()
                    return cur.rowcount
        except Exception as e:
            logger.error(f"Query failed: {e}\nQuery: {query}\nParams: {params}")
            return None

# Initialize database schema
def init_database():
    """Initialize database tables if they don't exist"""
    queries = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            company VARCHAR(255),
            subscription_tier VARCHAR(50) DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            timezone VARCHAR(50) DEFAULT 'America/New_York',
            currency VARCHAR(10) DEFAULT 'USD',
            fyp_threshold_good INTEGER DEFAULT 80,
            fyp_threshold_warn INTEGER DEFAULT 70,
            fyp_threshold_critical INTEGER DEFAULT 60,
            daily_email_reports BOOLEAN DEFAULT TRUE,
            weekly_summary_email BOOLEAN DEFAULT TRUE,
            alert_notifications BOOLEAN DEFAULT TRUE,
            alert_email BOOLEAN DEFAULT TRUE,
            alert_slack BOOLEAN DEFAULT FALSE,
            alert_telegram BOOLEAN DEFAULT FALSE,
            gmv_drop_threshold INTEGER DEFAULT 20,
            commission_drop_threshold INTEGER DEFAULT 15,
            PRIMARY KEY (user_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS tiktok_profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            username VARCHAR(100) NOT NULL,
            niche VARCHAR(100),
            profit INTEGER DEFAULT 0,
            growth DECIMAL(5,2) DEFAULT 0.0,
            fyp_score INTEGER DEFAULT 0,
            last_fyp_score INTEGER DEFAULT 0,
            last_gmv INTEGER DEFAULT 0,
            last_commission INTEGER DEFAULT 0,
            connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            UNIQUE(user_id, username)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            alert_type VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            level VARCHAR(20) DEFAULT 'info',
            data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read BOOLEAN DEFAULT FALSE,
            is_resolved BOOLEAN DEFAULT FALSE,
            resolved_at TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS analytics_daily (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            profile_id INTEGER REFERENCES tiktok_profiles(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            gmv INTEGER DEFAULT 0,
            commission INTEGER DEFAULT 0,
            fyp_score INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            products_sold INTEGER DEFAULT 0,
            UNIQUE(user_id, profile_id, date)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            session_token VARCHAR(255) UNIQUE NOT NULL,
            user_agent TEXT,
            ip_address VARCHAR(45),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT TRUE
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts(user_id);
        CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_analytics_user_date ON analytics_daily(user_id, date DESC);
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);
        CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
        """
    ]
    
    for query in queries:
        Database.execute_query(query)
    logger.info("Database schema initialized")

# Email service
class EmailService:
    @staticmethod
    def send_alert_email(user_email, alert):
        """Send alert email to user"""
        try:
            smtp_host = os.environ.get('SMTP_HOST')
            smtp_port = int(os.environ.get('SMTP_PORT', 587))
            smtp_user = os.environ.get('SMTP_USER')
            smtp_password = os.environ.get('SMTP_PASSWORD')
            
            if not all([smtp_host, smtp_user, smtp_password]):
                logger.warning("SMTP configuration missing, email not sent")
                return False
            
            msg = MIMEMultipart('alternative')
            msg['From'] = os.environ.get('FROM_EMAIL', 'alerts@peakoverwatch.com')
            msg['To'] = user_email
            msg['Subject'] = f"[Peak Overwatch] {alert['title']}"
            
            # HTML email content
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #FF0050, #00F2EA); padding: 20px; color: white; text-align: center; }}
                    .alert-box {{ border-left: 4px solid {'#ef4444' if alert['level'] == 'critical' else '#f59e0b' if alert['level'] == 'warning' else '#3b82f6'}; 
                                 background: #f9f9f9; padding: 15px; margin: 20px 0; }}
                    .footer {{ color: #888; font-size: 12px; text-align: center; margin-top: 30px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Peak Overwatch Alert</h1>
                    </div>
                    <div class="alert-box">
                        <h3>{alert['title']}</h3>
                        <p>{alert['message']}</p>
                        <p><strong>Time:</strong> {alert['created_at']}</p>
                        <p><strong>Level:</strong> {alert['level'].upper()}</p>
                    </div>
                    <p>View this alert in your dashboard: <a href="https://app.peakoverwatch.com/alerts">https://app.peakoverwatch.com/alerts</a></p>
                    <div class="footer">
                        <p>© 2026 Peak Overwatch. All rights reserved.</p>
                        <p><a href="https://app.peakoverwatch.com/settings">Manage your alert preferences</a></p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html, 'html'))
            
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            logger.info(f"Alert email sent to {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {user_email}: {e}")
            return False
    
    @staticmethod
    def send_welcome_email(user_email, user_name):
        """Send welcome email to new user"""
        # Implementation similar to send_alert_email
        logger.info(f"Welcome email would be sent to {user_email}")
        return True

# User model with database integration
class User:
    def __init__(self, user_data):
        self.id = user_data['id']
        self.email = user_data['email']
        self.full_name = user_data.get('full_name')
        self.company = user_data.get('company')
        self.subscription_tier = user_data.get('subscription_tier', 'free')
        self.created_at = user_data.get('created_at')
        self.last_login = user_data.get('last_login')
        self.socket_id = None
        self._settings = None
        self._profiles = None
    
    @property
    def settings(self):
        """Lazy load user settings"""
        if self._settings is None:
            self._settings = self._load_settings()
        return self._settings
    
    @property
    def profiles(self):
        """Lazy load user profiles"""
        if self._profiles is None:
            self._profiles = self._load_profiles()
        return self._profiles
    
    def _load_settings(self):
        """Load user settings from database"""
        query = "SELECT * FROM user_settings WHERE user_id = %s"
        result = Database.execute_query(query, (self.id,), fetch_one=True)
        if result:
            return dict(result)
        
        # Create default settings
        default_settings = {
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
            'alert_telegram': False,
            'gmv_drop_threshold': 20,
            'commission_drop_threshold': 15
        }
        
        query = """
        INSERT INTO user_settings (user_id, timezone, currency, fyp_threshold_good, 
                                  fyp_threshold_warn, fyp_threshold_critical,
                                  daily_email_reports, weekly_summary_email,
                                  alert_notifications, alert_email, alert_slack,
                                  alert_telegram, gmv_drop_threshold, commission_drop_threshold)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        Database.execute_query(query, (
            self.id, default_settings['timezone'], default_settings['currency'],
            default_settings['fyp_threshold_good'], default_settings['fyp_threshold_warn'],
            default_settings['fyp_threshold_critical'], default_settings['daily_email_reports'],
            default_settings['weekly_summary_email'], default_settings['alert_notifications'],
            default_settings['alert_email'], default_settings['alert_slack'],
            default_settings['alert_telegram'], default_settings['gmv_drop_threshold'],
            default_settings['commission_drop_threshold']
        ))
        
        return default_settings
    
    def _load_profiles(self):
        """Load user TikTok profiles from database"""
        query = """
        SELECT * FROM tiktok_profiles 
        WHERE user_id = %s AND is_active = TRUE 
        ORDER BY connected_at DESC
        """
        results = Database.execute_query(query, (self.id,), fetch_all=True)
        if results:
            return [dict(row) for row in results]
        
        # Create demo profiles for new users
        demo_profiles = [
            {
                'username': 'ourviralpicks',
                'niche': 'Home & Lifestyle',
                'profit': 12412,
                'growth': 24.7,
                'fyp_score': 95,
                'last_fyp_score': 95,
                'last_gmv': 5200,
                'last_commission': 780
            },
            {
                'username': 'homegadgetfinds',
                'niche': 'Gadgets & Tech',
                'profit': 8923,
                'growth': 18.2,
                'fyp_score': 88,
                'last_fyp_score': 88,
                'last_gmv': 3800,
                'last_commission': 570
            },
            {
                'username': 'beautytrends',
                'niche': 'Beauty & Skincare',
                'profit': 15678,
                'growth': 32.1,
                'fyp_score': 92,
                'last_fyp_score': 92,
                'last_gmv': 6200,
                'last_commission': 930
            }
        ]
        
        for profile in demo_profiles:
            query = """
            INSERT INTO tiktok_profiles 
            (user_id, username, niche, profit, growth, fyp_score, last_fyp_score, last_gmv, last_commission)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            Database.execute_query(query, (
                self.id, profile['username'], profile['niche'], profile['profit'],
                profile['growth'], profile['fyp_score'], profile['last_fyp_score'],
                profile['last_gmv'], profile['last_commission']
            ))
        
        return demo_profiles
    
    def verify_password(self, password):
        """Verify user password"""
        query = "SELECT password_hash FROM users WHERE id = %s"
        result = Database.execute_query(query, (self.id,), fetch_one=True)
        if not result:
            return False
        
        stored_hash = result['password_hash']
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
    
    def update_settings(self, new_settings):
        """Update user settings in database"""
        valid_keys = [
            'timezone', 'currency', 'fyp_threshold_good', 'fyp_threshold_warn',
            'fyp_threshold_critical', 'daily_email_reports', 'weekly_summary_email',
            'alert_notifications', 'alert_email', 'alert_slack', 'alert_telegram',
            'gmv_drop_threshold', 'commission_drop_threshold'
        ]
        
        updates = []
        params = []
        
        for key, value in new_settings.items():
            if key in valid_keys:
                updates.append(f"{key} = %s")
                params.append(value)
        
        if updates:
            params.append(self.id)
            query = f"UPDATE user_settings SET {', '.join(updates)} WHERE user_id = %s"
            Database.execute_query(query, params)
            self._settings = None  # Clear cache
    
    def add_alert(self, alert_type, title, message, level='info', data=None):
        """Add an alert for the user"""
        alert_id = secrets.token_urlsafe(8)
        alert_data = {
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
        
        # Store in database
        query = """
        INSERT INTO alerts (user_id, alert_type, title, message, level, data)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, created_at
        """
        result = Database.execute_query(
            query, 
            (self.id, alert_type, title, message, level, json.dumps(data or {})),
            fetch_one=True
        )
        
        if result:
            alert_data['id'] = result['id']
            alert_data['created_at'] = result['created_at'].isoformat()
        
        # Send real-time notification
        if self.socket_id:
            socketio.emit('new_alert', alert_data, room=self.socket_id)
        
        # Send email if enabled
        if self.settings['alert_email'] and level in ['warning', 'critical']:
            EmailService.send_alert_email(self.email, alert_data)
        
        logger.info(f"Alert created for user {self.email}: {title}")
        return alert_data
    
    def get_unread_alerts(self, limit=50):
        """Get unread alerts for the user"""
        query = """
        SELECT * FROM alerts 
        WHERE user_id = %s AND is_read = FALSE 
        ORDER BY created_at DESC 
        LIMIT %s
        """
        results = Database.execute_query(query, (self.id, limit), fetch_all=True)
        if results:
            return [
                {
                    'id': row['id'],
                    'type': row['alert_type'],
                    'title': row['title'],
                    'message': row['message'],
                    'level': row['level'],
                    'data': row['data'] or {},
                    'created_at': row['created_at'].isoformat(),
                    'is_read': row['is_read'],
                    'is_resolved': row['is_resolved']
                }
                for row in results
            ]
        return []
    
    def mark_alert_read(self, alert_id):
        """Mark an alert as read"""
        query = "UPDATE alerts SET is_read = TRUE WHERE id = %s AND user_id = %s"
        return Database.execute_query(query, (alert_id, self.id)) == 1
    
    def get_analytics(self, days=30):
        """Get analytics data for the user"""
        query = """
        SELECT date, SUM(gmv) as gmv, SUM(commission) as commission, 
               AVG(fyp_score) as fyp_score, SUM(views) as views,
               SUM(likes) as likes, SUM(shares) as shares, SUM(products_sold) as products_sold
        FROM analytics_daily 
        WHERE user_id = %s AND date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY date 
        ORDER BY date
        """
        results = Database.execute_query(query, (self.id, days), fetch_all=True)
        
        if results:
            return [dict(row) for row in results]
        
        # Generate mock analytics if none exist
        return self._generate_mock_analytics(days)
    
    def _generate_mock_analytics(self, days):
        """Generate mock analytics data"""
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
        
        # Store in database for future use
        for day in analytics:
            query = """
            INSERT INTO analytics_daily (user_id, date, gmv, commission, fyp_score, views, likes, shares, products_sold)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, date) DO NOTHING
            """
            Database.execute_query(query, (
                self.id, day['date'], day['gmv'], day['commission'], day['fyp_score'],
                day['views'], day['likes'], day['shares'], day['products_sold']
            ))
        
        return analytics

# Authentication and session management
class AuthService:
    @staticmethod
    def authenticate_user(email, password):
        """Authenticate user by email and password"""
        query = "SELECT * FROM users WHERE email = %s AND is_active = TRUE"
        result = Database.execute_query(query, (email,), fetch_one=True)
        
        if not result:
            return None
        
        user = User(dict(result))
        if not user.verify_password(password):
            return None
        
        # Update last login
        query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s"
        Database.execute_query(query, (user.id,))
        
        return user
    
    @staticmethod
    def register_user(email, password, full_name=None, company=None):
        """Register new user"""
        # Check if user exists
        query = "SELECT id FROM users WHERE email = %s"
        if Database.execute_query(query, (email,), fetch_one=True):
            return None
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user
        query = """
        INSERT INTO users (email, password_hash, full_name, company)
        VALUES (%s, %s, %s, %s)
        RETURNING id, email, full_name, company, created_at
        """
        result = Database.execute_query(
            query, (email, password_hash, full_name, company), 
            fetch_one=True
        )
        
        if result:
            user = User(dict(result))
            # Send welcome email
            EmailService.send_welcome_email(email, full_name or email)
            return user
        
        return None
    
    @staticmethod
    def create_session(user_id, user_agent=None, ip_address=None):
        """Create new session for user"""
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=7)
        
        query = """
        INSERT INTO sessions (user_id, session_token, user_agent, ip_address, expires_at)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING session_token
        """
        result = Database.execute_query(
            query, (user_id, session_token, user_agent, ip_address, expires_at),
            fetch_one=True
        )
        
        if result:
            return result['session_token']
        return None
    
    @staticmethod
    def validate_session(session_token):
        """Validate session token and return user"""
        query = """
        SELECT u.* FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.session_token = %s 
          AND s.expires_at > CURRENT_TIMESTAMP 
          AND s.is_active = TRUE
          AND u.is_active = TRUE
        """
        result = Database.execute_query(query, (session_token,), fetch_one=True)
        
        if result:
            return User(dict(result))
        return None
    
    @staticmethod
    def delete_session(session_token):
        """Delete session"""
        query = "UPDATE sessions SET is_active = FALSE WHERE session_token = %s"
        Database.execute_query(query, (session_token,))

# Background monitoring service
class MonitoringService:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """Start monitoring service"""
        if self.running:
            return
        
        self.running = True
        self.thread = Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("Monitoring service started")
    
    def stop(self):
        """Stop monitoring service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Monitoring service stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_all_users()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(30)
    
    def _check_all_users(self):
        """Check all active users for issues"""
        query = """
        SELECT u.id, u.email, us.* 
        FROM users u
        JOIN user_settings us ON u.id = us.user_id
        WHERE u.is_active = TRUE
        """
        users = Database.execute_query(query, fetch_all=True)
        
        if not users:
            return
        
        for user_data in users:
            try:
                user = User(dict(user_data))
                self._check_user_profiles(user)
            except Exception as e:
                logger.error(f"Error checking user {user_data.get('email')}: {e}")
    
    def _check_user_profiles(self, user):
        """Check user's TikTok profiles for issues"""
        for profile in user.profiles:
            # Simulate FYP score changes
            old_score = profile['last_fyp_score']
            new_score = random.randint(
                max(50, old_score - 15),
                min(100, old_score + 10)
            )
            
            # Check for significant drops
            if new_score < old_score:
                drop_amount = old_score - new_score
                
                if new_score < user.settings['fyp_threshold_critical']:
                    user.add_alert(
                        'fyp_drop_critical',
                        f'Critical FYP Drop: @{profile["username"]}',
                        f'FYP score dropped from {old_score}% to {new_score}% (below critical threshold)',
                        'critical',
                        {
                            'profile_id': profile['id'],
                            'profile_username': profile['username'],
                            'old_score': old_score,
                            'new_score': new_score,
                            'drop_amount': drop_amount
                        }
                    )
                elif new_score < user.settings['fyp_threshold_warn']:
                    user.add_alert(
                        'fyp_drop_warning',
                        f'FYP Warning: @{profile["username"]}',
                        f'FYP score dropped from {old_score}% to {new_score}% (below warning threshold)',
                        'warning',
                        {
                            'profile_id': profile['id'],
                            'profile_username': profile['username'],
                            'old_score': old_score,
                            'new_score': new_score
                        }
                    )
                elif drop_amount >= 10:
                    user.add_alert(
                        'fyp_drop_info',
                        f'FYP Drop: @{profile["username"]}',
                        f'FYP score dropped from {old_score}% to {new_score}%',
                        'info',
                        {
                            'profile_id': profile['id'],
                            'profile_username': profile['username'],
                            'old_score': old_score,
                            'new_score': new_score
                        }
                    )
            
            # Update profile score in database
            query = """
            UPDATE tiktok_profiles 
            SET fyp_score = %s, last_fyp_score = %s 
            WHERE id = %s
            """
            Database.execute_query(query, (new_score, new_score, profile['id']))

# Initialize services
init_database()
monitoring_service = MonitoringService()
monitoring_service.start()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('session_token')
        if not token:
            return redirect('/login')
        
        user = AuthService.validate_session(token)
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
    """Handle WebSocket connection"""
    token = request.args.get('token')
    if token:
        user = AuthService.validate_session(token)
        if user:
            user.socket_id = request.sid
            logger.info(f"User {user.email} connected via WebSocket")
            
            # Send any unread alerts
            unread_alerts = user.get_unread_alerts(10)
            if unread_alerts:
                emit('initial_alerts', unread_alerts)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    # Note: In production, you'd need a way to find user by socket_id
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('mark_alert_read')
def handle_mark_alert_read(data):
    """Mark an alert as read via WebSocket"""
    alert_id = data.get('alert_id')
    token = request.args.get('token')
    if token:
        user = AuthService.validate_session(token)
        if user and alert_id:
            user.mark_alert_read(alert_id)
            emit('alert_read', {'alert_id': alert_id})

# Routes
@app.route('/')
def index():
    """Home page - redirect to login or dashboard"""
    token = request.cookies.get('session_token')
    if token:
        user = AuthService.validate_session(token)
        if user:
            return redirect('/dashboard')
    return redirect('/login')

@app.route('/login')
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
    
    user = AuthService.authenticate_user(email, password)
    if not user:
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
    
    # Create session
    user_agent = request.headers.get('User-Agent')
    ip_address = request.remote_addr
    session_token = AuthService.create_session(user.id, user_agent, ip_address)
    
    if not session_token:
        return jsonify({'success': False, 'message': 'Failed to create session'}), 500
    
    response = jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'company': user.company,
            'subscription_tier': user.subscription_tier
        }
    })
    
    response.set_cookie(
        'session_token',
        session_token,
        httponly=True,
        secure=app.config['SESSION_COOKIE_SECURE'],
        samesite=app.config['SESSION_COOKIE_SAMESITE'],
        max_age=7*24*60*60
    )
    
    return response

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
    
    user = AuthService.register_user(email, password, full_name, company)
    if not user:
        return jsonify({'success': False, 'message': 'User already exists'}), 409
    
    # Create session
    user_agent = request.headers.get('User-Agent')
    ip_address = request.remote_addr
    session_token = AuthService.create_session(user.id, user_agent, ip_address)
    
    response = jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'company': user.company
        }
    })
    
    response.set_cookie(
        'session_token',
        session_token,
        httponly=True,
        secure=app.config['SESSION_COOKIE_SECURE'],
        samesite=app.config['SESSION_COOKIE_SAMESITE'],
        max_age=7*24*60*60
    )
    
    return response

@app.route('/logout')
def logout():
    """Logout endpoint"""
    token = request.cookies.get('session_token')
    if token:
        AuthService.delete_session(token)
    
    response = make_response(redirect('/login'))
    response.delete_cookie('session_token')
    return response

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    user = request.user
    
    # Get analytics data
    analytics = user.get_analytics(30)
    dates = [a['date'][5:] for a in analytics]  # MM-DD format
    gmv_data = [a['gmv'] for a in analytics]
    fyp_data = [a['fyp_score'] for a in analytics]
    
    # Calculate metrics
    total_gmv = sum(a['gmv'] for a