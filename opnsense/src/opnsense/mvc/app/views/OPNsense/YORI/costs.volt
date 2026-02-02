{#
 # Copyright (C) 2026 YORI Project
 # Cost monitoring and budget management view
 #}

<script src="{{ cache_safe('/ui/js/chart.min.js') }}"></script>

<div class="content-box">
    <header class="content-box-head">
        <h3>Cost Monitoring & Budgets</h3>
    </header>
    <div class="content-box-main">
        <!-- Cost Summary Cards -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="panel panel-info">
                    <div class="panel-heading">
                        <h4 class="panel-title">Today's Cost</h4>
                    </div>
                    <div class="panel-body text-center">
                        <h2 id="today_cost">-</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="panel panel-success">
                    <div class="panel-heading">
                        <h4 class="panel-title">This Month</h4>
                    </div>
                    <div class="panel-body text-center">
                        <h2 id="month_cost">-</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="panel panel-warning">
                    <div class="panel-heading">
                        <h4 class="panel-title">Projected Monthly</h4>
                    </div>
                    <div class="panel-body text-center">
                        <h2 id="projected_cost">-</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">Trend</h4>
                    </div>
                    <div class="panel-body text-center">
                        <h2 id="cost_trend">-</h2>
                    </div>
                </div>
            </div>
        </div>

        <!-- Cost Chart -->
        <div class="row mb-4">
            <div class="col-md-12">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">Daily Cost History (Last 30 Days)</h4>
                    </div>
                    <div class="panel-body">
                        <canvas id="costChart" height="100"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Budgets Section -->
        <div class="row">
            <div class="col-md-8">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">
                            Budgets
                            <button class="btn btn-xs btn-success pull-right" onclick="showAddBudgetModal()">
                                <i class="fa fa-plus"></i> Add Budget
                            </button>
                        </h4>
                    </div>
                    <div class="panel-body">
                        <table class="table table-striped" id="budgetTable">
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Type</th>
                                    <th>Target</th>
                                    <th>Daily Limit</th>
                                    <th>Monthly Limit</th>
                                    <th>Alert At</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="budgetTableBody">
                                <tr>
                                    <td colspan="8" class="text-center">Loading...</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">
                            Recent Alerts
                            <button class="btn btn-xs btn-default pull-right" onclick="loadAlerts()">
                                <i class="fa fa-refresh"></i>
                            </button>
                        </h4>
                    </div>
                    <div class="panel-body" style="max-height: 400px; overflow-y: auto;">
                        <div id="alertsList">Loading...</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Add/Edit Budget Modal -->
<div class="modal fade" id="budgetModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal">&times;</button>
                <h4 class="modal-title" id="budgetModalTitle">Add Budget</h4>
            </div>
            <div class="modal-body">
                <form id="budgetForm">
                    <div class="form-group">
                        <label for="budget_name">Budget Name</label>
                        <input type="text" class="form-control" id="budget_name" required>
                    </div>
                    <div class="form-group">
                        <label for="budget_type">Budget Type</label>
                        <select class="form-control" id="budget_type">
                            <option value="global">Global (All Usage)</option>
                            <option value="device">Per Device</option>
                            <option value="endpoint">Per Endpoint</option>
                            <option value="device_endpoint">Device + Endpoint</option>
                        </select>
                    </div>
                    <div class="form-group" id="targetGroup" style="display: none;">
                        <label for="budget_target">Target</label>
                        <input type="text" class="form-control" id="budget_target" placeholder="IP address, endpoint, or IP:endpoint">
                    </div>
                    <div class="form-group">
                        <label for="daily_limit">Daily Limit ($)</label>
                        <input type="number" class="form-control" id="daily_limit" step="0.01" min="0">
                    </div>
                    <div class="form-group">
                        <label for="monthly_limit">Monthly Limit ($)</label>
                        <input type="number" class="form-control" id="monthly_limit" step="0.01" min="0">
                    </div>
                    <div class="form-group">
                        <label for="alert_threshold">Alert Threshold (%)</label>
                        <input type="number" class="form-control" id="alert_threshold" value="80" min="1" max="100">
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-primary" onclick="saveBudget()">Save</button>
            </div>
        </div>
    </div>
</div>

<script>
var costChart = null;

function formatCost(cents) {
    return '$' + (cents / 100).toFixed(2);
}

function loadCostSummary() {
    $.ajax({
        url: '/api/yori/token/costSummary',
        method: 'GET',
        data: { days: 30 },
        success: function(response) {
            if (response.result === 'success' && response.summary) {
                var s = response.summary;
                $('#today_cost').text(formatCost(s.today_cost_cents || 0));
                $('#month_cost').text(formatCost(s.total_cost_cents || 0));
                $('#projected_cost').text(formatCost(s.projected_monthly_cents || 0));

                var trend = s.trend || 'stable';
                var trendPercent = s.trend_percent || 0;
                var trendIcon = trend === 'up' ? 'fa-arrow-up text-danger' :
                               (trend === 'down' ? 'fa-arrow-down text-success' : 'fa-minus text-muted');
                $('#cost_trend').html('<i class="fa ' + trendIcon + '"></i> ' + trendPercent.toFixed(1) + '%');
            }
        }
    });
}

function loadCostChart() {
    $.ajax({
        url: '/api/yori/token/stats',
        method: 'GET',
        data: { days: 30 },
        success: function(response) {
            if (response.result === 'success' && response.stats && response.stats.by_day) {
                var byDay = response.stats.by_day;
                var ctx = document.getElementById('costChart').getContext('2d');

                if (costChart) {
                    costChart.destroy();
                }

                costChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: byDay.map(function(d) { return d.date; }),
                        datasets: [{
                            label: 'Daily Cost ($)',
                            data: byDay.map(function(d) { return (d.cost_cents || 0) / 100; }),
                            backgroundColor: 'rgba(52, 152, 219, 0.7)',
                            borderColor: '#3498db',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) { return '$' + value.toFixed(2); }
                                }
                            }
                        }
                    }
                });
            }
        }
    });
}

