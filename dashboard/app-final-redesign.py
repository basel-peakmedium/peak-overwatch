#!/usr/bin/env python3
"""
Peak Overwatch Dashboard - Final Redesign
Matches peakoverwatch.com color scheme with sidebar navigation
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
    # Top metrics (matching screenshot)
    metrics = {
        'total_gmv': 186420,
        'commission_earned': 27963,
        'fyp_health_score': 94,
        'active_accounts': 12
    }
    
    # 30-day GMV data with rising trend
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
    """Main dashboard route with peakoverwatch.com design"""
    data = generate_mock_data()
    return render_template_string(DASHBOARD_TEMPLATE, **data['metrics'], 
                                 time_series=json.dumps(data['time_series']),
                                 accounts=data['accounts'])

@app.route('/api/mock-data')
def mock_data():
    """API endpoint for mock data"""
    data = generate_mock_data()
    return jsonify(data)

# HTML Template with peakoverwatch.com design
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Peak Overwatch • TikTok Affiliate Dashboard</title>
    <meta name="description" content="Strategic oversight platform for TikTok affiliate managers. Monitor FYP health, track GMV, and optimize performance across every account — all in one dashboard.">
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    
    <style>
        /* ===== PEAKOVERWATCH.COM DESIGN TOKENS ===== */
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
            margin: 0;
            padding: 0;
        }

        ::selection { background: var(--red); color: #fff; }

        /* ===== SCROLLBAR ===== */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: var(--dark); }
        ::-webkit-scrollbar-thumb { background: var(--red); border-radius: 3px; }

        /* ===== SIDEBAR ===== */
        .sidebar {
            position: fixed;
            top: 0;
            left: 0;
            bottom: 0;
            width: 260px;
            background: var(--surface);
            border-right: 1px solid var(--border);
            padding: 0;
            z-index: 100;
            overflow-y: auto;
        }

        .sidebar-header {
            padding: 1.5rem 1.5rem 1rem 1.5rem;
            border-bottom: 1px solid var(--border);
        }

        .logo {
            font-size: 1.25rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            text-decoration: none;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .logo span { color: var(--red); }
        .logo { color: #fff; }  /* Make "Peak" white and "Overwatch" red via span */

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
        }

        .sidebar-nav {
            padding: 1rem 0;
        }

        .nav-section {
            padding: 0 1.5rem;
            margin-bottom: 1.5rem;
        }

        .nav-section-title {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--muted);
            margin-bottom: 0.75rem;
            font-weight: 600;
        }

        .nav-item {
            margin-bottom: 0.25rem;
        }

        .nav-link {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1rem;
            color: var(--text);
            text-decoration: none;
            border-radius: 8px;
            transition: all 0.2s;
            font-size: 0.95rem;
        }

        .nav-link:hover {
            background: rgba(255, 255, 255, 0.05);
            color: var(--cyan);
        }

        .nav-link.active {
            background: rgba(255, 0, 80, 0.1);
            color: var(--cyan);
            border-left: 3px solid var(--red);
        }

        .nav-icon {
            width: 20px;
            text-align: center;
            opacity: 0.8;
        }

        .nav-link.active .nav-icon {
            opacity: 1;
        }

        /* ===== MAIN CONTENT ===== */
        .main-content {
            margin-left: 260px;
            padding: 2rem;
            min-height: 100vh;
        }

        /* ===== HEADER ===== */
        .dashboard-header {
            margin-bottom: 2.5rem;
        }

        .dashboard-header h1 {
            font-size: 2rem;
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

        /* ===== METRICS GRID ===== */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1.5rem;
            margin-bottom: 2.5rem;
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
            .main-content {
                margin-left: 0;
                padding: 1rem;
            }
            .sidebar {
                display: none;
            }
        }

        .metric-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            transition: all 0.3s;
        }

        .metric-card:hover {
            border-color: var(--cyan);
            transform: translateY(-4px);
            box-shadow: 0 12px 32px rgba(0, 242, 234, 0.1);
        }

        .metric-label {
            font-size: 0.9rem;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }

        .metric-value {
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--cyan), var(--red));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .metric-change {
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }

        .metric-change.positive {
            color: #10b981;
        }

        /* ===== CHART CONTAINER ===== */
        .chart-container {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }

        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }

        .chart-title {
            font-size: 1.1rem;
            font-weight: 600;
        }

        .chart-subtitle {
            font-size: 0.9rem;
            color: var(--muted);
            margin-top: 0.25rem;
        }

        .chart-wrapper {
            height: 300px;
            position: relative;
        }

        /* ===== ACCOUNTS TABLE ===== */
        .accounts-container {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
        }

        .accounts-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }

        .accounts-title {
            font-size: 1.1rem;
            font-weight: 600;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--red), #ff3366);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(255, 0, 80, 0.3);
        }

        .accounts-table {
            width: 100%;
            border-collapse: collapse;
        }

        .table-header {
            border-bottom: 1px solid var(--border);
            padding-bottom: 1rem;
            margin-bottom: 1rem;
        }

        .table-header-row {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr 1fr;
            gap: 1.5rem;
            padding: 0 0.5rem;
            font-weight: 600;
            color: var(--muted);
            font-size: 0.9rem;
        }

        .account-row {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr 1fr;
            gap: 1.5rem;
            padding: 1rem 0.5rem;
            border-bottom: 1px solid var(--border);
            align-items: center;
        }

        .account-row:last-child {
            border-bottom: none;
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
            font-size: 1rem;
        }

        .account-details h4 {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }

        .account-details p {
            font-size: 0.85rem;
            color: var(--muted);
            margin: 0;
        }

        .account-metric {
            text-align: right;
        }

        .account-metric .value {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }

        .account-metric .label {
            font-size: 0.8rem;
            color: var(--muted);
        }

        .fyp-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-block;
        }

        .fyp-good {
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
        }

        .fyp-warning {
            background: rgba(245, 158, 11, 0.15);
            color: #f59e0b;
        }

        .fyp-critical {
            background: rgba(239, 68, 68, 0.15);
            color: #ef4444;
        }

        /* ===== FOOTER ===== */
        .dashboard-footer {
            margin-top: 3rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border);
            text-align: center;
            color: var(--muted);
            font-size: 0.9rem;
        }

        .dashboard-footer a {
            color: var(--cyan);
            text-decoration: none;
        }

        .dashboard-footer a:hover {
            text-decoration: underline;
        }

        /* ===== FORM CONTROLS ===== */
        select {
            background: var(--surface);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
            cursor: pointer;
        }

        select:focus {
            outline: none;
            border-color: var(--cyan);
        }
    </style>
</head>
<body>
    <!-- Sidebar Navigation -->
    <div class="sidebar">
        <div class="sidebar-header">
            <a href="https://peakoverwatch.com" class="logo">
                <div class="logo-icon">P</div>
                <span style="color: #fff;">Peak</span><span style="color: #FF0050; margin-left: -4px;">Overwatch</span>
            </a>
        </div>
        
        <div class="sidebar-nav">
            <div class="nav-section">
                <div class="nav-section-title">Dashboard</div>
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
            </div>
            
            <div class="nav-section">
                <div class="nav-section-title">Content</div>
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
            </div>
            
            <div class="nav-section">
                <div class="nav-section-title">System</div>
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
                    <div class="chart-title">Daily GMV — All Accounts</div>
                    <div class="chart-subtitle">Last 30 days</div>
                </div>
                <div>
                    <select>
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
        
        <!-- Accounts Table -->
        <div class="accounts-container">
            <div class="accounts-header">
                <div class="accounts-title">Account Performance</div>
                <button class="btn-primary">
                    <i class="bi bi-plus"></i> Add Account
                </button>
            </div>
            
            <div class="accounts-table">
                <div class="table-header">
                    <div class="table-header-row">
                        <div>Account</div>
                        <div class="text-right">Profit</div>
                        <div class="text-right">Growth</div>
                        <div class="text-right">FYP Score</div>
                    </div>
                </div>
                
                <div class="table-body">
                    {% for account in accounts %}
                    <div class="account-row">
                        <div class="account-info">
                            <div class="account-avatar">{{ account.username[0].upper() }}</div>
                            <div class="account-details">
                                <h4>@{{ account.username }}</h4>
                                <p>{{ account.niche }}</p>
                            </div>
                        </div>
                        
                        <div class="account-metric">
                            <div class="value">${{ "{:,}".format(account.profit) }}</div>
                            <div class="label">Profit</div>
                        </div>
                        
                        <div class="account-metric">
                            <div class="value">{{ account.growth }}%</div>
                            <div class="label">Growth</div>
                        </div>
                        
                        <div class="account-metric">
                            <div class="value">{{ account.fyp_score }}%</div>
                            <div class="label">
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
            </div>
        </div>
        
        <!-- Footer -->
        <div class="dashboard-footer">
            <p>
                Peak Overwatch v1.0 • 
                <a href="https://peakoverwatch.com/terms">Terms</a> • 
                <a href="https://peakoverwatch.com/privacy">Privacy</a> • 
                TikTok Developer Portal Application: Pending
            </p>
            <p style="margin-top: 0.5rem; font-size: 0.8rem;">
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
            
            // Create GMV Chart with peakoverwatch.com transitional hue
            const ctx = document.getElementById('gmvChart').getContext('2d');
            
            // Create gradient for line (cyan to red)
            const lineGradient = ctx.createLinearGradient(0, 0, ctx.canvas.width, 0);
            lineGradient.addColorStop(0, '#00F2EA');
            lineGradient.addColorStop(1, '#FF0050');
            
            // Create gradient for fill - fills entire area under line
            // We'll create this after we know the chart area dimensions
            let fillGradient;
            
            function updateFillGradient() {
                const chartArea = chart.chartArea;
                if (!chartArea) return;
                
                // Create gradient from top of chart area to bottom
                fillGradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                
                // Cleaner, smoother transition - fewer stops, more gradual
                fillGradient.addColorStop(0, 'rgba(255, 0, 80, 0.35)');      // Red at top
                fillGradient.addColorStop(0.3, 'rgba(255, 50, 120, 0.25)');  // Red-pink
                fillGradient.addColorStop(0.6, 'rgba(100, 150, 255, 0.15)'); // Blue-purple
                fillGradient.addColorStop(1, 'rgba(0, 242, 234, 0.08)');     // Cyan at bottom
                
                // Update chart dataset
                chart.data.datasets[0].backgroundColor = fillGradient;
                chart.update('none'); // Update without animation
            }
            
            const chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: 'Daily GMV',
                        data: gmvData,
                        borderColor: lineGradient,
                        backgroundColor: 'rgba(255, 0, 80, 0.2)', // Initial color, will be updated with gradient
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: '#FFFFFF',
                        pointBorderColor: '#FF0050',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        pointHoverBorderWidth: 3
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
                            backgroundColor: 'rgba(22, 22, 22, 0.95)',
                            titleColor: '#e8e8e8',
                            bodyColor: '#e8e8e8',
                            borderColor: 'rgba(255,255,255,0.07)',
                            borderWidth: 1,
                            padding: 12,
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
                                color: '#888888',
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
                                color: '#888888',
                                maxRotation: 0
                            }
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'nearest'
                    }
                }
            });
            
            // Set initial gradient immediately (not waiting for animation)
            setTimeout(updateFillGradient, 100);
            
            // Update fill gradient after chart is rendered
            chart.options.animation.onComplete = function() {
                updateFillGradient();
            };
            
            // Also update on resize
            window.addEventListener('resize', function() {
                setTimeout(updateFillGradient, 100);
            });
            
            // Add interactive hover line (user-controlled, not automatic)
            let hoverLineX = null;
            let isHovering = false;
            
            function drawHoverLine() {
                if (!ctx.canvas || hoverLineX === null) return;
                
                const chartArea = chart.chartArea;
                if (!chartArea) return;
                
                // Only draw if mouse is over chart
                if (hoverLineX < chartArea.left || hoverLineX > chartArea.right) return;
                
                // Draw hover line
                ctx.save();
                ctx.beginPath();
                ctx.moveTo(hoverLineX, chartArea.top);
                ctx.lineTo(hoverLineX, chartArea.bottom);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)';
                ctx.lineWidth = 1;
                ctx.stroke();
                
                // Find closest data point
                const xScale = chart.scales.x;
                const dataIndex = Math.round((hoverLineX - chartArea.left) / (chartArea.right - chartArea.left) * (gmvData.length - 1));
                const dataPoint = chart.getDatasetMeta(0).data[Math.min(dataIndex, gmvData.length - 1)];
                
                if (dataPoint) {
                    // Draw dot on line
                    ctx.beginPath();
                    ctx.arc(dataPoint.x, dataPoint.y, 4, 0, Math.PI * 2);
                    ctx.fillStyle = '#FFFFFF';
                    ctx.fill();
                    
                    ctx.beginPath();
                    ctx.arc(dataPoint.x, dataPoint.y, 2, 0, Math.PI * 2);
                    ctx.fillStyle = '#FF0050';
                    ctx.fill();
                    
                    // Show value label
                    const value = gmvData[dataIndex];
                    ctx.fillStyle = 'rgba(22, 22, 22, 0.9)';
                    ctx.fillRect(dataPoint.x - 40, dataPoint.y - 40, 80, 30);
                    
                    ctx.fillStyle = '#FFFFFF';
                    ctx.font = '12px -apple-system, BlinkMacSystemFont, "Inter", sans-serif';
                    ctx.textAlign = 'center';
                    ctx.fillText(`$${value.toLocaleString()}`, dataPoint.x, dataPoint.y - 20);
                }
                
                ctx.restore();
            }
            
            // Mouse move handler for interactive line
            ctx.canvas.addEventListener('mousemove', function(event) {
                const rect = ctx.canvas.getBoundingClientRect();
                const x = event.clientX - rect.left;
                const y = event.clientY - rect.top;
                
                const chartArea = chart.chartArea;
                if (chartArea && x >= chartArea.left && x <= chartArea.right && 
                    y >= chartArea.top && y <= chartArea.bottom) {
                    hoverLineX = x;
                    isHovering = true;
                    chart.draw();
                    drawHoverLine();
                } else {
                    if (isHovering) {
                        isHovering = false;
                        hoverLineX = null;
                        chart.draw();
                    }
                }
            });
            
            ctx.canvas.addEventListener('mouseleave', function() {
                isHovering = false;
                hoverLineX = null;
                chart.draw();
            });
            
            // Redraw chart with hover line
            const originalDraw = chart.draw;
            chart.draw = function() {
                originalDraw.call(this);
                if (isHovering && hoverLineX !== null) {
                    drawHoverLine();
                }
            };
            
            // Add click handlers to sidebar links
            document.querySelectorAll('.nav-link').forEach(link => {
                link.addEventListener('click', function(e) {
                    if (this.getAttribute('href') === '#') {
                        e.preventDefault();
                        // Show loading state
                        const originalHTML = this.innerHTML;
                        this.innerHTML = '<i class="bi bi-hourglass-split nav-icon"></i> Loading...';
                        this.classList.add('disabled');
                        
                        setTimeout(() => {
                            this.innerHTML = originalHTML;
                            this.classList.remove('disabled');
                            // Show coming soon message
                            const navText = this.textContent.trim();
                            alert(`"${navText}" feature is coming soon!`);
                        }, 500);
                    }
                });
            });
            
            // Add Account button handler
            document.querySelector('.btn-primary').addEventListener('click', function() {
                alert('Account connection feature coming soon! This will integrate with TikTok OAuth.');
            });
        });
    </script>
</body>
</html>'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))  # Different port
    app.run(host='0.0.0.0', port=port, debug=(app.config['ENV'] == 'development'))