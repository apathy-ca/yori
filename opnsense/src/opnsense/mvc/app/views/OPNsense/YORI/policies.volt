{#
 # YORI Policy Editor UI
 # OPNsense Volt template for policy management
 #}

<div class="content-box">
    <div class="content-box-main">
        <div class="table-responsive">
            <div class="col-sm-12">
                <h2>{{ lang._('Policy Management') }}</h2>
                <p>{{ lang._('Configure and manage Rego policies for LLM governance.') }}</p>

                <!-- Policy List -->
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h3 class="panel-title">{{ lang._('Active Policies') }}</h3>
                    </div>
                    <div class="panel-body">
                        <table class="table table-striped table-hover">
                            <thead>
                                <tr>
                                    <th>{{ lang._('Policy Name') }}</th>
                                    <th>{{ lang._('Type') }}</th>
                                    <th>{{ lang._('Mode') }}</th>
                                    <th>{{ lang._('Status') }}</th>
                                    <th>{{ lang._('Actions') }}</th>
                                </tr>
                            </thead>
                            <tbody id="policy-list">
                                <!-- Populated via JavaScript/API -->
                            </tbody>
                        </table>

                        <button class="btn btn-primary" id="reload-policies">
                            <i class="fa fa-refresh"></i> {{ lang._('Reload Policies') }}
                        </button>
                    </div>
                </div>

                <!-- Pre-built Templates -->
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h3 class="panel-title">{{ lang._('Policy Templates') }}</h3>
                    </div>
                    <div class="panel-body">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="policy-template">
                                    <h4>Bedtime Policy</h4>
                                    <p>Alert on LLM usage after 9 PM</p>
                                    <p><strong>Mode:</strong> Advisory</p>
                                    <button class="btn btn-sm btn-success" data-template="bedtime">
                                        <i class="fa fa-moon-o"></i> Enable
                                    </button>
                                    <button class="btn btn-sm btn-info" data-template="bedtime" data-action="test">
                                        <i class="fa fa-flask"></i> Test
                                    </button>
                                </div>
                            </div>

                            <div class="col-md-6">
                                <div class="policy-template">
                                    <h4>High Usage Policy</h4>
                                    <p>Alert when daily requests exceed threshold</p>
                                    <p><strong>Mode:</strong> Advisory</p>
                                    <button class="btn btn-sm btn-success" data-template="high_usage">
                                        <i class="fa fa-line-chart"></i> Enable
                                    </button>
                                    <button class="btn btn-sm btn-info" data-template="high_usage" data-action="test">
                                        <i class="fa fa-flask"></i> Test
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div class="row" style="margin-top: 20px;">
                            <div class="col-md-6">
                                <div class="policy-template">
                                    <h4>Privacy Policy</h4>
                                    <p>Detect PII in prompts (email, phone, SSN)</p>
                                    <p><strong>Mode:</strong> Advisory</p>
                                    <button class="btn btn-sm btn-success" data-template="privacy">
                                        <i class="fa fa-shield"></i> Enable
                                    </button>
                                    <button class="btn btn-sm btn-info" data-template="privacy" data-action="test">
                                        <i class="fa fa-flask"></i> Test
                                    </button>
                                </div>
                            </div>

                            <div class="col-md-6">
                                <div class="policy-template">
                                    <h4>Homework Helper</h4>
                                    <p>Detect educational/homework queries</p>
                                    <p><strong>Mode:</strong> Advisory</p>
                                    <button class="btn btn-sm btn-success" data-template="homework_helper">
                                        <i class="fa fa-graduation-cap"></i> Enable
                                    </button>
                                    <button class="btn btn-sm btn-info" data-template="homework_helper" data-action="test">
                                        <i class="fa fa-flask"></i> Test
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Policy Testing -->
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h3 class="panel-title">{{ lang._('Policy Testing (Dry Run)') }}</h3>
                    </div>
                    <div class="panel-body">
                        <form id="policy-test-form">
                            <div class="form-group">
                                <label for="test-policy-select">{{ lang._('Select Policy') }}</label>
                                <select class="form-control" id="test-policy-select" name="policy">
                                    <option value="">-- {{ lang._('Select a policy') }} --</option>
                                    <option value="bedtime">Bedtime</option>
                                    <option value="high_usage">High Usage</option>
                                    <option value="privacy">Privacy</option>
                                    <option value="homework_helper">Homework Helper</option>
                                </select>
                            </div>

                            <div class="form-group">
                                <label for="test-input-json">{{ lang._('Test Input (JSON)') }}</label>
                                <textarea class="form-control" id="test-input-json" name="input" rows="8" placeholder='{"user": "alice", "hour": 22, "prompt": "test"}'>
{
  "user": "alice",
  "device": "iphone",
  "hour": 22,
  "prompt": "Help me with my homework"
}
                                </textarea>
                            </div>

                            <button type="submit" class="btn btn-primary">
                                <i class="fa fa-play"></i> {{ lang._('Run Test') }}
                            </button>
                        </form>

                        <div id="test-result" class="alert alert-info" style="display: none; margin-top: 20px;">
                            <h4>{{ lang._('Test Result') }}</h4>
                            <pre id="test-result-content"></pre>
                        </div>
                    </div>
                </div>

                <!-- Alert Configuration -->
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h3 class="panel-title">{{ lang._('Alert Configuration') }}</h3>
                    </div>
                    <div class="panel-body">
                        <p>{{ lang._('Configure how alerts are delivered when policies trigger.') }}</p>

                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="alert-email-enabled"> {{ lang._('Email Alerts') }}
                            </label>
                            <div id="alert-email-config" style="margin-left: 30px; display: none;">
                                <input type="text" class="form-control" placeholder="SMTP Host">
                                <input type="number" class="form-control" placeholder="SMTP Port">
                                <input type="email" class="form-control" placeholder="Recipient Email">
                            </div>
                        </div>

                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="alert-webhook-enabled"> {{ lang._('Webhook Alerts') }}
                            </label>
                            <div id="alert-webhook-config" style="margin-left: 30px; display: none;">
                                <input type="url" class="form-control" placeholder="Webhook URL">
                            </div>
                        </div>

                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="alert-pushover-enabled"> {{ lang._('Pushover Notifications') }}
                            </label>
                            <div id="alert-pushover-config" style="margin-left: 30px; display: none;">
                                <input type="text" class="form-control" placeholder="API Token">
                                <input type="text" class="form-control" placeholder="User Key">
                            </div>
                        </div>

                        <button class="btn btn-primary" id="save-alert-config">
                            <i class="fa fa-save"></i> {{ lang._('Save Alert Configuration') }}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<style>
.policy-template {
    border: 1px solid #ddd;
    padding: 15px;
    border-radius: 5px;
    margin-bottom: 15px;
}

.policy-template h4 {
    margin-top: 0;
}

#test-result pre {
    background: #f5f5f5;
    padding: 10px;
    border-radius: 3px;
}
</style>

<script>
$(document).ready(function() {
    // Load active policies
    function loadPolicies() {
        $.ajax({
            url: '/api/yori/policy/list',
            method: 'GET',
            success: function(data) {
                var tbody = $('#policy-list');
                tbody.empty();

                if (data.policies && data.policies.length > 0) {
                    data.policies.forEach(function(policy) {
                        var row = $('<tr>')
                            .append($('<td>').text(policy.name))
                            .append($('<td>').text(policy.type || 'custom'))
                            .append($('<td>').text(policy.mode || 'observe'))
                            .append($('<td>').html('<span class="label label-success">Active</span>'))
                            .append($('<td>').html(
                                '<button class="btn btn-xs btn-danger" data-policy="' + policy.name + '" data-action="disable">' +
                                '<i class="fa fa-times"></i> Disable</button>'
                            ));
                        tbody.append(row);
                    });
                } else {
                    tbody.append('<tr><td colspan="5" class="text-center">No policies loaded</td></tr>');
                }
            }
        });
    }

    // Reload policies button
    $('#reload-policies').click(function() {
        $.ajax({
            url: '/api/yori/policy/reload',
            method: 'POST',
            success: function(data) {
                alert('Policies reloaded: ' + data.count + ' loaded');
                loadPolicies();
            }
        });
    });

    // Test policy form
    $('#policy-test-form').submit(function(e) {
        e.preventDefault();

        var policy = $('#test-policy-select').val();
        var input = $('#test-input-json').val();

        if (!policy) {
            alert('Please select a policy');
            return;
        }

        try {
            var inputData = JSON.parse(input);
        } catch (err) {
            alert('Invalid JSON input: ' + err.message);
            return;
        }

        $.ajax({
            url: '/api/yori/policy/test',
            method: 'POST',
            data: JSON.stringify({
                policy: policy,
                input: inputData
            }),
            contentType: 'application/json',
            success: function(data) {
                $('#test-result').show();
                $('#test-result-content').text(JSON.stringify(data, null, 2));
            },
            error: function(xhr) {
                alert('Test failed: ' + xhr.responseText);
            }
        });
    });

    // Alert configuration toggles
    $('#alert-email-enabled').change(function() {
        $('#alert-email-config').toggle(this.checked);
    });

    $('#alert-webhook-enabled').change(function() {
        $('#alert-webhook-config').toggle(this.checked);
    });

    $('#alert-pushover-enabled').change(function() {
        $('#alert-pushover-config').toggle(this.checked);
    });

    // Initial load
    loadPolicies();
});
</script>