function loadBudgets() {
    $.ajax({
        url: '/api/yori/token/budgets',
        method: 'GET',
        success: function(response) {
            var tbody = $('#budgetTableBody');
            tbody.empty();

            if (response.result !== 'success' || !response.budgets || response.budgets.length === 0) {
                tbody.append('<tr><td colspan="8" class="text-center">No budgets configured</td></tr>');
                return;
            }

            response.budgets.forEach(function(budget) {
                var statusBadge = budget.enabled ?
                    '<span class="label label-success">Active</span>' :
                    '<span class="label label-default">Disabled</span>';

                tbody.append(
                    '<tr>' +
                    '<td>' + budget.name + '</td>' +
                    '<td>' + budget.budget_type + '</td>' +
                    '<td>' + (budget.target || '-') + '</td>' +
                    '<td>' + (budget.daily_limit_cents ? formatCost(budget.daily_limit_cents) : '-') + '</td>' +
                    '<td>' + (budget.monthly_limit_cents ? formatCost(budget.monthly_limit_cents) : '-') + '</td>' +
                    '<td>' + budget.alert_threshold_percent + '%</td>' +
                    '<td>' + statusBadge + '</td>' +
                    '<td>' +
                    '<button class="btn btn-xs btn-default" onclick="editBudget(\'' + budget.name + '\')"><i class="fa fa-edit"></i></button> ' +
                    '<button class="btn btn-xs btn-danger" onclick="deleteBudget(\'' + budget.name + '\')"><i class="fa fa-trash"></i></button>' +
                    '</td>' +
                    '</tr>'
                );
            });
        }
    });
}

