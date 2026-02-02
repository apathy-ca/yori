<?php

/**
 * Copyright (C) 2026 YORI Project
 * All rights reserved.
 *
 * Token tracking and cost monitoring API controller.
 */

namespace OPNsense\YORI\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Backend;

/**
 * Class TokenController
 * @package OPNsense\YORI\Api
 */
class TokenController extends ApiControllerBase
{
    /**
     * Get token usage statistics
     * @return array
     */
    public function statsAction()
    {
        $days = (int)$this->request->get('days', 'int', 7);
        $clientIp = $this->request->get('client_ip', 'string', null);

        $backend = new Backend();
        $params = json_encode(['days' => $days, 'client_ip' => $clientIp]);
        $response = $backend->configdRun("yori token stats", [$params]);

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return array('result' => 'success', 'stats' => $data);
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to get token stats');
    }

    /**
     * Get device usage breakdown
     * @return array
     */
    public function devicesAction()
    {
        $days = (int)$this->request->get('days', 'int', 7);

        $backend = new Backend();
        $response = $backend->configdRun("yori token devices", [$days]);

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return array('result' => 'success', 'devices' => $data);
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to get device usage');
    }

    /**
     * Get today's usage for a client
     * @return array
     */
    public function todayAction()
    {
        $clientIp = $this->request->get('client_ip', 'string', null);

        $backend = new Backend();
        $response = $backend->configdRun("yori token today", [$clientIp ?? '']);

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return array('result' => 'success', 'today' => $data);
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to get today usage');
    }

    /**
     * Get cost summary
     * @return array
     */
    public function costSummaryAction()
    {
        $days = (int)$this->request->get('days', 'int', 30);

        $backend = new Backend();
        $response = $backend->configdRun("yori cost summary", [$days]);

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return array('result' => 'success', 'summary' => $data);
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to get cost summary');
    }

    /**
     * List budgets
     * @return array
     */
    public function budgetsAction()
    {
        $backend = new Backend();
        $response = $backend->configdRun("yori budget list");

        if ($response) {
            $data = json_decode($response, true);
            if ($data !== null) {
                return array('result' => 'success', 'budgets' => $data);
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to get budgets');
    }

    /**
     * Create or update budget
     * @return array
     */
    public function setBudgetAction()
    {
        $result = array('result' => 'failed');

        if (!$this->request->isPost()) {
            $result['message'] = 'POST request required';
            return $result;
        }

        $data = $this->request->getJsonRawBody(true);
        if (empty($data['name'])) {
            $result['message'] = 'Budget name required';
            return $result;
        }

        $backend = new Backend();
        $response = $backend->configdRun("yori budget set", [json_encode($data)]);

        if ($response) {
            $decoded = json_decode($response, true);
            if ($decoded && isset($decoded['success']) && $decoded['success']) {
                return array('result' => 'success', 'message' => 'Budget saved');
            }
        }

        $result['message'] = 'Failed to save budget';
        return $result;
    }

    /**
     * Delete budget
     * @param string $name Budget name
     * @return array
     */
    public function deleteBudgetAction($name)
    {
        $result = array('result' => 'failed');

        if (!$this->request->isPost()) {
            $result['message'] = 'POST request required';
            return $result;
        }

        $backend = new Backend();
        $response = $backend->configdRun("yori budget delete", [$name]);

        if ($response) {
            $decoded = json_decode($response, true);
            if ($decoded && isset($decoded['success']) && $decoded['success']) {
                return array('result' => 'success', 'message' => 'Budget deleted');
            }
        }

        $result['message'] = 'Failed to delete budget';
        return $result;
    }

    /**
     * Check budgets and get alerts
     * @return array
     */
    public function checkBudgetsAction()
    {
        $backend = new Backend();
        $response = $backend->configdRun("yori budget check");

        if ($response) {
            $data = json_decode($response, true);
            if ($data !== null) {
                return array('result' => 'success', 'alerts' => $data);
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to check budgets');
    }

    /**
     * Get budget alerts
     * @return array
     */
    public function alertsAction()
    {
        $days = (int)$this->request->get('days', 'int', 7);
        $unacknowledged = $this->request->get('unacknowledged', 'int', 0);

        $backend = new Backend();
        $response = $backend->configdRun("yori budget alerts", [$days, $unacknowledged]);

        if ($response) {
            $data = json_decode($response, true);
            if ($data !== null) {
                return array('result' => 'success', 'alerts' => $data);
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to get alerts');
    }

    /**
     * Acknowledge alert
     * @param int $id Alert ID
     * @return array
     */
    public function acknowledgeAlertAction($id)
    {
        $result = array('result' => 'failed');

        if (!$this->request->isPost()) {
            $result['message'] = 'POST request required';
            return $result;
        }

        $backend = new Backend();
        $response = $backend->configdRun("yori budget acknowledge", [$id]);

        if ($response) {
            $decoded = json_decode($response, true);
            if ($decoded && isset($decoded['success']) && $decoded['success']) {
                return array('result' => 'success', 'message' => 'Alert acknowledged');
            }
        }

        $result['message'] = 'Failed to acknowledge alert';
        return $result;
    }
}
