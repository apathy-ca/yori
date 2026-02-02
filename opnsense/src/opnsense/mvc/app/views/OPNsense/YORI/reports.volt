{#
 # Copyright (C) 2026 YORI Project
 # Reports and analytics view
 #}

<script src="{{ cache_safe('/ui/js/chart.min.js') }}"></script>

<div class="content-box">
    <header class="content-box-head">
        <h3>Reports & Analytics</h3>
    </header>
    <div class="content-box-main">
        <!-- Report Controls -->
        <div class="row mb-4">
            <div class="col-md-3">
                <label for="report_type">Report Type</label>
                <select id="report_type" class="form-control">
                    <option value="usage">Usage Report</option>
                    <option value="enforcement">Enforcement Report</option>
                    <option value="cost">Cost Report</option>
                </select>
            </div>
            <div class="col-md-2">
                <label for="start_date">Start Date</label>
                <input type="date" id="start_date" class="form-control">
            </div>
            <div class="col-md-2">
                <label for="end_date">End Date</label>
                <input type="date" id="end_date" class="form-control">
            </div>
            <div class="col-md-2">
                <label for="group_by">Group By</label>
                <select id="group_by" class="form-control">
                    <option value="day">Day</option>
                    <option value="week">Week</option>
                    <option value="month">Month</option>
                    <option value="endpoint">Endpoint</option>
                    <option value="device">Device</option>
                </select>
            </div>
            <div class="col-md-3">
                <label>&nbsp;</label>
                <div class="btn-group btn-block">
                    <button class="btn btn-primary" onclick="generateReport()">
                        <i class="fa fa-chart-bar"></i> Generate
                    </button>
                    <button class="btn btn-default dropdown-toggle" data-toggle="dropdown">
                        <i class="fa fa-download"></i> Export <span class="caret"></span>
                    </button>
                    <ul class="dropdown-menu">
                        <li><a href="#" onclick="exportReport('csv')"><i class="fa fa-file-csv"></i> Export CSV</a></li>
                        <li><a href="#" onclick="exportReport('json')"><i class="fa fa-file-code"></i> Export JSON</a></li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Quick Date Range Buttons -->
        <div class="row mb-3">
            <div class="col-md-12">
                <div class="btn-group">
                    <button class="btn btn-xs btn-default" onclick="setDateRange(1)">Today</button>
                    <button class="btn btn-xs btn-default" onclick="setDateRange(7)">Last 7 Days</button>
                    <button class="btn btn-xs btn-default active" onclick="setDateRange(30)">Last 30 Days</button>
                    <button class="btn btn-xs btn-default" onclick="setDateRange(90)">Last 90 Days</button>
                    <button class="btn btn-xs btn-default" onclick="setDateRange(365)">Last Year</button>
                </div>
            </div>
        </div>

        <!-- Report Display Area -->
        <div id="reportContent">
            <!-- Usage Report -->
            <div id="usageReport" class="report-section">
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="panel panel-info">
                            <div class="panel-heading">Total Requests</div>
                            <div class="panel-body text-center"><h3 id="usage_requests">-</h3></div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="panel panel-success">
                            <div class="panel-heading">Total Tokens</div>
                            <div class="panel-body text-center"><h3 id="usage_tokens">-</h3></div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="panel panel-warning">
                            <div class="panel-heading">Avg Per Request</div>
                            <div class="panel-body text-center"><h3 id="usage_avg">-</h3></div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="panel panel-danger">
                            <div class="panel-heading">Total Cost</div>
                            <div class="panel-body text-center"><h3 id="usage_cost">-</h3></div>
                        </div>
                    </div>
                </div>
                <div class="panel panel-default">
                    <div class="panel-heading">Usage Trend</div>
                    <div class="panel-body">
                        <canvas id="usageChart" height="150"></canvas>
                    </div>
                </div>
            </div>

            <!-- Enforcement Report -->
            <div id="enforcementReport" class="report-section" style="display: none;">
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="panel panel-info">
                            <div class="panel-heading">Total Evaluated</div>
                            <div class="panel-body text-center"><h3 id="enf_total">-</h3></div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="panel panel-success">
                            <div class="panel-heading">Allowed</div>
                            <div class="panel-body text-center"><h3 id="enf_allowed">-</h3></div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="panel panel-warning">
                            <div class="panel-heading">Alerts</div>
                            <div class="panel-body text-center"><h3 id="enf_alerts">-</h3></div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="panel panel-danger">
                            <div class="panel-heading">Blocked</div>
                            <div class="panel-body text-center"><h3 id="enf_blocked">-</h3></div>
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="panel panel-default">
                            <div class="panel-heading">Enforcement Actions Over Time</div>
                            <div class="panel-body">
                                <canvas id="enforcementChart" height="200"></canvas>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="panel panel-default">
                            <div class="panel-heading">Actions by Policy</div>
                            <div class="panel-body">
                                <canvas id="policyChart" height="200"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Cost Report -->
            <div id="costReport" class="report-section" style="display: none;">
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="panel panel-info">
                            <div class="panel-heading">Total Cost</div>
                            <div class="panel-body text-center"><h3 id="cost_total">-</h3></div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="panel panel-success">
                            <div class="panel-heading">Daily Average</div>
                            <div class="panel-body text-center"><h3 id="cost_daily_avg">-</h3></div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="panel panel-warning">
                            <div class="panel-heading">Highest Day</div>
                            <div class="panel-body text-center"><h3 id="cost_peak">-</h3></div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="panel panel-default">
                            <div class="panel-heading">Cost Per Request</div>
                            <div class="panel-body text-center"><h3 id="cost_per_request">-</h3></div>
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-8">
                        <div class="panel panel-default">
                            <div class="panel-heading">Cost Over Time</div>
                            <div class="panel-body">
                                <canvas id="costTimeChart" height="150"></canvas>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="panel panel-default">
                            <div class="panel-heading">Cost by Endpoint</div>
                            <div class="panel-body">
                                <canvas id="costEndpointChart" height="200"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Data Table -->
        <div class="panel panel-default mt-4">
            <div class="panel-heading">
                <h4 class="panel-title">Report Data</h4>
            </div>
            <div class="panel-body">
                <table class="table table-striped table-hover" id="reportTable">
                    <thead id="reportTableHead"></thead>
                    <tbody id="reportTableBody">
                        <tr><td colspan="6" class="text-center">Select a report type and click Generate</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script>
var charts = {};

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function formatCost(cents) {
    return '$' + (cents / 100).toFixed(2);
}

function setDateRange(days) {
    var end = new Date();
    var start = new Date();
    start.setDate(start.getDate() - days);

    $('#start_date').val(start.toISOString().split('T')[0]);
    $('#end_date').val(end.toISOString().split('T')[0]);

    $('.btn-group .btn').removeClass('active');
    $(event.target).addClass('active');
}

function generateReport() {
    var reportType = $('#report_type').val();
    var startDate = $('#start_date').val();
    var endDate = $('#end_date').val();
    var groupBy = $('#group_by').val();

    // Show appropriate report section
    $('.report-section').hide();
    $('#' + reportType + 'Report').show();

    // Load report data
    var endpoint = '/api/yori/report/' + reportType;
    $.ajax({
        url: endpoint,
        method: 'GET',
        data: {
            start_date: startDate,
            end_date: endDate,
            group_by: groupBy
        },
        success: function(response) {
            if (response.result === 'success' && response.report) {
                renderReport(reportType, response.report);
            } else {
                alert('Failed to generate report');
            }
        },
        error: function() {
            alert('Error generating report');
        }
    });
}

function renderReport(type, data) {
    switch(type) {
        case 'usage':
            renderUsageReport(data);
            break;
        case 'enforcement':
            renderEnforcementReport(data);
            break;
        case 'cost':
            renderCostReport(data);
            break;
    }
}

function renderUsageReport(data) {
    // Summary cards
    $('#usage_requests').text(formatNumber(data.total_requests || 0));
    $('#usage_tokens').text(formatNumber(data.total_tokens || 0));
    $('#usage_avg').text(formatNumber(data.avg_tokens_per_request || 0));
    $('#usage_cost').text(formatCost(data.total_cost_cents || 0));

    // Chart
    var ctx = document.getElementById('usageChart').getContext('2d');
    if (charts.usage) charts.usage.destroy();

    var breakdown = data.breakdown || [];
    charts.usage = new Chart(ctx, {
        type: 'line',
        data: {
            labels: breakdown.map(function(d) { return d.period || d.date; }),
            datasets: [{
                label: 'Requests',
                data: breakdown.map(function(d) { return d.requests || 0; }),
                borderColor: '#3498db',
                yAxisID: 'requests'
            }, {
                label: 'Tokens',
                data: breakdown.map(function(d) { return d.tokens || 0; }),
                borderColor: '#2ecc71',
                yAxisID: 'tokens'
            }]
        },
        options: {
            responsive: true,
            scales: {
                requests: { position: 'left', beginAtZero: true },
                tokens: { position: 'right', beginAtZero: true, grid: { drawOnChartArea: false } }
            }
        }
    });

    // Table
    renderTable(['Period', 'Requests', 'Tokens', 'Cost'], breakdown.map(function(d) {
        return [d.period || d.date, d.requests || 0, formatNumber(d.tokens || 0), formatCost(d.cost_cents || 0)];
    }));
}

function renderEnforcementReport(data) {
    // Summary cards
    $('#enf_total').text(formatNumber(data.total_evaluated || 0));
    $('#enf_allowed').text(formatNumber(data.allowed || 0));
    $('#enf_alerts').text(formatNumber(data.alerts || 0));
    $('#enf_blocked').text(formatNumber(data.blocked || 0));

    // Enforcement over time chart
    var ctx = document.getElementById('enforcementChart').getContext('2d');
    if (charts.enforcement) charts.enforcement.destroy();

    var byTime = data.by_time || [];
    charts.enforcement = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: byTime.map(function(d) { return d.date; }),
            datasets: [{
                label: 'Allowed',
                data: byTime.map(function(d) { return d.allowed || 0; }),
                backgroundColor: '#2ecc71'
            }, {
                label: 'Alerts',
                data: byTime.map(function(d) { return d.alerts || 0; }),
                backgroundColor: '#f39c12'
            }, {
                label: 'Blocked',
                data: byTime.map(function(d) { return d.blocked || 0; }),
                backgroundColor: '#e74c3c'
            }]
        },
        options: {
            responsive: true,
            scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } }
        }
    });

    // Policy chart
    var policyCtx = document.getElementById('policyChart').getContext('2d');
    if (charts.policy) charts.policy.destroy();

    var byPolicy = data.by_policy || [];
    charts.policy = new Chart(policyCtx, {
        type: 'doughnut',
        data: {
            labels: byPolicy.map(function(p) { return p.policy; }),
            datasets: [{
                data: byPolicy.map(function(p) { return p.count || 0; }),
                backgroundColor: ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c']
            }]
        },
        options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });

    // Table
    renderTable(['Date', 'Allowed', 'Alerts', 'Blocked', 'Total'], byTime.map(function(d) {
        return [d.date, d.allowed || 0, d.alerts || 0, d.blocked || 0, (d.allowed || 0) + (d.alerts || 0) + (d.blocked || 0)];
    }));
}

