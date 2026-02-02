<?php

/**
 * Copyright (C) 2026 YORI Project
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice,
 *    this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
 * INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
 * AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 */

namespace OPNsense\YORI\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Backend;

/**
 * Class AuditController
 * @package OPNsense\YORI\Api
 * Handles audit log queries and exports
 */
class AuditController extends ApiControllerBase
{
    private $dbPath = '/var/db/yori/audit.db';

    /**
     * Search audit logs with filters
     * @return array search results
     */
    public function searchAction()
    {
        $result = array('result' => 'success', 'rows' => array(), 'total' => 0);

        // Get query parameters
        $page = (int)$this->request->get('page', 'int', 1);
        $limit = (int)$this->request->get('limit', 'int', 50);
        $offset = ($page - 1) * $limit;

        $startDate = $this->request->get('start_date', 'string', null);
        $endDate = $this->request->get('end_date', 'string', null);
        $endpoint = $this->request->get('endpoint', 'string', null);
        $clientIp = $this->request->get('client_ip', 'string', null);
        $policyResult = $this->request->get('policy_result', 'string', null);
        $search = $this->request->get('search', 'string', null);

        if (!file_exists($this->dbPath)) {
            return $result;
        }

        try {
            $db = new \PDO('sqlite:' . $this->dbPath);
            $db->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);

            // Build query
            $where = array('1=1');
            $params = array();

            if ($startDate) {
                $where[] = 'timestamp >= :start_date';
                $params[':start_date'] = $startDate;
            }
            if ($endDate) {
                $where[] = 'timestamp <= :end_date';
                $params[':end_date'] = $endDate . ' 23:59:59';
            }
            if ($endpoint) {
                $where[] = 'endpoint = :endpoint';
                $params[':endpoint'] = $endpoint;
            }
            if ($clientIp) {
                $where[] = 'client_ip = :client_ip';
                $params[':client_ip'] = $clientIp;
            }
            if ($policyResult) {
                $where[] = 'policy_result = :policy_result';
                $params[':policy_result'] = $policyResult;
            }
            if ($search) {
                $where[] = '(prompt_preview LIKE :search OR client_device LIKE :search2)';
                $params[':search'] = '%' . $search . '%';
                $params[':search2'] = '%' . $search . '%';
            }

            $whereClause = implode(' AND ', $where);

            // Get total count
            $countSql = "SELECT COUNT(*) FROM audit_events WHERE {$whereClause}";
            $stmt = $db->prepare($countSql);
            $stmt->execute($params);
            $result['total'] = (int)$stmt->fetchColumn();

            // Get rows
            $sql = "SELECT * FROM audit_events WHERE {$whereClause} ORDER BY timestamp DESC LIMIT :limit OFFSET :offset";
            $stmt = $db->prepare($sql);
            foreach ($params as $key => $value) {
                $stmt->bindValue($key, $value);
            }
            $stmt->bindValue(':limit', $limit, \PDO::PARAM_INT);
            $stmt->bindValue(':offset', $offset, \PDO::PARAM_INT);
            $stmt->execute();

            $result['rows'] = $stmt->fetchAll(\PDO::FETCH_ASSOC);
            $result['page'] = $page;
            $result['limit'] = $limit;
            $result['pages'] = ceil($result['total'] / $limit);

        } catch (\Exception $e) {
            $result['result'] = 'failed';
            $result['message'] = 'Database error: ' . $e->getMessage();
        }

