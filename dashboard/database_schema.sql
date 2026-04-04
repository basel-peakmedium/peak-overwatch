-- Peak Overwatch Database Schema
-- PostgreSQL database for user accounts, TikTok connections, and analytics data

-- ===== USERS =====
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- bcrypt hashed
    full_name VARCHAR(255),
    company VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    subscription_tier VARCHAR(50) DEFAULT 'free', -- free, pro, enterprise
    subscription_ends_at TIMESTAMP
);

-- ===== TIKTOK CONNECTIONS =====
CREATE TABLE tiktok_connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    tiktok_open_id VARCHAR(255) UNIQUE NOT NULL,
    tiktok_display_name VARCHAR(255),
    tiktok_username VARCHAR(255),
    tiktok_avatar_url TEXT,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    scopes TEXT[], -- Array of granted scopes
    is_active BOOLEAN DEFAULT TRUE,
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP
);

-- ===== USER SETTINGS =====
CREATE TABLE user_settings (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    timezone VARCHAR(50) DEFAULT 'America/New_York',
    currency VARCHAR(3) DEFAULT 'USD',
    fyp_threshold_good INTEGER DEFAULT 80,
    fyp_threshold_warn INTEGER DEFAULT 70,
    fyp_threshold_critical INTEGER DEFAULT 60,
    daily_email_reports BOOLEAN DEFAULT TRUE,
    weekly_summary_email BOOLEAN DEFAULT TRUE,
    alert_notifications BOOLEAN DEFAULT TRUE,
    alert_email BOOLEAN DEFAULT TRUE,
    alert_slack BOOLEAN DEFAULT FALSE,
    alert_telegram BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===== MOCK DATA PROFILES (for pre-TikTok approval) =====
CREATE TABLE mock_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    profile_name VARCHAR(255) NOT NULL,
    niche VARCHAR(100), -- Home & Lifestyle, Gadgets & Tech, etc.
    monthly_gmv_base INTEGER DEFAULT 50000,
    monthly_gmv_variance INTEGER DEFAULT 20000,
    commission_rate DECIMAL(5,2) DEFAULT 15.0,
    fyp_score_base INTEGER DEFAULT 85,
    fyp_score_variance INTEGER DEFAULT 10,
    growth_rate DECIMAL(5,2) DEFAULT 20.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===== ANALYTICS DATA (mock until TikTok API) =====
CREATE TABLE analytics_daily (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    tiktok_connection_id INTEGER REFERENCES tiktok_connections(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    gmv DECIMAL(12,2) DEFAULT 0,
    commission DECIMAL(12,2) DEFAULT 0,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    products_sold INTEGER DEFAULT 0,
    conversion_rate DECIMAL(5,2) DEFAULT 0,
    fyp_score INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, tiktok_connection_id, date)
);

-- ===== ALERTS =====
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    tiktok_connection_id INTEGER REFERENCES tiktok_connections(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL, -- fyp_drop, gmv_drop, commission_change, etc.
    alert_level VARCHAR(20) NOT NULL, -- info, warning, critical
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSONB, -- Additional alert data
    is_read BOOLEAN DEFAULT FALSE,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===== SESSIONS =====
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    user_agent TEXT,
    ip_address INET,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===== AUDIT LOG =====
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL, -- login, logout, connect_tiktok, etc.
    resource_type VARCHAR(50), -- user, tiktok_connection, etc.
    resource_id INTEGER,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===== INDEXES =====
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_tiktok_connections_user_id ON tiktok_connections(user_id);
CREATE INDEX idx_tiktok_connections_open_id ON tiktok_connections(tiktok_open_id);
CREATE INDEX idx_analytics_daily_user_date ON analytics_daily(user_id, date);
CREATE INDEX idx_analytics_daily_connection_date ON analytics_daily(tiktok_connection_id, date);
CREATE INDEX idx_alerts_user_unread ON alerts(user_id, is_read) WHERE NOT is_read;
CREATE INDEX idx_sessions_token ON sessions(session_token);
CREATE INDEX idx_sessions_expires ON sessions(expires_at) WHERE expires_at < CURRENT_TIMESTAMP;
CREATE INDEX idx_audit_log_user_created ON audit_log(user_id, created_at);

-- ===== FUNCTIONS =====
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ===== TRIGGERS =====
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_settings_updated_at BEFORE UPDATE ON user_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===== SAMPLE DATA =====
-- Insert a sample user for testing (password: "password123")
INSERT INTO users (email, password_hash, full_name, company, subscription_tier) 
VALUES ('demo@peakoverwatch.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Demo User', 'Peak Medium', 'pro');

-- Insert user settings for demo user
INSERT INTO user_settings (user_id) 
VALUES (1);

-- Insert mock profiles for demo
INSERT INTO mock_profiles (user_id, profile_name, niche, monthly_gmv_base, commission_rate, fyp_score_base, growth_rate) VALUES
(1, 'ourviralpicks', 'Home & Lifestyle', 120000, 15.0, 95, 24.7),
(1, 'homegadgetfinds', 'Gadgets & Tech', 85000, 12.5, 88, 18.2),
(1, 'beautytrends', 'Beauty & Skincare', 150000, 18.0, 92, 32.1),
(1, 'cartcravings30', 'Food & Kitchen', 45000, 10.0, 72, 8.3),
(1, 'fitnessessentials', 'Fitness & Wellness', 95000, 14.0, 89, 21.5);

-- Generate 30 days of mock analytics data
INSERT INTO analytics_daily (user_id, date, gmv, commission, views, likes, shares, comments, products_sold, conversion_rate, fyp_score)
SELECT 
    1 as user_id,
    CURRENT_DATE - (n || ' days')::INTERVAL as date,
    (3000 + n * 200 + (random() * 600 - 300))::DECIMAL(12,2) as gmv,
    ((3000 + n * 200 + (random() * 600 - 300)) * 0.15)::DECIMAL(12,2) as commission,
    (50000 + n * 1000 + (random() * 20000 - 10000))::INTEGER as views,
    (5000 + n * 200 + (random() * 2000 - 1000))::INTEGER as likes,
    (200 + n * 10 + (random() * 100 - 50))::INTEGER as shares,
    (100 + n * 5 + (random() * 50 - 25))::INTEGER as comments,
    (50 + n * 3 + (random() * 20 - 10))::INTEGER as products_sold,
    (0.15 + n * 0.002 + (random() * 0.02 - 0.01))::DECIMAL(5,2) as conversion_rate,
    (85 + n * 0.3 + (random() * 10 - 5))::INTEGER as fyp_score
FROM generate_series(0, 29) n;