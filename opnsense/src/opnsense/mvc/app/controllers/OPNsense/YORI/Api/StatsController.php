<?php

/**
 * YORI Statistics API Controller
 *
 * Provides JSON endpoints for dashboard charts and statistics
 *
 * @package OPNsense\YORI
 */

namespace OPNsense\YORI\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Config;

/**
 * Class StatsController
 * @package OPNsense\YORI\Api
 */
class StatsController extends ApiControllerBase
{
    /**
     * Database path
     */
    private const DB_PATH = '/var/db/yori/audit.db';

    /**
     * Get database connection
     *
     * @return \PDO|null
     */
    private function getDb()
    {
        try {
            if (!file_exists(self::DB_PATH)) {
                return null;
            }
            $db = new \PDO('sqlite:' . self::DB_PATH);
            $db->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);
            return $db;
        } catch (\PDOException $e) {
            error_log("YORI StatsController: Database connection failed: " . $e->getMessage());
            return null;
        }
    }

    /**
     * Get requests for last 24 hours
     *
     * @return array
     */
    public function last24hAction()
    {
        $this->sessionClose();
        $result = ['status' => 'error', 'data' => []];

        $db = $this->getDb();
        if ($db === null) {
            $result['message'] = 'Database not available';
            return $result;
        }

        try {
            $stmt = $db->prepare("
                SELECT
                    strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                    COUNT(*) as count
                FROM audit_events
                WHERE timestamp >= datetime('now', '-24 hours')
                    AND event_type = 'request'
                GROUP BY strftime('%Y-%m-%d %H:00:00', timestamp)
                ORDER BY hour ASC
            ");
            $stmt->execute();
            $data = $stmt->fetchAll(\PDO::FETCH_ASSOC);

            $result['status'] = 'ok';
            $result['data'] = $data;
        } catch (\PDOException $e) {
            $result['message'] = 'Query failed: ' . $e->getMessage();
        }

        return $result;
    }

    /**
     * Get top endpoints distribution
     *
     * @return array
     */
    public function topEndpointsAction()
    {
        $this->sessionClose();
        $result = ['status' => 'error', 'data' => []];

        $db = $this->getDb();
        if ($db === null) {
            $result['message'] = 'Database not available';
            return $result;
        }

        try {
            $stmt = $db->prepare("
                SELECT
                    endpoint,
                    COUNT(*) as count
                FROM audit_events
                WHERE event_type = 'request'
                GROUP BY endpoint
                ORDER BY count DESC
                LIMIT 10
            ");
            $stmt->execute();
            $data = $stmt->fetchAll(\PDO::FETCH_ASSOC);

            $result['status'] = 'ok';
            $result['data'] = $data;
        } catch (\PDOException $e) {
            $result['message'] = 'Query failed: ' . $e->getMessage();
        }

        return $result;
    }

    /**
     * Get top devices by request count
     *
     * @return array
     */
    public function topDevicesAction()
    {
        $this->sessionClose();
        $result = ['status' => 'error', 'data' => []];

        $db = $this->getDb();
        if ($db === null) {
            $result['message'] = 'Database not available';
            return $result;
        }

        try {
            $stmt = $db->prepare("
                SELECT
                    COALESCE(client_device, client_ip) as device,
                    client_ip,
                    COUNT(*) as count
                FROM audit_events
                WHERE event_type = 'request'
                GROUP BY client_ip, client_device
                ORDER BY count DESC
                LIMIT 10
            ");
            $stmt->execute();
            $data = $stmt->fetchAll(\PDO::FETCH_ASSOC);

            $result['status'] = 'ok';
            $result['data'] = $data;
        } catch (\PDOException $e) {
            $result['message'] = 'Query failed: ' . $e->getMessage();
        }

        return $result;
    }

    /**
     * Get recent alerts
     *
     * @return array
     */
    public function recentAlertsAction()
    {
        $this->sessionClose();
        $result = ['status' => 'error', 'data' => []];

        $db = $this->getDb();
        if ($db === null) {
            $result['message'] = 'Database not available';
            return $result;
        }

        try {
            $stmt = $db->prepare("
                SELECT
                    id,
                    timestamp,
                    client_ip,
                    endpoint,
                    policy_name,
                    policy_reason,
                    prompt_preview
                FROM audit_events
                WHERE policy_result IN ('alert', 'block')
                ORDER BY timestamp DESC
                LIMIT 10
            ");
            $stmt->execute();
            $data = $stmt->fetchAll(\PDO::FETCH_ASSOC);

            $result['status'] = 'ok';
            $result['data'] = $data;
        } catch (\PDOException $e) {
            $result['message'] = 'Query failed: ' . $e->getMessage();
        }

        return $result;
    }

    /**
     * Get summary statistics
     *
     * @return array
     */
    public function summaryAction()
    {
        $this->sessionClose();
        $result = ['status' => 'error', 'data' => []];

        $db = $this->getDb();
        if ($db === null) {
            $result['message'] = 'Database not available';
            return $result;
        }

        try {
            // Get total requests
            $stmt = $db->query("SELECT COUNT(*) as total FROM audit_events WHERE event_type = 'request'");
            $total = $stmt->fetch(\PDO::FETCH_ASSOC)['total'];

            // Get last 24h requests
            $stmt = $db->query("
                SELECT COUNT(*) as count
                FROM audit_events
                WHERE event_type = 'request'
                    AND timestamp >= datetime('now', '-24 hours')
            ");
            $last24h = $stmt->fetch(\PDO::FETCH_ASSOC)['count'];

            // Get last 7 days requests
            $stmt = $db->query("
                SELECT COUNT(*) as count
                FROM audit_events
                WHERE event_type = 'request'
                    AND timestamp >= datetime('now', '-7 days')
            ");
            $last7days = $stmt->fetch(\PDO::FETCH_ASSOC)['count'];

            // Get average tokens
            $stmt = $db->query("
                SELECT AVG(prompt_tokens + response_tokens) as avg_tokens
                FROM audit_events
                WHERE event_type = 'request'
                    AND prompt_tokens IS NOT NULL
                    AND response_tokens IS NOT NULL
            ");
            $avgTokens = $stmt->fetch(\PDO::FETCH_ASSOC)['avg_tokens'];

            // Get total alerts
            $stmt = $db->query("
                SELECT COUNT(*) as count
                FROM audit_events
                WHERE policy_result IN ('alert', 'block')
            ");
            $totalAlerts = $stmt->fetch(\PDO::FETCH_ASSOC)['count'];

            $result['status'] = 'ok';
            $result['data'] = [
                'total_requests' => (int)$total,
                'last_24h' => (int)$last24h,
                'last_7days' => (int)$last7days,
                'avg_tokens' => round((float)$avgTokens, 2),
                'total_alerts' => (int)$totalAlerts
            ];
        } catch (\PDOException $e) {
            $result['message'] = 'Query failed: ' . $e->getMessage();
        }

        return $result;
    }

    /**
     * Get hourly distribution (peak usage hours)
     *
     * @return array
     */
    public function hourlyDistributionAction()
    {
        $this->sessionClose();
        $result = ['status' => 'error', 'data' => []];

        $db = $this->getDb();
        if ($db === null) {
            $result['message'] = 'Database not available';
            return $result;
        }

        try {
            $stmt = $db->prepare("
                SELECT
                    strftime('%H', timestamp) as hour,
                    COUNT(*) as count
                FROM audit_events
                WHERE event_type = 'request'
                    AND timestamp >= datetime('now', '-7 days')
                GROUP BY strftime('%H', timestamp)
                ORDER BY hour ASC
            ");
            $stmt->execute();
            $data = $stmt->fetchAll(\PDO::FETCH_ASSOC);

            $result['status'] = 'ok';
            $result['data'] = $data;
        } catch (\PDOException $e) {
            $result['message'] = 'Query failed: ' . $e->getMessage();
        }

        return $result;
    }
}