function renderCostReport(data) {
    // Summary cards
    $('#cost_total').text(formatCost(data.total_cost_cents || 0));
    $('#cost_daily_avg').text(formatCost(data.avg_daily_cost_cents || 0));
    $('#cost_peak').text(formatCost(data.peak_day_cost_cents || 0));
    $('#cost_per_request').text((data.avg_cost_per_request_cents || 0).toFixed(3) + 'c');

    // Cost over time chart
    var ctx = document.getElementById('costTimeChart').getContext('2d');
    if (charts.costTime) charts.costTime.destroy();

    var byDay = data.by_day || [];
    charts.costTime = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: byDay.map(function(d) { return d.date; }),
            datasets: [{
                label: 'Daily Cost ($)',
                data: byDay.map(function(d) { return (d.cost_cents || 0) / 100; }),
                backgroundColor: 'rgba(52, 152, 219, 0.7)'
            }]
        },
        options: {
            responsive: true,
            scales: { y: { beginAtZero: true, ticks: { callback: function(v) { return '$' + v.toFixed(2); } } } }
        }
    });

    // Cost by endpoint chart
    var endpointCtx = document.getElementById('costEndpointChart').getContext('2d');
    if (charts.costEndpoint) charts.costEndpoint.destroy();

    var byEndpoint = data.by_endpoint || [];
    charts.costEndpoint = new Chart(endpointCtx, {
        type: 'pie',
        data: {
            labels: byEndpoint.map(function(e) { return e.endpoint.replace('api.', '').replace('.com', ''); }),
            datasets: [{
                data: byEndpoint.map(function(e) { return e.cost_cents || 0; }),
                backgroundColor: ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6']
            }]
        },
        options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });

    // Table
    renderTable(['Date', 'Requests', 'Tokens', 'Cost'], byDay.map(function(d) {
        return [d.date, d.requests || 0, formatNumber(d.tokens || 0), formatCost(d.cost_cents || 0)];
    }));
}

