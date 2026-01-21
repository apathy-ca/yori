{#
 # Copyright (C) 2026 YORI Project
 # All rights reserved.
 #
 # YORI Enforcement Mode Dashboard Widget
 # Shows current enforcement status at a glance
 #}

<script>
    function updateYORIEnforcementWidget() {
        ajaxGet('/api/yori/enforcement/status', {}, function(data, status) {
            var statusHtml = '';
            var statusClass = '';
            var iconClass = '';

            if (data.enforcement_active) {
                statusClass = 'danger';
                iconClass = 'fa-shield text-danger';
                statusHtml = '<strong class="text-danger">ENFORCEMENT ACTIVE</strong><br>' +
                            '<small>Requests are being blocked</small>';
            } else if (data.mode === 'enforce' && !data.enforcement_enabled) {
                statusClass = 'warning';
                iconClass = 'fa-shield text-warning';
                statusHtml = '<strong class="text-warning">Enforcement Configured</strong><br>' +
                            '<small>Not active (missing consent or enabled flag)</small>';
            } else if (data.mode === 'advisory') {
                statusClass = 'info';
                iconClass = 'fa-eye text-info';
                statusHtml = '<strong>Advisory Mode</strong><br>' +
                            '<small>Monitoring with alerts</small>';
            } else {
                statusClass = 'success';
                iconClass = 'fa-eye text-success';
                statusHtml = '<strong>Observe Mode</strong><br>' +
                            '<small>Monitoring only</small>';
            }

            $('#yori-enforcement-icon').removeClass().addClass('fa ' + iconClass + ' fa-3x');
            $('#yori-enforcement-status').html(statusHtml);
            $('#yori-mode-badge').removeClass().addClass('label label-' + statusClass).text(data.mode || 'observe');

            // Update details
            var detailsHtml = '<table class="table table-condensed" style="margin-bottom: 0;">' +
                '<tr><td><strong>Mode:</strong></td><td><span class="label label-' + statusClass + '">' + (data.mode || 'observe') + '</span></td></tr>' +
                '<tr><td><strong>Enabled:</strong></td><td>' + (data.enforcement_enabled ? 'Yes' : 'No') + '</td></tr>' +
                '<tr><td><strong>Consent:</strong></td><td>' + (data.consent_accepted ? 'Accepted' : 'Not Accepted') + '</td></tr>' +
                '<tr><td><strong>Policies:</strong></td><td>' + (data.policies_configured || 0) + ' configured</td></tr>' +
                '</table>';

            $('#yori-enforcement-details').html(detailsHtml);

            // Warning banner
            if (data.enforcement_active) {
                $('#yori-enforcement-warning').html(
                    '<div class="alert alert-danger" style="margin-top: 10px; margin-bottom: 0; padding: 8px;">' +
                    '<i class="fa fa-exclamation-triangle"></i> ' +
                    '<strong>Active blocking enabled</strong>' +
                    '</div>'
                ).show();
            } else {
                $('#yori-enforcement-warning').hide();
            }
        });
    }

    // Update on load and every 10 seconds
    $(document).ready(function() {
        updateYORIEnforcementWidget();
        setInterval(updateYORIEnforcementWidget, 10000);
    });
</script>

<div id="yori-enforcement-widget">
    <div class="row">
        <div class="col-md-4 text-center" style="padding-top: 20px;">
            <i id="yori-enforcement-icon" class="fa fa-eye fa-3x text-success"></i>
        </div>
        <div class="col-md-8">
            <div id="yori-enforcement-status">
                <strong>Loading...</strong>
            </div>
            <div style="margin-top: 10px;">
                <a href="/ui/yori/enforcement" class="btn btn-primary btn-xs">
                    <i class="fa fa-cog"></i> Configure Enforcement
                </a>
            </div>
        </div>
    </div>

    <div id="yori-enforcement-warning" style="display: none;"></div>

    <div class="row" style="margin-top: 15px;">
        <div class="col-md-12">
            <div id="yori-enforcement-details">
                <em class="text-muted">Loading status...</em>
            </div>
        </div>
    </div>

    <div class="row" style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd;">
        <div class="col-md-12 text-center">
            <small class="text-muted">
                <i class="fa fa-info-circle"></i>
                YORI Zero-Trust LLM Gateway
            </small>
        </div>
    </div>
</div>

<style>
    #yori-enforcement-widget {
        padding: 10px;
    }
    #yori-enforcement-widget .table {
        font-size: 12px;
    }
    #yori-enforcement-widget .table td {
        padding: 4px 8px;
        border: none;
    }
</style>
