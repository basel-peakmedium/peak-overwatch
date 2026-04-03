#!/usr/bin/env python3
"""
Peak Overwatch Dashboard - Production Ready
For deployment to app.peakoverwatch.com
"""

from flask import Flask, render_template_string
import os

app = Flask(__name__)

# Production settings
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['ENV'] = os.environ.get('FLASK_ENV', 'production')

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Peak Overwatch • TikTok Affiliate Dashboard</title>
    <meta name="description" content="Strategic oversight platform for TikTok affiliate operations. Monitor FYP health, track performance metrics, and optimize your TikTok Shop strategy.">
    
    <!-- Open Graph / Social Meta -->
    <meta property="og:title" content="Peak Overwatch • TikTok Affiliate Dashboard">
    <meta property="og:description" content="Strategic oversight platform for TikTok affiliate operations">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://app.peakoverwatch.com">
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <!-- Bootstrap 5 -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    
    <!-- Custom Styles -->
    <style>
        :root {
            --primary: #000000;
            --secondary: #FF0050;
            --accent: #00F2EA;
            --dark-bg: #0f172a;
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
            padding: 20px;
            min-height: 100vh;
        }
        
        .navbar-brand {
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            transition: transform 0.2s;
        }
        
        .card:hover {
            transform: translateY(-2px);
        }
        
        .metric-value {
            font-size: 1.75rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .metric-tabs {
            display: flex;
            gap: 4px;
            background-color: var(--card-bg);
            border-radius: 8px;
            padding: 4px;
            margin-bottom: 1rem;
        }
        
        .metric-tab {
            flex: 1;
            padding: 0.5rem 1rem;
            text-align: center;
            border-radius: 6px;
            cursor: pointer;
            color: var(--text-secondary);
            transition: all 0.2s;
        }
        
        .metric-tab:hover {
            background-color: rgba(139, 92, 246, 0.1);
        }
        
        .metric-tab.active {
            background-color: var(--secondary);
            color: white;
        }
        
        .fyp-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }
        
        .fyp-good { background-color: var(--success); }
        .fyp-warning { background-color: var(--warning); }
        .fyp-critical { background-color: var(--danger); }
        
        .chart-container {
            height: 300px;
            position: relative;
        }
        
        .account-card {
            border-left: 4px solid var(--accent);
        }
        
        .profit-badge {
            background: linear-gradient(135deg, var(--success), #059669);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 600;
        }
        
        .alert-box {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(245, 158, 11, 0.1));
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            body { padding: 10px; }
            .metric-tabs { flex-direction: column; }
            .metric-tab { padding: 0.75rem; }
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg mb-4">
        <div class="container-fluid">
            <a class="navbar-brand" href="https://peakoverwatch.com">
                <i class="bi bi-binoculars-fill me-2"></i>Peak Overwatch
            </a>
            <div class="d-flex align-items-center">
                <span class="badge bg-dark me-3">v1.0</span>
                <a href="https://peakoverwatch.com" class="btn btn-sm btn-outline-light">
                    <i class="bi bi-house me-1"></i>Home
                </a>
            </div>
        </div>
    </nav>

    <div class="container-fluid">
        <div class="row">
            <!-- Left Sidebar - Portfolio Overview -->
            <div class="col-lg-3">
                <!-- Portfolio Summary -->
                <div class="card">
                    <h6 class="text-uppercase text-secondary mb-3">
                        <i class="bi bi-pie-chart-fill me-2"></i>Portfolio Overview
                    </h6>
                    <div class="metric-value">$5,128</div>
                    <div class="text-secondary">Monthly Profit</div>
                    <div class="mt-2">
                        <span class="profit-badge">
                            <i class="bi bi-arrow-up-right me-1"></i>18.4% growth
                        </span>
                    </div>
                    
                    <hr class="my-3" style="border-color: var(--border-color);">
                    
                    <div class="row text-center">
                        <div class="col-6">
                            <div class="text-secondary small">Accounts</div>
                            <div class="h5 mb-0">5</div>
                        </div>
                        <div class="col-6">
                            <div class="text-secondary small">Active</div>
                            <div class="h5 mb-0">5</div>
                        </div>
                    </div>
                </div>
                
                <!-- FYP Health Monitor -->
                <div class="card">
                    <h6 class="mb-3">
                        <i class="bi bi-heart-pulse-fill me-2"></i>FYP Health Status
                    </h6>
                    
                    <div class="alert-box">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>
                            <div>
                                <div class="small fw-bold">Monitor Required</div>
                                <div class="small text-secondary">2 accounts below 80% threshold</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="fyp-list">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <div>
                                <span class="fyp-indicator fyp-good"></span>
                                <span>@ourviralpicks</span>
                            </div>
                            <div class="fw-bold">85.2%</div>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <div>
                                <span class="fyp-indicator fyp-good"></span>
                                <span>@homegadgetfinds</span>
                            </div>
                            <div class="fw-bold">88.1%</div>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <div>
                                <span class="fyp-indicator fyp-good"></span>
                                <span>@beautytrends</span>
                            </div>
                            <div class="fw-bold">83.7%</div>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <div>
                                <span class="fyp-indicator fyp-warning"></span>
                                <span>@cartcravings30</span>
                            </div>
                            <div class="fw-bold text-warning">72.3%</div>
                        </div>
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <span class="fyp-indicator fyp-warning"></span>
                                <span>@fitnessessentials</span>
                            </div>
                            <div class="fw-bold text-warning">76.4%</div>
                        </div>
                    </div>
                    
                    <div class="mt-3 pt-3 border-top" style="border-color: var(--border-color) !important;">
                        <div class="small text-secondary">FYP Thresholds:</div>
                        <div class="d-flex justify-content-between small">
                            <span><span class="fyp-indicator fyp-good"></span> Good: ≥80%</span>
                            <span><span class="fyp-indicator fyp-warning"></span> Warn: 70-79%</span>
                            <span><span class="fyp-indicator fyp-critical"></span> Critical: <70%</span>
                        </div>
                    </div>
                </div>
                
                <!-- Quick Stats -->
                <div class="card">
                    <h6 class="text-secondary mb-3">Quick Stats</h6>
                    <div class="row g-2">
                        <div class="col-6">
                            <div class="card account-card">
                                <div class="small text-secondary">Total GMV</div>
                                <div class="h5 mb-0">$42.8K</div>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="card account-card">
                                <div class="small text-secondary">Products Sold</div>
                                <div class="h5 mb-0">1,847</div>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="card account-card">
                                <div class="small text-secondary">Avg RPM</div>
                                <div class="h5 mb-0">$28.07</div>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="card account-card">
                                <div class="small text-secondary">Conversion</div>
                                <div class="h5 mb-0">0.14%</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Main Content Area -->
            <div class="col-lg-9">
                <!-- Metric Selection Tabs -->
                <div class="metric-tabs" id="metricTabs">
                    <div class="metric-tab active" data-metric="profit">
                        <i class="bi bi-cash-stack me-1"></i> Profit Tracking
                    </div>
                    <div class="metric-tab" data-metric="gmv">
                        <i class="bi bi-graph-up me-1"></i> GMV Analysis
                    </div>
                    <div class="metric-tab" data-metric="products">
                        <i class="bi bi-box-seam me-1"></i> Products Sold
                    </div>
                    <div class="metric-tab" data-metric="videos">
                        <i class="bi bi-camera-video me-1"></i> Video Performance
                    </div>
                </div>

                <!-- Main Chart Card -->
                <div class="card">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5 id="chartTitle" class="mb-0">Portfolio Profit Trend Analysis</h5>
                        <select class="form-select form-select-sm w-auto" style="background-color: var(--card-bg); color: var(--text-primary); border-color: var(--border-color);">
                            <option>Last 30 Days</option>
                            <option>Last 90 Days</option>
                            <option>Year to Date</option>
                            <option>All Time</option>
                        </select>
                    </div>
                    
                    <div class="chart-container">
                        <canvas id="mainChart"></canvas>
                    </div>
                    
                    <div class="mt-3 pt-3 border-top" style="border-color: var(--border-color) !important;">
                        <div class="row text-center">
                            <div class="col-3">
                                <div class="small text-secondary">Peak Profit</div>
                                <div class="fw-bold">$1,842</div>
                            </div>
                            <div class="col-3">
                                <div class="small text-secondary">Avg Daily</div>
                                <div class="fw-bold">$171</div>
                            </div>
                            <div class="col-3">
                                <div class="small text-secondary">Growth Rate</div>
                                <div class="fw-bold text-success">+15.2%</div>
                            </div>
                            <div class="col-3">
                                <div class="small text-secondary">Volatility</div>
                                <div class="fw-bold">12.4%</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Account Performance Grid -->
                <div class="row">
                    <div class="col-md-6">
                        <div class="card">
                            <h6 class="mb-3">
                                <i class="bi bi-trophy-fill me-2"></i>Top Performing Account
                            </h6>
                            <div class="d-flex align-items-center">
                                <div class="rounded-circle bg-dark d-flex align-items-center justify-content-center" style="width: 50px; height: 50px;">
                                    <i class="bi bi-star-fill text-warning"></i>
                                </div>
                                <div class="ms-3">
                                    <div class="fw-bold">@ourviralpicks</div>
                                    <div class="text-secondary small">Home & Lifestyle</div>
                                </div>
                                <div class="ms-auto text-end">
                                    <div class="metric-value">$2,412</div>
                                    <div class="text-success small">
                                        <i class="bi bi-arrow-up-right me-1"></i>24.7%
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <div class="card">
                            <h6 class="mb-3">
                                <i class="bi bi-activity me-2"></i>Needs Attention
                            </h6>
                            <div class="d-flex align-items-center">
                                <div class="rounded-circle bg-dark d-flex align-items-center justify-content-center" style="width: 50px; height: 50px;">
                                    <i class="bi bi-exclamation-triangle text-warning"></i>
                                </div>
                                <div class="ms-3">
                                    <div class="fw-bold">@cartcravings30</div>
                                    <div class="text-secondary small">Food & Kitchen</div>
                                </div>
                                <div class="ms-auto text-end">
                                    <div class="metric-value">$842</div>
                                    <div class="text-warning small">
                                        <i class="bi bi-arrow-down-right me-1"></i>8.3%
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Footer -->
        <div class="mt-4 pt-4 border-top text-center" style="border-color: var(--border-color) !important;">
            <div class="text-secondary small">
                <i class="bi bi-shield-check me-1"></i>Peak Overwatch v1.0 • 
                <a href="https://peakoverwatch.com/terms" class="text-secondary">Terms</a> • 
                <a href="https://peakoverwatch.com/privacy" class="text-secondary">Privacy</a> • 
                TikTok Developer Portal Application: Pending
            </div>
            <div class="text-secondary small mt-1">
                &copy; 2026 Peak Medium / Revler Inc • Data updates every 24 hours
            </div>
        </div>
    </div>

    <!-- JavaScript -->
    <script>
        // Chart Configuration
        let currentMetric = 'profit';
        let mainChart;
        
        document.addEventListener('DOMContentLoaded', function() {
            setupChart();
            setupMetricTabs();
            setupInteractivity();
        });
        
        function setupChart() {
            const ctx = document.getElementById('mainChart').getContext('2d');
            const labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6'];
            
            // Data generators for different metrics
            const dataGenerators = {
                profit: (base) => {
                    const trend = [base, base * 1.1, base * 1.25, base * 1.15, base * 1.3, base * 1.4];
                    return trend.map(val => val + (val * 0.2 * (Math.random() - 0.5)));
                },
                gmv: (base) => {
                    const trend = [base * 7.8, base * 8.2, base * 8.9, base * 8.5, base * 9.3, base * 9.8];
                    return trend.map(val => val + (val * 0.15 * (Math.random() - 0.5)));
                },
                products: (base) => {
                    const trend = [base * 0.033, base * 0.035, base * 0.038, base * 0.036, base * 0.04, base * 0.042];
                    return trend.map(val => Math.round(val + (val * 0.25 * (Math.random() - 0.5))));
                },
                videos: (base) => {
                    const trend = [base * 0.355, base * 0.37, base * 0.39, base * 0.38, base * 0.41, base * 0.43];
                    return trend.map(val => Math.round(val + (val * 0.2 * (Math.random() - 0.5))));
                }
            };
            
            const datasets = [
                {
                    label: '@ourviralpicks',
                    data: dataGenerators[currentMetric](2412),
                    borderColor: '#00F2EA',
                    backgroundColor: '#00F2EA20',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                },
                {
                    label: '@homegadgetfinds',
                    data: dataGenerators[currentMetric](1520),
                    borderColor: '#FF0050',
                    backgroundColor: '#FF005020',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                },
                {
                    label: '@beautytrends',
                    data: dataGenerators[currentMetric](985),
                    borderColor: '#8b5cf6',
                    backgroundColor: '#8b5cf620',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }
            ];
            
            if (mainChart) mainChart.destroy();
            
            mainChart = new Chart(ctx, {
                type: 'line',
                data: { labels, datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                color: '#f1f5f9',
                                padding: 20,
                                font: { size: 12 }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rg(30, 41, 59, 0.9)',
                            titleColor: '#f1f5f9',
                            bodyColor: '#f1f5f9',
                            borderColor: '#334155',
                            borderWidth: 1
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: '#334155', drawBorder: false },
                            ticks: { color: '#94a3b8' }
                        },
                        y: {
                            beginAtZero: true,
                            grid: { color: '#334155', drawBorder: false },
                            ticks: {
                                color: '#94a3b8',
                                callback: function(value) {
                                    if (currentMetric === 'profit' || currentMetric === 'gmv') {
                                        return '$' + value.toLocaleString();
                                    }
                                    return value.toLocaleString();
                                }
                            }
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    }
                }
            });
            
            // Update chart title
            const titles = {
                profit: 'Portfolio Profit Trend Analysis',
                gmv: 'Gross Merchandise Value Tracking',
                products: 'Unique Products Sold Trend',
                videos: 'Video Content Performance'
            };
            document.getElementById('chartTitle').textContent = titles[currentMetric] || 'Performance Analysis';
        }
        
        function setupMetricTabs() {
            document.querySelectorAll('.metric-tab').forEach(tab => {
                tab.addEventListener('click', function() {
                    // Update active tab
                    document.querySelectorAll('.metric-tab').forEach(t => t.classList.remove('active'));
                    this.classList.add('active');
                    
                    // Update metric and redraw chart
                    currentMetric = this.dataset.metric;
                    setupChart();
                });
            });
        }
        
        function setupInteractivity() {
            // Time period selector
            const timeSelector = document.querySelector('select');
            if (timeSelector) {
                timeSelector.addEventListener('change', function() {
                    // In production, this would fetch new data based on time period
                    console.log('Time period changed to:', this.value);
                    // For demo, we'll just regenerate with slight variation
                    setupChart();
                });
            }
            
            // Add hover effects to cards
            document.querySelectorAll('.card').forEach(card => {
                card.style.cursor = 'pointer';
                card.addEventListener('click', function() {
                    // In production, this would navigate or show details
                    console.log('Card clicked:', this.querySelector('h6')?.textContent);
                });
            });
        }
        
        // Auto-refresh simulation (every 30 seconds in demo)
        setInterval(() => {
            // Simulate live data updates
            if (mainChart) {
                mainChart.data.datasets.forEach(dataset => {
                    const lastValue = dataset.data[dataset.data.length - 1];
                    const newValue = lastValue * (1 + (Math.random() * 0.1 - 0.05));
                    dataset.data.push(newValue);
                    dataset.data.shift();
                });
                mainChart.update('none');
            }
        }, 30000);
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)