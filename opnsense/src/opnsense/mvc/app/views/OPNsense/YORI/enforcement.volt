{#
 # Copyright (C) 2026 YORI Project
 # All rights reserved.
 #
 # Enforcement Mode Settings
 # WARNING: This page controls whether YORI actually blocks LLM requests.
 # Enabling enforcement mode can break LLM-dependent applications.
 #}

<script>
    $( document ).ready(function() {
        var data_get_map = {'frm_enforcement_settings':"/api/yori/enforcement/get"};
        mapDataToFormUI(data_get_map).done(function(data){
            formatTokenizersUI();
            $('.selectpicker').selectpicker('refresh');
            updateEnforcementStatus();
        });

        // Update enforcement status display
        function updateEnforcementStatus() {
            ajaxGet('/api/yori/enforcement/status', {}, function(data, status) {
                if (data.enforcement_active) {
                    $('#enforcement-status').removeClass('label-default label-warning').addClass('label-danger');
                    $('#enforcement-status').text('ACTIVE - Requests will be blocked');
                    $('#enforcement-warning').show();
                } else if (data.mode === 'enforce' && !data.enforcement_enabled) {
                    $('#enforcement-status').removeClass('label-default label-danger').addClass('label-warning');
                    $('#enforcement-status').text('Configured but NOT active (missing consent or enabled flag)');
                    $('#enforcement-warning').hide();
                } else {
                    $('#enforcement-status').removeClass('label-danger label-warning').addClass('label-default');
                    $('#enforcement-status').text('Disabled');
                    $('#enforcement-warning').hide();
                }

                $('#current-mode').text(data.mode || 'observe');
                $('#consent-status').text(data.consent_accepted ? 'Accepted' : 'Not Accepted');
                $('#enabled-status').text(data.enforcement_enabled ? 'Yes' : 'No');
            });
        }

        // Monitor consent checkbox
        $('#enforcement\\.consent_accepted').change(function() {
            if ($(this).is(':checked')) {
                $('#consent-warning-modal').modal('show');
            }
        });

        // Confirm consent in modal
        $('#confirm-consent-btn').click(function() {
            $('#consent-warning-modal').modal('hide');
        });

        // Cancel consent
        $('#cancel-consent-btn').click(function() {
            $('#enforcement\\.consent_accepted').prop('checked', false);
            $('#consent-warning-modal').modal('hide');
        });

        // Save settings
        $("#saveAct").click(function(){
            saveFormToEndpoint(url="/api/yori/enforcement/set", formid='frm_enforcement_settings', callback_ok=function(){
                $("#saveAct_progress").addClass("fa fa-spinner fa-pulse");
                ajaxCall(url="/api/yori/service/reconfigure", sendData={}, callback=function(data,status) {
                    $("#saveAct_progress").removeClass("fa fa-spinner fa-pulse");
                    updateEnforcementStatus();
                    if (data.status === 'ok') {
                        ajaxCall(url="/api/yori/service/status", sendData={}, callback=function(data,status) {
                            updateServiceStatusUI(data['status']);
                        });
                    }
                });
            });
        });

        // Test policy action
        $("#testPolicyBtn").click(function(){
            var policyName = $('#test-policy-name').val();
            if (policyName) {
                ajaxGet('/api/yori/enforcement/test/' + policyName, {}, function(data, status) {
                    $('#test-result').html(
                        '<div class="alert alert-info">' +
                        '<strong>Policy:</strong> ' + data.policy_name + '<br>' +
                        '<strong>Action:</strong> ' + data.action + '<br>' +
                        '<strong>Enabled:</strong> ' + data.enabled + '<br>' +
                        '<strong>Would Block:</strong> ' + data.would_block +
                        '</div>'
                    );
                });
            }
        });

        // Refresh status every 5 seconds
        setInterval(updateEnforcementStatus, 5000);
    });
</script>

<div class="content-box">
    <div class="content-box-main">
        <div class="table-responsive">
            <div class="col-md-12">
                <!-- Status Header -->
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h3 class="panel-title">
                            <i class="fa fa-shield"></i>
                            Enforcement Mode Status
                            <span id="enforcement-status" class="label label-default pull-right">Loading...</span>
                        </h3>
                    </div>
                    <div class="panel-body">
                        <div id="enforcement-warning" style="display: none;">
                            <div class="alert alert-danger">
                                <i class="fa fa-exclamation-triangle"></i>
                                <strong>WARNING: Enforcement mode is ACTIVE!</strong>
                                YORI is actively blocking LLM requests based on your policies.
                                This may break applications that depend on LLM APIs.
                            </div>
                        </div>

                        <table class="table table-condensed">
                            <tbody>
                                <tr>
                                    <td style="width: 200px;"><strong>Current Mode:</strong></td>
                                    <td><span id="current-mode" class="label label-info">observe</span></td>
                                </tr>
                                <tr>
                                    <td><strong>Enforcement Enabled:</strong></td>
                                    <td><span id="enabled-status">No</span></td>
                                </tr>
                                <tr>
                                    <td><strong>Consent Accepted:</strong></td>
                                    <td><span id="consent-status">Not Accepted</span></td>
                                </tr>
                            </tbody>
                        </table>

                        <div class="alert alert-info">
                            <strong>Note:</strong> For enforcement to actually block requests, you must:
                            <ul>
                                <li>Set mode to "enforce"</li>
                                <li>Enable enforcement mode below</li>
                                <li>Accept the consent checkbox</li>
                                <li>Configure at least one policy with action "block"</li>
                            </ul>
                        </div>
                    </div>
                </div>

                <!-- Enforcement Settings Form -->
                {{ partial("layout_partials/base_form",['fields':formEnforcement,'id':'frm_enforcement_settings'])}}

                <!-- Policy Configuration -->
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h3 class="panel-title">
                            <i class="fa fa-list"></i>
                            Per-Policy Enforcement
                        </h3>
                    </div>
                    <div class="panel-body">
                        <p class="help-block">
                            Configure enforcement actions for each policy individually.
                            <br><strong>allow:</strong> Pass requests through (policy disabled for enforcement)
                            <br><strong>alert:</strong> Log policy violations but don't block
                            <br><strong>block:</strong> Actually block requests (enforcement mode only)
                        </p>

                        <table class="table table-striped table-condensed">
                            <thead>
                                <tr>
                                    <th>Policy Name</th>
                                    <th>Enabled</th>
                                    <th>Action</th>
                                    <th>Description</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td><strong>bedtime</strong></td>
                                    <td><input type="checkbox" id="policy.bedtime.enabled" checked></td>
                                    <td>
                                        <select id="policy.bedtime.action" class="form-control">
                                            <option value="allow">Allow</option>
                                            <option value="alert" selected>Alert</option>
                                            <option value="block">Block</option>
                                        </select>
                                    </td>
                                    <td>Restrict LLM access during bedtime hours</td>
                                </tr>
                                <tr>
                                    <td><strong>privacy</strong></td>
                                    <td><input type="checkbox" id="policy.privacy.enabled" checked></td>
                                    <td>
                                        <select id="policy.privacy.action" class="form-control">
                                            <option value="allow">Allow</option>
                                            <option value="alert" selected>Alert</option>
                                            <option value="block">Block</option>
                                        </select>
                                    </td>
                                    <td>Block prompts containing sensitive data</td>
                                </tr>
                                <tr>
                                    <td><strong>content_filter</strong></td>
                                    <td><input type="checkbox" id="policy.content_filter.enabled" checked></td>
                                    <td>
                                        <select id="policy.content_filter.action" class="form-control">
                                            <option value="allow">Allow</option>
                                            <option value="alert" selected>Alert</option>
                                            <option value="block">Block</option>
                                        </select>
                                    </td>
                                    <td>Filter inappropriate content requests</td>
                                </tr>
                                <tr>
                                    <td><strong>token_limit</strong></td>
                                    <td><input type="checkbox" id="policy.token_limit.enabled" checked></td>
                                    <td>
                                        <select id="policy.token_limit.action" class="form-control">
                                            <option value="allow">Allow</option>
                                            <option value="alert" selected>Alert</option>
                                            <option value="block">Block</option>
                                        </select>
                                    </td>
                                    <td>Enforce token usage limits</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Test Policy Action -->
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h3 class="panel-title">
                            <i class="fa fa-flask"></i>
                            Test Policy Configuration
                        </h3>
                    </div>
                    <div class="panel-body">
                        <p class="help-block">
                            Test what action would be taken for a specific policy with current settings.
                        </p>
                        <div class="form-group">
                            <label>Policy Name:</label>
                            <input type="text" id="test-policy-name" class="form-control" placeholder="bedtime">
                        </div>
                        <button id="testPolicyBtn" class="btn btn-primary">
                            <i class="fa fa-play"></i> Test Policy
                        </button>
                        <div id="test-result" style="margin-top: 15px;"></div>
                    </div>
                </div>

                <!-- Save Button -->
                <div class="col-md-12">
                    <button class="btn btn-primary" id="saveAct" type="button">
                        <b>{{ lang._('Save') }}</b>
                        <i id="saveAct_progress" class=""></i>
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Consent Warning Modal -->
<div class="modal fade" id="consent-warning-modal" tabindex="-1" role="dialog">
    <div class="modal-dialog modal-lg" role="document">
        <div class="modal-content">
            <div class="modal-header bg-danger">
                <button type="button" class="close" data-dismiss="modal">&times;</button>
                <h4 class="modal-title">
                    <i class="fa fa-exclamation-triangle"></i>
                    WARNING: Enforcement Mode Consent Required
                </h4>
            </div>
            <div class="modal-body">
                <div class="alert alert-danger">
                    <h4><strong>Enabling enforcement mode will actively BLOCK LLM requests based on your policies.</strong></h4>
                </div>

                <p>This can break:</p>
                <ul>
                    <li>AI-powered applications and services</li>
                    <li>ChatGPT, Claude, and other LLM interfaces</li>
                    <li>Development tools that use LLM APIs</li>
                    <li>Any software relying on intercepted endpoints</li>
                </ul>

                <h4>Before enabling enforcement mode:</h4>
                <ol>
                    <li><strong>Test ALL policies in 'observe' mode first</strong></li>
                    <li><strong>Review audit logs to understand what will be blocked</strong></li>
                    <li><strong>Configure per-policy actions carefully (allow/alert/block)</strong></li>
                    <li><strong>Have a plan to quickly disable enforcement if needed</strong></li>
                    <li><strong>Inform users that blocking may occur</strong></li>
                </ol>

                <div class="alert alert-warning">
                    <strong>Emergency Disable:</strong> You can always disable enforcement by:
                    <ul>
                        <li>Unchecking the "Enforcement Enabled" checkbox, OR</li>
                        <li>Changing mode to "observe" or "advisory", OR</li>
                        <li>Editing /usr/local/etc/yori/yori.conf and restarting YORI</li>
                    </ul>
                </div>

                <p><strong>By accepting this consent, you acknowledge these risks and agree to test thoroughly before deploying.</strong></p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-default" id="cancel-consent-btn">
                    <i class="fa fa-times"></i> Cancel - Don't Enable
                </button>
                <button type="button" class="btn btn-danger" id="confirm-consent-btn">
                    <i class="fa fa-check"></i> I Accept the Risks - Enable Enforcement
                </button>
            </div>
        </div>
    </div>
</div>

<style>
    .bg-danger {
        background-color: #d9534f;
        color: white;
    }
    #enforcement-warning {
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.8; }
    }
</style>
