"""
Database models for Peak Overwatch Dashboard
"""

from datetime import datetime, timedelta
import json
from typing import Optional, Dict, Any
import bcrypt
from jose import JWTError, jwt
from flask import current_app
import psycopg2
from psycopg2.extras import RealDictCursor
import os

class Database:
    """Database connection manager"""
    
    @staticmethod
    def get_connection():
        """Get database connection"""
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            port=os.environ.get('DB_PORT', '5432'),
            database=os.environ.get('DB_NAME', 'peakoverwatch'),
            user=os.environ.get('DB_USER', 'postgres'),
            password=os.environ.get('DB_PASSWORD', '')
        )
        return conn
    
    @staticmethod
    def execute_query(query, params=None, fetch_one=False, fetch_all=False):
        """Execute a database query"""
        conn = Database.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute(query, params or ())
            
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            else:
                result = cursor.rowcount
            
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

class User:
    """User model"""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.email = data.get('email')
        self.password_hash = data.get('password_hash')
        self.full_name = data.get('full_name')
        self.company = data.get('company')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
        self.last_login = data.get('last_login')
        self.is_active = data.get('is_active', True)
        self.subscription_tier = data.get('subscription_tier', 'free')
        self.subscription_ends_at = data.get('subscription_ends_at')
    
    @staticmethod
    def create(email: str, password: str, full_name: str = None, company: str = None) -> 'User':
        """Create a new user"""
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        query = """
            INSERT INTO users (email, password_hash, full_name, company)
            VALUES (%s, %s, %s, %s)
            RETURNING *
        """
        
        result = Database.execute_query(query, (email, password_hash, full_name, company), fetch_one=True)
        
        # Create user settings
        settings_query = "INSERT INTO user_settings (user_id) VALUES (%s)"
        Database.execute_query(settings_query, (result['id'],))
        
        return User(result)
    
    @staticmethod
    def get_by_id(user_id: int) -> Optional['User']:
        """Get user by ID"""
        query = "SELECT * FROM users WHERE id = %s AND is_active = TRUE"
        result = Database.execute_query(query, (user_id,), fetch_one=True)
        return User(result) if result else None
    
    @staticmethod
    def get_by_email(email: str) -> Optional['User']:
        """Get user by email"""
        query = "SELECT * FROM users WHERE email = %s AND is_active = TRUE"
        result = Database.execute_query(query, (email,), fetch_one=True)
        return User(result) if result else None
    
    def verify_password(self, password: str) -> bool:
        """Verify user password"""
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def update_last_login(self):
        """Update user's last login timestamp"""
        query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s"
        Database.execute_query(query, (self.id,))
    
    def get_settings(self) -> Dict[str, Any]:
        """Get user settings"""
        query = "SELECT * FROM user_settings WHERE user_id = %s"
        result = Database.execute_query(query, (self.id,), fetch_one=True)
        return dict(result) if result else {}
    
    def update_settings(self, settings: Dict[str, Any]):
        """Update user settings"""
        # Filter out None values
        settings = {k: v for k, v in settings.items() if v is not None}
        
        if not settings:
            return
        
        set_clause = ', '.join([f"{k} = %s" for k in settings.keys()])
        values = list(settings.values()) + [self.id]
        
        query = f"""
            UPDATE user_settings 
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """
        Database.execute_query(query, values)
    
    def get_mock_profiles(self) -> list:
        """Get user's mock TikTok profiles"""
        query = """
            SELECT * FROM mock_profiles 
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY profile_name
        """
        results = Database.execute_query(query, (self.id,), fetch_all=True)
        return [dict(r) for r in results] if results else []
    
    def get_daily_analytics(self, days: int = 30) -> list:
        """Get user's daily analytics data"""
        query = """
            SELECT date, SUM(gmv) as gmv, SUM(commission) as commission, 
                   AVG(fyp_score) as fyp_score
            FROM analytics_daily 
            WHERE user_id = %s AND date >= CURRENT_DATE - %s
            GROUP BY date
            ORDER BY date
        """
        results = Database.execute_query(query, (self.id, days), fetch_all=True)
        return [dict(r) for r in results] if results else []
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get user's account summary"""
        # Get total GMV and commission
        query = """
            SELECT 
                COALESCE(SUM(gmv), 0) as total_gmv,
                COALESCE(SUM(commission), 0) as total_commission,
                COUNT(DISTINCT tiktok_connection_id) as active_accounts
            FROM analytics_daily 
            WHERE user_id = %s AND date >= DATE_TRUNC('month', CURRENT_DATE)
        """
        result = Database.execute_query(query, (self.id,), fetch_one=True)
        
        # Get average FYP score
        fyp_query = """
            SELECT COALESCE(AVG(fyp_score), 0) as avg_fyp_score
            FROM analytics_daily 
            WHERE user_id = %s AND date >= CURRENT_DATE - 7
        """
        fyp_result = Database.execute_query(fyp_query, (self.id,), fetch_one=True)
        
        summary = {
            'total_gmv': float(result['total_gmv']) if result else 0,
            'total_commission': float(result['total_commission']) if result else 0,
            'active_accounts': result['active_accounts'] if result else 0,
            'avg_fyp_score': float(fyp_result['avg_fyp_score']) if fyp_result else 0
        }
        
        return summary

