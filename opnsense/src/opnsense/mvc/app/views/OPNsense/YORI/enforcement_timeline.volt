{#
YORI Enforcement Timeline
Chronological view of all enforcement events
#}

<div class="content-box" style="padding-bottom: 1.5em;">
    <h1>{{ lang._('Enforcement Timeline') }}</h1>

    <!-- Filters -->
    <div class="row">
        <div class="col-md-12">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <h3 class="panel-title">
                        <i class="fa fa-filter"></i> {{ lang._('Filters') }}
                    </h3>
                </div>
                <div class="panel-body">
                    <form class="form-inline">
                        <div class="form-group">
                            <label for="filter-hours">{{ lang._('Time Range') }}</label>
                            <select class="form-control" id="filter-hours">
                                <option value="1">{{ lang._('Last Hour') }}</option>
                                <option value="6">{{ lang._('Last 6 Hours') }}</option>
                                <option value="24" selected>{{ lang._('Last 24 Hours') }}</option>
                                <option value="168">{{ lang._('Last 7 Days') }}</option>
                            </select>
                        </div>

                        <div class="form-group" style="margin-left: 15px;">
                            <label for="filter-action">{{ lang._('Action Type') }}</label>
                            <select class="form-control" id="filter-action">
                                <option value="">{{ lang._('All Actions') }}</option>
                                <option value="block">{{ lang._('Blocks Only') }}</option>
                                <option value="override">{{ lang._('Overrides Only') }}</option>
                                <option value="allowlist_bypass">{{ lang._('Bypasses Only') }}</option>
                                <option value="alert">{{ lang._('Alerts Only') }}</option>
                            </select>
                        </div>

                        <div class="form-group" style="margin-left: 15px;">
                            <label for="filter-client">{{ lang._('Client IP') }}</label>
                            <input type="text" class="form-control" id="filter-client" placeholder="192.168.1.100">
                        </div>

                        <button type="button" class="btn btn-primary" id="apply-filters" style="margin-left: 15px;">
                            <i class="fa fa-search"></i> {{ lang._('Apply') }}
                        </button>

                        <button type="button" class="btn btn-default" id="clear-filters" style="margin-left: 5px;">
                            <i class="fa fa-times"></i> {{ lang._('Clear') }}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </div>

    <!-- Timeline -->
    <div class="row">
        <div class="col-md-12">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <h3 class="panel-title">
                        <i class="fa fa-clock-o"></i> {{ lang._('Event Timeline') }}
                        <span class="pull-right">
                            <button class="btn btn-xs btn-primary" id="refresh-timeline">
                                <i class="fa fa-refresh"></i> {{ lang._('Refresh') }}
                            </button>
                        </span>
                    </h3>
                </div>
                <div class="panel-body">
                    <div class="timeline" id="timeline-container">
                        <!-- Timeline events will be inserted here -->
                        <div class="text-center text-muted" id="timeline-loading">
                            <i class="fa fa-spinner fa-spin"></i> {{ lang._('Loading timeline...') }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Back to Dashboard -->
    <div class="row">
        <div class="col-md-12">
            <a href="/ui/yori/enforcement/dashboard" class="btn btn-default">
                <i class="fa fa-arrow-left"></i> {{ lang._('Back to Dashboard') }}
            </a>
        </div>
    </div>
</div>

<style>
.timeline {
    position: relative;
    padding: 20px 0;
}

.timeline-event {
    position: relative;
    padding: 15px;
    margin-bottom: 15px;
    border-left: 3px solid #ddd;
    background: #f9f9f9;
    border-radius: 3px;
}

.timeline-event.block {
    border-left-color: #d9534f;
}

.timeline-event.override {
    border-left-color: #f0ad4e;
}

.timeline-event.allowlist_bypass {
    border-left-color: #5bc0de;
}

.timeline-event.alert {
    border-left-color: #f0ad4e;
}

.timeline-event.allow {
    border-left-color: #5cb85c;
}

.timeline-icon {
    font-size: 24px;
    margin-right: 10px;
}

.timeline-timestamp {
    color: #999;
    font-size: 12px;
}

.timeline-details {
    margin-top: 10px;
}

.timeline-details dl {
    margin-bottom: 0;
}

.timeline-details dt {
    width: 120px;
}

.timeline-details dd {
    margin-left: 140px;
}
</style>

<script>
$(document).ready(function() {
    var currentFilters = {
        hours: 24,
        action: '',
        client: ''
    };

    // Load timeline events
    function loadTimeline() {
        $('#timeline-loading').show();
        $('#timeline-container .timeline-event').remove();

        var params = {
            hours: currentFilters.hours
        };

        if (currentFilters.action) {
            params.action = currentFilters.action;
        }

        if (currentFilters.client) {
            params.client_ip = currentFilters.client;
        }

        $.ajax({
            url: '/api/yori/enforcement/timeline',
            type: 'GET',
            data: params,
            success: function(data) {
                $('#timeline-loading').hide();

                if (data && data.events && data.events.length > 0) {
                    data.events.forEach(function(event) {
                        renderTimelineEvent(event);
                    });
                } else {
                    $('#timeline-container').append(
                        '<div class="text-center text-muted">' +
                        '<i class="fa fa-info-circle"></i> No events found for the selected filters' +
                        '</div>'
                    );
                }
            },
            error: function() {
                $('#timeline-loading').hide();
                $('#timeline-container').append(
                    '<div class="text-center text-danger">' +
                    '<i class="fa fa-exclamation-triangle"></i> Failed to load timeline events' +
                    '</div>'
                );
            }
        });
    }

    // Render a single timeline event
    function renderTimelineEvent(event) {
        var timestamp = new Date(event.timestamp).toLocaleString();
        var actionClass = event.enforcement_action.replace('_', '-');

        var html = '<div class="timeline-event ' + actionClass + '">' +
            '<div class="timeline-icon">' + event.icon + '</div>' +
            '<div style="display: inline-block; vertical-align: top; width: calc(100% - 50px);">' +
            '<strong>' + event.display_text + '</strong>' +
            '<div class="timeline-timestamp">' + timestamp + '</div>' +
            '<div class="timeline-details">' +
            '<dl class="dl-horizontal">' +
            '<dt>Client:</dt><dd>' + (event.client_device || event.client_ip) + '</dd>';

        if (event.policy_name) {
            html += '<dt>Policy:</dt><dd>' + event.policy_name + '</dd>';
        }

        if (event.reason && event.reason !== 'N/A') {
            html += '<dt>Reason:</dt><dd>' + event.reason + '</dd>';
        }

        if (event.override_user) {
            html += '<dt>Override By:</dt><dd>' + event.override_user + '</dd>';
        }

        html += '</dl></div></div></div>';

        $('#timeline-container').append(html);
    }

    // Apply filters
    $('#apply-filters').click(function() {
        currentFilters.hours = parseInt($('#filter-hours').val());
        currentFilters.action = $('#filter-action').val();
        currentFilters.client = $('#filter-client').val().trim();
        loadTimeline();
    });

    // Clear filters
    $('#clear-filters').click(function() {
        $('#filter-hours').val('24');
        $('#filter-action').val('');
        $('#filter-client').val('');
        currentFilters = { hours: 24, action: '', client: '' };
        loadTimeline();
    });

    // Refresh timeline
    $('#refresh-timeline').click(function() {
        loadTimeline();
        $(this).find('i').addClass('fa-spin');
        setTimeout(function() {
            $('#refresh-timeline i').removeClass('fa-spin');
        }, 1000);
    });

    // Initial load
    loadTimeline();

    // Auto-refresh every 30 seconds
    setInterval(loadTimeline, 30000);
});
</script>
