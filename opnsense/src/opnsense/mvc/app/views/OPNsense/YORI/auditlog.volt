{#
    Copyright (C) 2026 YORI Project
    All rights reserved.

    YORI Audit Log Viewer
#}

<script>
    var currentPage = 1;
    var totalPages = 1;
    var autoRefresh = false;
    var refreshInterval = null;

    $(document).ready(function() {
        // Initialize date pickers with today's date
        var today = new Date().toISOString().split('T')[0];
        $('#endDate').val(today);

        // Load initial data
        loadAuditLog();

        // Search button
        $('#searchBtn').click(function() {
            currentPage = 1;
            loadAuditLog();
        });

        // Clear filters
        $('#clearBtn').click(function() {
            $('#startDate').val('');
            $('#endDate').val(today);
            $('#endpoint').val('');
            $('#clientIp').val('');
            $('#policyResult').val('');
            $('#searchText').val('');
            currentPage = 1;
            loadAuditLog();
        });

        // Export button
        $('#exportBtn').click(function() {
            exportAuditLog();
        });

        // Auto-refresh toggle
        $('#autoRefreshToggle').change(function() {
            autoRefresh = $(this).prop('checked');
            if (autoRefresh) {
                refreshInterval = setInterval(loadAuditLog, 5000);
            } else if (refreshInterval) {
                clearInterval(refreshInterval);
                refreshInterval = null;
            }
        });

        // Pagination
        $('#prevPage').click(function() {
            if (currentPage > 1) {
                currentPage--;
                loadAuditLog();
            }
        });

        $('#nextPage').click(function() {
            if (currentPage < totalPages) {
                currentPage++;
                loadAuditLog();
            }
        });

        // Enter key in search
        $('#searchText').keypress(function(e) {
            if (e.which === 13) {
                currentPage = 1;
                loadAuditLog();
            }
        });
    });

    function loadAuditLog() {
        var params = {
            page: currentPage,
            limit: 50
        };

        if ($('#startDate').val()) params.start_date = $('#startDate').val();
        if ($('#endDate').val()) params.end_date = $('#endDate').val();
        if ($('#endpoint').val()) params.endpoint = $('#endpoint').val();
        if ($('#clientIp').val()) params.client_ip = $('#clientIp').val();
        if ($('#policyResult').val()) params.policy_result = $('#policyResult').val();
        if ($('#searchText').val()) params.search = $('#searchText').val();

        $.ajax({
            url: '/api/yori/audit/search',
            method: 'GET',
            data: params,
            success: function(response) {
                if (response.result === 'success') {
                    renderTable(response.rows);
                    updatePagination(response);
                } else {
                    showAlert('danger', 'Failed to load audit log: ' + (response.message || 'Unknown error'));
                }
            },
            error: function() {
                showAlert('danger', 'Failed to connect to API');
            }
        });
    }

    function renderTable(rows) {
        var table = $('#auditTable tbody');
        table.empty();

        if (rows.length === 0) {
            table.append('<tr><td colspan="8" class="text-center text-muted">No records found</td></tr>');
            return;
        }

        rows.forEach(function(row) {
            var resultClass = 'default';
            if (row.policy_result === 'block') resultClass = 'danger';
            else if (row.policy_result === 'alert') resultClass = 'warning';
            else if (row.policy_result === 'allow') resultClass = 'success';

            var promptPreview = row.prompt_preview || '';
            if (promptPreview.length > 50) {
                promptPreview = promptPreview.substring(0, 50) + '...';
            }

            var tr = '<tr>' +
                '<td class="nowrap">' + escapeHtml(row.timestamp) + '</td>' +
                '<td>' + escapeHtml(row.client_ip) + '</td>' +
                '<td>' + escapeHtml(row.client_device || '-') + '</td>' +
                '<td>' + escapeHtml(row.endpoint || '-') + '</td>' +
                '<td><code>' + escapeHtml(row.http_method + ' ' + (row.http_path || '')) + '</code></td>' +
                '<td class="prompt-preview" title="' + escapeHtml(row.prompt_preview || '') + '">' +
                    escapeHtml(promptPreview) + '</td>' +
                '<td><span class="label label-' + resultClass + '">' +
                    escapeHtml(row.policy_result || 'allow') + '</span></td>' +
                '<td>' + escapeHtml(row.policy_name || '-') + '</td>' +
                '</tr>';
            table.append(tr);
        });
    }

    function updatePagination(response) {
        totalPages = response.pages || 1;
        $('#currentPage').text(response.page);
        $('#totalPages').text(totalPages);
        $('#totalRecords').text(response.total);

        $('#prevPage').prop('disabled', response.page <= 1);
        $('#nextPage').prop('disabled', response.page >= totalPages);
    }

    function exportAuditLog() {
        var params = new URLSearchParams();

        if ($('#startDate').val()) params.append('start_date', $('#startDate').val());
        if ($('#endDate').val()) params.append('end_date', $('#endDate').val());
        if ($('#endpoint').val()) params.append('endpoint', $('#endpoint').val());
        if ($('#policyResult').val()) params.append('policy_result', $('#policyResult').val());

        $.ajax({
            url: '/api/yori/audit/export?' + params.toString(),
            method: 'GET',
            success: function(response) {
                if (response.result === 'success') {
                    // Download CSV
                    var blob = new Blob([response.csv], { type: 'text/csv' });
                    var url = URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url;
                    a.download = response.filename;
                    a.click();
                    URL.revokeObjectURL(url);
                    showAlert('success', 'Exported ' + response.count + ' records');
                } else {
                    showAlert('danger', 'Export failed: ' + (response.message || 'Unknown error'));
                }
            }
        });
    }

    function showAlert(type, message) {
        var alert = '<div class="alert alert-' + type + ' alert-dismissible" role="alert">' +
            '<button type="button" class="close" data-dismiss="alert"><span>&times;</span></button>' +
            message + '</div>';
        $('#alertArea').html(alert);

        if (type === 'success') {
            setTimeout(function() {
                $('#alertArea .alert').fadeOut();
            }, 3000);
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
</script>

<style>
    .nowrap { white-space: nowrap; }
    .prompt-preview { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    #auditTable { font-size: 12px; }
</style>

<div class="content-box">
    <div id="alertArea"></div>

    <div class="content-box-header">
        <h3><i class="fa fa-list"></i> Audit Log</h3>
    </div>

    <div class="content-box-main">
        <!-- Filters -->
        <div class="panel panel-default">
            <div class="panel-heading">
                <h4 class="panel-title">Filters</h4>
            </div>
            <div class="panel-body">
                <div class="row">
                    <div class="col-md-2">
                        <label>Start Date</label>
                        <input type="date" id="startDate" class="form-control">
                    </div>
                    <div class="col-md-2">
                        <label>End Date</label>
                        <input type="date" id="endDate" class="form-control">
                    </div>
                    <div class="col-md-2">
                        <label>Endpoint</label>
                        <select id="endpoint" class="form-control">
                            <option value="">All</option>
                            <option value="api.openai.com">OpenAI</option>
                            <option value="api.anthropic.com">Anthropic</option>
                            <option value="generativelanguage.googleapis.com">Google</option>
                            <option value="api.mistral.ai">Mistral</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label>Client IP</label>
                        <input type="text" id="clientIp" class="form-control" placeholder="192.168.1.x">
                    </div>
                    <div class="col-md-2">
                        <label>Policy Result</label>
                        <select id="policyResult" class="form-control">
                            <option value="">All</option>
                            <option value="allow">Allow</option>
                            <option value="alert">Alert</option>
                            <option value="block">Block</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label>Search</label>
                        <input type="text" id="searchText" class="form-control" placeholder="Keyword...">
                    </div>
                </div>
                <div class="row" style="margin-top: 10px;">
                    <div class="col-md-12">
                        <button id="searchBtn" class="btn btn-primary"><i class="fa fa-search"></i> Search</button>
                        <button id="clearBtn" class="btn btn-default"><i class="fa fa-times"></i> Clear</button>
                        <button id="exportBtn" class="btn btn-default"><i class="fa fa-download"></i> Export CSV</button>
                        <label class="checkbox-inline" style="margin-left: 20px;">
                            <input type="checkbox" id="autoRefreshToggle"> Auto-refresh (5s)
                        </label>
                    </div>
                </div>
            </div>
        </div>

        <!-- Results Table -->
        <div class="table-responsive">
            <table id="auditTable" class="table table-striped table-condensed table-hover">
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Client IP</th>
                        <th>Device</th>
                        <th>Endpoint</th>
                        <th>Request</th>
                        <th>Prompt Preview</th>
                        <th>Result</th>
                        <th>Policy</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td colspan="8" class="text-center text-muted">Loading...</td></tr>
                </tbody>
            </table>
        </div>

        <!-- Pagination -->
        <div class="row">
            <div class="col-md-6">
                <span class="text-muted">
                    Page <strong id="currentPage">1</strong> of <strong id="totalPages">1</strong>
                    (<strong id="totalRecords">0</strong> total records)
                </span>
            </div>
            <div class="col-md-6 text-right">
                <button id="prevPage" class="btn btn-default btn-sm" disabled>
                    <i class="fa fa-chevron-left"></i> Previous
                </button>
                <button id="nextPage" class="btn btn-default btn-sm" disabled>
                    Next <i class="fa fa-chevron-right"></i>
                </button>
            </div>
        </div>
    </div>
</div>
