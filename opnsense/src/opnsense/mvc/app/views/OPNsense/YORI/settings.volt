{#
    Copyright (C) 2026 YORI Project
    All rights reserved.

    YORI Settings Page - Configuration management
#}

<script>
    $(document).ready(function() {
        // Load current settings
        loadSettings();

        // Save button handler
        $('#saveSettingsBtn').click(function() {
            saveSettings();
        });

        // Test button handler
        $('#testSettingsBtn').click(function() {
            testSettings();
        });

        // Backup button handler
        $('#backupBtn').click(function() {
            backupConfig();
        });

        // Restore button handler
        $('#restoreBtn').click(function() {
            $('#restoreFile').click();
        });

        // File input change handler
        $('#restoreFile').change(function(e) {
            if (e.target.files.length > 0) {
                restoreConfig(e.target.files[0]);
            }
        });

        // Mode change warning
        $('#mode').change(function() {
            if ($(this).val() === 'enforce') {
                $('#enforceWarning').show();
            } else {
                $('#enforceWarning').hide();
            }
        });
    });

    function loadSettings() {
        $.ajax({
            url: '/api/yori/settings/get',
            method: 'GET',
            success: function(response) {
                if (response.result === 'success') {
                    populateForm(response.settings);
                } else {
                    showAlert('danger', 'Failed to load settings: ' + (response.message || 'Unknown error'));
                }
            },
            error: function() {
                showAlert('danger', 'Failed to connect to API');
            }
        });
    }

    function populateForm(settings) {
        // General settings
        $('#mode').val(settings.mode || 'observe');
        if (settings.listen) {
            var parts = settings.listen.split(':');
            $('#listenAddress').val(parts[0] || '0.0.0.0');
            $('#listenPort').val(parts[1] || '8443');
        }

        // TLS settings
        if (settings.tls) {
            $('#tlsEnabled').prop('checked', settings.tls.enabled !== false);
            $('#certPath').val(settings.tls.cert_path || '');
            $('#keyPath').val(settings.tls.key_path || '');
            $('#caPath').val(settings.tls.ca_path || '');
        }

        // Audit settings
        if (settings.audit) {
            $('#dbPath').val(settings.audit.database || '/var/db/yori/audit.db');
            $('#retentionDays').val(settings.audit.retention_days || 365);
            $('#logPrompts').prop('checked', settings.audit.log_prompts !== false);
            $('#promptPreviewLength').val(settings.audit.prompt_preview_length || 200);
        }

        // Policy settings
        if (settings.policies) {
            $('#policyDirectory').val(settings.policies.directory || '/usr/local/etc/yori/policies');
            $('#defaultPolicy').val(settings.policies.default || 'home_default.rego');
        }

        // Endpoints
        if (settings.endpoints) {
            populateEndpoints(settings.endpoints);
        }

        // Trigger mode change handler
        $('#mode').trigger('change');
    }

    function populateEndpoints(endpoints) {
        var table = $('#endpointsTable tbody');
        table.empty();

        endpoints.forEach(function(ep) {
            var row = '<tr>' +
                '<td>' + escapeHtml(ep.domain) + '</td>' +
                '<td>' + escapeHtml(ep.name || ep.domain) + '</td>' +
                '<td>' +
                    '<input type="checkbox" class="endpoint-toggle" data-domain="' + escapeHtml(ep.domain) + '" ' +
                    (ep.enabled ? 'checked' : '') + '>' +
                '</td>' +
                '</tr>';
            table.append(row);
        });

        // Bind toggle handlers
        $('.endpoint-toggle').change(function() {
            var domain = $(this).data('domain');
            var enabled = $(this).prop('checked');
            toggleEndpoint(domain, enabled);
        });
    }

    function toggleEndpoint(domain, enabled) {
        $.ajax({
            url: '/api/yori/settings/endpoint/' + encodeURIComponent(domain),
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ enabled: enabled }),
            success: function(response) {
                if (response.result === 'success') {
                    showAlert('success', 'Endpoint ' + (enabled ? 'enabled' : 'disabled'));
                } else {
                    showAlert('danger', 'Failed: ' + (response.message || 'Unknown error'));
                    loadSettings(); // Reload to reset state
                }
            }
        });
    }

    function collectFormData() {
        return {
            mode: $('#mode').val(),
            listen: $('#listenAddress').val() + ':' + $('#listenPort').val(),
            tls: {
                enabled: $('#tlsEnabled').prop('checked'),
                cert_path: $('#certPath').val(),
                key_path: $('#keyPath').val(),
                ca_path: $('#caPath').val()
            },
            audit: {
                database: $('#dbPath').val(),
                retention_days: parseInt($('#retentionDays').val()) || 365,
                log_prompts: $('#logPrompts').prop('checked'),
                prompt_preview_length: parseInt($('#promptPreviewLength').val()) || 200
            },
            policies: {
                directory: $('#policyDirectory').val(),
                default: $('#defaultPolicy').val()
            }
        };
    }

    function saveSettings() {
        var data = collectFormData();

        $.ajax({
            url: '/api/yori/settings/set',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function(response) {
                if (response.result === 'success') {
                    showAlert('success', 'Settings saved successfully');
                } else {
                    showAlert('danger', 'Failed to save: ' + (response.message || 'Unknown error'));
                }
            },
            error: function() {
                showAlert('danger', 'Failed to connect to API');
            }
        });
    }

    function testSettings() {
        var data = collectFormData();

        $.ajax({
            url: '/api/yori/settings/test',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function(response) {
                if (response.valid) {
                    var msg = 'Configuration is valid';
                    if (response.warnings && response.warnings.length > 0) {
                        msg += '<br><small>Warnings:<br>' + response.warnings.join('<br>') + '</small>';
                    }
                    showAlert('success', msg);
                } else {
                    showAlert('danger', 'Validation failed: ' + (response.message || 'Unknown error'));
                }
            },
            error: function() {
                showAlert('danger', 'Failed to validate configuration');
            }
        });
    }

    function backupConfig() {
        $.ajax({
            url: '/api/yori/settings/backup',
            method: 'GET',
            success: function(response) {
                if (response.result === 'success') {
                    // Download as JSON file
                    var blob = new Blob([JSON.stringify(response.backup, null, 2)], { type: 'application/json' });
                    var url = URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url;
                    a.download = 'yori-config-backup-' + new Date().toISOString().slice(0, 10) + '.json';
                    a.click();
                    URL.revokeObjectURL(url);
                    showAlert('success', 'Configuration backup downloaded');
                } else {
                    showAlert('danger', 'Backup failed: ' + (response.message || 'Unknown error'));
                }
            }
        });
    }

    function restoreConfig(file) {
        var reader = new FileReader();
        reader.onload = function(e) {
            try {
                var backup = JSON.parse(e.target.result);
                if (confirm('Are you sure you want to restore this configuration? Current settings will be backed up.')) {
                    $.ajax({
                        url: '/api/yori/settings/restore',
                        method: 'POST',
                        contentType: 'application/json',
                        data: JSON.stringify({ backup: backup }),
                        success: function(response) {
                            if (response.result === 'success') {
                                showAlert('success', 'Configuration restored successfully');
                                loadSettings();
                            } else {
                                showAlert('danger', 'Restore failed: ' + (response.message || 'Unknown error'));
                            }
                        }
                    });
                }
            } catch (ex) {
                showAlert('danger', 'Invalid backup file format');
            }
        };
        reader.readAsText(file);
        $('#restoreFile').val(''); // Reset file input
    }

    function showAlert(type, message) {
        var alert = '<div class="alert alert-' + type + ' alert-dismissible" role="alert">' +
            '<button type="button" class="close" data-dismiss="alert"><span>&times;</span></button>' +
            message + '</div>';
        $('#alertArea').html(alert);

        // Auto-dismiss success alerts
        if (type === 'success') {
            setTimeout(function() {
                $('#alertArea .alert').fadeOut();
            }, 3000);
        }
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
</script>

<div class="content-box">
    <div id="alertArea"></div>

    <div class="content-box-header">
        <h3>YORI Settings</h3>
    </div>

    <div class="content-box-main">
        <!-- General Settings -->
        <fieldset>
            <legend>General</legend>

            <div class="form-group">
                <label for="mode">Operating Mode</label>
                <select id="mode" class="form-control">
                    <option value="observe">Observe - Log only, no alerts or blocking</option>
                    <option value="advisory">Advisory - Log and send alerts</option>
                    <option value="enforce">Enforce - Log, alert, and optionally block</option>
                </select>
                <small class="form-text text-muted">
                    Start with Observe mode to understand your network's LLM usage patterns.
                </small>
            </div>

            <div id="enforceWarning" class="alert alert-warning" style="display: none;">
                <strong>Warning:</strong> Enforce mode can block LLM requests. Ensure you have tested your
                policies in Advisory mode first. Enforcement requires explicit consent on the Enforcement page.
            </div>

            <div class="form-group">
                <label>Listen Address</label>
                <div class="row">
                    <div class="col-md-8">
                        <input type="text" id="listenAddress" class="form-control" value="0.0.0.0" placeholder="0.0.0.0">
                    </div>
                    <div class="col-md-4">
                        <input type="number" id="listenPort" class="form-control" value="8443" min="1" max="65535" placeholder="8443">
                    </div>
                </div>
                <small class="form-text text-muted">IP address and port for the proxy server</small>
            </div>
        </fieldset>

        <!-- TLS Settings -->
        <fieldset>
            <legend>TLS/SSL</legend>

            <div class="form-group">
                <div class="checkbox">
                    <label>
                        <input type="checkbox" id="tlsEnabled" checked> Enable TLS
                    </label>
                </div>
                <small class="form-text text-muted">Required for HTTPS interception</small>
            </div>

            <div class="form-group">
                <label for="certPath">Certificate Path</label>
                <input type="text" id="certPath" class="form-control" placeholder="/usr/local/etc/yori/certs/yori.crt">
            </div>

            <div class="form-group">
                <label for="keyPath">Private Key Path</label>
                <input type="text" id="keyPath" class="form-control" placeholder="/usr/local/etc/yori/certs/yori.key">
            </div>

            <div class="form-group">
                <label for="caPath">CA Certificate Path</label>
                <input type="text" id="caPath" class="form-control" placeholder="/usr/local/etc/yori/certs/ca.crt">
                <small class="form-text text-muted">CA certificate for signing intercepted connections</small>
            </div>
        </fieldset>

        <!-- Audit Settings -->
        <fieldset>
            <legend>Audit Logging</legend>

            <div class="form-group">
                <label for="dbPath">Database Path</label>
                <input type="text" id="dbPath" class="form-control" value="/var/db/yori/audit.db">
            </div>

            <div class="form-group">
                <label for="retentionDays">Retention (days)</label>
                <input type="number" id="retentionDays" class="form-control" value="365" min="1" max="3650">
                <small class="form-text text-muted">How long to keep audit records (1-3650 days)</small>
            </div>

            <div class="form-group">
                <div class="checkbox">
                    <label>
                        <input type="checkbox" id="logPrompts" checked> Log prompt previews
                    </label>
                </div>
            </div>

            <div class="form-group">
                <label for="promptPreviewLength">Prompt Preview Length</label>
                <input type="number" id="promptPreviewLength" class="form-control" value="200" min="0" max="10000">
                <small class="form-text text-muted">Characters of prompt to store (0 to disable)</small>
            </div>
        </fieldset>

        <!-- Policy Settings -->
        <fieldset>
            <legend>Policies</legend>

            <div class="form-group">
                <label for="policyDirectory">Policy Directory</label>
                <input type="text" id="policyDirectory" class="form-control" value="/usr/local/etc/yori/policies">
            </div>

            <div class="form-group">
                <label for="defaultPolicy">Default Policy</label>
                <input type="text" id="defaultPolicy" class="form-control" value="home_default.rego">
                <small class="form-text text-muted">Policy to apply when no other matches</small>
            </div>
        </fieldset>

        <!-- Endpoints -->
        <fieldset>
            <legend>LLM Endpoints</legend>

            <table id="endpointsTable" class="table table-striped">
                <thead>
                    <tr>
                        <th>Domain</th>
                        <th>Name</th>
                        <th>Enabled</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- Populated by JavaScript -->
                </tbody>
            </table>

            <small class="form-text text-muted">
                Enable or disable monitoring for specific LLM API endpoints.
            </small>
        </fieldset>

        <!-- Buttons -->
        <div class="form-group" style="margin-top: 20px;">
            <button id="saveSettingsBtn" class="btn btn-primary">
                <i class="fa fa-save"></i> Save Settings
            </button>
            <button id="testSettingsBtn" class="btn btn-default">
                <i class="fa fa-check"></i> Test Configuration
            </button>
            <button id="backupBtn" class="btn btn-default">
                <i class="fa fa-download"></i> Backup
            </button>
            <button id="restoreBtn" class="btn btn-default">
                <i class="fa fa-upload"></i> Restore
            </button>
            <input type="file" id="restoreFile" style="display: none;" accept=".json">
        </div>
    </div>
</div>
