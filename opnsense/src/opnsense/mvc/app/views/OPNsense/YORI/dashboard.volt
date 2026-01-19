{#
 # YORI Dashboard - LLM Usage Statistics and Monitoring
 # Copyright (c) 2026 YORI Project
 # License: MIT
 #}

<style>
    @import url('/ui/css/yori/dashboard.css');
</style>

<div class="content-box">
    <div class="content-box-main">
        <div class="table-responsive">
            <div class="container-fluid">
                <!-- Page Header -->
                <div class="row mb-4">
                    <div class="col-12">
                        <h1 class="page-header">
                            <i class="fa fa-dashboard"></i> YORI Dashboard
                            <small>LLM Usage & Audit Monitoring</small>
                        </h1>
                    </div>
                </div>

                <!-- Summary Cards -->
                <div class="row mb-4" id="summary-cards">
                    <div class="col-md-3 col-sm-6">
                        <div class="card border-primary">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 class="card-subtitle mb-2 text-muted">Total Requests</h6>
                                        <h3 class="card-title mb-0" id="total-requests">-</h3>
                                    </div>
                                    <div class="text-primary">
                                        <i class="fa fa-globe fa-3x opacity-50"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-3 col-sm-6">
                        <div class="card border-success">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 class="card-subtitle mb-2 text-muted">Last 24 Hours</h6>
                                        <h3 class="card-title mb-0" id="last-24h">-</h3>
                                    </div>
                                    <div class="text-success">
                                        <i class="fa fa-clock-o fa-3x opacity-50"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-3 col-sm-6">
                        <div class="card border-info">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 class="card-subtitle mb-2 text-muted">Avg Tokens</h6>
                                        <h3 class="card-title mb-0" id="avg-tokens">-</h3>
                                    </div>
                                    <div class="text-info">
                                        <i class="fa fa-bar-chart fa-3x opacity-50"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-3 col-sm-6">
                        <div class="card border-warning">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 class="card-subtitle mb-2 text-muted">Total Alerts</h6>
                                        <h3 class="card-title mb-0" id="total-alerts">-</h3>
                                    </div>
                                    <div class="text-warning">
                                        <i class="fa fa-exclamation-triangle fa-3x opacity-50"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Charts Row 1 -->
                <div class="row mb-4">
                    <div class="col-lg-8">
                        <div class="card">
                            <div class="card-header">
                                <h5 class="card-title mb-0">
                                    <i class="fa fa-line-chart"></i> Requests Last 24 Hours
                                </h5>
                            </div>
                            <div class="card-body">
                                <canvas id="chart-24h" height="80"></canvas>
                            </div>
                        </div>
                    </div>

                    <div class="col-lg-4">
                        <div class="card">
                            <div class="card-header">
                                <h5 class="card-title mb-0">
                                    <i class="fa fa-pie-chart"></i> Top Endpoints
                                </h5>
                            </div>
                            <div class="card-body">
                                <canvas id="chart-endpoints"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Charts Row 2 -->
                <div class="row mb-4">
                    <div class="col-lg-6">
                        <div class="card">
                            <div class="card-header">
                                <h5 class="card-title mb-0">
                                    <i class="fa fa-laptop"></i> Top Devices
                                </h5>
                            </div>
                            <div class="card-body">
                                <canvas id="chart-devices" height="60"></canvas>
                            </div>
                        </div>
                    </div>

                    <div class="col-lg-6">
                        <div class="card">
                            <div class="card-header">
                                <h5 class="card-title mb-0">
                                    <i class="fa fa-clock-o"></i> Peak Usage Hours (Last 7 Days)
                                </h5>
                            </div>
                            <div class="card-body">
                                <canvas id="chart-hourly" height="60"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Recent Alerts -->
                <div class="row">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <h5 class="card-title mb-0">
                                    <i class="fa fa-bell"></i> Recent Alerts
                                </h5>
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-striped table-hover" id="alerts-table">
                                        <thead>
                                            <tr>
                                                <th>Timestamp</th>
                                                <th>Client IP</th>
                                                <th>Endpoint</th>
                                                <th>Policy</th>
                                                <th>Reason</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr>
                                                <td colspan="5" class="text-center">Loading alerts...</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Quick Actions -->
                <div class="row mt-4">
                    <div class="col-12">
                        <div class="btn-group" role="group">
                            <a href="/ui/yori/audit" class="btn btn-primary">
                                <i class="fa fa-list"></i> View Full Audit Log
                            </a>
                            <a href="/ui/yori/stats" class="btn btn-info">
                                <i class="fa fa-area-chart"></i> Detailed Statistics
                            </a>
                            <button id="refresh-btn" class="btn btn-secondary">
                                <i class="fa fa-refresh"></i> Refresh
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Chart.js from CDN -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>

<!-- Dashboard JavaScript -->
<script src="/ui/js/yori/dashboard.js"></script>

<script>
    // Initialize dashboard when page loads
    $(document).ready(function() {
        if (typeof YORIDashboard !== 'undefined') {
            YORIDashboard.init();

            // Refresh button handler
            $('#refresh-btn').on('click', function() {
                $(this).find('i').addClass('fa-spin');
                YORIDashboard.loadAll().finally(() => {
                    $('#refresh-btn i').removeClass('fa-spin');
                });
            });

            // Auto-refresh every 60 seconds
            setInterval(function() {
                YORIDashboard.loadAll();
            }, 60000);
        } else {
            console.error('YORI Dashboard JavaScript not loaded');
        }
    });
</script>
