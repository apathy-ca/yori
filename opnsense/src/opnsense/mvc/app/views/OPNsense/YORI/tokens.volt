{#
 # Copyright (C) 2026 YORI Project
 # Token usage tracking view
 #}

<script src="{{ cache_safe('/ui/js/chart.min.js') }}"></script>

<div class="content-box">
    <header class="content-box-head">
        <h3>Token Usage Tracking</h3>
    </header>
    <div class="content-box-main">
        <!-- Date Range Selector -->
        <div class="row mb-3">
            <div class="col-md-3">
                <label for="token_days">Time Period</label>
                <select id="token_days" class="form-control">
                    <option value="1">Today</option>
                    <option value="7" selected>Last 7 Days</option>
                    <option value="14">Last 14 Days</option>
                    <option value="30">Last 30 Days</option>
                    <option value="90">Last 90 Days</option>
                </select>
            </div>
            <div class="col-md-3">
                <label for="token_client">Device Filter</label>
                <select id="token_client" class="form-control">
                    <option value="">All Devices</option>
                </select>
            </div>
            <div class="col-md-3">
                <label>&nbsp;</label>
                <button class="btn btn-primary btn-block" onclick="loadTokenStats()">
                    <i class="fa fa-refresh"></i> Refresh
                </button>
            </div>
        </div>

        <!-- Summary Cards -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="panel panel-info">
                    <div class="panel-heading">
                        <h4 class="panel-title">Total Requests</h4>
                    </div>
                    <div class="panel-body text-center">
                        <h2 id="total_requests">-</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="panel panel-success">
                    <div class="panel-heading">
                        <h4 class="panel-title">Input Tokens</h4>
                    </div>
                    <div class="panel-body text-center">
                        <h2 id="input_tokens">-</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="panel panel-warning">
                    <div class="panel-heading">
                        <h4 class="panel-title">Output Tokens</h4>
                    </div>
                    <div class="panel-body text-center">
                        <h2 id="output_tokens">-</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="panel panel-danger">
                    <div class="panel-heading">
                        <h4 class="panel-title">Estimated Cost</h4>
                    </div>
                    <div class="panel-body text-center">
                        <h2 id="total_cost">-</h2>
                    </div>
                </div>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="row mb-4">
            <div class="col-md-8">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">Token Usage Over Time</h4>
                    </div>
                    <div class="panel-body">
                        <canvas id="tokenChart" height="200"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">By Endpoint</h4>
                    </div>
                    <div class="panel-body">
                        <canvas id="endpointChart" height="200"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Device Usage Table -->
        <div class="panel panel-default">
            <div class="panel-heading">
                <h4 class="panel-title">Usage by Device</h4>
            </div>
            <div class="panel-body">
                <table class="table table-striped table-hover" id="deviceTable">
                    <thead>
                        <tr>
                            <th>Device IP</th>
                            <th>Requests</th>
                            <th>Tokens</th>
                            <th>Cost</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="deviceTableBody">
                        <tr>
                            <td colspan="5" class="text-center">Loading...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Endpoint Usage Table -->
        <div class="panel panel-default">
            <div class="panel-heading">
                <h4 class="panel-title">Usage by Endpoint</h4>
            </div>
            <div class="panel-body">
                <table class="table table-striped table-hover">
                    <thead>
                        <tr>
                            <th>Endpoint</th>
                            <th>Requests</th>
                            <th>Tokens</th>
                            <th>Cost</th>
                        </tr>
                    </thead>
                    <tbody id="endpointTableBody">
                        <tr>
                            <td colspan="4" class="text-center">Loading...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script>
var tokenChart = null;
var endpointChart = null;

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function formatCost(cents) {
    return '$' + (cents / 100).toFixed(2);
}

function loadTokenStats() {
    var days = $('#token_days').val();
    var clientIp = $('#token_client').val();

    $.ajax({
        url: '/api/yori/token/stats',
        method: 'GET',
        data: { days: days, client_ip: clientIp },
        success: function(response) {
            if (response.result === 'success' && response.stats) {
                updateSummary(response.stats);
                updateCharts(response.stats);
                updateEndpointTable(response.stats.by_endpoint || []);
            }
        },
        error: function() {
            console.error('Failed to load token stats');
        }
    });

    loadDeviceUsage(days);
}

function loadDeviceUsage(days) {
    $.ajax({
        url: '/api/yori/token/devices',
        method: 'GET',
        data: { days: days },
        success: function(response) {
            if (response.result === 'success') {
                updateDeviceTable(response.devices || []);
                updateDeviceFilter(response.devices || []);
            }
        }
    });
}

function updateSummary(stats) {
    $('#total_requests').text(formatNumber(stats.total_requests || 0));
    $('#input_tokens').text(formatNumber(stats.total_input_tokens || 0));
    $('#output_tokens').text(formatNumber(stats.total_output_tokens || 0));
    $('#total_cost').text(formatCost(stats.total_cost_cents || 0));
}

function updateCharts(stats) {
    var byDay = stats.by_day || [];

    // Token usage over time
    var ctx = document.getElementById('tokenChart').getContext('2d');
    if (tokenChart) {
        tokenChart.destroy();
    }
    tokenChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: byDay.map(function(d) { return d.date; }),
            datasets: [{
                label: 'Tokens',
                data: byDay.map(function(d) { return d.tokens || 0; }),
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                fill: true
            }, {
                label: 'Cost (cents)',
                data: byDay.map(function(d) { return d.cost_cents || 0; }),
                borderColor: '#e74c3c',
                backgroundColor: 'rgba(231, 76, 60, 0.1)',
                fill: true,
                yAxisID: 'cost'
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    position: 'left'
                },
                cost: {
                    beginAtZero: true,
                    position: 'right',
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });

    // Endpoint pie chart
    var byEndpoint = stats.by_endpoint || [];
    var endpointCtx = document.getElementById('endpointChart').getContext('2d');
    if (endpointChart) {
        endpointChart.destroy();
    }
    endpointChart = new Chart(endpointCtx, {
        type: 'doughnut',
        data: {
            labels: byEndpoint.map(function(e) {
                return e.endpoint.replace('api.', '').replace('.com', '');
            }),
            datasets: [{
                data: byEndpoint.map(function(e) { return e.cost_cents || 0; }),
                backgroundColor: ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6']
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}

function updateDeviceTable(devices) {
    var tbody = $('#deviceTableBody');
    tbody.empty();

    if (devices.length === 0) {
        tbody.append('<tr><td colspan="5" class="text-center">No data available</td></tr>');
        return;
    }

    devices.forEach(function(device) {
        tbody.append(
            '<tr>' +
            '<td>' + device.client_ip + '</td>' +
            '<td>' + formatNumber(device.requests || 0) + '</td>' +
            '<td>' + formatNumber(device.tokens || 0) + '</td>' +
            '<td>' + formatCost(device.cost_cents || 0) + '</td>' +
            '<td><button class="btn btn-xs btn-default" onclick="filterByDevice(\'' + device.client_ip + '\')"><i class="fa fa-filter"></i></button></td>' +
            '</tr>'
        );
    });
}

function updateEndpointTable(endpoints) {
    var tbody = $('#endpointTableBody');
    tbody.empty();

    if (endpoints.length === 0) {
        tbody.append('<tr><td colspan="4" class="text-center">No data available</td></tr>');
        return;
    }

    endpoints.forEach(function(endpoint) {
        tbody.append(
            '<tr>' +
            '<td>' + endpoint.endpoint + '</td>' +
            '<td>' + formatNumber(endpoint.requests || 0) + '</td>' +
            '<td>' + formatNumber(endpoint.tokens || 0) + '</td>' +
            '<td>' + formatCost(endpoint.cost_cents || 0) + '</td>' +
            '</tr>'
        );
    });
}

function updateDeviceFilter(devices) {
    var select = $('#token_client');
    var currentVal = select.val();
    select.find('option:not(:first)').remove();

    devices.forEach(function(device) {
        select.append('<option value="' + device.client_ip + '">' + device.client_ip + '</option>');
    });

    if (currentVal) {
        select.val(currentVal);
    }
}

function filterByDevice(ip) {
    $('#token_client').val(ip);
    loadTokenStats();
}

$(document).ready(function() {
    loadTokenStats();

    $('#token_days').change(function() {
        loadTokenStats();
    });

    // Auto-refresh every 60 seconds
    setInterval(loadTokenStats, 60000);
});
</script>