        return $result;
    }

    /**
     * Export audit logs as CSV
     * @return mixed CSV download or error
     */
    public function exportAction()
    {
        // Get filters (same as search)
        $startDate = $this->request->get('start_date', 'string', null);
        $endDate = $this->request->get('end_date', 'string', null);
        $endpoint = $this->request->get('endpoint', 'string', null);
        $policyResult = $this->request->get('policy_result', 'string', null);

        if (!file_exists($this->dbPath)) {
            return array('result' => 'failed', 'message' => 'Audit database not found');
        }

        try {
            $db = new \PDO('sqlite:' . $this->dbPath);
            $db->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);

            // Build query
            $where = array('1=1');
            $params = array();

            if ($startDate) {
                $where[] = 'timestamp >= :start_date';
                $params[':start_date'] = $startDate;
            }
            if ($endDate) {
                $where[] = 'timestamp <= :end_date';
                $params[':end_date'] = $endDate . ' 23:59:59';
            }
            if ($endpoint) {
                $where[] = 'endpoint = :endpoint';
                $params[':endpoint'] = $endpoint;
            }
            if ($policyResult) {
                $where[] = 'policy_result = :policy_result';
                $params[':policy_result'] = $policyResult;
            }

            $whereClause = implode(' AND ', $where);

            $sql = "SELECT timestamp, client_ip, client_device, endpoint, http_method, http_path, " .
                   "prompt_preview, response_status, policy_result, policy_name " .
                   "FROM audit_events WHERE {$whereClause} ORDER BY timestamp DESC LIMIT 10000";

            $stmt = $db->prepare($sql);
            $stmt->execute($params);
            $rows = $stmt->fetchAll(\PDO::FETCH_ASSOC);

            // Generate CSV
            $csv = "Timestamp,Client IP,Device,Endpoint,Method,Path,Prompt Preview,Status,Policy Result,Policy Name\n";
            foreach ($rows as $row) {
                $csv .= sprintf(
                    '"%s","%s","%s","%s","%s","%s","%s","%s","%s","%s"' . "\n",
                    str_replace('"', '""', $row['timestamp'] ?? ''),
                    str_replace('"', '""', $row['client_ip'] ?? ''),
                    str_replace('"', '""', $row['client_device'] ?? ''),
                    str_replace('"', '""', $row['endpoint'] ?? ''),
                    str_replace('"', '""', $row['http_method'] ?? ''),
                    str_replace('"', '""', $row['http_path'] ?? ''),
                    str_replace('"', '""', $row['prompt_preview'] ?? ''),
                    str_replace('"', '""', $row['response_status'] ?? ''),
                    str_replace('"', '""', $row['policy_result'] ?? ''),
                    str_replace('"', '""', $row['policy_name'] ?? '')
                );
            }

            return array(
                'result' => 'success',
                'csv' => $csv,
                'filename' => 'yori-audit-' . date('Y-m-d') . '.csv',
                'count' => count($rows)
            );

        } catch (\Exception $e) {
            return array('result' => 'failed', 'message' => 'Export error: ' . $e->getMessage());
        }
    }

    /**
     * Get recent events (for live tail)
     * @return array recent events
     */
    public function tailAction()
    {
        $result = array('result' => 'success', 'events' => array());
        $limit = (int)$this->request->get('limit', 'int', 20);
        $since = $this->request->get('since', 'string', null);

        if (!file_exists($this->dbPath)) {
            return $result;
        }

        try {
            $db = new \PDO('sqlite:' . $this->dbPath);
            $db->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);

            if ($since) {
                $sql = "SELECT * FROM audit_events WHERE timestamp > :since ORDER BY timestamp DESC LIMIT :limit";
                $stmt = $db->prepare($sql);
                $stmt->bindValue(':since', $since);
                $stmt->bindValue(':limit', $limit, \PDO::PARAM_INT);
            } else {
                $sql = "SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT :limit";
                $stmt = $db->prepare($sql);
                $stmt->bindValue(':limit', $limit, \PDO::PARAM_INT);
            }

            $stmt->execute();
            $result['events'] = $stmt->fetchAll(\PDO::FETCH_ASSOC);

        } catch (\Exception $e) {
            $result['result'] = 'failed';
            $result['message'] = 'Database error: ' . $e->getMessage();
        }

        return $result;
    }

    /**
     * Get summary statistics
     * @return array statistics
     */
    public function statsAction()
    {
        $result = array(
            'result' => 'success',
            'stats' => array(
                'total_requests' => 0,
                'requests_today' => 0,
                'requests_week' => 0,
                'requests_month' => 0,
                'blocks_today' => 0,
                'alerts_today' => 0
            )
        );

        if (!file_exists($this->dbPath)) {
            return $result;
        }

        try {
            $db = new \PDO('sqlite:' . $this->dbPath);
            $db->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);

            // Total requests
            $stmt = $db->query("SELECT COUNT(*) FROM audit_events WHERE event_type = 'request'");
            $result['stats']['total_requests'] = (int)$stmt->fetchColumn();

            // Today
            $today = date('Y-m-d');
            $stmt = $db->prepare("SELECT COUNT(*) FROM audit_events WHERE event_type = 'request' AND timestamp >= :today");
            $stmt->execute([':today' => $today]);
            $result['stats']['requests_today'] = (int)$stmt->fetchColumn();

            // This week
            $weekAgo = date('Y-m-d', strtotime('-7 days'));
            $stmt = $db->prepare("SELECT COUNT(*) FROM audit_events WHERE event_type = 'request' AND timestamp >= :week");
            $stmt->execute([':week' => $weekAgo]);
            $result['stats']['requests_week'] = (int)$stmt->fetchColumn();

            // This month
            $monthAgo = date('Y-m-d', strtotime('-30 days'));
            $stmt = $db->prepare("SELECT COUNT(*) FROM audit_events WHERE event_type = 'request' AND timestamp >= :month");
            $stmt->execute([':month' => $monthAgo]);
            $result['stats']['requests_month'] = (int)$stmt->fetchColumn();

            // Blocks today
            $stmt = $db->prepare("SELECT COUNT(*) FROM audit_events WHERE policy_result = 'block' AND timestamp >= :today");
            $stmt->execute([':today' => $today]);
            $result['stats']['blocks_today'] = (int)$stmt->fetchColumn();

            // Alerts today
            $stmt = $db->prepare("SELECT COUNT(*) FROM audit_events WHERE policy_result = 'alert' AND timestamp >= :today");
            $stmt->execute([':today' => $today]);
            $result['stats']['alerts_today'] = (int)$stmt->fetchColumn();

        } catch (\Exception $e) {
            $result['result'] = 'failed';
            $result['message'] = 'Database error: ' . $e->getMessage();
        }

        return $result;
    }

    /**
     * Get endpoint breakdown
     * @return array endpoint statistics
     */
    public function endpointsAction()
    {
        $result = array('result' => 'success', 'endpoints' => array());
        $days = (int)$this->request->get('days', 'int', 7);

        if (!file_exists($this->dbPath)) {
            return $result;
        }

        try {
            $db = new \PDO('sqlite:' . $this->dbPath);
            $db->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);

            $since = date('Y-m-d', strtotime("-{$days} days"));
            $sql = "SELECT endpoint, COUNT(*) as count FROM audit_events " .
                   "WHERE event_type = 'request' AND timestamp >= :since " .
                   "GROUP BY endpoint ORDER BY count DESC";

            $stmt = $db->prepare($sql);
            $stmt->execute([':since' => $since]);
            $result['endpoints'] = $stmt->fetchAll(\PDO::FETCH_ASSOC);

        } catch (\Exception $e) {
            $result['result'] = 'failed';
            $result['message'] = 'Database error: ' . $e->getMessage();
        }

        return $result;
    }

    /**
     * Get device breakdown
     * @return array device statistics
     */
    public function devicesAction()
    {
        $result = array('result' => 'success', 'devices' => array());
        $days = (int)$this->request->get('days', 'int', 7);

        if (!file_exists($this->dbPath)) {
            return $result;
        }

        try {
            $db = new \PDO('sqlite:' . $this->dbPath);
            $db->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);

            $since = date('Y-m-d', strtotime("-{$days} days"));
            $sql = "SELECT client_ip, client_device, COUNT(*) as count FROM audit_events " .
                   "WHERE event_type = 'request' AND timestamp >= :since " .
                   "GROUP BY client_ip ORDER BY count DESC LIMIT 20";

            $stmt = $db->prepare($sql);
            $stmt->execute([':since' => $since]);
            $result['devices'] = $stmt->fetchAll(\PDO::FETCH_ASSOC);

        } catch (\Exception $e) {
            $result['result'] = 'failed';
            $result['message'] = 'Database error: ' . $e->getMessage();
        }

        return $result;
    }

    /**
     * Get hourly breakdown for charts
     * @return array hourly statistics
     */
    public function hourlyAction()
    {
        $result = array('result' => 'success', 'hourly' => array());
        $days = (int)$this->request->get('days', 'int', 1);

        if (!file_exists($this->dbPath)) {
            return $result;
        }

        try {
            $db = new \PDO('sqlite:' . $this->dbPath);
            $db->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);

            $since = date('Y-m-d H:i:s', strtotime("-{$days} days"));
            $sql = "SELECT strftime('%Y-%m-%d %H:00:00', timestamp) as hour, COUNT(*) as count " .
                   "FROM audit_events WHERE event_type = 'request' AND timestamp >= :since " .
                   "GROUP BY hour ORDER BY hour";

            $stmt = $db->prepare($sql);
            $stmt->execute([':since' => $since]);
            $result['hourly'] = $stmt->fetchAll(\PDO::FETCH_ASSOC);

        } catch (\Exception $e) {
            $result['result'] = 'failed';
            $result['message'] = 'Database error: ' . $e->getMessage();
        }

        return $result;
    }
}
