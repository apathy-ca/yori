<?php

/**
 * Copyright (C) 2026 James Henry
 * All rights reserved.
 *
 * YORI Allowlist API Controller
 *
 * This controller provides API endpoints for managing the YORI allowlist.
 * It interfaces with the Python backend via subprocess calls.
 */

namespace OPNsense\YORI\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Backend;

/**
 * Class AllowlistController
 * @package OPNsense\YORI\Api
 */
class AllowlistController extends ApiControllerBase
{
    /**
     * Get current allowlist configuration
     * @return array
     */
    public function getAction()
    {
        $backend = new Backend();
        $response = $backend->configdRun("yori allowlist get");

        if (!empty($response)) {
            return json_decode($response, true);
        }

        return ['devices' => [], 'groups' => [], 'time_exceptions' => []];
    }

    /**
     * Set allowlist configuration
     * @return array
     */
    public function setAction()
    {
        $backend = new Backend();
        $data = $this->request->getPost();

        // Validate input
        // TODO: Add validation

        $result = $backend->configdRun("yori allowlist set", $data);

        return ['result' => $result ? 'saved' : 'failed'];
    }

    /**
     * Search/list allowlist devices
     * @return array
     */
    public function searchDeviceAction()
    {
        $backend = new Backend();
        $response = $backend->configdRun("yori allowlist search");

        if (!empty($response)) {
            $devices = json_decode($response, true);
            return ['rows' => $devices];
        }

        return ['rows' => []];
    }

    /**
     * Add a device to the allowlist
     * @return array
     */
    public function addDeviceAction()
    {
        if ($this->request->isPost()) {
            $ip = $this->request->getPost('ip');
            $name = $this->request->getPost('name');
            $mac = $this->request->getPost('mac', null);
            $permanent = $this->request->getPost('permanent', false);

            // Validate IP
            if (!filter_var($ip, FILTER_VALIDATE_IP)) {
                return ['result' => 'failed', 'message' => 'Invalid IP address'];
            }

            // Validate name
            if (empty($name)) {
                return ['result' => 'failed', 'message' => 'Name is required'];
            }

            $backend = new Backend();
            $params = [
                'ip' => $ip,
                'name' => $name,
                'mac' => $mac,
                'permanent' => $permanent
            ];

            $result = $backend->configdRun("yori allowlist add", $params);

            return ['result' => $result ? 'saved' : 'failed'];
        }

        return ['result' => 'failed', 'message' => 'Method not allowed'];
    }

    /**
     * Remove a device from the allowlist
     * @return array
     */
    public function delDeviceAction()
    {
        if ($this->request->isPost()) {
            $ip = $this->request->getPost('ip');

            if (!filter_var($ip, FILTER_VALIDATE_IP)) {
                return ['result' => 'failed', 'message' => 'Invalid IP address'];
            }

            $backend = new Backend();
            $result = $backend->configdRun("yori allowlist del " . escapeshellarg($ip));

            return ['result' => $result ? 'deleted' : 'failed'];
        }

        return ['result' => 'failed', 'message' => 'Method not allowed'];
    }

    /**
     * Get recent devices for discovery
     * @return array
     */
    public function getRecentDevicesAction()
    {
        $backend = new Backend();
        $response = $backend->configdRun("yori allowlist recent");

        if (!empty($response)) {
            $devices = json_decode($response, true);
            return ['devices' => $devices];
        }

        return ['devices' => []];
    }

    /**
     * Add a time-based exception
     * @return array
     */
    public function addTimeExceptionAction()
    {
        if ($this->request->isPost()) {
            $name = $this->request->getPost('name');
            $days = $this->request->getPost('days');
            $start_time = $this->request->getPost('start_time');
            $end_time = $this->request->getPost('end_time');
            $device_ips = $this->request->getPost('device_ips');

            // Validate required fields
            if (empty($name) || empty($days) || empty($start_time) || empty($end_time)) {
                return ['result' => 'failed', 'message' => 'Missing required fields'];
            }

            $backend = new Backend();
            $params = [
                'name' => $name,
                'days' => $days,
                'start_time' => $start_time,
                'end_time' => $end_time,
                'device_ips' => $device_ips
            ];

            $result = $backend->configdRun("yori timeexception add", $params);

            return ['result' => $result ? 'saved' : 'failed'];
        }

        return ['result' => 'failed', 'message' => 'Method not allowed'];
    }

    /**
     * Remove a time-based exception
     * @return array
     */
    public function delTimeExceptionAction()
    {
        if ($this->request->isPost()) {
            $name = $this->request->getPost('name');

            if (empty($name)) {
                return ['result' => 'failed', 'message' => 'Name is required'];
            }

            $backend = new Backend();
            $result = $backend->configdRun("yori timeexception del " . escapeshellarg($name));

            return ['result' => $result ? 'deleted' : 'failed'];
        }

        return ['result' => 'failed', 'message' => 'Method not allowed'];
    }
}