class Auth:
    """Authentication and authorization manager"""
    
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=Auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, Auth.SECRET_KEY, algorithm=Auth.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, Auth.SECRET_KEY, algorithms=[Auth.ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = User.get_by_email(email)
        if not user:
            return None
        if not user.verify_password(password):
            return None
        
        # Update last login
        user.update_last_login()
        
        return user
    
    @staticmethod
    def register_user(email: str, password: str, full_name: str = None, company: str = None) -> Optional[User]:
        """Register a new user"""
        # Check if user already exists
        existing_user = User.get_by_email(email)
        if existing_user:
            return None
        
        # Create new user
        user = User.create(email, password, full_name, company)
        
        # Create mock profiles for demo
        Auth._create_demo_mock_profiles(user.id)
        
        return user
    
    @staticmethod
    def _create_demo_mock_profiles(user_id: int):
        """Create demo mock profiles for new user"""
        profiles = [
            ('ourviralpicks', 'Home & Lifestyle', 120000, 15.0, 95, 24.7),
            ('homegadgetfinds', 'Gadgets & Tech', 85000, 12.5, 88, 18.2),
            ('beautytrends', 'Beauty & Skincare', 150000, 18.0, 92, 32.1),
            ('cartcravings30', 'Food & Kitchen', 45000, 10.0, 72, 8.3),
            ('fitnessessentials', 'Fitness & Wellness', 95000, 14.0, 89, 21.5)
        ]
        
        for profile in profiles:
            query = """
                INSERT INTO mock_profiles 
                (user_id, profile_name, niche, monthly_gmv_base, commission_rate, fyp_score_base, growth_rate)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            Database.execute_query(query, (user_id, *profile))
        
        # Generate 30 days of mock analytics data
        for i in range(30):
            date = datetime.now().date() - timedelta(days=i)
            gmv = 3000 + i * 200 + (i % 10 * 100)
            commission = gmv * 0.15
            fyp_score = 85 + i * 0.3 + (i % 5)
            
            query = """
                INSERT INTO analytics_daily 
                (user_id, date, gmv, commission, fyp_score)
                VALUES (%s, %s, %s, %s, %s)
            """
            Database.execute_query(query, (user_id, date, gmv, commission, fyp_score))

class SessionManager:
    """Session management"""
    
    @staticmethod
    def create_session(user_id: int, user_agent: str = None, ip_address: str = None) -> str:
        """Create a new session"""
        import secrets
        session_token = secrets.token_urlsafe(32)
        
        expires_at = datetime.now() + timedelta(days=7)
        
        query = """
            INSERT INTO sessions (user_id, session_token, user_agent, ip_address, expires_at)
            VALUES (%s, %s, %s, %s, %s)
        """
        Database.execute_query(query, (user_id, session_token, user_agent, ip_address, expires_at))
        
        return session_token
    
    @staticmethod
    def validate_session(session_token: str) -> Optional[User]:
        """Validate session token and return user"""
        query = """
            SELECT u.* FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token = %s 
            AND s.expires_at > CURRENT_TIMESTAMP
            AND u.is_active = TRUE
        """
        result = Database.execute_query(query, (session_token,), fetch_one=True)
        
        if result:
            return User(result)
        return None
    
    @staticmethod
    def delete_session(session_token: str):
        """Delete session"""
        query = "DELETE FROM sessions WHERE session_token = %s"
        Database.execute_query(query, (session_token,))
    
    @staticmethod
    def delete_user_sessions(user_id: int):
        """Delete all sessions for a user"""
        query = "DELETE FROM sessions WHERE user_id = %s"
        Database.execute_query(query, (user_id,))