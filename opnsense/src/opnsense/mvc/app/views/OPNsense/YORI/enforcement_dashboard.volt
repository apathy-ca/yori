{#
YORI Enforcement Dashboard
Displays enforcement statistics, recent blocks, and override activity
#}

<div class="content-box" style="padding-bottom: 1.5em;">
    <h1>{{ lang._('Enforcement Dashboard') }}</h1>

    <!-- Enforcement Status Widget -->
    <div class="row">
        <div class="col-md-12">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <h3 class="panel-title">
                        <i class="fa fa-shield"></i> {{ lang._('Enforcement Status') }}
                    </h3>
                </div>
                <div class="panel-body">
                    <div class="row">
                        <div class="col-md-6">
                            <dl class="dl-horizontal">
                                <dt>{{ lang._('Mode') }}</dt>
                                <dd id="enforcement-mode">
                                    <span class="badge" id="mode-badge">Loading...</span>
                                </dd>
                                <dt>{{ lang._('Status') }}</dt>
                                <dd id="enforcement-status">
                                    <i class="fa fa-circle text-success"></i> Active
                                </dd>
                            </dl>
                        </div>
                        <div class="col-md-6">
                            <dl class="dl-horizontal">
                                <dt>{{ lang._('Last Updated') }}</dt>
                                <dd id="last-updated">{{ "now"|date("Y-m-d H:i:s") }}</dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Statistics Row -->
    <div class="row">
        <!-- Blocks Widget -->
        <div class="col-md-3">
            <div class="panel panel-danger">
                <div class="panel-heading">
                    <h3 class="panel-title">
                        <i class="fa fa-ban"></i> {{ lang._('Blocks (24h)') }}
                    </h3>
                </div>
                <div class="panel-body text-center">
                    <h2 id="total-blocks" class="text-danger">0</h2>
                    <small class="text-muted">{{ lang._('Requests Blocked') }}</small>
                </div>
            </div>
        </div>

        <!-- Overrides Widget -->
        <div class="col-md-3">
            <div class="panel panel-warning">
                <div class="panel-heading">
                    <h3 class="panel-title">
                        <i class="fa fa-unlock"></i> {{ lang._('Overrides (24h)') }}
                    </h3>
                </div>
                <div class="panel-body text-center">
                    <h2 id="total-overrides" class="text-warning">0</h2>
                    <small class="text-muted" id="override-rate">Success rate: 0%</small>
                </div>
            </div>
        </div>

        <!-- Bypasses Widget -->
        <div class="col-md-3">
            <div class="panel panel-info">
                <div class="panel-heading">
                    <h3 class="panel-title">
                        <i class="fa fa-arrow-right"></i> {{ lang._('Bypasses (24h)') }}
                    </h3>
                </div>
                <div class="panel-body text-center">
                    <h2 id="total-bypasses" class="text-info">0</h2>
                    <small class="text-muted">{{ lang._('Allowlist Bypasses') }}</small>
                </div>
            </div>
        </div>

        <!-- Alerts Widget -->
        <div class="col-md-3">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <h3 class="panel-title">
                        <i class="fa fa-exclamation-triangle"></i> {{ lang._('Alerts (24h)') }}
                    </h3>
                </div>
                <div class="panel-body text-center">
                    <h2 id="total-alerts" class="text-muted">0</h2>
                    <small class="text-muted">{{ lang._('Advisory Alerts') }}</small>
                </div>
            </div>
        </div>
    </div>

    <!-- Recent Blocks Widget -->
    <div class="row">
        <div class="col-md-8">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <h3 class="panel-title">
                        <i class="fa fa-list"></i> {{ lang._('Recent Blocks') }}
                    </h3>
                </div>
                <div class="panel-body">
                    <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                        <table class="table table-striped table-condensed">
                            <thead>
                                <tr>
                                    <th>{{ lang._('Time') }}</th>
                                    <th>{{ lang._('Client') }}</th>
                                    <th>{{ lang._('Policy') }}</th>
                                    <th>{{ lang._('Reason') }}</th>
                                    <th>{{ lang._('Action') }}</th>
                                </tr>
                            </thead>
                            <tbody id="recent-blocks-tbody">
                                <tr>
                                    <td colspan="5" class="text-center text-muted">
                                        {{ lang._('Loading...') }}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="text-center">
                        <a href="/ui/yori/enforcement/timeline" class="btn btn-primary btn-sm">
                            <i class="fa fa-clock-o"></i> {{ lang._('View Full Timeline') }}
                        </a>
                    </div>
                </div>
            </div>
        </div>

        <!-- Top Blocking Policies Widget -->
        <div class="col-md-4">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <h3 class="panel-title">
                        <i class="fa fa-bar-chart"></i> {{ lang._('Top Blocking Policies') }}
                    </h3>
                </div>
                <div class="panel-body">
                    <ul class="list-group" id="top-policies-list">
                        <li class="list-group-item text-center text-muted">
                            {{ lang._('Loading...') }}
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <!-- Actions -->
    <div class="row">
        <div class="col-md-12">
            <div class="btn-group" role="group">
                <a href="/ui/yori/enforcement/timeline" class="btn btn-default">
                    <i class="fa fa-clock-o"></i> {{ lang._('View Timeline') }}
                </a>
                <a href="/ui/yori/enforcement/report" class="btn btn-default">
                    <i class="fa fa-file-text-o"></i> {{ lang._('Generate Report') }}
                </a>
                <button class="btn btn-primary" id="refresh-dashboard">
                    <i class="fa fa-refresh"></i> {{ lang._('Refresh') }}
                </button>
            </div>
        </div>
    </div>
</div>

<script>
$(document).ready(function() {
    // Load enforcement dashboard data
    function loadDashboardData() {
        $.ajax({
            url: '/api/yori/enforcement/stats',
            type: 'GET',
            success: function(data) {
                if (data && data.summary) {
                    // Update summary statistics
                    $('#total-blocks').text(data.summary.total_blocks || 0);
                    $('#total-overrides').text(data.summary.total_overrides || 0);
                    $('#total-bypasses').text(data.summary.total_bypasses || 0);
                    $('#total-alerts').text(data.summary.total_alerts || 0);

                    // Update override rate
                    var rate = data.summary.override_success_rate || 0;
                    $('#override-rate').text('Success rate: ' + rate + '%');

                    // Update mode badge
                    var mode = data.mode || 'observe';
                    var badgeClass = mode === 'enforce' ? 'badge-danger' :
                                   mode === 'advisory' ? 'badge-warning' : 'badge-info';
                    $('#mode-badge').removeClass().addClass('badge ' + badgeClass)
                                   .text(mode.charAt(0).toUpperCase() + mode.slice(1));
                }
            },
            error: function() {
                console.error('Failed to load dashboard data');
            }
        });
    }

    // Load recent blocks
    function loadRecentBlocks() {
        $.ajax({
            url: '/api/yori/enforcement/recent_blocks',
            type: 'GET',
            success: function(data) {
                if (data && data.blocks) {
                    var tbody = $('#recent-blocks-tbody');
                    tbody.empty();

                    if (data.blocks.length === 0) {
                        tbody.append('<tr><td colspan="5" class="text-center text-muted">No blocks in the last 24 hours</td></tr>');
                    } else {
                        data.blocks.forEach(function(block) {
                            var time = new Date(block.timestamp).toLocaleTimeString();
                            var actionClass = block.enforcement_action === 'override' ? 'text-warning' : 'text-danger';
                            var actionIcon = block.enforcement_action === 'override' ? 'fa-unlock' : 'fa-ban';
                            var actionText = block.enforcement_action === 'override' ? 'Override' : 'Blocked';

                            var row = '<tr>' +
                                '<td>' + time + '</td>' +
                                '<td>' + (block.client_device || block.client_ip) + '</td>' +
                                '<td>' + (block.policy_name || 'N/A') + '</td>' +
                                '<td>' + (block.reason || 'No reason') + '</td>' +
                                '<td class="' + actionClass + '"><i class="fa ' + actionIcon + '"></i> ' + actionText + '</td>' +
                                '</tr>';
                            tbody.append(row);
                        });
                    }
                }
            },
            error: function() {
                console.error('Failed to load recent blocks');
            }
        });
    }

    // Load top policies
    function loadTopPolicies() {
        $.ajax({
            url: '/api/yori/enforcement/top_policies',
            type: 'GET',
            success: function(data) {
                if (data && data.policies) {
                    var list = $('#top-policies-list');
                    list.empty();

                    if (data.policies.length === 0) {
                        list.append('<li class="list-group-item text-center text-muted">No blocking policies active</li>');
                    } else {
                        data.policies.forEach(function(policy, index) {
                            var item = '<li class="list-group-item">' +
                                '<span class="badge">' + policy.block_count + '</span>' +
                                '<strong>' + (index + 1) + '.</strong> ' + policy.policy_name +
                                '<br><small class="text-muted">' + policy.affected_clients + ' clients affected</small>' +
                                '</li>';
                            list.append(item);
                        });
                    }
                }
            },
            error: function() {
                console.error('Failed to load top policies');
            }
        });
    }

    // Auto-refresh every 30 seconds
    function refreshAll() {
        loadDashboardData();
        loadRecentBlocks();
        loadTopPolicies();
        $('#last-updated').text(new Date().toLocaleString());
    }

    // Initial load
    refreshAll();

    // Auto-refresh
    setInterval(refreshAll, 30000);

    // Manual refresh button
    $('#refresh-dashboard').click(function() {
        refreshAll();
        $(this).find('i').addClass('fa-spin');
        setTimeout(function() {
            $('#refresh-dashboard i').removeClass('fa-spin');
        }, 1000);
    });
});
</script>
