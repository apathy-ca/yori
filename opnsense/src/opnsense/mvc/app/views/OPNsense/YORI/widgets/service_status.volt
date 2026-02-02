{#
    Copyright (C) 2026 YORI Project
    All rights reserved.

    YORI Service Status Widget
#}

<script>
    $(document).ready(function() {
        loadYoriServiceStatus();
        setInterval(loadYoriServiceStatus, 10000);
    });

    function loadYoriServiceStatus() {
        $.ajax({
            url: '/api/yori/enforcement/status',
            method: 'GET',
            success: function(response) {
                var status = 'Unknown';
                var statusClass = 'default';
                var icon = 'fa-question';

                if (response.mode === 'enforce' && response.enforcement_active) {
                    status = 'Enforcing';
                    statusClass = 'danger';
                    icon = 'fa-shield';
                } else if (response.mode === 'advisory') {
                    status = 'Advisory';
                    statusClass = 'warning';
                    icon = 'fa-bell';
                } else if (response.mode === 'observe') {
                    status = 'Observing';
                    statusClass = 'info';
                    icon = 'fa-eye';
                }

                $('#yori-widget-status').html(
                    '<i class="fa ' + icon + '"></i> ' +
                    '<span class="label label-' + statusClass + '">' + status + '</span>'
                );
                $('#yori-widget-mode').text(response.mode || 'observe');
                $('#yori-widget-policies').text(response.policies_configured || 0);
            },
            error: function() {
                $('#yori-widget-status').html(
                    '<i class="fa fa-times"></i> ' +
                    '<span class="label label-default">Offline</span>'
                );
            }
        });
    }
</script>

<div class="widget-content">
    <table class="table table-condensed">
        <tbody>
            <tr>
                <td>Status</td>
                <td id="yori-widget-status">
                    <i class="fa fa-spinner fa-spin"></i> Loading...
                </td>
            </tr>
            <tr>
                <td>Mode</td>
                <td id="yori-widget-mode">-</td>
            </tr>
            <tr>
                <td>Policies</td>
                <td id="yori-widget-policies">-</td>
            </tr>
        </tbody>
    </table>
    <a href="/ui/yori/dashboard" class="btn btn-primary btn-xs btn-block">
        <i class="fa fa-external-link"></i> Open Dashboard
    </a>
</div>
