"""
Templates for Peak Overwatch complete dashboard
All 5 tabs: Dashboard, Accounts, Analytics, Alerts, Settings
"""

DASHBOARD_TEMPLATE = '''
<div class="page-header">
    <h1>Dashboard Overview</h1>
    <p>Monitor your TikTok affiliate performance across all accounts</p>
</div>

<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; margin-bottom: 2rem;">
    <div class="card">
        <div style="color: var(--muted); font-size: 0.9rem; margin-bottom: 0.5rem;">Total GMV</div>
        <div style="font-size: 2rem; font-weight: 800; color: var(--cyan);">${{ "{:,}".format(total_gmv) }}</div>
        <div style="color: #10b981; font-size: 0.85rem; margin-top: 0.5rem;">
            <i class="bi bi-arrow-up-right"></i> +12.4% from last month
        </div>
    </div>
    
    <div class="card">
        <div style="color: var(--muted); font-size: 0.9rem; margin-bottom: 0.5rem;">Commission Earned</div>
        <div style="font-size: 2rem; font-weight: 800; color: var(--cyan);">${{ "{:,}".format(commission_earned) }}</div>
        <div style="color: #10b981; font-size: 0.85rem; margin-top: 0.5rem;">
            <i class="bi bi-arrow-up-right"></i> +8.7% from last month
        </div>
    </div>
    
    <div class="card">
        <div style="color: var(--muted); font-size: 0.9rem; margin-bottom: 0.5rem;">FYP Health Score</div>
        <div style="font-size: 2rem; font-weight: 800; color: var(--cyan);">{{ fyp_health_score }}%</div>
        <div style="color: #10b981; font-size: 0.85rem; margin-top: 0.5rem;">
            <i class="bi bi-arrow-up-right"></i> +3.2% from last week
        </div>
    </div>
    
    <div class="card">
        <div style="color: var(--muted); font-size: 0.9rem; margin-bottom: 0.5rem;">Active Accounts</div>
        <div style="font-size: 2rem; font-weight: 800; color: var(--cyan);">{{ active_accounts }}</div>
        <div style="color: #10b981; font-size: 0.85rem; margin-top: 0.5rem;">
            <i class="bi bi-plus-circle"></i> +2 new this month
        </div>
    </div>
</div>

<div class="card" style="margin-bottom: 2rem;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2 style="font-size: 1.25rem; font-weight: 600;">Performance Trends</h2>
        <div style="display: flex; gap: 0.5rem;">
            <button class="btn" style="padding: 0.5rem 1rem; font-size: 0.9rem;">30 Days</button>
            <button style="background: none; border: 1px solid var(--border); color: var(--text); padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.9rem; cursor: pointer;">90 Days</button>
        </div>
    </div>
    <div style="height: 300px;">
        <canvas id="performanceChart"></canvas>
    </div>
</div>

<div class="card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2 style="font-size: 1.25rem; font-weight: 600;">Account Performance</h2>
        <button class="btn" onclick="alert('Connect TikTok feature coming soon!')">
            <i class="bi bi-plus"></i> Add Account
        </button>
    </div>
    
    <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr>
                    <th style="text-align: left; padding: 0.75rem 1rem; color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--border);">Account</th>
                    <th style="text-align: left; padding: 0.75rem 1rem; color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--border);">Niche</th>
                    <th style="text-align: left; padding: 0.75rem 1rem; color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--border);">Profit</th>
                    <th style="text-align: left; padding: 0.75rem 1rem; color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--border);">Growth</th>
                    <th style="text-align: left; padding: 0.75rem 1rem; color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--border);">FYP Score</th>
                    <th style="text-align: left; padding: 0.75rem 1rem; color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--border);">Status</th>
                </tr>
            </thead>
            <tbody>
                {% for account in user.profiles %}
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 1rem;">
                        <div style="font-weight: 600;">@{{ account.username }}</div>
                        <div style="font-size: 0.9rem; color: var(--muted);">{{ account.niche }}</div>
                    </td>
                    <td style="padding: 1rem;">{{ account.niche }}</td>
                    <td style="padding: 1rem; font-weight: 600;">${{ "{:,}".format(account.profit) }}</td>
                    <td style="padding: 1rem;">
                        <span style="color: #10b981; font-weight: 600;">{{ account.growth }}%</span>
                    </td>
                    <td style="padding: 1rem;">
                        <span style="font-weight: 700; font-size: 1.1rem; color: {% if account.fyp_score >= 80 %}#10b981{% elif account.fyp_score >= 70 %}#f59e0b{% else %}#ef4444{% endif %};">
                            {{ account.fyp_score }}%
                        </span>
                    </td>
                    <td style="padding: 1rem;">
                        <span style="display: inline-block; padding: 0.25rem 0.75rem; background: rgba(16,185,129,0.1); color: #10b981; border-radius: 20px; font-size: 0.8rem; font-weight: 600;">
                            {{ account.status|title }}
                        </span>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<script>
    // Performance chart
    const timeSeries = {{ time_series|safe }};
    const dates = timeSeries.map(item => item.date.substring(5));
    const gmvData = timeSeries.map(item => item.gmv);
    const commissionData = timeSeries.map(item => item.commission);
    
    const ctx = document.getElementById('performanceChart').getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(255, 0, 80, 0.35)');
    gradient.addColorStop(0.5, 'rgba(255, 50, 120, 0.25)');
    gradient.addColorStop(1, 'rgba(0, 242, 234, 0.08)');
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'GMV',
                    data: gmvData,
                    borderColor: '#FF0050',
                    backgroundColor: gradient,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Commission',
                    data: commissionData,
                    borderColor: '#00F2EA',
                    backgroundColor: 'rgba(0, 242, 234, 0.1)',
                    borderWidth: 2,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#888' }
                }
            },
            scales: {
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { 
                        color: '#888',
                        callback: value => '$' + value.toLocaleString()
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#888', maxRotation: 0 }
                }
            }
        }
    });
</script>
'''

