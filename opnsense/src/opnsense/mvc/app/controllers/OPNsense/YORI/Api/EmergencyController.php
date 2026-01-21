<?php

/**
 * Copyright (C) 2026 James Henry
 * All rights reserved.
 *
 * YORI Emergency Override API Controller
 *
 * This controller provides API endpoints for emergency override management.
 */

namespace OPNsense\YORI\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Backend;

/**
 * Class EmergencyController
 * @package OPNsense\YORI\Api
 */
class EmergencyController extends ApiControllerBase
{
    /**
     * Get emergency override status
     * @return array
     */
    public function getStatusAction()
    {
        $backend = new Backend();
        $response = $backend->configdRun("yori emergency status");

        if (!empty($response)) {
            $status = json_decode($response, true);
            return ['status' => $status];
        }

        return [
            'status' => [
                'enabled' => false,
                'activated_at' => null,
                'activated_by' => null,
                'require_password' => true,
                'has_password' => false
            ]
        ];
    }

    /**
     * Activate emergency override
     * @return array
     */
    public function activateAction()
    {
        if ($this->request->isPost()) {
            $password = $this->request->getPost('password');
            $client_ip = $_SERVER['REMOTE_ADDR'] ?? 'unknown';

            if (empty($password)) {
                return [
                    'result' => 'failed',
                    'message' => 'Password is required'
                ];
            }

            $backend = new Backend();
            $params = [
                'password' => $password,
                'activated_by' => $client_ip
            ];

            $result = $backend->configdRun("yori emergency activate", $params);
            $response = json_decode($result, true);

            if ($response && $response['success']) {
                // Log the activation
                syslog(LOG_WARNING, "YORI: Emergency override activated by {$client_ip}");

                return [
                    'result' => 'success',
                    'message' => $response['message'] ?? 'Emergency override activated'
                ];
            } else {
                return [
                    'result' => 'failed',
                    'message' => $response['message'] ?? 'Failed to activate override'
                ];
            }
        }

        return ['result' => 'failed', 'message' => 'Method not allowed'];
    }

    /**
     * Deactivate emergency override
     * @return array
     */
    public function deactivateAction()
    {
        if ($this->request->isPost()) {
            $password = $this->request->getPost('password');

            if (empty($password)) {
                return [
                    'result' => 'failed',
                    'message' => 'Password is required'
                ];
            }

            $backend = new Backend();
            $params = ['password' => $password];

            $result = $backend->configdRun("yori emergency deactivate", $params);
            $response = json_decode($result, true);

            if ($response && $response['success']) {
                // Log the deactivation
                syslog(LOG_WARNING, "YORI: Emergency override deactivated");

                return [
                    'result' => 'success',
                    'message' => $response['message'] ?? 'Emergency override deactivated'
                ];
            } else {
                return [
                    'result' => 'failed',
                    'message' => $response['message'] ?? 'Failed to deactivate override'
                ];
            }
        }

        return ['result' => 'failed', 'message' => 'Method not allowed'];
    }

    /**
     * Set emergency override password
     * @return array
     */
    public function setPasswordAction()
    {
        if ($this->request->isPost()) {
            $old_password = $this->request->getPost('old_password');
            $new_password = $this->request->getPost('new_password');

            if (empty($new_password)) {
                return [
                    'result' => 'failed',
                    'message' => 'New password is required'
                ];
            }

            // Validate password strength
            if (strlen($new_password) < 8) {
                return [
                    'result' => 'failed',
                    'message' => 'Password must be at least 8 characters'
                ];
            }

            $backend = new Backend();
            $params = [
                'old_password' => $old_password,
                'new_password' => $new_password
            ];

            $result = $backend->configdRun("yori emergency setpassword", $params);
            $response = json_decode($result, true);

            if ($response && $response['success']) {
                return [
                    'result' => 'success',
                    'message' => 'Password updated successfully'
                ];
            } else {
                return [
                    'result' => 'failed',
                    'message' => $response['message'] ?? 'Failed to update password'
                ];
            }
        }

        return ['result' => 'failed', 'message' => 'Method not allowed'];
    }
}
