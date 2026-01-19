/**
 * YORI Dashboard JavaScript
 * Handles Chart.js visualizations and API data loading
 *
 * @package YORI
 * @license MIT
 */

var YORIDashboard = (function() {
    'use strict';

    // Chart instances
    var charts = {
        last24h: null,
        endpoints: null,
        devices: null,
        hourly: null
    };

    // Color palette
    var colors = {
        primary: '#0d6efd',
        success: '#198754',
        info: '#0dcaf0',
        warning: '#ffc107',
        danger: '#dc3545',
        secondary: '#6c757d'
    };

    var endpointColors = {
        'api.openai.com': '#10a37f',
        'api.anthropic.com': '#d4a574',
        'generativelanguage.googleapis.com': '#4285f4',
        'api.mistral.ai': '#ff7000'
    };

    /**
     * Initialize dashboard
     */
    function init() {
        console.log('Initializing YORI Dashboard...');
        loadAll();
    }

    /**
     * Load all dashboard data
     */
    function loadAll() {
        return Promise.all([
            loadSummary(),
            load24hChart(),
            loadEndpointsChart(),
            loadDevicesChart(),
            loadHourlyChart(),
            loadRecentAlerts()
        ]);
    }

    /**
     * Load summary statistics
     */
    function loadSummary() {
        return $.ajax({
            url: '/api/yori/stats/summary',
            type: 'GET',
            dataType: 'json'
        })
        .done(function(response) {
            if (response.status === 'ok') {
                var data = response.data;
                $('#total-requests').text(data.total_requests.toLocaleString());
                $('#last-24h').text(data.last_24h.toLocaleString());
                $('#avg-tokens').text(data.avg_tokens ? data.avg_tokens.toLocaleString() : 'N/A');
                $('#total-alerts').text(data.total_alerts.toLocaleString());
            } else {
                console.error('Failed to load summary:', response.message);
            }
        })
        .fail(function(xhr, status, error) {
            console.error('AJAX error loading summary:', error);
        });
    }

    /**
     * Load 24-hour requests chart
     */
    function load24hChart() {
        return $.ajax({
            url: '/api/yori/stats/last24h',
            type: 'GET',
            dataType: 'json'
        })
        .done(function(response) {
            if (response.status === 'ok') {
                var data = response.data;

                // Extract labels and values
                var labels = data.map(function(item) {
                    var date = new Date(item.hour);
                    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
                });
                var values = data.map(function(item) {
                    return item.count;
                });

                // Destroy existing chart
                if (charts.last24h) {
                    charts.last24h.destroy();
                }

                // Create chart
                var ctx = document.getElementById('chart-24h').getContext('2d');
                charts.last24h = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Requests',
                            data: values,
                            borderColor: colors.primary,
                            backgroundColor: colors.primary + '20',
                            tension: 0.4,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                display: false
                            },
                            tooltip: {
                                mode: 'index',
                                intersect: false
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    precision: 0
                                }
                            }
                        }
                    }
                });
            } else {
                console.error('Failed to load 24h data:', response.message);
                showEmptyChart('chart-24h', 'No data available');
            }
        })
        .fail(function(xhr, status, error) {
            console.error('AJAX error loading 24h chart:', error);
            showEmptyChart('chart-24h', 'Error loading data');
        });
    }

    /**
     * Load endpoints distribution chart
     */
    function loadEndpointsChart() {
        return $.ajax({
            url: '/api/yori/stats/topEndpoints',
            type: 'GET',
            dataType: 'json'
        })
        .done(function(response) {
            if (response.status === 'ok') {
                var data = response.data;

                var labels = data.map(function(item) {
                    return item.endpoint;
                });
                var values = data.map(function(item) {
                    return item.count;
                });
                var backgroundColors = labels.map(function(label) {
                    return endpointColors[label] || colors.secondary;
                });

                // Destroy existing chart
                if (charts.endpoints) {
                    charts.endpoints.destroy();
                }

                // Create chart
                var ctx = document.getElementById('chart-endpoints').getContext('2d');
                charts.endpoints = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: values,
                            backgroundColor: backgroundColors,
                            borderWidth: 2,
                            borderColor: '#fff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                position: 'bottom'
                            }
                        }
                    }
                });
            } else {
                console.error('Failed to load endpoints data:', response.message);
                showEmptyChart('chart-endpoints', 'No data available');
            }
        })
        .fail(function(xhr, status, error) {
            console.error('AJAX error loading endpoints chart:', error);
            showEmptyChart('chart-endpoints', 'Error loading data');
        });
    }

    /**
     * Load devices chart
     */
    function loadDevicesChart() {
        return $.ajax({
            url: '/api/yori/stats/topDevices',
            type: 'GET',
            dataType: 'json'
        })
        .done(function(response) {
            if (response.status === 'ok') {
                var data = response.data;

                var labels = data.map(function(item) {
                    return item.device;
                });
                var values = data.map(function(item) {
                    return item.count;
                });

                // Destroy existing chart
                if (charts.devices) {
                    charts.devices.destroy();
                }

                // Create chart
                var ctx = document.getElementById('chart-devices').getContext('2d');
                charts.devices = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Requests',
                            data: values,
                            backgroundColor: colors.info,
                            borderColor: colors.info,
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        indexAxis: 'y',
                        plugins: {
                            legend: {
                                display: false
                            }
                        },
                        scales: {
                            x: {
                                beginAtZero: true,
                                ticks: {
                                    precision: 0
                                }
                            }
                        }
                    }
                });
            } else {
                console.error('Failed to load devices data:', response.message);
                showEmptyChart('chart-devices', 'No data available');
            }
        })
        .fail(function(xhr, status, error) {
            console.error('AJAX error loading devices chart:', error);
            showEmptyChart('chart-devices', 'Error loading data');
        });
    }

    /**
     * Load hourly distribution chart
     */
    function loadHourlyChart() {
        return $.ajax({
            url: '/api/yori/stats/hourlyDistribution',
            type: 'GET',
            dataType: 'json'
        })
        .done(function(response) {
            if (response.status === 'ok') {
                var data = response.data;

                // Fill in all 24 hours (0-23)
                var hourlyData = new Array(24).fill(0);
                data.forEach(function(item) {
                    var hour = parseInt(item.hour, 10);
                    hourlyData[hour] = item.count;
                });

                var labels = [];
                for (var i = 0; i < 24; i++) {
                    labels.push(i + ':00');
                }

                // Destroy existing chart
                if (charts.hourly) {
                    charts.hourly.destroy();
                }

                // Create chart
                var ctx = document.getElementById('chart-hourly').getContext('2d');
                charts.hourly = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Requests',
                            data: hourlyData,
                            backgroundColor: colors.success,
                            borderColor: colors.success,
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                display: false
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    precision: 0
                                }
                            }
                        }
                    }
                });
            } else {
                console.error('Failed to load hourly data:', response.message);
                showEmptyChart('chart-hourly', 'No data available');
            }
        })
        .fail(function(xhr, status, error) {
            console.error('AJAX error loading hourly chart:', error);
            showEmptyChart('chart-hourly', 'Error loading data');
        });
    }

    /**
     * Load recent alerts table
     */
    function loadRecentAlerts() {
        return $.ajax({
            url: '/api/yori/stats/recentAlerts',
            type: 'GET',
            dataType: 'json'
        })
        .done(function(response) {
            if (response.status === 'ok') {
                var data = response.data;
                var tbody = $('#alerts-table tbody');
                tbody.empty();

                if (data.length === 0) {
                    tbody.append('<tr><td colspan="5" class="text-center text-muted">No alerts found</td></tr>');
                } else {
                    data.forEach(function(alert) {
                        var timestamp = new Date(alert.timestamp).toLocaleString();
                        var row = '<tr>' +
                            '<td>' + timestamp + '</td>' +
                            '<td>' + escapeHtml(alert.client_ip) + '</td>' +
                            '<td>' + escapeHtml(alert.endpoint) + '</td>' +
                            '<td><span class="badge bg-warning">' + escapeHtml(alert.policy_name || 'N/A') + '</span></td>' +
                            '<td>' + escapeHtml(alert.policy_reason || '') + '</td>' +
                            '</tr>';
                        tbody.append(row);
                    });
                }
            } else {
                console.error('Failed to load alerts:', response.message);
                $('#alerts-table tbody').html('<tr><td colspan="5" class="text-center text-danger">Error loading alerts</td></tr>');
            }
        })
        .fail(function(xhr, status, error) {
            console.error('AJAX error loading alerts:', error);
            $('#alerts-table tbody').html('<tr><td colspan="5" class="text-center text-danger">Error loading alerts</td></tr>');
        });
    }

    /**
     * Show empty chart with message
     */
    function showEmptyChart(canvasId, message) {
        var ctx = document.getElementById(canvasId).getContext('2d');
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        ctx.font = '14px Arial';
        ctx.fillStyle = '#999';
        ctx.textAlign = 'center';
        ctx.fillText(message, ctx.canvas.width / 2, ctx.canvas.height / 2);
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        if (!text) return '';
        var map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.toString().replace(/[&<>"']/g, function(m) { return map[m]; });
    }

    // Public API
    return {
        init: init,
        loadAll: loadAll,
        loadSummary: loadSummary,
        load24hChart: load24hChart,
        loadEndpointsChart: loadEndpointsChart,
        loadDevicesChart: loadDevicesChart,
        loadHourlyChart: loadHourlyChart,
        loadRecentAlerts: loadRecentAlerts
    };
})();