function renderTable(headers, rows) {
    var thead = $('#reportTableHead');
    var tbody = $('#reportTableBody');

    thead.html('<tr>' + headers.map(function(h) { return '<th>' + h + '</th>'; }).join('') + '</tr>');
    tbody.empty();

    if (rows.length === 0) {
        tbody.html('<tr><td colspan="' + headers.length + '" class="text-center">No data available</td></tr>');
        return;
    }

    rows.forEach(function(row) {
        tbody.append('<tr>' + row.map(function(cell) { return '<td>' + cell + '</td>'; }).join('') + '</tr>');
    });
}

function exportReport(format) {
    var reportType = $('#report_type').val();
    var startDate = $('#start_date').val();
    var endDate = $('#end_date').val();

    var url = '/api/yori/report/export' + format.charAt(0).toUpperCase() + format.slice(1);
    url += '?type=' + reportType + '&start_date=' + startDate + '&end_date=' + endDate;

    $.ajax({
        url: url,
        method: 'GET',
        success: function(response) {
            if (response.result === 'success' && response.content) {
                var blob = new Blob([response.content], { type: format === 'csv' ? 'text/csv' : 'application/json' });
                var link = document.createElement('a');
                link.href = window.URL.createObjectURL(blob);
                link.download = response.filename || ('report.' + format);
                link.click();
            } else {
                alert('Failed to export report');
            }
        },
        error: function() {
            alert('Error exporting report');
        }
    });
}

$('#report_type').change(function() {
    var type = $(this).val();
    // Update group_by options based on report type
    var groupBySelect = $('#group_by');
    groupBySelect.find('option').show();

    if (type === 'enforcement') {
        groupBySelect.find('option[value="endpoint"]').hide();
    }
});

$(document).ready(function() {
    // Set default date range (last 30 days)
    setDateRange(30);
});
</script>
