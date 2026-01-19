{#
 # YORI Audit Log Viewer
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
                            <i class="fa fa-list"></i> Audit Log Viewer
                            <small>LLM API Request History</small>
                        </h1>
                    </div>
                    <div class="col-md-4 text-end">
                        <button id="export-csv-btn" class="btn btn-success">
                            <i class="fa fa-download"></i> Export to CSV
                        </button>
                        <a href="/ui/yori/dashboard" class="btn btn-secondary">
                            <i class="fa fa-dashboard"></i> Back to Dashboard
                        </a>
                    </div>
                </div>

                <!-- Filters -->
                <div class="row mb-4">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <h5 class="card-title mb-0">
                                    <i class="fa fa-filter"></i> Filters
                                    <button id="toggle-filters" class="btn btn-sm btn-outline-secondary float-end">
                                        <i class="fa fa-chevron-up"></i> Hide
                                    </button>
                                </h5>
                            </div>
                            <div class="card-body" id="filter-panel">
                                <form id="filter-form">
                                    <div class="row g-3">
                                        <div class="col-md-3">
                                            <label for="filter-date-from" class="form-label">Date From</label>
                                            <input type="datetime-local" class="form-control" id="filter-date-from" name="date_from">
                                        </div>
                                        <div class="col-md-3">
                                            <label for="filter-date-to" class="form-label">Date To</label>
                                            <input type="datetime-local" class="form-control" id="filter-date-to" name="date_to">
                                        </div>
                                        <div class="col-md-3">
                                            <label for="filter-endpoint" class="form-label">Endpoint</label>
                                            <select class="form-select" id="filter-endpoint" name="endpoint">
                                                <option value="">All Endpoints</option>
                                            </select>
                                        </div>
                                        <div class="col-md-3">
                                            <label for="filter-client-ip" class="form-label">Client IP/Device</label>
                                            <select class="form-select" id="filter-client-ip" name="client_ip">
                                                <option value="">All Clients</option>
                                            </select>
                                        </div>
                                        <div class="col-md-3">
                                            <label for="filter-event-type" class="form-label">Event Type</label>
                                            <select class="form-select" id="filter-event-type" name="event_type">
                                                <option value="">All Types</option>
                                                <option value="request">Request</option>
                                                <option value="response">Response</option>
                                                <option value="block">Block</option>
                                            </select>
                                        </div>
                                        <div class="col-md-6">
                                            <label for="filter-search" class="form-label">Search (prompt preview or policy reason)</label>
                                            <input type="text" class="form-control" id="filter-search" name="search" placeholder="Enter search term...">
                                        </div>
                                        <div class="col-md-3 d-flex align-items-end">
                                            <button type="submit" class="btn btn-primary me-2">
                                                <i class="fa fa-search"></i> Apply Filters
                                            </button>
                                            <button type="button" id="clear-filters" class="btn btn-secondary">
                                                <i class="fa fa-times"></i> Clear
                                            </button>
                                        </div>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Results Summary -->
                <div class="row mb-3">
                    <div class="col-md-6">
                        <p class="text-muted mb-0">
                            Showing <strong id="result-start">0</strong> to <strong id="result-end">0</strong> of <strong id="result-total">0</strong> events
                        </p>
                    </div>
                    <div class="col-md-6 text-end">
                        <label for="per-page" class="me-2">Per page:</label>
                        <select id="per-page" class="form-select d-inline-block w-auto">
                            <option value="25">25</option>
                            <option value="50" selected>50</option>
                            <option value="100">100</option>
                            <option value="250">250</option>
                        </select>
                    </div>
                </div>

                <!-- Audit Log Table -->
                <div class="row">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-striped table-hover" id="audit-table">
                                        <thead>
                                            <tr>
                                                <th>Timestamp</th>
                                                <th>Type</th>
                                                <th>Client</th>
                                                <th>Endpoint</th>
                                                <th>Path</th>
                                                <th>Tokens (P/R)</th>
                                                <th>Duration</th>
                                                <th>Policy</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody id="audit-tbody">
                                            <tr>
                                                <td colspan="9" class="text-center">
                                                    <i class="fa fa-spinner fa-spin"></i> Loading audit events...
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Pagination -->
                <div class="row mt-3">
                    <div class="col-12">
                        <nav aria-label="Audit log pagination">
                            <ul class="pagination justify-content-center" id="pagination">
                                <li class="page-item disabled"><a class="page-link" href="#">Loading...</a></li>
                            </ul>
                        </nav>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Event Detail Modal -->
<div class="modal fade" id="event-detail-modal" tabindex="-1" aria-labelledby="eventDetailLabel" aria-hidden="true">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="eventDetailLabel">Event Details</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body" id="event-detail-body">
                <p class="text-center"><i class="fa fa-spinner fa-spin"></i> Loading...</p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>

<script>
$(document).ready(function() {
    var currentPage = 1;
    var currentLimit = 50;
    var currentFilters = {};

    // Initialize
    loadFilterOptions();
    loadAuditLog();

    // Toggle filters
    $('#toggle-filters').on('click', function() {
        $('#filter-panel').slideToggle();
        var icon = $(this).find('i');
        if (icon.hasClass('fa-chevron-up')) {
            icon.removeClass('fa-chevron-up').addClass('fa-chevron-down');
            $(this).html('<i class="fa fa-chevron-down"></i> Show');
        } else {
            icon.removeClass('fa-chevron-down').addClass('fa-chevron-up');
            $(this).html('<i class="fa fa-chevron-up"></i> Hide');
        }
    });

    // Filter form submission
    $('#filter-form').on('submit', function(e) {
        e.preventDefault();
        currentPage = 1;
        currentFilters = $(this).serializeArray().reduce(function(obj, item) {
            if (item.value) obj[item.name] = item.value;
            return obj;
        }, {});
        loadAuditLog();
    });

    // Clear filters
    $('#clear-filters').on('click', function() {
        $('#filter-form')[0].reset();
        currentFilters = {};
        currentPage = 1;
        loadAuditLog();
    });

    // Per page change
    $('#per-page').on('change', function() {
        currentLimit = parseInt($(this).val());
        currentPage = 1;
        loadAuditLog();
    });

    // Export CSV
    $('#export-csv-btn').on('click', function() {
        var params = $.param(currentFilters);
        window.location.href = '/api/yori/audit/export?' + params;
    });

    // Load filter options
    function loadFilterOptions() {
        // Load endpoints
        $.ajax({
            url: '/api/yori/audit/endpoints',
            type: 'GET',
            dataType: 'json',
            success: function(response) {
                if (response.status === 'ok') {
                    var select = $('#filter-endpoint');
                    response.data.forEach(function(endpoint) {
                        select.append('<option value="' + endpoint + '">' + endpoint + '</option>');
                    });
                }
            }
        });

        // Load clients
        $.ajax({
            url: '/api/yori/audit/clients',
            type: 'GET',
            dataType: 'json',
            success: function(response) {
                if (response.status === 'ok') {
                    var select = $('#filter-client-ip');
                    response.data.forEach(function(client) {
                        select.append('<option value="' + client.client_ip + '">' + client.display_name + '</option>');
                    });
                }
            }
        });
    }

    // Load audit log
    function loadAuditLog() {
        var data = $.extend({}, currentFilters, {
            page: currentPage,
            limit: currentLimit
        });

        $.ajax({
            url: '/api/yori/audit/search',
            type: 'POST',
            data: data,
            dataType: 'json',
            success: function(response) {
                if (response.status === 'ok') {
                    renderAuditTable(response.data);
                    renderPagination(response.page, response.pages, response.total);
                } else {
                    $('#audit-tbody').html('<tr><td colspan="9" class="text-center text-danger">Error: ' + response.message + '</td></tr>');
                }
            },
            error: function() {
                $('#audit-tbody').html('<tr><td colspan="9" class="text-center text-danger">Error loading audit log</td></tr>');
            }
        });
    }

    // Render audit table
    function renderAuditTable(data) {
        var tbody = $('#audit-tbody');
        tbody.empty();

        if (data.length === 0) {
            tbody.append('<tr><td colspan="9" class="text-center text-muted">No audit events found</td></tr>');
            return;
        }

        data.forEach(function(event) {
            var timestamp = new Date(event.timestamp).toLocaleString();
            var eventTypeBadge = getEventTypeBadge(event.event_type);
            var clientDisplay = event.client_device || event.client_ip;
            var tokens = (event.prompt_tokens || 0) + ' / ' + (event.response_tokens || 0);
            var duration = event.response_duration_ms ? event.response_duration_ms + ' ms' : '-';
            var policyBadge = getPolicyBadge(event.policy_result);

            var row = '<tr>' +
                '<td>' + timestamp + '</td>' +
                '<td>' + eventTypeBadge + '</td>' +
                '<td>' + escapeHtml(clientDisplay) + '</td>' +
                '<td>' + escapeHtml(event.endpoint) + '</td>' +
                '<td><small>' + escapeHtml(event.http_path) + '</small></td>' +
                '<td>' + tokens + '</td>' +
                '<td>' + duration + '</td>' +
                '<td>' + policyBadge + '</td>' +
                '<td><button class="btn btn-sm btn-outline-primary view-details" data-id="' + event.id + '"><i class="fa fa-eye"></i></button></td>' +
                '</tr>';
            tbody.append(row);
        });

        // View details handler
        $('.view-details').on('click', function() {
            var eventId = $(this).data('id');
            viewEventDetails(eventId);
        });
    }

    // Render pagination
    function renderPagination(page, totalPages, total) {
        var start = ((page - 1) * currentLimit) + 1;
        var end = Math.min(page * currentLimit, total);

        $('#result-start').text(start);
        $('#result-end').text(end);
        $('#result-total').text(total);

        var pagination = $('#pagination');
        pagination.empty();

        // Previous button
        var prevDisabled = page === 1 ? 'disabled' : '';
        pagination.append('<li class="page-item ' + prevDisabled + '"><a class="page-link" href="#" data-page="' + (page - 1) + '">Previous</a></li>');

        // Page numbers
        var startPage = Math.max(1, page - 2);
        var endPage = Math.min(totalPages, page + 2);

        for (var i = startPage; i <= endPage; i++) {
            var active = i === page ? 'active' : '';
            pagination.append('<li class="page-item ' + active + '"><a class="page-link" href="#" data-page="' + i + '">' + i + '</a></li>');
        }

        // Next button
        var nextDisabled = page === totalPages ? 'disabled' : '';
        pagination.append('<li class="page-item ' + nextDisabled + '"><a class="page-link" href="#" data-page="' + (page + 1) + '">Next</a></li>');

        // Pagination click handlers
        $('.page-link').on('click', function(e) {
            e.preventDefault();
            var newPage = parseInt($(this).data('page'));
            if (newPage > 0 && newPage <= totalPages) {
                currentPage = newPage;
                loadAuditLog();
            }
        });
    }

    // View event details
    function viewEventDetails(eventId) {
        $('#event-detail-modal').modal('show');
        $('#event-detail-body').html('<p class="text-center"><i class="fa fa-spinner fa-spin"></i> Loading...</p>');

        $.ajax({
            url: '/api/yori/audit/get',
            type: 'POST',
            data: { id: eventId },
            dataType: 'json',
            success: function(response) {
                if (response.status === 'ok') {
                    renderEventDetails(response.data);
                } else {
                    $('#event-detail-body').html('<p class="text-danger">Error: ' + response.message + '</p>');
                }
            },
            error: function() {
                $('#event-detail-body').html('<p class="text-danger">Error loading event details</p>');
            }
        });
    }

    // Render event details
    function renderEventDetails(event) {
        var html = '<dl class="row">';
        html += '<dt class="col-sm-3">Timestamp</dt><dd class="col-sm-9">' + event.timestamp + '</dd>';
        html += '<dt class="col-sm-3">Event Type</dt><dd class="col-sm-9">' + getEventTypeBadge(event.event_type) + '</dd>';
        html += '<dt class="col-sm-3">Client IP</dt><dd class="col-sm-9">' + escapeHtml(event.client_ip) + '</dd>';
        if (event.client_device) {
            html += '<dt class="col-sm-3">Client Device</dt><dd class="col-sm-9">' + escapeHtml(event.client_device) + '</dd>';
        }
        html += '<dt class="col-sm-3">Endpoint</dt><dd class="col-sm-9">' + escapeHtml(event.endpoint) + '</dd>';
        html += '<dt class="col-sm-3">HTTP Method</dt><dd class="col-sm-9">' + escapeHtml(event.http_method) + '</dd>';
        html += '<dt class="col-sm-3">HTTP Path</dt><dd class="col-sm-9">' + escapeHtml(event.http_path) + '</dd>';
        if (event.prompt_preview) {
            html += '<dt class="col-sm-3">Prompt Preview</dt><dd class="col-sm-9"><code>' + escapeHtml(event.prompt_preview) + '</code></dd>';
        }
        html += '<dt class="col-sm-3">Prompt Tokens</dt><dd class="col-sm-9">' + (event.prompt_tokens || 'N/A') + '</dd>';
        html += '<dt class="col-sm-3">Response Tokens</dt><dd class="col-sm-9">' + (event.response_tokens || 'N/A') + '</dd>';
        html += '<dt class="col-sm-3">Response Status</dt><dd class="col-sm-9">' + (event.response_status || 'N/A') + '</dd>';
        html += '<dt class="col-sm-3">Response Duration</dt><dd class="col-sm-9">' + (event.response_duration_ms ? event.response_duration_ms + ' ms' : 'N/A') + '</dd>';
        if (event.policy_name) {
            html += '<dt class="col-sm-3">Policy</dt><dd class="col-sm-9">' + escapeHtml(event.policy_name) + '</dd>';
        }
        if (event.policy_result) {
            html += '<dt class="col-sm-3">Policy Result</dt><dd class="col-sm-9">' + getPolicyBadge(event.policy_result) + '</dd>';
        }
        if (event.policy_reason) {
            html += '<dt class="col-sm-3">Policy Reason</dt><dd class="col-sm-9">' + escapeHtml(event.policy_reason) + '</dd>';
        }
        if (event.user_agent) {
            html += '<dt class="col-sm-3">User Agent</dt><dd class="col-sm-9"><small>' + escapeHtml(event.user_agent) + '</small></dd>';
        }
        html += '</dl>';

        $('#event-detail-body').html(html);
    }

    // Helper: Get event type badge
    function getEventTypeBadge(type) {
        var badges = {
            'request': '<span class="badge bg-primary">Request</span>',
            'response': '<span class="badge bg-success">Response</span>',
            'block': '<span class="badge bg-danger">Block</span>'
        };
        return badges[type] || '<span class="badge bg-secondary">' + type + '</span>';
    }

    // Helper: Get policy badge
    function getPolicyBadge(result) {
        if (!result) return '<span class="badge bg-secondary">N/A</span>';
        var badges = {
            'allow': '<span class="badge policy-allow">Allow</span>',
            'alert': '<span class="badge policy-alert">Alert</span>',
            'block': '<span class="badge policy-block">Block</span>'
        };
        return badges[result] || '<span class="badge bg-secondary">' + result + '</span>';
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