function loadAlerts() {
    $.ajax({
        url: '/api/yori/token/alerts',
        method: 'GET',
        data: { days: 7, unacknowledged: 0 },
        success: function(response) {
            var container = $('#alertsList');
            container.empty();

            if (response.result !== 'success' || !response.alerts || response.alerts.length === 0) {
                container.html('<p class="text-muted text-center">No recent alerts</p>');
                return;
            }

            response.alerts.forEach(function(alert) {
                var levelClass = alert.alert_level === 'critical' ? 'danger' :
                                (alert.alert_level === 'warning' ? 'warning' : 'info');
                var ackButton = alert.acknowledged ?
                    '<span class="text-muted"><i class="fa fa-check"></i></span>' :
                    '<button class="btn btn-xs btn-default" onclick="acknowledgeAlert(' + alert.id + ')"><i class="fa fa-check"></i></button>';

                container.append(
                    '<div class="alert alert-' + levelClass + ' alert-dismissible" style="padding: 8px; margin-bottom: 8px;">' +
                    '<small>' + alert.timestamp.split('T')[0] + '</small><br>' +
                    '<strong>' + alert.budget_name + '</strong><br>' +
                    '<small>' + alert.message + '</small>' +
                    '<div class="pull-right">' + ackButton + '</div>' +
                    '</div>'
                );
            });
        }
    });
}

function showAddBudgetModal() {
    $('#budgetModalTitle').text('Add Budget');
    $('#budgetForm')[0].reset();
    $('#budget_name').prop('disabled', false);
    $('#targetGroup').hide();
    $('#budgetModal').modal('show');
}

function editBudget(name) {
    // Load budget details and show modal
    $.ajax({
        url: '/api/yori/token/budgets',
        method: 'GET',
        success: function(response) {
            if (response.result === 'success' && response.budgets) {
                var budget = response.budgets.find(function(b) { return b.name === name; });
                if (budget) {
                    $('#budgetModalTitle').text('Edit Budget');
                    $('#budget_name').val(budget.name).prop('disabled', true);
                    $('#budget_type').val(budget.budget_type);
                    $('#budget_target').val(budget.target || '');
                    $('#daily_limit').val(budget.daily_limit_cents ? (budget.daily_limit_cents / 100).toFixed(2) : '');
                    $('#monthly_limit').val(budget.monthly_limit_cents ? (budget.monthly_limit_cents / 100).toFixed(2) : '');
                    $('#alert_threshold').val(budget.alert_threshold_percent || 80);

                    if (budget.budget_type !== 'global') {
                        $('#targetGroup').show();
                    }

                    $('#budgetModal').modal('show');
                }
            }
        }
    });
}

function saveBudget() {
    var data = {
        name: $('#budget_name').val(),
        budget_type: $('#budget_type').val(),
        target: $('#budget_target').val() || null,
        daily_limit_cents: $('#daily_limit').val() ? parseFloat($('#daily_limit').val()) * 100 : null,
        monthly_limit_cents: $('#monthly_limit').val() ? parseFloat($('#monthly_limit').val()) * 100 : null,
        alert_threshold_percent: parseInt($('#alert_threshold').val()) || 80
    };

    $.ajax({
        url: '/api/yori/token/setBudget',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(response) {
            if (response.result === 'success') {
                $('#budgetModal').modal('hide');
                loadBudgets();
            } else {
                alert('Failed to save budget: ' + (response.message || 'Unknown error'));
            }
        },
        error: function() {
            alert('Failed to save budget');
        }
    });
}

function deleteBudget(name) {
    if (!confirm('Delete budget "' + name + '"?')) return;

    $.ajax({
        url: '/api/yori/token/deleteBudget/' + encodeURIComponent(name),
        method: 'POST',
        success: function(response) {
            if (response.result === 'success') {
                loadBudgets();
            } else {
                alert('Failed to delete budget: ' + (response.message || 'Unknown error'));
            }
        }
    });
}

function acknowledgeAlert(id) {
    $.ajax({
        url: '/api/yori/token/acknowledgeAlert/' + id,
        method: 'POST',
        success: function(response) {
            if (response.result === 'success') {
                loadAlerts();
            }
        }
    });
}

$('#budget_type').change(function() {
    if ($(this).val() === 'global') {
        $('#targetGroup').hide();
    } else {
        $('#targetGroup').show();
    }
});

$(document).ready(function() {
    loadCostSummary();
    loadCostChart();
    loadBudgets();
    loadAlerts();

    // Auto-refresh every 5 minutes
    setInterval(function() {
        loadCostSummary();
        loadAlerts();
    }, 300000);
});
</script>
