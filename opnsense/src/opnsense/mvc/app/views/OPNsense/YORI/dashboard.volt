{#
    Copyright (C) 2026 YORI Project
    All rights reserved.

    YORI Dashboard - Main overview page
#}

<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>

<script>
    var hourlyChart = null;
    var endpointChart = null;

    $(document).ready(function() {
        loadDashboard();

        // Auto-refresh every 30 seconds
        setInterval(loadDashboard, 30000);
    });

    function loadDashboard() {
        loadServiceStatus();
        loadStats();
        loadHourlyChart();
        loadEndpointChart();
        loadTopDevices();
        loadRecentEvents();
    }

    function loadServiceStatus() {
        $.ajax({
            url: '/api/yori/enforcement/status',
            method: 'GET',
            success: function(response) {
                var status = 'Unknown';
                var statusClass = 'default';

                if (response.mode === 'enforce' && response.enforcement_active) {
                    status = 'Enforcing';
                    statusClass = 'danger';
                } else if (response.mode === 'advisory') {
                    status = 'Advisory';
                    statusClass = 'warning';
                } else if (response.mode === 'observe') {
                    status = 'Observing';
                    statusClass = 'info';
                }

                $('#serviceStatus').html('<span class="label label-' + statusClass + '">' + status + '</span>');
                $('#currentMode').text(response.mode || 'observe');
                $('#policiesConfigured').text(response.policies_configured || 0);
            }
        });
    }

    function loadStats() {
        $.ajax({
            url: '/api/yori/audit/stats',
            method: 'GET',
            success: function(response) {
                if (response.result === 'success') {
                    $('#requestsToday').text(response.stats.requests_today);
                    $('#requestsWeek').text(response.stats.requests_week);
                    $('#requestsMonth').text(response.stats.requests_month);
                    $('#blocksToday').text(response.stats.blocks_today);
                    $('#alertsToday').text(response.stats.alerts_today);
                    $('#totalRequests').text(response.stats.total_requests);
                }
            }
        });
    }

    function loadHourlyChart() {
        $.ajax({
            url: '/api/yori/audit/hourly?days=1',
            method: 'GET',
            success: function(response) {
                if (response.result === 'success') {
                    renderHourlyChart(response.hourly);
                }
            }
        });
    }

    function renderHourlyChart(data) {
        var ctx = document.getElementById('hourlyChart').getContext('2d');

        var labels = data.map(function(d) {
            return d.hour.substring(11, 16); // HH:MM
        });
        var values = data.map(function(d) {
            return d.count;
        });

        if (hourlyChart) {
            hourlyChart.destroy();
        }

        hourlyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Requests',
                    data: values,
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    function loadEndpointChart() {
        $.ajax({
            url: '/api/yori/audit/endpoints?days=7',
            method: 'GET',
            success: function(response) {
                if (response.result === 'success') {
                    renderEndpointChart(response.endpoints);
                }
            }
        });
    }

    function renderEndpointChart(data) {
        var ctx = document.getElementById('endpointChart').getContext('2d');

        var labels = data.map(function(d) {
            return d.endpoint.replace('api.', '').replace('.com', '');
        });
        var values = data.map(function(d) {
            return d.count;
        });
        var colors = [
            'rgba(255, 99, 132, 0.7)',
            'rgba(54, 162, 235, 0.7)',
            'rgba(255, 206, 86, 0.7)',
            'rgba(75, 192, 192, 0.7)',
            'rgba(153, 102, 255, 0.7)'
        ];

        if (endpointChart) {
            endpointChart.destroy();
        }

        endpointChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors.slice(0, labels.length)
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }

    function loadTopDevices() {
        $.ajax({
            url: '/api/yori/audit/devices?days=7',
            method: 'GET',
            success: function(response) {
                if (response.result === 'success') {
                    var table = $('#devicesTable tbody');
                    table.empty();

                    response.devices.slice(0, 5).forEach(function(d) {
                        var row = '<tr>' +
                            '<td>' + escapeHtml(d.client_ip) + '</td>' +
                            '<td>' + escapeHtml(d.client_device || 'Unknown') + '</td>' +
                            '<td>' + d.count + '</td>' +
                            '</tr>';
                        table.append(row);
                    });

                    if (response.devices.length === 0) {
                        table.append('<tr><td colspan="3" class="text-muted">No data</td></tr>');
                    }
                }
            }
        });
    }

    function loadRecentEvents() {
        $.ajax({
            url: '/api/yori/audit/tail?limit=10',
            method: 'GET',
            success: function(response) {
                if (response.result === 'success') {
                    var table = $('#recentTable tbody');
                    table.empty();

                    response.events.forEach(function(e) {
                        var resultClass = 'default';
                        if (e.policy_result === 'block') resultClass = 'danger';
                        else if (e.policy_result === 'alert') resultClass = 'warning';
                        else if (e.policy_result === 'allow') resultClass = 'success';

                        var row = '<tr>' +
                            '<td>' + escapeHtml(e.timestamp.substring(11, 19)) + '</td>' +
                            '<td>' + escapeHtml(e.client_ip) + '</td>' +
                            '<td>' + escapeHtml(e.endpoint || '') + '</td>' +
                            '<td><span class="label label-' + resultClass + '">' + escapeHtml(e.policy_result || 'allow') + '</span></td>' +
                            '</tr>';
                        table.append(row);
                    });

                    if (response.events.length === 0) {
                        table.append('<tr><td colspan="4" class="text-muted">No recent events</td></tr>');
                    }
                }
            }
        });
    }

    function escapeHtml(text) {
        if (!text) return '';
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
</script>

<div class="content-box">
    <div class="content-box-header">
        <h3><i class="fa fa-shield"></i> YORI Dashboard</h3>
    </div>

    <div class="content-box-main">
        <!-- Status Row -->
        <div class="row">
            <div class="col-md-3">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">Service Status</h4>
                    </div>
                    <div class="panel-body text-center">
                        <div id="serviceStatus" style="font-size: 18px; margin-bottom: 10px;">
                            <span class="label label-default">Loading...</span>
                        </div>
                        <div>Mode: <strong id="currentMode">-</strong></div>
                        <div>Policies: <strong id="policiesConfigured">-</strong></div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="panel panel-info">
                    <div class="panel-heading">
                        <h4 class="panel-title">Today</h4>
                    </div>
                    <div class="panel-body text-center">
                        <div style="font-size: 32px; font-weight: bold;" id="requestsToday">0</div>
                        <div>Requests</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="panel panel-warning">
                    <div class="panel-heading">
                        <h4 class="panel-title">Alerts Today</h4>
                    </div>
                    <div class="panel-body text-center">
                        <div style="font-size: 32px; font-weight: bold;" id="alertsToday">0</div>
                        <div>Alerts</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="panel panel-danger">
                    <div class="panel-heading">
                        <h4 class="panel-title">Blocks Today</h4>
                    </div>
                    <div class="panel-body text-center">
                        <div style="font-size: 32px; font-weight: bold;" id="blocksToday">0</div>
                        <div>Blocked</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="row" style="margin-top: 20px;">
            <div class="col-md-8">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">Requests (Last 24 Hours)</h4>
                    </div>
                    <div class="panel-body">
                        <div style="height: 250px;">
                            <canvas id="hourlyChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">Endpoints (7 Days)</h4>
                    </div>
                    <div class="panel-body">
                        <div style="height: 250px;">
                            <canvas id="endpointChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Data Row -->
        <div class="row" style="margin-top: 20px;">
            <div class="col-md-6">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">Top Devices (7 Days)</h4>
                    </div>
                    <div class="panel-body">
                        <table id="devicesTable" class="table table-striped table-condensed">
                            <thead>
                                <tr>
                                    <th>IP Address</th>
                                    <th>Device</th>
                                    <th>Requests</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr><td colspan="3" class="text-muted">Loading...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">Recent Activity</h4>
                    </div>
                    <div class="panel-body">
                        <table id="recentTable" class="table table-striped table-condensed">
                            <thead>
                                <tr>
                                    <th>Time</th>
                                    <th>Client</th>
                                    <th>Endpoint</th>
                                    <th>Result</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr><td colspan="4" class="text-muted">Loading...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Summary Stats -->
        <div class="row" style="margin-top: 20px;">
            <div class="col-md-12">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">Summary</h4>
                    </div>
                    <div class="panel-body">
                        <div class="row text-center">
                            <div class="col-md-3">
                                <div style="font-size: 24px; font-weight: bold;" id="requestsWeek">0</div>
                                <div class="text-muted">This Week</div>
                            </div>
                            <div class="col-md-3">
                                <div style="font-size: 24px; font-weight: bold;" id="requestsMonth">0</div>
                                <div class="text-muted">This Month</div>
                            </div>
                            <div class="col-md-3">
                                <div style="font-size: 24px; font-weight: bold;" id="totalRequests">0</div>
                                <div class="text-muted">All Time</div>
                            </div>
                            <div class="col-md-3">
                                <a href="/ui/yori/auditlog" class="btn btn-primary">
                                    <i class="fa fa-list"></i> View Full Audit Log
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Quick Links -->
        <div class="row" style="margin-top: 20px;">
            <div class="col-md-12">
                <div class="btn-group" role="group">
                    <a href="/ui/yori/enforcement" class="btn btn-default"><i class="fa fa-gavel"></i> Enforcement</a>
                    <a href="/ui/yori/policies" class="btn btn-default"><i class="fa fa-file-text"></i> Policies</a>
                    <a href="/ui/yori/allowlist" class="btn btn-default"><i class="fa fa-check-circle"></i> Allowlist</a>
                    <a href="/ui/yori/emergency" class="btn btn-default"><i class="fa fa-exclamation-triangle"></i> Emergency</a>
                    <a href="/ui/yori/settings" class="btn btn-default"><i class="fa fa-cog"></i> Settings</a>
                </div>
            </div>
        </div>
    </div>
</div>
