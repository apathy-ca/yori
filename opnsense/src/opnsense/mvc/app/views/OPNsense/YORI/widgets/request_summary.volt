{#
    Copyright (C) 2026 YORI Project
    All rights reserved.

    YORI Request Summary Widget
#}

<script>
    $(document).ready(function() {
        loadYoriRequestSummary();
        setInterval(loadYoriRequestSummary, 30000);
    });

    function loadYoriRequestSummary() {
        $.ajax({
            url: '/api/yori/audit/stats',
            method: 'GET',
            success: function(response) {
                if (response.result === 'success') {
                    $('#yori-widget-today').text(response.stats.requests_today || 0);
                    $('#yori-widget-week').text(response.stats.requests_week || 0);
                    $('#yori-widget-blocks').text(response.stats.blocks_today || 0);
                    $('#yori-widget-alerts').text(response.stats.alerts_today || 0);
                }
            },
            error: function() {
                $('#yori-widget-today').text('-');
                $('#yori-widget-week').text('-');
                $('#yori-widget-blocks').text('-');
                $('#yori-widget-alerts').text('-');
            }
        });
    }
</script>

<div class="widget-content">
    <table class="table table-condensed">
        <tbody>
            <tr>
                <td>Today</td>
                <td><strong id="yori-widget-today">-</strong> requests</td>
            </tr>
            <tr>
                <td>This Week</td>
                <td><strong id="yori-widget-week">-</strong> requests</td>
            </tr>
            <tr>
                <td>Blocks Today</td>
                <td><span class="label label-danger" id="yori-widget-blocks">-</span></td>
            </tr>
            <tr>
                <td>Alerts Today</td>
                <td><span class="label label-warning" id="yori-widget-alerts">-</span></td>
            </tr>
        </tbody>
    </table>
    <a href="/ui/yori/auditlog" class="btn btn-default btn-xs btn-block">
        <i class="fa fa-list"></i> View Audit Log
    </a>
</div>
