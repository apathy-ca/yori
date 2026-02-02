{#
    Copyright (C) 2026 YORI Project
    All rights reserved.

    YORI Policies Management Page
#}

<script>
    $(document).ready(function() {
        loadPolicies();

        // Refresh button
        $('#refreshBtn').click(function() {
            loadPolicies();
        });
    });

    function loadPolicies() {
        $.ajax({
            url: '/api/yori/policy/list',
            method: 'GET',
            success: function(response) {
                if (response.result === 'success') {
                    renderPolicies(response.policies);
                } else {
                    showAlert('danger', 'Failed to load policies');
                }
            },
            error: function() {
                showAlert('danger', 'Failed to connect to API');
            }
        });
    }

    function renderPolicies(policies) {
        var table = $('#policiesTable tbody');
        table.empty();

        if (policies.length === 0) {
            table.append('<tr><td colspan="5" class="text-center text-muted">No policies installed. <a href="/ui/yori/policyLibrary">Install from library</a></td></tr>');
            return;
        }

        policies.forEach(function(policy) {
            var row = '<tr>' +
                '<td><strong>' + escapeHtml(policy.name) + '</strong></td>' +
                '<td>' + escapeHtml(policy.description || '-') + '</td>' +
                '<td>' + escapeHtml(policy.version || '-') + '</td>' +
                '<td>' + formatDate(policy.modified) + '</td>' +
                '<td>' +
                    '<div class="btn-group btn-group-xs">' +
                        '<a href="/ui/yori/policyEditor/' + escapeHtml(policy.name) + '" class="btn btn-default" title="Edit"><i class="fa fa-edit"></i></a>' +
                        '<button class="btn btn-default" onclick="testPolicy(\'' + escapeHtml(policy.name) + '\')" title="Test"><i class="fa fa-play"></i></button>' +
                        '<button class="btn btn-danger" onclick="deletePolicy(\'' + escapeHtml(policy.name) + '\')" title="Delete"' +
                            (policy.name === 'home_default' ? ' disabled' : '') + '><i class="fa fa-trash"></i></button>' +
                    '</div>' +
                '</td>' +
                '</tr>';
            table.append(row);
        });
    }

    function testPolicy(name) {
        $.ajax({
            url: '/api/yori/policy/test/' + encodeURIComponent(name),
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                input: {
                    timestamp: new Date().toISOString(),
                    client_ip: '192.168.1.100',
                    endpoint: 'api.openai.com',
                    prompt: 'Test prompt for policy evaluation'
                }
            }),
            success: function(response) {
                if (response.result === 'success') {
                    var result = JSON.stringify(response.test_result, null, 2);
                    $('#testResultModal .modal-body pre').text(result);
                    $('#testResultModal').modal('show');
                } else {
                    showAlert('danger', 'Test failed: ' + (response.message || 'Unknown error'));
                }
            }
        });
    }

    function deletePolicy(name) {
        if (!confirm('Are you sure you want to delete the policy "' + name + '"?')) {
            return;
        }

        $.ajax({
            url: '/api/yori/policy/delete/' + encodeURIComponent(name),
            method: 'POST',
            success: function(response) {
                if (response.result === 'success') {
                    showAlert('success', 'Policy deleted');
                    loadPolicies();
                } else {
                    showAlert('danger', 'Delete failed: ' + (response.message || 'Unknown error'));
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

    function formatDate(isoDate) {
        if (!isoDate) return '-';
        var d = new Date(isoDate);
        return d.toLocaleDateString() + ' ' + d.toLocaleTimeString();
    }

    function escapeHtml(text) {
        if (!text) return '';
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
</script>

<div class="content-box">
    <div id="alertArea"></div>

    <div class="content-box-header">
        <h3><i class="fa fa-file-text"></i> Policies</h3>
    </div>

    <div class="content-box-main">
        <div class="row" style="margin-bottom: 15px;">
            <div class="col-md-12">
                <a href="/ui/yori/policyEditor" class="btn btn-primary">
                    <i class="fa fa-plus"></i> New Policy
                </a>
                <a href="/ui/yori/policyLibrary" class="btn btn-default">
                    <i class="fa fa-book"></i> Policy Library
                </a>
                <button id="refreshBtn" class="btn btn-default">
                    <i class="fa fa-refresh"></i> Refresh
                </button>
            </div>
        </div>

        <table id="policiesTable" class="table table-striped table-hover">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Description</th>
                    <th>Version</th>
                    <th>Modified</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                <tr><td colspan="5" class="text-center text-muted">Loading...</td></tr>
            </tbody>
        </table>

        <div class="panel panel-info">
            <div class="panel-heading">
                <h4 class="panel-title">About Policies</h4>
            </div>
            <div class="panel-body">
                <p>YORI uses <a href="https://www.openpolicyagent.org/docs/latest/policy-language/" target="_blank">Rego</a> policies to evaluate LLM requests.</p>
                <p>Each policy can define:</p>
                <ul>
                    <li><code>allow</code> - Whether to allow the request</li>
                    <li><code>alert</code> - Whether to send an alert notification</li>
                    <li><code>block</code> - Whether to block the request (requires Enforce mode)</li>
                </ul>
                <p>Policies have access to:</p>
                <ul>
                    <li><code>input.timestamp</code> - Request timestamp</li>
                    <li><code>input.client_ip</code> - Client IP address</li>
                    <li><code>input.endpoint</code> - LLM API endpoint</li>
                    <li><code>input.prompt</code> - Prompt preview (if enabled)</li>
                    <li><code>input.daily_request_count</code> - Requests today from this client</li>
                </ul>
            </div>
        </div>
    </div>
</div>

<!-- Test Result Modal -->
<div class="modal fade" id="testResultModal" tabindex="-1" role="dialog">
    <div class="modal-dialog" role="document">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                <h4 class="modal-title">Policy Test Result</h4>
            </div>
            <div class="modal-body">
                <pre style="max-height: 400px; overflow: auto;"></pre>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>
