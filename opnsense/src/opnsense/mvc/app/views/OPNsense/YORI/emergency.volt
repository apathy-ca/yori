{#
 # Copyright (C) 2026 James Henry
 # All rights reserved.
 #
 # YORI Emergency Override Interface
 #}

<script>
    $( document ).ready(function() {
        // Load override status
        function loadStatus() {
            ajaxCall(url="/api/yori/emergency/getStatus", sendData={}, callback=function(data,status) {
                if (data && data.status) {
                    updateStatusDisplay(data.status);
                }
            });
        }

        function updateStatusDisplay(status) {
            if (status.enabled) {
                $("#override_status").removeClass("alert-info").addClass("alert-danger");
                $("#override_status_text").html('<i class="fa fa-exclamation-triangle"></i> <strong>EMERGENCY OVERRIDE ACTIVE</strong><br/>All enforcement is currently disabled.');
                $("#activateBtn").hide();
                $("#deactivateBtn").show();

                if (status.activated_at) {
                    $("#activation_info").html(
                        'Activated: ' + status.activated_at + '<br/>' +
                        'By: ' + (status.activated_by || 'Unknown')
                    );
                    $("#activation_info_panel").show();
                }
            } else {
                $("#override_status").removeClass("alert-danger").addClass("alert-info");
                $("#override_status_text").html('<i class="fa fa-info-circle"></i> Emergency override is currently inactive. Enforcement policies are active.');
                $("#activateBtn").show();
                $("#deactivateBtn").hide();
                $("#activation_info_panel").hide();
            }
        }

        // Activate override
        $("#activateBtn").click(function(){
            var password = $("#override_password").val();

            if (!password) {
                alert("Please enter the admin password");
                return;
            }

            if (!confirm("⚠️ WARNING: This will disable ALL enforcement immediately. Continue?")) {
                return;
            }

            ajaxCall(url="/api/yori/emergency/activate", sendData={
                password: password
            }, callback=function(data,status) {
                if (data.result == "success") {
                    $("#override_password").val('');
                    loadStatus();
                } else {
                    alert("Error: " + (data.message || "Failed to activate override"));
                }
            });
        });

        // Deactivate override
        $("#deactivateBtn").click(function(){
            var password = $("#deactivate_password").val();

            if (!password) {
                alert("Please enter the admin password");
                return;
            }

            if (!confirm("Re-enable enforcement policies?")) {
                return;
            }

            ajaxCall(url="/api/yori/emergency/deactivate", sendData={
                password: password
            }, callback=function(data,status) {
                if (data.result == "success") {
                    $("#deactivate_password").val('');
                    loadStatus();
                } else {
                    alert("Error: " + (data.message || "Failed to deactivate override"));
                }
            });
        });

        // Load status on page load
        loadStatus();
        // Refresh every 10 seconds
        setInterval(loadStatus, 10000);
    });
</script>

<div class="content-box">
    <div class="content-box-main">
        <div class="table-responsive">
            <div class="col-md-12">
                <h1>{{ lang._('Emergency Override') }}</h1>
                <p>{{ lang._('Instantly disable all enforcement for emergency situations.') }}</p>

                <!-- Status Display -->
                <div id="override_status" class="alert alert-info" role="alert">
                    <h3 id="override_status_text">
                        <i class="fa fa-spinner fa-spin"></i> {{ lang._('Loading status...') }}
                    </h3>
                </div>

                <!-- Activation Info (shown when active) -->
                <div id="activation_info_panel" class="panel panel-info" style="display:none;">
                    <div class="panel-heading">{{ lang._('Override Details') }}</div>
                    <div class="panel-body">
                        <p id="activation_info"></p>
                    </div>
                </div>

                <!-- Activate Override -->
                <div id="activatePanel" class="panel panel-warning">
                    <div class="panel-heading">
                        <h3 class="panel-title">{{ lang._('Activate Emergency Override') }}</h3>
                    </div>
                    <div class="panel-body">
                        <div class="alert alert-warning">
                            <i class="fa fa-exclamation-triangle"></i>
                            <strong>{{ lang._('Warning:') }}</strong>
                            {{ lang._('This will immediately disable ALL enforcement policies. All LLM requests will be allowed through, regardless of policy violations.') }}
                        </div>

                        <div class="form-group">
                            <label>{{ lang._('Admin Password') }}</label>
                            <input type="password" id="override_password" class="form-control" placeholder="Enter admin password">
                            <small class="form-text text-muted">
                                {{ lang._('Required to prevent accidental activation') }}
                            </small>
                        </div>

                        <button id="activateBtn" class="btn btn-danger btn-lg">
                            <i class="fa fa-exclamation-triangle"></i>
                            {{ lang._('ACTIVATE EMERGENCY OVERRIDE') }}
                        </button>
                    </div>
                </div>

                <!-- Deactivate Override -->
                <div id="deactivatePanel" class="panel panel-success" style="display:none;">
                    <div class="panel-heading">
                        <h3 class="panel-title">{{ lang._('Deactivate Emergency Override') }}</h3>
                    </div>
                    <div class="panel-body">
                        <p>{{ lang._('Re-enable normal enforcement policies.') }}</p>

                        <div class="form-group">
                            <label>{{ lang._('Admin Password') }}</label>
                            <input type="password" id="deactivate_password" class="form-control" placeholder="Enter admin password">
                        </div>

                        <button id="deactivateBtn" class="btn btn-success btn-lg" style="display:none;">
                            <i class="fa fa-check"></i>
                            {{ lang._('DEACTIVATE OVERRIDE - Re-enable Enforcement') }}
                        </button>
                    </div>
                </div>

                <!-- Usage Instructions -->
                <div class="panel panel-default">
                    <div class="panel-heading">{{ lang._('When to Use Emergency Override') }}</div>
                    <div class="panel-body">
                        <h4>{{ lang._('Appropriate Use Cases:') }}</h4>
                        <ul>
                            <li>{{ lang._('Emergency situation requiring immediate unrestricted LLM access') }}</li>
                            <li>{{ lang._('Critical work task where enforcement is blocking legitimate use') }}</li>
                            <li>{{ lang._('Temporary troubleshooting of policy issues') }}</li>
                            <li>{{ lang._('Time-sensitive situation where adding device to allowlist would take too long') }}</li>
                        </ul>

                        <h4>{{ lang._('Better Alternatives:') }}</h4>
                        <ul>
                            <li>{{ lang._('Add device to allowlist (permanent or temporary)') }}</li>
                            <li>{{ lang._('Configure time-based exception for recurring needs') }}</li>
                            <li>{{ lang._('Adjust policy rules to allow legitimate use') }}</li>
                        </ul>

                        <div class="alert alert-info">
                            <i class="fa fa-info-circle"></i>
                            {{ lang._('All emergency override activations are logged in the audit database with timestamp and source IP.') }}
                        </div>
                    </div>
                </div>

                <!-- Password Management -->
                <div class="panel panel-default">
                    <div class="panel-heading">{{ lang._('Password Configuration') }}</div>
                    <div class="panel-body">
                        <p>{{ lang._('To set or change the emergency override password, use the command line:') }}</p>
                        <pre>python3 -c "from yori.emergency import set_override_password; from yori.config import YoriConfig; config = YoriConfig.from_default_locations(); set_override_password(config, 'your_new_password')"</pre>

                        <p class="text-muted">{{ lang._('UI-based password management coming soon.') }}</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
