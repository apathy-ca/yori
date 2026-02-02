{#
    Copyright (C) 2026 YORI Project
    All rights reserved.

    YORI Policy Editor
#}

<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/theme/monokai.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js"></script>

<script>
    var editor = null;
    var policyName = '{{ policyName }}';
    var isNew = !policyName;

    $(document).ready(function() {
        // Initialize CodeMirror
        editor = CodeMirror.fromTextArea(document.getElementById('policyContent'), {
            lineNumbers: true,
            mode: 'text/plain',
            theme: 'monokai',
            indentUnit: 4,
            tabSize: 4,
            lineWrapping: true
        });

        editor.setSize('100%', '400px');

        // Load policy if editing
        if (policyName) {
            $('#policyName').val(policyName).prop('readonly', true);
            loadPolicy(policyName);
        } else {
            // New policy template
            editor.setValue(getNewPolicyTemplate());
        }

        // Save button
        $('#saveBtn').click(function() {
            savePolicy();
        });

        // Validate button
        $('#validateBtn').click(function() {
            validatePolicy();
        });

        // Test button
        $('#testBtn').click(function() {
            testPolicy();
        });
    });

    function loadPolicy(name) {
        $.ajax({
            url: '/api/yori/policy/get/' + encodeURIComponent(name),
            method: 'GET',
            success: function(response) {
                if (response.result === 'success') {
                    editor.setValue(response.policy.content);
                } else {
                    showAlert('danger', 'Failed to load policy: ' + (response.message || 'Unknown error'));
                }
            }
        });
    }

    function savePolicy() {
        var name = $('#policyName').val().trim();
        if (!name) {
            showAlert('danger', 'Policy name is required');
            return;
        }

        if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
            showAlert('danger', 'Policy name can only contain letters, numbers, underscores, and hyphens');
            return;
        }

        var content = editor.getValue();

        $.ajax({
            url: '/api/yori/policy/set/' + encodeURIComponent(name),
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ content: content }),
            success: function(response) {
                if (response.result === 'success') {
                    showAlert('success', 'Policy saved successfully');
                    // Update URL if new policy
                    if (isNew) {
                        window.history.replaceState({}, '', '/ui/yori/policyEditor/' + name);
                        $('#policyName').prop('readonly', true);
                        policyName = name;
                        isNew = false;
                    }
                } else {
                    showAlert('danger', 'Save failed: ' + (response.message || 'Unknown error'));
                }
            }
        });
    }

    function validatePolicy() {
        var content = editor.getValue();

        $.ajax({
            url: '/api/yori/policy/validate',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ content: content }),
            success: function(response) {
                if (response.valid) {
                    showAlert('success', 'Policy syntax is valid');
                } else {
                    showAlert('danger', 'Validation error: ' + response.message);
                }
            }
        });
    }

    function testPolicy() {
        var name = $('#policyName').val().trim();
        if (!name) {
            showAlert('danger', 'Save the policy first before testing');
            return;
        }

        // First save, then test
        var content = editor.getValue();

        $.ajax({
            url: '/api/yori/policy/set/' + encodeURIComponent(name),
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ content: content }),
            success: function(response) {
                if (response.result === 'success') {
                    // Now test
                    runTest(name);
                } else {
                    showAlert('danger', 'Save failed: ' + (response.message || 'Unknown error'));
                }
            }
        });
    }

    function runTest(name) {
        var testInput = {
            timestamp: new Date().toISOString(),
            client_ip: $('#testClientIp').val() || '192.168.1.100',
            endpoint: $('#testEndpoint').val() || 'api.openai.com',
            prompt: $('#testPrompt').val() || 'Test prompt',
            daily_request_count: parseInt($('#testDailyCount').val()) || 10
        };

        $.ajax({
            url: '/api/yori/policy/test/' + encodeURIComponent(name),
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ input: testInput }),
            success: function(response) {
                if (response.result === 'success') {
                    $('#testResult').text(JSON.stringify(response.test_result, null, 2));
                    $('#testResultPanel').show();
                } else {
                    showAlert('danger', 'Test failed: ' + (response.message || 'Unknown error'));
                }
            }
        });
    }

    function getNewPolicyTemplate() {
        return `# YORI Policy: New Policy
# @description Describe your policy here
# @author Your Name
# @version 1.0.0

package yori.policies.new_policy

# Default allow all requests
default allow = true

# Set to true to send alerts
default alert = false

# Set to true to block (requires Enforce mode)
default block = false

# Example: Alert on specific condition
# alert if {
#     input.daily_request_count > 50
# }
`;
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
</script>

<div class="content-box">
    <div id="alertArea"></div>

    <div class="content-box-header">
        <h3><i class="fa fa-edit"></i> Policy Editor</h3>
    </div>

    <div class="content-box-main">
        <div class="row">
            <div class="col-md-8">
                <!-- Editor -->
                <div class="form-group">
                    <label for="policyName">Policy Name</label>
                    <input type="text" id="policyName" class="form-control"
                           placeholder="my_policy (letters, numbers, underscores, hyphens only)">
                </div>

                <div class="form-group">
                    <label>Policy Content (Rego)</label>
                    <textarea id="policyContent"></textarea>
                </div>

                <div class="btn-group">
                    <button id="saveBtn" class="btn btn-primary">
                        <i class="fa fa-save"></i> Save
                    </button>
                    <button id="validateBtn" class="btn btn-default">
                        <i class="fa fa-check"></i> Validate
                    </button>
                    <button id="testBtn" class="btn btn-default">
                        <i class="fa fa-play"></i> Test
                    </button>
                    <a href="/ui/yori/policies" class="btn btn-default">
                        <i class="fa fa-arrow-left"></i> Back to List
                    </a>
                </div>
            </div>

            <div class="col-md-4">
                <!-- Test Panel -->
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">Test Input</h4>
                    </div>
                    <div class="panel-body">
                        <div class="form-group">
                            <label>Client IP</label>
                            <input type="text" id="testClientIp" class="form-control" value="192.168.1.100">
                        </div>
                        <div class="form-group">
                            <label>Endpoint</label>
                            <select id="testEndpoint" class="form-control">
                                <option value="api.openai.com">OpenAI</option>
                                <option value="api.anthropic.com">Anthropic</option>
                                <option value="generativelanguage.googleapis.com">Google</option>
                                <option value="api.mistral.ai">Mistral</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Prompt</label>
                            <textarea id="testPrompt" class="form-control" rows="3">Test prompt for evaluation</textarea>
                        </div>
                        <div class="form-group">
                            <label>Daily Request Count</label>
                            <input type="number" id="testDailyCount" class="form-control" value="10">
                        </div>
                    </div>
                </div>

                <!-- Test Result Panel -->
                <div id="testResultPanel" class="panel panel-info" style="display: none;">
                    <div class="panel-heading">
                        <h4 class="panel-title">Test Result</h4>
                    </div>
                    <div class="panel-body">
                        <pre id="testResult" style="max-height: 200px; overflow: auto;"></pre>
                    </div>
                </div>

                <!-- Help Panel -->
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">Quick Reference</h4>
                    </div>
                    <div class="panel-body" style="font-size: 12px;">
                        <p><strong>Available Input:</strong></p>
                        <ul>
                            <li><code>input.timestamp</code></li>
                            <li><code>input.client_ip</code></li>
                            <li><code>input.endpoint</code></li>
                            <li><code>input.prompt</code></li>
                            <li><code>input.daily_request_count</code></li>
                        </ul>
                        <p><strong>Rules:</strong></p>
                        <ul>
                            <li><code>allow</code> - Allow request</li>
                            <li><code>alert</code> - Send notification</li>
                            <li><code>block</code> - Block request</li>
                        </ul>
                        <p><a href="https://www.openpolicyagent.org/docs/latest/policy-language/" target="_blank">Rego Documentation</a></p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
