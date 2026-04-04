#!/usr/bin/env python3
"""
Peak Overwatch Dashboard - Sidebar Navigation Design
Matches the screenshot from app.peakoverwatch.com
"""

from flask import Flask, render_template_string, session, redirect, url_for, request, jsonify
import os
import json
from datetime import datetime, timedelta
import random

app = Flask(__name__)

# Production settings
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['ENV'] = os.environ.get('FLASK_ENV', 'production')

# Mock data generation
def generate_mock_data():
    # Top metrics
    metrics = {
        'total_gmv': 186420,
        'commission_earned': 27963,
        'fyp_health_score': 94,
        'active_accounts': 12
    }
    
    # 30-day GMV data
    time_series = []
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(30):
        date = base_date + timedelta(days=i)
        # Create rising trend
        base_gmv = 4000 + (i * 200) + random.randint(-300, 300)
        time_series.append({
            'date': date.strftime('%Y-%m-%d'),
            'gmv': base_gmv,
            'commission': base_gmv * 0.15 + random.randint(-200, 200)
        })
    
    # Account data
    accounts = [
        {'username': 'ourviralpicks', 'niche': 'Home & Lifestyle', 'profit': 12412, 'growth': 24.7, 'fyp_score': 95},
        {'username': 'homegadgetfinds', 'niche': 'Gadgets & Tech', 'profit': 8923, 'growth': 18.2, 'fyp_score': 88},
        {'username': 'beautytrends', 'niche': 'Beauty & Skincare', 'profit': 15678, 'growth': 32.1, 'fyp_score': 92},
        {'username': 'cartcravings30', 'niche': 'Food & Kitchen', 'profit': 5842, 'growth': 8.3, 'fyp_score': 72},
        {'username': 'fitnessessentials', 'niche': 'Fitness & Wellness', 'profit': 10234, 'growth': 21.5, 'fyp_score': 89}
    ]
    
    return {
        'metrics': metrics,
        'time_series': time_series,
        'accounts': accounts
    }

@app.route('/')
@app.route('/dashboard')
def dashboard():
    """Main dashboard route with sidebar navigation"""
    data = generate_mock_data()
    return render_template_string(DASHBOARD_TEMPLATE, **data['metrics'], 
                                 time_series=json.dumps(data['time_series']),
                                 accounts=data['accounts'])

@app.route('/api/mock-data')
def mock_data():
    """API endpoint for mock data"""
    data = generate_mock_data()
    return jsonify(data)

# HTML Template with Sidebar Navigation
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Peak Overwatch • TikTok Affiliate Dashboard</title>
    
    <!-- Bootstrap 5 -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <style>
        :root {
            --primary: #000000;
            --secondary: #FF0050;
            --accent: #00F2EA;
            --dark-bg: #0f172a;
            --sidebar-bg: #1e293b;
            --card-bg: #1e293b;
            --border-color: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
        }
        
        body {
            background-color: var(--dark-bg);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            overflow-x: hidden;
        }
        
        /* Sidebar */
        .sidebar {
            position: fixed;
            top: 0;
            left: 0;
            bottom: 0;
            width: 250px;
            background-color: var(--sidebar-bg);
            border-right: 1px solid var(--border-color);
            padding: 20px 0;
            z-index: 100;
        }
        
        .sidebar-brand {
            padding: 0 20px 30px 20px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 20px;
        }
        
        .sidebar-brand h3 {
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
        }
        
        .sidebar-nav {
            padding: 0 20px;
        }
        
        .nav-item {
            margin-bottom: 8px;
        }
        
        .nav-link {
            color: var(--text-secondary);
            padding: 10px 15px;
            border-radius: 8px;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.2s;
        }
        
        .nav-link:hover {
            color: var(--text-primary);
            background-color: rgba(255, 255, 255, 0.05);
        }
        
        .nav-link.active {
            color: var(--text-primary);
            background-color: rgba(255, 0, 80, 0.1);
            border-left: 3px solid var(--secondary);
        }
        
        .nav-icon {
            width: 20px;
            text-align: center;
        }
        
        /* Main Content */
        .main-content {
            margin-left: 250px;
            padding: 30px;
            min-height: 100vh;
        }
        
        /* Header */
        .dashboard-header {
            margin-bottom: 30px;
        }
        
        .dashboard-header h1 {
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .dashboard-header p {
            color: var(--text-secondary);
            margin: 0;
        }
        
        /* Metrics Cards */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        
        @media (max-width: 1200px) {
            .metrics-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        @media (max-width: 768px) {
            .metrics-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .metric-card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
        }
        
        .metric-label {
            font-size: 0.9rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 5px;
        }
        
        .metric-change {
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .metric-change.positive {
            color: var(--success);
        }
        
        .metric-change.negative {
            color: var(--danger);
        }
        
        /* Chart Container */
        .chart-container {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
        }
        
        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .chart-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin: 0;
        }
        
        .chart-subtitle {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin: 0;
        }
        
        .chart-wrapper {
            height: 300px;
            position: relative;
        }
        
        /* Accounts List */
        .accounts-container {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 25px;
        }
        
        .accounts-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .accounts-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin: 0;
        }
        
        .account-row {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr 1fr;
            gap: 20px;
            padding: 15px 0;
            border-bottom: 1px solid var(--border-color);
            align-items: center;
        }
        
        .account-row:last-child {
            border-bottom: none;
        }
        
        .account-username {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .account-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--accent), var(--secondary));
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            color: white;
        }
        
        .account-niche {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }
        
        .account-metric {
            text-align: right;
        }
        
        .account-metric-value {
            font-weight: 600;
            font-size: 1.1rem;
        }
        
        .account-metric-label {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }
        
        .fyp-badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .fyp-good {
            background-color: rgba(16, 185, 129, 0.15);
            color: var(--success);
        }
        
        .fyp-warning {
            background-color: rgba(245, 158, 11, 0.15);
            color: var(--warning);
        }
        
        .fyp-critical {
            background-color: rgba(239, 68, 68, 0.15);
            color: var(--danger);
        }
        
        /* Footer */
        .dashboard-footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }
        
        .dashboard-footer a {
            color: var(--accent);
            text-decoration: none;
        }
        
        .dashboard-footer a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <!-- Sidebar Navigation -->
    <div class="sidebar">
        <div class="sidebar-brand">
            <h3>Peak Overwatch</h3>
        </div>
        
        <div class="sidebar-nav">
            <div class="nav-item">
                <a href="/dashboard" class="nav-link active">
                    <i class="bi bi-speedometer2 nav-icon"></i>
                    Overview
                </a>
            </div>
            
            <div class="nav-item">
                <a href="#" class="nav-link">
                    <i class="bi bi-graph-up nav-icon"></i>
                    GMV Tracker
                </a>
            </div>
            
            <div class="nav-item">
                <a href="#" class="nav-link">
                    <i class="bi bi-cash-stack nav-icon"></i>
                    Commissions
                </a>
            </div>
            
            <div class="nav-item">
                <a href="#" class="nav-link">
                    <i class="bi bi-heart-pulse nav-icon"></i>
                    FYP Health
                </a>
            </div>
            
            <div class="nav-item">
                <a href="#" class="nav-link">
                    <i class="bi bi-play-circle nav-icon"></i>
                    Videos
                </a>
            </div>
            
            <div class="nav-item">
                <a href="#" class="nav-link">
                    <i class="bi bi-box-seam nav-icon"></i>
                    Products
                </a>
            </div>
            
            <div class="nav-item">
                <a href="#" class="nav-link">
                    <i class="bi bi-bell nav-icon"></i>
                    Alerts
                </a>
            </div>
            
            <div class="nav-item">
                <a href="#" class="nav-link">
                    <i class="bi bi-gear nav-icon"></i>
                    Settings
                </a>
            </div>
        </div>
    </div>
    
    <!-- Main Content -->
    <div class="main-content">
        <!-- Header -->
        <div class="dashboard-header">
            <h1>Portfolio Overview</h1>
            <p>Monitor your TikTok affiliate performance across all accounts</p>
        </div>
        
        <!-- Metrics Grid -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Total GMV</div>
                <div class="metric-value">${{ "{:,}".format(total_gmv) }}</div>
                <div class="metric-change positive">
                    <i class="bi bi-arrow-up"></i>
                    +24.3%
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Commission Earned</div>
                <div class="metric-value">${{ "{:,}".format(commission_earned) }}</div>
                <div class="metric-change positive">
                    <i class="bi bi-arrow-up"></i>
                    +18.7%
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">FYP Health Score</div>
                <div class="metric-value">{{ fyp_health_score }}%</div>
                <div class="metric-change positive">
                    <i class="bi bi-arrow-up"></i>
                    Optimal
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Active Accounts</div>
                <div class="metric-value">{{ active_accounts }}</div>
                <div class="metric-change positive">
                    <i class="bi bi-arrow-up"></i>
                    +2 new
                </div>
            </div>
        </div>
        
        <!-- GMV Chart -->
        <div class="chart-container">
            <div class="chart-header">
                <div>
                    <h3 class="chart-title">Daily GMV — All Accounts</h3>
                    <p class="chart-subtitle">Last 30 days</p>
                </div>
                <div>
                    <select class="form-select form-select-sm" style="width: auto; background-color: var(--card-bg); color: var(--text-primary); border-color: var(--border-color);">
                        <option>Last 30 days</option>
                        <option>Last 7 days</option>
                        <option>Last 90 days</option>
                    </select>
                </div>
            </div>
            
            <div class="chart-wrapper">
                <canvas id="gmvChart"></canvas>
            </div>
        </div>
        
        <!-- Accounts List -->
        <div class="accounts-container">
            <div class="accounts-header">
                <h3 class="accounts-title">Account Performance</h3>
                <a href="#" class="btn btn-sm" style="background-color: var(--secondary); color: white; border: none;">
                    <i class="bi bi-plus"></i> Add Account
                </a>
            </div>
            
            <div class="account-row" style="border-bottom: 1px solid var(--border-color); padding-bottom: 10px; margin-bottom: 10px; font-weight: 600; color: var(--text-secondary);">
                <div>Account</div>
                <div class="text-end">Profit</div>
                <div class="text-end">Growth</div>
                <div class="text-end">FYP Score</div>
            </div>
            
            {% for account in accounts %}
            <div class="account-row">
                <div class="account-username">
                    <div class="account-avatar">{{ account.username[0].upper() }}</div>
                    <div>
                        <div>@{{ account.username }}</div>
                        <div class="account-niche">{{ account.niche }}</div>
                    </div>
                </div>
                
                <div class="account-metric">
                    <div class="account-metric-value">${{ "{:,}".format(account.profit) }}</div>
                    <div class="account-metric-label">Profit</div>
                </div>
                
                <div class="account-metric">
                    <div class="account-metric-value">{{ account.growth }}%</div>
                    <div class="account-metric-label">Growth</div>
                </div>
                
                <div class="account-metric">
                    <div class="account-metric-value">{{ account.fyp_score }}%</div>
                    <div class="account-metric-label">
                        {% if account.fyp_score >= 80 %}
                        <span class="fyp-badge fyp-good">Good</span>
                        {% elif account.fyp_score >= 70 %}
                        <span class="fyp-badge fyp-warning">Warning</span>
                        {% else %}
                        <span class="fyp-badge fyp-critical">Critical</span>
                        {% endif %}
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        
        <!-- Footer -->
        <div class="dashboard-footer">
            <p>
                Peak Overwatch v1.0 • 
                <a href="https://peakoverwatch.com/terms">Terms</a> • 
                <a href="https://peakoverwatch.com/privacy">Privacy</a> • 
                TikTok Developer Portal Application: Pending
            </p>
            <p style="margin-top: 5px; font-size: 0.8rem;">
                © 2026 Peak Medium / Revler Inc • Data updates every 24 hours • Mock data for demonstration
            </p>
        </div>
    </div>

    <script>
        // Initialize chart when page loads
        document.addEventListener('DOMContentLoaded', function() {
            // Parse time series data
            const timeSeries = {{ time_series | safe }};
            const dates = timeSeries.map(d => {
                const date = new Date(d.date);
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            });
            const gmvData = timeSeries.map(d => d.gmv);
            
            // Create GMV Chart
            const ctx = document.getElementById('gmvChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: 'Daily GMV',
                        data: gmvData,
                        borderColor: '#FF0050',
                        backgroundColor: 'rgba(255, 0, 80, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: '#FF0050',
                        pointBorderColor: '#FFFFFF',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            backgroundColor: 'rgba(30, 41, 59, 0.9)',
                            titleColor: '#f1f5f9',
                            bodyColor: '#f1f5f9',
                            borderColor: '#334155',
                            borderWidth: 1,
                            callbacks: {
                                label: function(context) {
                                    return `GMV: $${context.parsed.y.toLocaleString()}`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            },
                            ticks: {
                                color: '#94a3b8',
                                callback: function(value) {
                                    return '$' + value.toLocaleString();
                                }
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: '#94a3b8'
                            }
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'nearest'
                    }
                }
            });
            
            // Add click handlers to sidebar links
            document.querySelectorAll('.nav-link').forEach(link => {
                link.addEventListener('click', function(e) {
                    if (this.getAttribute('href') === '#') {
                        e.preventDefault();
                        // Show loading state
                        this.classList.add('disabled');
                        setTimeout(() => {
                            this.classList.remove('disabled');
                            alert('This feature is coming soon!');
                        }, 300);
                    }
                });
            });
        });
    </script>
</body>
</html>'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))  # Different port
    app.run(host='0.0.0.0', port=port, debug=(app.config['ENV'] == 'development'))