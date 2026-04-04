#!/usr/bin/env python3
"""
Peak Overwatch Dashboard - Redesigned to match peakoverwatch.com aesthetic
For deployment to app.peakoverwatch.com
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
def generate_mock_accounts(count=5):
    accounts = []
    usernames = ['ourviralpicks', 'homegadgetfinds', 'beautytrends', 'cartcravings30', 'fitnessessentials']
    niches = ['Home & Lifestyle', 'Gadgets & Tech', 'Beauty & Skincare', 'Food & Kitchen', 'Fitness & Wellness']
    
    for i in range(min(count, len(usernames))):
        fyp_score = random.randint(65, 95)
        status = "Good" if fyp_score >= 80 else "Warn" if fyp_score >= 70 else "Critical"
        
        accounts.append({
            'username': usernames[i],
            'niche': niches[i],
            'fyp_score': fyp_score,
            'status': status,
            'profit': random.randint(500, 2500),
            'growth': random.uniform(5, 25),
            'gmv': random.randint(5000, 15000),
            'products_sold': random.randint(200, 800),
            'conversion': random.uniform(0.1, 0.3)
        })
    
    return accounts

def generate_time_series_data(days=30):
    data = []
    base_date = datetime.now() - timedelta(days=days)
    
    for i in range(days):
        date = base_date + timedelta(days=i)
        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'gmv': random.randint(800, 2500),
            'profit': random.randint(100, 500),
            'fyp_score': random.randint(70, 95)
        })
    
    return data

@app.route('/')
@app.route('/dashboard')
def dashboard():
    """Main dashboard route with redesigned UI"""
    accounts = generate_mock_accounts(5)
    time_series = generate_time_series_data(30)
    
    # Calculate totals
    total_profit = sum(acc['profit'] for acc in accounts)
    total_gmv = sum(acc['gmv'] for acc in accounts)
    avg_fyp = sum(acc['fyp_score'] for acc in accounts) / len(accounts)
    accounts_needing_attention = len([acc for acc in accounts if acc['status'] in ['Warn', 'Critical']])
    
    return render_template_string(DASHBOARD_TEMPLATE, 
                                 accounts=accounts,
                                 time_series=json.dumps(time_series),
                                 total_profit=total_profit,
                                 total_gmv=total_gmv,
                                 avg_fyp=avg_fyp,
                                 accounts_needing_attention=accounts_needing_attention,
                                 total_accounts=len(accounts))

@app.route('/api/mock-data')
def mock_data():
    """API endpoint for mock data (for charts)"""
    accounts = generate_mock_accounts(5)
    time_series = generate_time_series_data(30)
    
    return jsonify({
        'accounts': accounts,
        'time_series': time_series,
        'summary': {
            'total_profit': sum(acc['profit'] for acc in accounts),
            'total_gmv': sum(acc['gmv'] for acc in accounts),
            'avg_fyp': sum(acc['fyp_score'] for acc in accounts) / len(accounts),
            'accounts_needing_attention': len([acc for acc in accounts if acc['status'] in ['Warn', 'Critical']])
        }
    })

@app.route('/login')
def login():
    """Login page (mock for now)"""
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def api_login():
    """Mock login endpoint"""
    data = request.json
    # In production, this would validate credentials
    return jsonify({'success': True, 'message': 'Login successful (mock)'})

# HTML Templates
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Peak Overwatch — TikTok Affiliate Dashboard</title>
    <meta name="description" content="Strategic oversight platform for TikTok affiliate managers. Monitor FYP health, track GMV, and optimize performance across every account — all in one dashboard.">

    <!-- GSAP -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>

    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        /* ===== RESET & TOKENS ===== */
        *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

        :root {
            --red: #FF0050;
            --cyan: #00F2EA;
            --black: #000000;
            --dark: #0a0a0a;
            --dark2: #111111;
            --dark3: #1a1a1a;
            --dark4: #222222;
            --surface: #161616;
            --border: rgba(255,255,255,0.07);
            --text: #e8e8e8;
            --muted: #888888;
            --font: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
        }

        html {
            scroll-behavior: smooth;
            overflow-x: hidden;
        }

        body {
            font-family: var(--font);
            background: var(--dark);
            color: var(--text);
            line-height: 1.6;
            overflow-x: hidden;
            width: 100%;
            max-width: 100vw;
            padding: 0;
            margin: 0;
        }

        ::selection { background: var(--red); color: #fff; }

        /* ===== SCROLLBAR ===== */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: var(--dark); }
        ::-webkit-scrollbar-thumb { background: var(--red); border-radius: 3px; }

        /* ===== NAV ===== */
        nav {
            position: fixed;
            top: 0; left: 0; right: 0;
            z-index: 100;
            padding: 1rem 0;
            background: rgba(0,0,0,0.85);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border);
        }

        .nav-inner {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .logo {
            font-size: 1.25rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            text-decoration: none;
            color: #fff;
        }
        .logo span { color: var(--red); }

        .nav-links {
            display: flex;
            gap: 2rem;
            list-style: none;
        }

        .nav-links a {
            color: var(--text);
            text-decoration: none;
            font-weight: 500;
            font-size: 0.95rem;
            transition: color 0.2s;
        }

        .nav-links a:hover { color: var(--cyan); }

        .nav-actions {
            display: flex;
            gap: 1rem;
            align-items: center;
        }

        .btn {
            padding: 0.6rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            text-decoration: none;
            transition: all 0.2s;
            border: none;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--red), #ff3366);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(255, 0, 80, 0.3);
        }

        .btn-outline {
            background: transparent;
            color: var(--text);
            border: 1px solid var(--border);
        }

        .btn-outline:hover {
            background: rgba(255,255,255,0.05);
            border-color: var(--cyan);
        }

        /* ===== MAIN LAYOUT ===== */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 100px 32px 60px;
        }

        .dashboard-header {
            margin-bottom: 3rem;
        }

        .dashboard-header h1 {
            font-size: 2.5rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--cyan), var(--red));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .dashboard-header p {
            font-size: 1.1rem;
            color: var(--muted);
            max-width: 600px;
        }

        /* ===== GRID SYSTEM ===== */
        .grid {
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 24px;
        }

        .col-3 { grid-column: span 3; }
        .col-4 { grid-column: span 4; }
        .col-6 { grid-column: span 6; }
        .col-8 { grid-column: span 8; }
        .col-12 { grid-column: span 12; }

        @media (max-width: 1200px) {
            .col-3 { grid-column: span 6; }
            .col-4 { grid-column: span 6; }
            .col-6 { grid-column: span 12; }
            .col-8 { grid-column: span 12; }
        }

        @media (max-width: 768px) {
            .col-3, .col-4, .col-6, .col-8 { grid-column: span 12; }
        }

        /* ===== CARDS ===== */
        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            transition: all 0.3s;
        }

        .card:hover {
            border-color: var(--cyan);
            transform: translateY(-4px);
            box-shadow: 0 12px 32px rgba(0, 242, 234, 0.1);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }

        .card-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text);
        }

        .card-subtitle {
            font-size: 0.9rem;
            color: var(--muted);
            margin-top: 0.25rem;
        }

        /* ===== METRIC CARDS ===== */
        .metric-card {
            text-align: center;
            padding: 2rem 1.5rem;
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--cyan), var(--red));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            line-height: 1;
            margin-bottom: 0.5rem;
        }

        .metric-label {
            font-size: 0.9rem;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .metric-change {
            font-size: 0.85rem;
            margin-top: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.25rem;
        }

        .metric-change.positive { color: #10b981; }
        .metric-change.negative { color: #ef4444; }

        /* ===== FYP HEALTH CARDS ===== */
        .fyp-card {
            padding: 1.5rem;
        }

        .fyp-status {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
        }

        .status-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }

        .status-good { background: rgba(16, 185, 129, 0.15); color: #10b981; }
        .status-warn { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
        .status-critical { background: rgba(239, 68, 68, 0.15); color: #ef4444; }

        .fyp-score {
            font-size: 1.5rem;
            font-weight: 700;
        }

        .fyp-progress {
            height: 6px;
            background: var(--dark3);
            border-radius: 3px;
            margin-top: 0.5rem;
            overflow: hidden;
        }

        .fyp-progress-bar {
            height: 100%;
            border-radius: 3px;
            transition: width 0.5s ease;
        }

        .progress-good { background: linear-gradient(90deg, #10b981, #34d399); }
        .progress-warn { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
        .progress-critical { background: linear-gradient(90deg, #ef4444, #f87171); }

        /* ===== CHARTS ===== */
        .chart-container {
            height: 300px;
            margin-top: 1rem;
        }

        /* ===== ACCOUNT LIST ===== */
        .account-list {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .account-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem;
            background: var(--dark2);
            border-radius: 12px;
            border: 1px solid var(--border);
            transition: all 0.2s;
        }

        .account-item:hover {
            background: var(--dark3);
            border-color: var(--cyan);
        }

        .account-info {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .account-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--cyan), var(--red));
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            color: white;
        }

        .account-details h4 {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }

        .account-details p {
            font-size: 0.85rem;
            color: var(--muted);
        }

        .account-metrics {
            display: flex;
            gap: 1.5rem;
            align-items: center;
        }

        .account-metric {
            text-align: right;
        }

        .account-metric .value {
            font-size: 1.1rem;
            font-weight: 600;
        }

        .account-metric .label {
            font-size: 0.8rem;
            color: var(--muted);
        }

        /* ===== FOOTER ===== */
        footer {
            margin-top: 4rem;
            padding-top: 2rem;
            border-top: 1px solid var(--border);
            text-align: center;
            color: var(--muted);
            font-size: 0.9rem;
        }

        footer a {
            color: var(--cyan);
            text-decoration: none;
        }

        footer a:hover { text-decoration: underline; }

        /* ===== ANIMATIONS ===== */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .fade-in {
            animation: fadeIn 0.6s ease forwards;
        }

        .delay-1 { animation-delay: 0.1s; }
        .delay-2 { animation-delay: 0.2s; }
        .delay-3 { animation-delay: 0.3s; }
        .delay-4 { animation-delay: 0.4s; }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav>
        <div class="nav-inner">
            <a href="/" class="logo">Peak<span>Overwatch</span></a>
            
            <ul class="nav-links">
                <li><a href="/dashboard">Dashboard</a></li>
                <li><a href="#">Analytics</a></li>
                <li><a href="#">Alerts</a></li>
                <li><a href="#">Settings</a></li>
            </ul>
            
            <div class="nav-actions">
                <a href="/login" class="btn btn-outline">Sign In</a>
                <a href="#" class="btn btn-primary">Connect TikTok</a>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="container">
        <!-- Dashboard Header -->
        <div class="dashboard-header fade-in">
            <h1>Affiliate Command Center</h1>
            <p>Real-time monitoring of your TikTok Shop empire. Track FYP health, GMV, and optimize performance across all accounts.</p>
        </div>

        <!-- Metrics Grid -->
        <div class="grid">
            <!-- Total Profit -->
            <div class="col-3 fade-in delay-1">
                <div class="card metric-card">
                    <div class="metric-value">${{ total_profit | int }}</div>
                    <div class="metric-label">Monthly Profit</div>
                    <div class="metric-change positive">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="18 15 12 9 6 15"></polyline>
                        </svg>
                        18.4% growth
                    </div>
                </div>
            </div>

            <!-- Total GMV -->
            <div class="col-3 fade-in delay-2">
                <div class="card metric-card">
                    <div class="metric-value">${{ total_gmv | int }}K</div>
                    <div class="metric-label">Total GMV</div>
                    <div class="metric-change positive">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="18 15 12 9 6 15"></polyline>
                        </svg>
                        24.3% growth
                    </div>
                </div>
            </div>

            <!-- FYP Health -->
            <div class="col-3 fade-in delay-3">
                <div class="card metric-card">
                    <div class="metric-value">{{ avg_fyp | int }}%</div>
                    <div class="metric-label">Avg FYP Score</div>
                    <div class="metric-change positive">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="18 15 12 9 6 15"></polyline>
                        </svg>
                        Optimal
                    </div>
                </div>
            </div>

            <!-- Accounts Needing Attention -->
            <div class="col-3 fade-in delay-4">
                <div class="card metric-card">
                    <div class="metric-value">{{ accounts_needing_attention }}/{{ total_accounts }}</div>
                    <div class="metric-label">Needs Attention</div>
                    <div class="metric-change negative">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="6 9 12 15 18 9"></polyline>
                        </svg>
                        Monitor Required
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Content Grid -->
        <div class="grid" style="margin-top: 2rem;">
            <!-- FYP Health Monitor -->
            <div class="col-8 fade-in">
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">FYP Health Monitor</div>
                            <div class="card-subtitle">Real-time scoring of your For You Page performance</div>
                        </div>
                        <div class="status-badge status-warn">2 Accounts Below Threshold</div>
                    </div>
                    
                    <div class="account-list">
                        {% for account in accounts %}
                        <div class="account-item">
                            <div class="account-info">
                                <div class="account-avatar">{{ account.username[0].upper() }}</div>
                                <div class="account-details">
                                    <h4>@{{ account.username }}</h4>
                                    <p>{{ account.niche }}</p>
                                </div>
                            </div>
                            
                            <div class="account-metrics">
                                <div class="account-metric">
                                    <div class="value">${{ account.profit }}</div>
                                    <div class="label">Profit</div>
                                </div>
                                <div class="account-metric">
                                    <div class="value">{{ account.growth | round(1) }}%</div>
                                    <div class="label">Growth</div>
                                </div>
                                <div class="account-metric">
                                    <div class="value">{{ account.fyp_score }}%</div>
                                    <div class="label">FYP Score</div>
                                </div>
                                <div class="status-badge status-{{ account.status.lower() }}">{{ account.status }}</div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>

            <!-- Performance Charts -->
            <div class="col-4 fade-in delay-1">
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Performance Trends</div>
                            <div class="card-subtitle">Last 30 days overview</div>
                        </div>
                    </div>
                    
                    <div class="chart-container">
                        <canvas id="performanceChart"></canvas>
                    </div>
                </div>

                <!-- Quick Stats -->
                <div class="card" style="margin-top: 1.5rem;">
                    <div class="card-header">
                        <div class="card-title">Quick Stats</div>
                    </div>
                    
                    <div class="grid" style="gap: 1rem;">
                        <div class="col-6">
                            <div style="text-align: center;">
                                <div style="font-size: 1.5rem; font-weight: 700; color: var(--cyan);">1,847</div>
                                <div style="font-size: 0.85rem; color: var(--muted);">Products Sold</div>
                            </div>
                        </div>
                        <div class="col-6">
                            <div style="text-align: center;">
                                <div style="font-size: 1.5rem; font-weight: 700; color: var(--cyan);">$28.07</div>
                                <div style="font-size: 0.85rem; color: var(--muted);">Avg RPM</div>
                            </div>
                        </div>
                        <div class="col-6">
                            <div style="text-align: center;">
                                <div style="font-size: 1.5rem; font-weight: 700; color: var(--cyan);">0.14%</div>
                                <div style="font-size: 0.85rem; color: var(--muted);">Conversion</div>
                            </div>
                        </div>
                        <div class="col-6">
                            <div style="text-align: center;">
                                <div style="font-size: 1.5rem; font-weight: 700; color: var(--cyan);">12.4%</div>
                                <div style="font-size: 0.85rem; color: var(--muted);">Volatility</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Bottom Row -->
        <div class="grid" style="margin-top: 2rem;">
            <!-- GMV Analysis -->
            <div class="col-6 fade-in">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">GMV Analysis</div>
                        <div class="card-subtitle">Gross Merchandise Value trends</div>
                    </div>
                    <div class="chart-container">
                        <canvas id="gmvChart"></canvas>
                    </div>
                </div>
            </div>

            <!-- Profit Tracking -->
            <div class="col-6 fade-in delay-1">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">Profit Tracking</div>
                        <div class="card-subtitle">Daily profit and growth rate</div>
                    </div>
                    <div class="chart-container">
                        <canvas id="profitChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer>
        <div class="container">
            <p>Peak Overwatch v1.0 • 
                <a href="https://peakoverwatch.com/terms">Terms</a> • 
                <a href="https://peakoverwatch.com/privacy">Privacy</a> • 
                TikTok Developer Portal Application: Pending
            </p>
            <p style="margin-top: 0.5rem; font-size: 0.8rem;">
                © 2026 Peak Medium / Revler Inc • Data updates every 24 hours • Mock data for demonstration
            </p>
        </div>
    </footer>

    <script>
        // Initialize charts when page loads
        document.addEventListener('DOMContentLoaded', function() {
            // Fetch mock data
            fetch('/api/mock-data')
                .then(response => response.json())
                .then(data => {
                    initializeCharts(data);
                });
        });

        function initializeCharts(data) {
            // Performance Chart (Line)
            const perfCtx = document.getElementById('performanceChart').getContext('2d');
            const dates = data.time_series.map(d => d.date.substring(5)); // MM-DD
            const fypScores = data.time_series.map(d => d.fyp_score);
            
            new Chart(perfCtx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: 'FYP Score',
                        data: fypScores,
                        borderColor: '#00F2EA',
                        backgroundColor: 'rgba(0, 242, 234, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            min: 60,
                            max: 100,
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#888' }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#888' }
                        }
                    }
                }
            });

            // GMV Chart (Bar)
            const gmvCtx = document.getElementById('gmvChart').getContext('2d');
            const gmvData = data.time_series.slice(-7).map(d => d.gmv); // Last 7 days
            
            new Chart(gmvCtx, {
                type: 'bar',
                data: {
                    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    datasets: [{
                        label: 'GMV',
                        data: gmvData,
                        backgroundColor: 'rgba(255, 0, 80, 0.7)',
                        borderColor: '#FF0050',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#888' }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#888' }
                        }
                    }
                }
            });

            // Profit Chart (Line)
            const profitCtx = document.getElementById('profitChart').getContext('2d');
            const profitData = data.time_series.slice(-14).map(d => d.profit); // Last 14 days
            
            new Chart(profitCtx, {
                type: 'line',
                data: {
                    labels: Array.from({length: 14}, (_, i) => `Day ${i+1}`),
                    datasets: [{
                        label: 'Daily Profit',
                        data: profitData,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#888' }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#888' }
                        }
                    }
                }
            });
        }

        // GSAP animations
        gsap.registerPlugin(ScrollTrigger);

        // Animate cards on scroll
        gsap.utils.toArray('.fade-in').forEach(card => {
            gsap.from(card, {
                scrollTrigger: {
                    trigger: card,
                    start: 'top 80%',
                    toggleActions: 'play none none reverse'
                },
                opacity: 0,
                y: 30,
                duration: 0.8,
                ease: 'power2.out'
            });
        });
    </script>
</body>
</html>'''

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
            background: linear-gradient(135deg, var(--cyan), var(--red));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

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

        .tiktok-btn {
            width: 100%;
            padding: 0.75rem;
            background: #000000;
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            transition: all 0.2s;
        }

        .tiktok-btn:hover {
            background: #111111;
            transform: translateY(-2px);
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
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">PeakOverwatch</div>
        <div class="subtitle">Sign in to access your TikTok affiliate dashboard</div>
        
        <form id="loginForm">
            <div class="form-group">
                <label for="email">Email Address</label>
                <input type="email" id="email" placeholder="you@example.com" required>
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" placeholder="••••••••" required>
            </div>
            
            <button type="submit" class="btn">Sign In</button>
        </form>
        
        <div class="divider"><span>Or continue with</span></div>
        
        <button class="tiktok-btn" onclick="window.location.href='/tiktok/login'">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64c.302-.002.603.052.89.16V9.4a6.18 6.18 0 0 0-1-.05A6.27 6.27 0 0 0 5 20.1a6.27 6.27 0 0 0 10.14-2.94V9.5a8.27 8.27 0 0 0 4.8 1.5v-3.8a4.85 4.85 0 0 1-1-.11z"/>
            </svg>
            Connect TikTok Account
        </button>
        
        <div class="footer-links">
            <p>Don't have an account? <a href="#">Request Access</a></p>
            <p><a href="https://peakoverwatch.com">← Back to Homepage</a></p>
        </div>
    </div>

    <script>
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            // Mock login - in production this would call your backend
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            
            const result = await response.json();
            
            if (result.success) {
                window.location.href = '/dashboard';
            } else {
                alert('Login failed: ' + (result.message || 'Invalid credentials'));
            }
        });
    </script>
</body>
</html>'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))  # Changed from 5000 to 5001
    app.run(host='0.0.0.0', port=port, debug=(app.config['ENV'] == 'development'))