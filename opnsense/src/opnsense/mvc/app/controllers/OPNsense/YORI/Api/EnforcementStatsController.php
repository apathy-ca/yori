<?php

/**
 * YORI Enforcement Statistics API Controller
 *
 * Provides REST API endpoints for enforcement statistics and metrics.
 * Calls Python enforcement_stats module to retrieve data from SQLite.
 */

namespace OPNsense\YORI\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Backend;

class EnforcementStatsController extends ApiControllerBase
{
    /**
     * Get enforcement summary statistics
     *
     * GET /api/yori/enforcement/stats
     *
     * @return array Enforcement summary
     */
    public function statsAction()
    {
        $this->sessionClose();

        $backend = new Backend();
        $response = $backend->configdRun("yori enforcement stats");

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return [
                    'status' => 'success',
                    'summary' => $data['summary'],
                    'mode' => $data['mode'] ?? 'observe'
                ];
            }
        }

        return [
            'status' => 'error',
            'message' => 'Failed to retrieve enforcement statistics',
            'summary' => [
                'total_blocks' => 0,
                'total_overrides' => 0,
                'total_bypasses' => 0,
                'total_alerts' => 0,
                'total_allows' => 0,
                'override_success_rate' => 0.0,
                'top_blocking_policy' => null,
                'most_blocked_client' => null
            ],
            'mode' => 'observe'
        ];
    }

    /**
     * Get recent block events
     *
     * GET /api/yori/enforcement/recent_blocks
     *
     * @return array Recent blocks
     */
    public function recent_blocksAction()
    {
        $this->sessionClose();

        $limit = $this->request->get('limit', 'int', 50);

        $backend = new Backend();
        $response = $backend->configdRun("yori enforcement recent_blocks {$limit}");

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return [
                    'status' => 'success',
                    'blocks' => $data['blocks']
                ];
            }
        }

        return [
            'status' => 'error',
            'message' => 'Failed to retrieve recent blocks',
            'blocks' => []
        ];
    }

    /**
     * Get top blocking policies
     *
     * GET /api/yori/enforcement/top_policies
     *
     * @return array Top policies
     */
    public function top_policiesAction()
    {
        $this->sessionClose();

        $limit = $this->request->get('limit', 'int', 10);
        $days = $this->request->get('days', 'int', 7);

        $backend = new Backend();
        $response = $backend->configdRun("yori enforcement top_policies {$limit} {$days}");

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return [
                    'status' => 'success',
                    'policies' => $data['policies']
                ];
            }
        }

        return [
            'status' => 'error',
            'message' => 'Failed to retrieve top policies',
            'policies' => []
        ];
    }

    /**
     * Get enforcement timeline
     *
     * GET /api/yori/enforcement/timeline
     *
     * @return array Timeline events
     */
    public function timelineAction()
    {
        $this->sessionClose();

        $hours = $this->request->get('hours', 'int', 24);
        $limit = $this->request->get('limit', 'int', 50);
        $action = $this->request->get('action', 'string', '');
        $clientIp = $this->request->get('client_ip', 'string', '');

        $params = "{$hours} {$limit}";
        if (!empty($action)) {
            $params .= " --action=" . escapeshellarg($action);
        }
        if (!empty($clientIp)) {
            $params .= " --client-ip=" . escapeshellarg($clientIp);
        }

        $backend = new Backend();
        $response = $backend->configdRun("yori enforcement timeline {$params}");

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return [
                    'status' => 'success',
                    'events' => $data['events']
                ];
            }
        }

        return [
            'status' => 'error',
            'message' => 'Failed to retrieve timeline events',
            'events' => []
        ];
    }

    /**
     * Get daily enforcement statistics
     *
     * GET /api/yori/enforcement/daily_stats
     *
     * @return array Daily statistics
     */
    public function daily_statsAction()
    {
        $this->sessionClose();

        $days = $this->request->get('days', 'int', 30);

        $backend = new Backend();
        $response = $backend->configdRun("yori enforcement daily_stats {$days}");

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return [
                    'status' => 'success',
                    'stats' => $data['stats']
                ];
            }
        }

        return [
            'status' => 'error',
            'message' => 'Failed to retrieve daily statistics',
            'stats' => []
        ];
    }

    /**
     * Get enforcement mode history
     *
     * GET /api/yori/enforcement/mode_history
     *
     * @return array Mode change history
     */
    public function mode_historyAction()
    {
        $this->sessionClose();

        $limit = $this->request->get('limit', 'int', 20);

        $backend = new Backend();
        $response = $backend->configdRun("yori enforcement mode_history {$limit}");

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return [
                    'status' => 'success',
                    'history' => $data['history']
                ];
            }
        }

        return [
            'status' => 'error',
            'message' => 'Failed to retrieve mode history',
            'history' => []
        ];
    }
}
