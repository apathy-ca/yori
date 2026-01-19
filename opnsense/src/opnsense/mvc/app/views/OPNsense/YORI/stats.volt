{#
 # YORI Statistics Summary Page
 # Copyright (c) 2026 YORI Project
 # License: MIT
 #}

<style>
    @import url('/ui/css/yori/dashboard.css');
</style>

<div class="content-box">
    <div class="content-box-main">
        <div class="table-responsive">
            <div class="container-fluid">
                <!-- Page Header -->
                <div class="row mb-4">
                    <div class="col-md-8">
                        <h1 class="page-header">
                            <i class="fa fa-area-chart"></i> Detailed Statistics
                            <small>Comprehensive LLM Usage Analytics</small>
                        </h1>
                    </div>
                    <div class="col-md-4 text-end">
                        <a href="/ui/yori/dashboard" class="btn btn-secondary">
                            <i class="fa fa-dashboard"></i> Back to Dashboard
                        </a>
                    </div>
                </div>

                <!-- Overall Statistics -->
                <div class="row mb-4">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <h5 class="card-title mb-0">
                                    <i class="fa fa-info-circle"></i> Overall Statistics
                                </h5>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-3">
                                        <h6 class="text-muted">Total Requests (All Time)</h6>
                                        <h2 id="stat-total-requests">-</h2>
                                    </div>
                                    <div class="col-md-3">
                                        <h6 class="text-muted">Last 7 Days</h6>
                                        <h2 id="stat-last-7days">-</h2>
                                    </div>
                                    <div class="col-md-3">
                                        <h6 class="text-muted">Last 24 Hours</h6>
                                        <h2 id="stat-last-24h">-</h2>
                                    </div>
                                    <div class="col-md-3">
                                        <h6 class="text-muted">Average Tokens/Request</h6>
                                        <h2 id="stat-avg-tokens">-</h2>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Endpoint Breakdown -->
                <div class="row mb-4">
                    <div class="col-lg-6">
                        <div class="card">
                            <div class="card-header">
                                <h5 class="card-title mb-0">
                                    <i class="fa fa-server"></i> Endpoint Distribution
                                </h5>
                            </div>
                            <div class="card-body">
                                <table class="table table-striped" id="endpoint-stats-table">
                                    <thead>
                                        <tr>
                                            <th>Endpoint</th>
                                            <th class="text-end">Requests</th>
                                            <th class="text-end">Avg Tokens</th>
                                            <th class="text-end">Avg Duration</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td colspan="4" class="text-center">Loading...</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <!-- Device Breakdown -->
                    <div class="col-lg-6">
                        <div class="card">
                            <div class="card-header">
                                <h5 class="card-title mb-0">
                                    <i class="fa fa-laptop"></i> Device Statistics
                                </h5>
                            </div>
                            <div class="card-body">
                                <table class="table table-striped" id="device-stats-table">
                                    <thead>
                                        <tr>
                                            <th>Device</th>
                                            <th>IP Address</th>
                                            <th class="text-end">Requests</th>
                                            <th class="text-end">Last Seen</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td colspan="4" class="text-center">Loading...</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Hourly Heatmap -->
                <div class="row mb-4">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <h5 class="card-title mb-0">
                                    <i class="fa fa-clock-o"></i> Usage by Hour of Day (Last 7 Days)
                                </h5>
                            </div>
                            <div class="card-body">
                                <canvas id="hourly-chart" height="80"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Weekly Trend -->
                <div class="row mb-4">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <h5 class="card-title mb-0">
                                    <i class="fa fa-line-chart"></i> Weekly Trend (Last 30 Days)
                                </h5>
                            </div>
                            <div class="card-body">
                                <div class="alert alert-info">
                                    <i class="fa fa-info-circle"></i> This chart would show daily request trends over the last 30 days. Implementation requires additional API endpoint.
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Policy Activity -->
                <div class="row">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <h5 class="card-title mb-0">
                                    <i class="fa fa-shield"></i> Policy Activity
                                </h5>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-4">
                                        <h6 class="text-muted">Total Alerts</h6>
                                        <h3 id="stat-total-alerts">-</h3>
                                    </div>
                                    <div class="col-md-4">
                                        <h6 class="text-muted">Total Blocks</h6>
                                        <h3 id="stat-total-blocks">-</h3>
                                    </div>
                                    <div class="col-md-4">
                                        <h6 class="text-muted">Alert Rate</h6>
                                        <h3 id="stat-alert-rate">-</h3>
                                    </div>
                                </div>
                                <hr>
                                <table class="table table-sm" id="policy-activity-table">
                                    <thead>
                                        <tr>
                                            <th>Policy Name</th>
                                            <th class="text-end">Triggers</th>
                                            <th>Last Triggered</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td colspan="3" class="text-center text-muted">No policy activity recorded</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Chart.js from CDN -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>

<script>
$(document).ready(function() {
    var hourlyChart = null;

    // Load all statistics
    loadStats();

    function loadStats() {
        loadSummary();
        loadEndpointStats();
        loadDeviceStats();
        loadHourlyDistribution();
        loadPolicyActivity();
    }

    // Load summary statistics
    function loadSummary() {
        $.ajax({
            url: '/api/yori/stats/summary',
            type: 'GET',
            dataType: 'json',
            success: function(response) {
                if (response.status === 'ok') {
                    var data = response.data;
                    $('#stat-total-requests').text(data.total_requests.toLocaleString());
                    $('#stat-last-7days').text(data.last_7days.toLocaleString());
                    $('#stat-last-24h').text(data.last_24h.toLocaleString());
                    $('#stat-avg-tokens').text(data.avg_tokens ? data.avg_tokens.toLocaleString() : 'N/A');
                    $('#stat-total-alerts').text(data.total_alerts.toLocaleString());

                    // Calculate alert rate
                    var alertRate = data.total_requests > 0 ? ((data.total_alerts / data.total_requests) * 100).toFixed(2) : 0;
                    $('#stat-alert-rate').text(alertRate + '%');
                }
            },
            error: function() {
                console.error('Failed to load summary statistics');
            }
        });
    }

    // Load endpoint statistics
    function loadEndpointStats() {
        $.ajax({
            url: '/api/yori/stats/topEndpoints',
            type: 'GET',
            dataType: 'json',
            success: function(response) {
                if (response.status === 'ok') {
                    var tbody = $('#endpoint-stats-table tbody');
                    tbody.empty();

                    if (response.data.length === 0) {
                        tbody.append('<tr><td colspan="4" class="text-center text-muted">No data available</td></tr>');
                        return;
                    }

                    response.data.forEach(function(endpoint) {
                        var avgTokens = endpoint.avg_tokens ? Math.round(endpoint.avg_tokens) : 'N/A';
                        var avgDuration = endpoint.avg_duration_ms ? Math.round(endpoint.avg_duration_ms) + ' ms' : 'N/A';

                        var row = '<tr>' +
                            '<td>' + escapeHtml(endpoint.endpoint) + '</td>' +
                            '<td class="text-end">' + endpoint.count.toLocaleString() + '</td>' +
                            '<td class="text-end">' + avgTokens + '</td>' +
                            '<td class="text-end">' + avgDuration + '</td>' +
                            '</tr>';
                        tbody.append(row);
                    });
                }
            },
            error: function() {
                $('#endpoint-stats-table tbody').html('<tr><td colspan="4" class="text-center text-danger">Error loading data</td></tr>');
            }
        });
    }

    // Load device statistics
    function loadDeviceStats() {
        $.ajax({
            url: '/api/yori/stats/topDevices',
            type: 'GET',
            dataType: 'json',
            success: function(response) {
                if (response.status === 'ok') {
                    var tbody = $('#device-stats-table tbody');
                    tbody.empty();

                    if (response.data.length === 0) {
                        tbody.append('<tr><td colspan="4" class="text-center text-muted">No data available</td></tr>');
                        return;
                    }

                    response.data.forEach(function(device) {
                        var lastSeen = device.last_seen ? new Date(device.last_seen).toLocaleString() : 'N/A';

                        var row = '<tr>' +
                            '<td>' + escapeHtml(device.device) + '</td>' +
                            '<td>' + escapeHtml(device.client_ip) + '</td>' +
                            '<td class="text-end">' + device.count.toLocaleString() + '</td>' +
                            '<td class="text-end"><small>' + lastSeen + '</small></td>' +
                            '</tr>';
                        tbody.append(row);
                    });
                }
            },
            error: function() {
                $('#device-stats-table tbody').html('<tr><td colspan="4" class="text-center text-danger">Error loading data</td></tr>');
            }
        });
    }

    // Load hourly distribution chart
    function loadHourlyDistribution() {
        $.ajax({
            url: '/api/yori/stats/hourlyDistribution',
            type: 'GET',
            dataType: 'json',
            success: function(response) {
                if (response.status === 'ok') {
                    var data = response.data;

                    // Fill in all 24 hours
                    var hourlyData = new Array(24).fill(0);
                    data.forEach(function(item) {
                        var hour = parseInt(item.hour, 10);
                        hourlyData[hour] = item.count;
                    });

                    var labels = [];
                    for (var i = 0; i < 24; i++) {
                        labels.push(i + ':00');
                    }

                    // Destroy existing chart
                    if (hourlyChart) {
                        hourlyChart.destroy();
                    }

                    // Create chart
                    var ctx = document.getElementById('hourly-chart').getContext('2d');
                    hourlyChart = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Requests per Hour',
                                data: hourlyData,
                                backgroundColor: '#198754',
                                borderColor: '#198754',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {
                                legend: {
                                    display: false
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: {
                                        precision: 0
                                    }
                                }
                            }
                        }
                    });
                }
            },
            error: function() {
                console.error('Failed to load hourly distribution');
            }
        });
    }

    // Load policy activity (placeholder - would need additional API endpoint)
    function loadPolicyActivity() {
        // This would require a new API endpoint to get policy-specific statistics
        // For now, showing total blocks from summary
        $.ajax({
            url: '/api/yori/stats/summary',
            type: 'GET',
            dataType: 'json',
            success: function(response) {
                if (response.status === 'ok') {
                    // We don't have separate block count in current schema
                    // This is a placeholder for future implementation
                    $('#stat-total-blocks').text('N/A');
                }
            }
        });
    }

    // Helper: Escape HTML
    function escapeHtml(text) {
        if (!text) return '';
        var map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.toString().replace(/[&<>"']/g, function(m) { return map[m]; });
    }
});
</script>
