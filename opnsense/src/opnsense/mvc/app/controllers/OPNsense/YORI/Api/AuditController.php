<?php

/**
 * YORI Audit Log API Controller
 *
 * Provides JSON endpoints for audit log viewing, searching, and exporting
 *
 * @package OPNsense\YORI
 */

namespace OPNsense\YORI\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Config;

/**
 * Class AuditController
 * @package OPNsense\YORI\Api
 */
class AuditController extends ApiControllerBase
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
            error_log("YORI AuditController: Database connection failed: " . $e->getMessage());
            return null;
        }
    }

    /**
     * Search audit events with pagination and filters
     *
     * @return array
     */
    public function searchAction()
    {
        $this->sessionClose();
        $result = ['status' => 'error', 'data' => [], 'total' => 0];

        $db = $this->getDb();
        if ($db === null) {
            $result['message'] = 'Database not available';
            return $result;
        }

        // Get request parameters
        $request = $this->request;
        $page = (int)($request->getPost('page', 'int', 1));
        $limit = (int)($request->getPost('limit', 'int', 50));
        $offset = ($page - 1) * $limit;

        // Filter parameters
        $dateFrom = $request->getPost('date_from', 'string', '');
        $dateTo = $request->getPost('date_to', 'string', '');
        $endpoint = $request->getPost('endpoint', 'string', '');
        $clientIp = $request->getPost('client_ip', 'string', '');
        $searchTerm = $request->getPost('search', 'string', '');
        $eventType = $request->getPost('event_type', 'string', '');

        try {
            // Build WHERE clause
            $where = ['1=1'];
            $params = [];

            if (!empty($dateFrom)) {
                $where[] = "timestamp >= :date_from";
                $params[':date_from'] = $dateFrom;
            }
            if (!empty($dateTo)) {
                $where[] = "timestamp <= :date_to";
                $params[':date_to'] = $dateTo;
            }
            if (!empty($endpoint)) {
                $where[] = "endpoint = :endpoint";
                $params[':endpoint'] = $endpoint;
            }
            if (!empty($clientIp)) {
                $where[] = "client_ip = :client_ip";
                $params[':client_ip'] = $clientIp;
            }
            if (!empty($searchTerm)) {
                $where[] = "(prompt_preview LIKE :search OR policy_reason LIKE :search)";
                $params[':search'] = '%' . $searchTerm . '%';
            }
            if (!empty($eventType)) {
                $where[] = "event_type = :event_type";
                $params[':event_type'] = $eventType;
            }

            $whereClause = implode(' AND ', $where);

            // Get total count
            $countStmt = $db->prepare("
                SELECT COUNT(*) as total
                FROM audit_events
                WHERE {$whereClause}
            ");
            $countStmt->execute($params);
            $total = (int)$countStmt->fetch(\PDO::FETCH_ASSOC)['total'];

            // Get paginated results
            $stmt = $db->prepare("
                SELECT
                    id,
                    timestamp,
                    event_type,
                    client_ip,
                    client_device,
                    endpoint,
                    http_method,
                    http_path,
                    prompt_preview,
                    prompt_tokens,
                    response_status,
                    response_tokens,
                    response_duration_ms,
                    policy_name,
                    policy_result,
                    policy_reason,
                    user_agent
                FROM audit_events
                WHERE {$whereClause}
                ORDER BY timestamp DESC
                LIMIT :limit OFFSET :offset
            ");

            foreach ($params as $key => $value) {
                $stmt->bindValue($key, $value);
            }
            $stmt->bindValue(':limit', $limit, \PDO::PARAM_INT);
            $stmt->bindValue(':offset', $offset, \PDO::PARAM_INT);

            $stmt->execute();
            $data = $stmt->fetchAll(\PDO::FETCH_ASSOC);

            $result['status'] = 'ok';
            $result['data'] = $data;
            $result['total'] = $total;
            $result['page'] = $page;
            $result['pages'] = ceil($total / $limit);
        } catch (\PDOException $e) {
            $result['message'] = 'Query failed: ' . $e->getMessage();
        }

        return $result;
    }

    /**
     * Get single audit event details
     *
     * @return array
     */
    public function getAction()
    {
        $this->sessionClose();
        $result = ['status' => 'error', 'data' => null];

        $db = $this->getDb();
        if ($db === null) {
            $result['message'] = 'Database not available';
            return $result;
        }

        $id = $this->request->getPost('id', 'int', 0);
        if ($id <= 0) {
            $result['message'] = 'Invalid ID';
            return $result;
        }

        try {
            $stmt = $db->prepare("
                SELECT *
                FROM audit_events
                WHERE id = :id
            ");
            $stmt->bindValue(':id', $id, \PDO::PARAM_INT);
            $stmt->execute();
            $data = $stmt->fetch(\PDO::FETCH_ASSOC);

            if ($data) {
                $result['status'] = 'ok';
                $result['data'] = $data;
            } else {
                $result['message'] = 'Event not found';
            }
        } catch (\PDOException $e) {
            $result['message'] = 'Query failed: ' . $e->getMessage();
        }

        return $result;
    }

    /**
     * Export audit events to CSV
     *
     * @return array
     */
    public function exportAction()
    {
        $this->sessionClose();

        $db = $this->getDb();
        if ($db === null) {
            return ['status' => 'error', 'message' => 'Database not available'];
        }

        // Filter parameters (same as searchAction)
        $request = $this->request;
        $dateFrom = $request->getPost('date_from', 'string', '');
        $dateTo = $request->getPost('date_to', 'string', '');
        $endpoint = $request->getPost('endpoint', 'string', '');
        $clientIp = $request->getPost('client_ip', 'string', '');

        try {
            // Build WHERE clause
            $where = ['1=1'];
            $params = [];

            if (!empty($dateFrom)) {
                $where[] = "timestamp >= :date_from";
                $params[':date_from'] = $dateFrom;
            }
            if (!empty($dateTo)) {
                $where[] = "timestamp <= :date_to";
                $params[':date_to'] = $dateTo;
            }
            if (!empty($endpoint)) {
                $where[] = "endpoint = :endpoint";
                $params[':endpoint'] = $endpoint;
            }
            if (!empty($clientIp)) {
                $where[] = "client_ip = :client_ip";
                $params[':client_ip'] = $clientIp;
            }

            $whereClause = implode(' AND ', $where);

            $stmt = $db->prepare("
                SELECT
                    timestamp,
                    event_type,
                    client_ip,
                    client_device,
                    endpoint,
                    http_method,
                    http_path,
                    prompt_tokens,
                    response_status,
                    response_tokens,
                    response_duration_ms,
                    policy_result,
                    policy_reason
                FROM audit_events
                WHERE {$whereClause}
                ORDER BY timestamp DESC
                LIMIT 10000
            ");
            $stmt->execute($params);
            $data = $stmt->fetchAll(\PDO::FETCH_ASSOC);

            // Generate CSV
            $filename = 'yori_audit_' . date('Y-m-d_His') . '.csv';

            // Set headers for download
            header('Content-Type: text/csv');
            header('Content-Disposition: attachment; filename="' . $filename . '"');
            header('Cache-Control: no-cache, must-revalidate');
            header('Pragma: no-cache');

            $output = fopen('php://output', 'w');

            // Write header row
            if (count($data) > 0) {
                fputcsv($output, array_keys($data[0]));
            }

            // Write data rows
            foreach ($data as $row) {
                fputcsv($output, $row);
            }

            fclose($output);
            exit;
        } catch (\PDOException $e) {
            return ['status' => 'error', 'message' => 'Export failed: ' . $e->getMessage()];
        }
    }

    /**
     * Get list of unique endpoints for filter dropdown
     *
     * @return array
     */
    public function endpointsAction()
    {
        $this->sessionClose();
        $result = ['status' => 'error', 'data' => []];

        $db = $this->getDb();
        if ($db === null) {
            $result['message'] = 'Database not available';
            return $result;
        }

        try {
            $stmt = $db->query("
                SELECT DISTINCT endpoint
                FROM audit_events
                ORDER BY endpoint ASC
            ");
            $data = $stmt->fetchAll(\PDO::FETCH_COLUMN);

            $result['status'] = 'ok';
            $result['data'] = $data;
        } catch (\PDOException $e) {
            $result['message'] = 'Query failed: ' . $e->getMessage();
        }

        return $result;
    }

    /**
     * Get list of unique client IPs for filter dropdown
     *
     * @return array
     */
    public function clientsAction()
    {
        $this->sessionClose();
        $result = ['status' => 'error', 'data' => []];

        $db = $this->getDb();
        if ($db === null) {
            $result['message'] = 'Database not available';
            return $result;
        }

        try {
            $stmt = $db->query("
                SELECT DISTINCT
                    client_ip,
                    COALESCE(client_device, client_ip) as display_name
                FROM audit_events
                ORDER BY client_ip ASC
            ");
            $data = $stmt->fetchAll(\PDO::FETCH_ASSOC);

            $result['status'] = 'ok';
            $result['data'] = $data;
        } catch (\PDOException $e) {
            $result['message'] = 'Query failed: ' . $e->getMessage();
        }

        return $result;
    }
}