ACCOUNTS_TEMPLATE = '''
<div class="page-header">
    <h1>Account Management</h1>
    <p>Manage your TikTok accounts and monitor their performance</p>
</div>

<div class="card" style="margin-bottom: 2rem;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2 style="font-size: 1.25rem; font-weight: 600;">Your TikTok Accounts</h2>
        <button class="btn" onclick="showAddAccountModal()">
            <i class="bi bi-plus"></i> Add Account
        </button>
    </div>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem;">
        {% for account in user.profiles %}
        <div style="background: var(--dark); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                <div>
                    <div style="font-size: 1.25rem; font-weight: 700; margin-bottom: 0.25rem;">@{{ account.username }}</div>
                    <div style="color: var(--muted); font-size: 0.9rem;">{{ account.niche }}</div>
                </div>
                <span style="padding: 0.25rem 0.75rem; background: {% if account.status == 'active' %}rgba(16,185,129,0.1){% elif account.status == 'warning' %}rgba(245,158,11,0.1){% else %}rgba(239,68,68,0.1){% endif %}; color: {% if account.status == 'active' %}#10b981{% elif account.status == 'warning' %}#f59e0b{% else %}#ef4444{% endif %}; border-radius: 20px; font-size: 0.8rem; font-weight: 600;">
                    {{ account.status|title }}
                </span>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
                <div>
                    <div style="color: var(--muted); font-size: 0.8rem; margin-bottom: 0.25rem;">Followers</div>
                    <div style="font-weight: 600; font-size: 1.1rem;">{{ "{:,}".format(account.followers) }}</div>
                </div>
                <div>
                    <div style="color: var(--muted); font-size: 0.8rem; margin-bottom: 0.25rem;">Videos</div>
                    <div style="font-weight: 600; font-size: 1.1rem;">{{ account.videos }}</div>
                </div>
                <div>
                    <div style="color: var(--muted); font-size: 0.8rem; margin-bottom: 0.25rem;">Profit</div>
                    <div style="font-weight: 600; font-size: 1.1rem; color: var(--cyan);">${{ "{:,}".format(account.profit) }}</div>
                </div>
                <div>
                    <div style="color: var(--muted); font-size: 0.8rem; margin-bottom: 0.25rem;">FYP Score</div>
                    <div style="font-weight: 700; font-size: 1.1rem; color: {% if account.fyp_score >= 80 %}#10b981{% elif account.fyp_score >= 70 %}#f59e0b{% else %}#ef4444{% endif %};">
                        {{ account.fyp_score }}%
                    </div>
                </div>
            </div>
            
            <div style="color: var(--muted); font-size: 0.85rem; margin-bottom: 1rem;">
                <i class="bi bi-clock"></i> Last active: {{ account.last_active }}
            </div>
            
            <div style="display: flex; gap: 0.5rem;">
                <button class="btn" style="flex: 1; padding: 0.5rem; font-size: 0.9rem;" onclick="viewAccountDetails({{ account.id }})">
                    <i class="bi bi-eye"></i> View Details
                </button>
                <button style="flex: 1; background: none; border: 1px solid var(--border); color: var(--text); padding: 0.5rem; border-radius: 8px; font-size: 0.9rem; cursor: pointer;" onclick="editAccount({{ account.id }})">
                    <i class="bi bi-pencil"></i> Edit
                </button>
            </div>
        </div>
        {% endfor %}
    </div>
</div>

<div class="card">
    <h2 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 1rem;">Account Health Summary</h2>
    
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; margin-bottom: 1.5rem;">
        <div style="text-align: center; padding: 1rem; background: rgba(16,185,129,0.1); border-radius: 12px;">
            <div style="font-size: 2rem; font-weight: 800; color: #10b981;">{{ user.profiles|selectattr('status', 'equalto', 'active')|list|length }}</div>
            <div style="color: var(--muted); font-size: 0.9rem;">Active Accounts</div>
        </div>
        
        <div style="text-align: center; padding: 1rem; background: rgba(245,158,11,0.1); border-radius: 12px;">
            <div style="font-size: 2rem; font-weight: 800; color: #f59e0b;">{{ user.profiles|selectattr('status', 'equalto', 'warning')|list|length }}</div>
            <div style="color: var(--muted); font-size: 0.9rem;">Needs Attention</div>
        </div>
        
        <div style="text-align: center; padding: 1rem; background: rgba(239,68,68,0.1); border-radius: 12px;">
            <div style="font-size: 2rem; font-weight: 800; color: #ef4444;">{{ user.profiles|selectattr('status', 'equalto', 'critical')|list|length }}</div>
            <div style="color: var(--muted); font-size: 0.9rem;">Critical</div>
        </div>
    </div>
    
    <div style="color: var(--muted); font-size: 0.9rem;">
        <i class="bi bi-info-circle"></i> Average FYP Score: {{ (user.profiles|map(attribute='fyp_score')|sum / user.profiles|length)|round(1) }}%
    </div>
</div>

<script>
    function showAddAccountModal() {
        alert('Connect TikTok Account feature coming soon!\\n\\nThis will integrate with TikTok\'s OAuth to add real accounts.');
    }
    
    function viewAccountDetails(accountId) {
        alert('Account details view coming soon!\\n\\nAccount ID: ' + accountId);
    }
    
    function editAccount(accountId) {
        alert('Account editing coming soon!\\n\\nAccount ID: ' + accountId);
    }
</script>
'''

ANALYTICS_TEMPLATE = '''
<div class="page-header">
    <h1>Analytics & Insights</h1>
    <p>Deep dive into your performance metrics and trends</p>
</div>

<div style="display: grid; grid-template-columns: 2fr 1fr; gap: 2rem; margin-bottom: 2rem;">
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: