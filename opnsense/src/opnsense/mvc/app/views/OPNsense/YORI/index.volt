{#
 # Copyright (C) 2024 YORI Project
 # All rights reserved.
 #
 # Redistribution and use in source and binary forms, with or without
 # modification, are permitted provided that the following conditions are met:
 #
 # 1. Redistributions of source code must retain the above copyright notice,
 #    this list of conditions and the following disclaimer.
 #
 # 2. Redistributions in binary form must reproduce the above copyright
 #    notice, this list of conditions and the following disclaimer in the
 #    documentation and/or other materials provided with the distribution.
 #
 # THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
 # INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
 # AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 # AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
 # OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 # SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 # INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 # CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 # ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 # POSSIBILITY OF SUCH DAMAGE.
 #}

<div class="content-box" style="padding-bottom: 1.5em;">
    <div class="content-box-main">
        <div class="table-responsive">
            <div class="container-fluid">
                <h1>{{ lang._('YORI - LLM Gateway') }}</h1>
                <p>{{ lang._('Zero-trust LLM governance for home networks') }}</p>

                <hr/>

                <div class="row">
                    <div class="col-md-12">
                        <h2>{{ lang._('Service Status') }}</h2>
                        <table class="table table-striped">
                            <tbody>
                                <tr>
                                    <td style="width:22%"><strong>{{ lang._('Status') }}</strong></td>
                                    <td>
                                        <span id="service-status-text" class="badge badge-{% if service_status == 'running' %}success{% else %}danger{% endif %}">
                                            {{ service_status|upper }}
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td><strong>{{ lang._('Version') }}</strong></td>
                                    <td>{{ version }}</td>
                                </tr>
                                <tr>
                                    <td><strong>{{ lang._('Configuration File') }}</strong></td>
                                    <td><code>{{ config_path }}</code></td>
                                </tr>
                                <tr>
                                    <td><strong>{{ lang._('Audit Database') }}</strong></td>
                                    <td><code>{{ database_path }}</code></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-12">
                        <h2>{{ lang._('Service Control') }}</h2>
                        <div class="btn-group" role="group">
                            <button type="button" class="btn btn-success" id="btn-start-service">
                                <i class="fa fa-play fa-fw"></i> {{ lang._('Start') }}
                            </button>
                            <button type="button" class="btn btn-danger" id="btn-stop-service">
                                <i class="fa fa-stop fa-fw"></i> {{ lang._('Stop') }}
                            </button>
                            <button type="button" class="btn btn-warning" id="btn-restart-service">
                                <i class="fa fa-refresh fa-fw"></i> {{ lang._('Restart') }}
                            </button>
                            <button type="button" class="btn btn-primary" id="btn-refresh-status">
                                <i class="fa fa-sync fa-fw"></i> {{ lang._('Refresh Status') }}
                            </button>
                        </div>
                    </div>
                </div>

                <div class="row" style="margin-top: 20px;">
                    <div class="col-md-12">
                        <div id="service-message" class="alert" style="display:none;"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    'use strict';

    // Helper function to show messages
    function showMessage(message, type) {
        var messageDiv = $('#service-message');
        messageDiv.removeClass('alert-success alert-danger alert-info alert-warning');
        messageDiv.addClass('alert-' + type);
        messageDiv.text(message);
        messageDiv.show();
        setTimeout(function() {
            messageDiv.fadeOut();
        }, 5000);
    }

    // Helper function to update service status
    function updateServiceStatus() {
        $.ajax({
            url: '/api/yori/service/status',
            type: 'GET',
            dataType: 'json',
            success: function(data) {
                if (data.status === 'running') {
                    $('#service-status-text')
                        .removeClass('badge-danger')
                        .addClass('badge-success')
                        .text('RUNNING');
                } else {
                    $('#service-status-text')
                        .removeClass('badge-success')
                        .addClass('badge-danger')
                        .text('STOPPED');
                }
            },
            error: function() {
                showMessage('Failed to get service status', 'danger');
            }
        });
    }

    // Start service
    $('#btn-start-service').click(function() {
        $.ajax({
            url: '/api/yori/service/start',
            type: 'POST',
            dataType: 'json',
            success: function(data) {
                showMessage('Service start command sent', 'success');
                setTimeout(updateServiceStatus, 2000);
            },
            error: function() {
                showMessage('Failed to start service', 'danger');
            }
        });
    });

    // Stop service
    $('#btn-stop-service').click(function() {
        $.ajax({
            url: '/api/yori/service/stop',
            type: 'POST',
            dataType: 'json',
            success: function(data) {
                showMessage('Service stop command sent', 'success');
                setTimeout(updateServiceStatus, 2000);
            },
            error: function() {
                showMessage('Failed to stop service', 'danger');
            }
        });
    });

    // Restart service
    $('#btn-restart-service').click(function() {
        $.ajax({
            url: '/api/yori/service/restart',
            type: 'POST',
            dataType: 'json',
            success: function(data) {
                showMessage('Service restart command sent', 'success');
                setTimeout(updateServiceStatus, 2000);
            },
            error: function() {
                showMessage('Failed to restart service', 'danger');
            }
        });
    });

    // Refresh status
    $('#btn-refresh-status').click(function() {
        updateServiceStatus();
        showMessage('Status refreshed', 'info');
    });

    // Auto-refresh status every 10 seconds
    setInterval(updateServiceStatus, 10000);
});
</script>
