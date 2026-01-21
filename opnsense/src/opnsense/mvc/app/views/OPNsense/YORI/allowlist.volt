{#
 # Copyright (C) 2026 James Henry
 # All rights reserved.
 #
 # YORI Allowlist Management Interface
 #}

<script>
    $( document ).ready(function() {
        var data_get_map = {'frm_allowlist_settings':"/api/yori/allowlist/get"};
        mapDataToFormUI(data_get_map).done(function(data){
            formatTokenizersUI();
            $('.selectpicker').selectpicker('refresh');
        });

        updateServiceControlUI('yori');

        // Link save button to API set action
        $("#saveAct").click(function(){
            saveFormToEndpoint(url="/api/yori/allowlist/set", formid='frm_allowlist_settings',callback_ok=function(){
                $("#saveAct_progress").addClass("fa fa-spinner fa-pulse");
                ajaxCall(url="/api/yori/service/reconfigure", sendData={}, callback=function(data,status) {
                    updateServiceControlUI('yori');
                    $("#saveAct_progress").removeClass("fa fa-spinner fa-pulse");
                });
            });
        });

        // Load device list
        function loadDevices() {
            ajaxCall(url="/api/yori/allowlist/searchDevice", sendData={}, callback=function(data,status) {
                if (data && data.rows) {
                    updateDeviceTable(data.rows);
                }
            });
        }

        // Add device button
        $("#addDevice").click(function(){
            var ip = $("#device_ip").val();
            var name = $("#device_name").val();
            var mac = $("#device_mac").val();
            var permanent = $("#device_permanent").is(':checked');

            if (!ip || !name) {
                alert("IP address and name are required");
                return;
            }

            ajaxCall(url="/api/yori/allowlist/addDevice", sendData={
                ip: ip,
                name: name,
                mac: mac,
                permanent: permanent
            }, callback=function(data,status) {
                if (data.result == "saved") {
                    loadDevices();
                    $("#device_ip").val('');
                    $("#device_name").val('');
                    $("#device_mac").val('');
                    $("#device_permanent").prop('checked', false);
                }
            });
        });

        // Remove device
        $(".removeDevice").click(function(){
            var ip = $(this).data('ip');
            if (confirm("Remove device from allowlist?")) {
                ajaxCall(url="/api/yori/allowlist/delDevice", sendData={ip: ip}, callback=function(data,status) {
                    loadDevices();
                });
            }
        });

        // Load devices on page load
        loadDevices();
    });
</script>

<div class="content-box">
    <div class="content-box-main">
        <div class="table-responsive">
            <div class="col-md-12">
                <h1>{{ lang._('YORI Allowlist Management') }}</h1>
                <p>{{ lang._('Configure devices that should bypass enforcement policies.') }}</p>

                <ul class="nav nav-tabs" data-tabs="tabs" id="maintabs">
                    <li class="active"><a data-toggle="tab" href="#devices">{{ lang._('Devices') }}</a></li>
                    <li><a data-toggle="tab" href="#groups">{{ lang._('Groups') }}</a></li>
                    <li><a data-toggle="tab" href="#time_exceptions">{{ lang._('Time Exceptions') }}</a></li>
                    <li><a data-toggle="tab" href="#recent">{{ lang._('Recent Devices') }}</a></li>
                </ul>

                <div class="tab-content content-box tab-content">
                    <!-- Devices Tab -->
                    <div id="devices" class="tab-pane fade in active">
                        <h2>{{ lang._('Allowlisted Devices') }}</h2>
                        <p>{{ lang._('Devices that will never be blocked by enforcement policies.') }}</p>

                        <div class="panel panel-default">
                            <div class="panel-heading">{{ lang._('Add New Device') }}</div>
                            <div class="panel-body">
                                <div class="form-group">
                                    <label>{{ lang._('IP Address') }} *</label>
                                    <input type="text" id="device_ip" class="form-control" placeholder="192.168.1.100">
                                </div>
                                <div class="form-group">
                                    <label>{{ lang._('Device Name') }} *</label>
                                    <input type="text" id="device_name" class="form-control" placeholder="Dad's Laptop">
                                </div>
                                <div class="form-group">
                                    <label>{{ lang._('MAC Address') }}</label>
                                    <input type="text" id="device_mac" class="form-control" placeholder="aa:bb:cc:dd:ee:ff">
                                    <small class="form-text text-muted">{{ lang._('Optional: Allows device to stay allowlisted even if IP changes') }}</small>
                                </div>
                                <div class="form-group">
                                    <div class="checkbox">
                                        <label>
                                            <input type="checkbox" id="device_permanent">
                                            {{ lang._('Permanent (never block, even if disabled)') }}
                                        </label>
                                    </div>
                                </div>
                                <button id="addDevice" class="btn btn-primary">{{ lang._('Add Device') }}</button>
                            </div>
                        </div>

                        <div class="panel panel-default">
                            <div class="panel-heading">{{ lang._('Current Allowlist') }}</div>
                            <div class="panel-body">
                                <table id="deviceTable" class="table table-striped table-condensed">
                                    <thead>
                                        <tr>
                                            <th>{{ lang._('Name') }}</th>
                                            <th>{{ lang._('IP Address') }}</th>
                                            <th>{{ lang._('MAC Address') }}</th>
                                            <th>{{ lang._('Status') }}</th>
                                            <th>{{ lang._('Actions') }}</th>
                                        </tr>
                                    </thead>
                                    <tbody id="deviceTableBody">
                                        <tr>
                                            <td colspan="5" class="text-center">{{ lang._('Loading...') }}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <!-- Groups Tab -->
                    <div id="groups" class="tab-pane fade">
                        <h2>{{ lang._('Device Groups') }}</h2>
                        <p>{{ lang._('Organize devices into groups for easier management.') }}</p>
                        <p class="text-muted">{{ lang._('Group management UI - to be implemented') }}</p>
                    </div>

                    <!-- Time Exceptions Tab -->
                    <div id="time_exceptions" class="tab-pane fade">
                        <h2>{{ lang._('Time-Based Exceptions') }}</h2>
                        <p>{{ lang._('Allow access during specific hours (e.g., homework time 3-6pm).') }}</p>

                        <div class="panel panel-default">
                            <div class="panel-heading">{{ lang._('Example: Homework Hours') }}</div>
                            <div class="panel-body">
                                <p><strong>{{ lang._('Name:') }}</strong> homework_hours</p>
                                <p><strong>{{ lang._('Days:') }}</strong> Monday - Friday</p>
                                <p><strong>{{ lang._('Time:') }}</strong> 3:00 PM - 6:00 PM</p>
                                <p><strong>{{ lang._('Devices:') }}</strong> Kid's Laptop (192.168.1.102)</p>
                                <p class="text-muted">{{ lang._('Configure in yori.conf for now. UI management coming soon.') }}</p>
                            </div>
                        </div>
                    </div>

                    <!-- Recent Devices Tab -->
                    <div id="recent" class="tab-pane fade">
                        <h2>{{ lang._('Device Discovery') }}</h2>
                        <p>{{ lang._('Recently seen devices - click to add to allowlist.') }}</p>
                        <p class="text-muted">{{ lang._('Requires audit database integration - to be implemented') }}</p>
                    </div>
                </div>

                <div class="col-md-12">
                    <hr/>
                    <button class="btn btn-primary" id="saveAct" type="button">
                        <b>{{ lang._('Save') }}</b> <i id="saveAct_progress" class=""></i>
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>
