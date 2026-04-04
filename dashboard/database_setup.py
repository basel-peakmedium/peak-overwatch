#!/usr/bin/env python3
"""
Database setup for Peak Overwatch Dashboard
Creates PostgreSQL database, tables, and initial data
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import bcrypt

# Load environment variables
load_dotenv()

def get_db_config():
    """Get database configuration from environment variables"""
    return {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': os.environ.get('DB_PORT', '5432'),
        'database': os.environ.get('DB_NAME', 'peakoverwatch'),
        'user': os.environ.get('DB_USER', 'postgres'),
        'password': os.environ.get('DB_PASSWORD', '')
    }

def create_database():
    """Create database if it doesn't exist"""
    config = get_db_config()
    
    # Connect to default postgres database to create our database
    conn = psycopg2.connect(
        host=config['host'],
        port=config['port'],
        user=config['user'],
        password=config['password'],
        database='postgres'
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Check if database exists
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (config['database'],))
    exists = cursor.fetchone()
    
    if not exists:
        print(f"Creating database: {config['database']}")
        cursor.execute(f"CREATE DATABASE {config['database']}")
        print("Database created successfully")
    else:
        print(f"Database {config['database']} already exists")
    
    cursor.close()
    conn.close()

def create_tables():
    """Create all tables from schema"""
    config = get_db_config()
    
    conn = psycopg2.connect(**config)
    cursor = conn.cursor()
    
    # Read schema SQL
    with open('database_schema.sql', 'r') as f:
        schema_sql = f.read()
    
    # Split into individual statements
    statements = schema_sql.split(';')
    
    for statement in statements:
        statement = statement.strip()
        if statement:
            try:
                cursor.execute(statement)
            except Exception as e:
                print(f"Error executing statement: {e}")
                print(f"Statement: {statement[:100]}...")
    
    conn.commit()
    print("Tables created successfully")
    
    cursor.close()
    conn.close()

def create_admin_user():
    """Create an admin user for testing"""
    config = get_db_config()
    
    conn = psycopg2.connect(**config)
    cursor = conn.cursor()
    
    # Hash password
    password = "admin123"
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Check if admin exists
    cursor.execute("SELECT id FROM users WHERE email = %s", ('admin@peakoverwatch.com',))
    if cursor.fetchone():
        print("Admin user already exists")
    else:
        # Insert admin user
        cursor.execute("""
            INSERT INTO users (email, password_hash, full_name, company, subscription_tier)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, ('admin@peakoverwatch.com', hashed_password, 'Admin User', 'Peak Medium', 'enterprise'))
        
        user_id = cursor.fetchone()[0]
        
        # Insert user settings
        cursor.execute("""
            INSERT INTO user_settings (user_id)
            VALUES (%s)
        """, (user_id,))
        
        conn.commit()
        print(f"Admin user created with ID: {user_id}")
        print(f"Email: admin@peakoverwatch.com")
        print(f"Password: {password}")
    
    cursor.close()
    conn.close()

def test_connection():
    """Test database connection"""
    config = get_db_config()
    
    try:
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"Connected to PostgreSQL: {version[0]}")
        
        # List tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        print(f"Tables in database: {[t[0] for t in tables]}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

def main():
    """Main setup function"""
    print("=== Peak Overwatch Database Setup ===")
    
    # Step 1: Create database
    print("\n1. Creating database...")
    create_database()
    
    # Step 2: Create tables
    print("\n2. Creating tables...")
    create_tables()
    
    # Step 3: Create admin user
    print("\n3. Creating admin user...")
    create_admin_user()
    
    # Step 4: Test connection
    print("\n4. Testing connection...")
    if test_connection():
        print("\n✅ Database setup completed successfully!")
        print("\nNext steps:")
        print("1. Update your .env file with database credentials")
        print("2. Install PostgreSQL client: pip install psycopg2-binary")
        print("3. Run the Flask app with database support")
    else:
        print("\n❌ Database setup failed!")

if __name__ == '__main__':
    main()