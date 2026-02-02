<?php

/**
 * Copyright (C) 2026 YORI Project
 * All rights reserved.
 *
 * Reporting and analytics API controller.
 */

namespace OPNsense\YORI\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Backend;

/**
 * Class ReportController
 * @package OPNsense\YORI\Api
 */
class ReportController extends ApiControllerBase
{
    /**
     * Get usage report
     * @return array
     */
    public function usageAction()
    {
        $startDate = $this->request->get('start_date', 'string', null);
        $endDate = $this->request->get('end_date', 'string', null);
        $groupBy = $this->request->get('group_by', 'string', 'day');

        $backend = new Backend();
        $params = json_encode([
            'start_date' => $startDate,
            'end_date' => $endDate,
            'group_by' => $groupBy
        ]);
        $response = $backend->configdRun("yori report usage", [$params]);

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return array('result' => 'success', 'report' => $data);
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to generate usage report');
    }

    /**
     * Get enforcement report
     * @return array
     */
    public function enforcementAction()
    {
        $startDate = $this->request->get('start_date', 'string', null);
        $endDate = $this->request->get('end_date', 'string', null);

        $backend = new Backend();
        $params = json_encode([
            'start_date' => $startDate,
            'end_date' => $endDate
        ]);
        $response = $backend->configdRun("yori report enforcement", [$params]);

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return array('result' => 'success', 'report' => $data);
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to generate enforcement report');
    }

    /**
     * Get cost report
     * @return array
     */
    public function costAction()
    {
        $startDate = $this->request->get('start_date', 'string', null);
        $endDate = $this->request->get('end_date', 'string', null);

        $backend = new Backend();
        $params = json_encode([
            'start_date' => $startDate,
            'end_date' => $endDate
        ]);
        $response = $backend->configdRun("yori report cost", [$params]);

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return array('result' => 'success', 'report' => $data);
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to generate cost report');
    }

    /**
     * Export report to CSV
     * @return array
     */
    public function exportCsvAction()
    {
        $reportType = $this->request->get('type', 'string', 'usage');
        $startDate = $this->request->get('start_date', 'string', null);
        $endDate = $this->request->get('end_date', 'string', null);

        $backend = new Backend();
        $params = json_encode([
            'type' => $reportType,
            'format' => 'csv',
            'start_date' => $startDate,
            'end_date' => $endDate
        ]);
        $response = $backend->configdRun("yori report export", [$params]);

        if ($response) {
            $data = json_decode($response, true);
            if ($data && isset($data['content'])) {
                return array(
                    'result' => 'success',
                    'filename' => $data['filename'] ?? 'report.csv',
                    'content' => $data['content']
                );
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to export report');
    }

    /**
     * Export report to JSON
     * @return array
     */
    public function exportJsonAction()
    {
        $reportType = $this->request->get('type', 'string', 'usage');
        $startDate = $this->request->get('start_date', 'string', null);
        $endDate = $this->request->get('end_date', 'string', null);

        $backend = new Backend();
        $params = json_encode([
            'type' => $reportType,
            'format' => 'json',
            'start_date' => $startDate,
            'end_date' => $endDate
        ]);
        $response = $backend->configdRun("yori report export", [$params]);

        if ($response) {
            $data = json_decode($response, true);
            if ($data && isset($data['content'])) {
                return array(
                    'result' => 'success',
                    'filename' => $data['filename'] ?? 'report.json',
                    'content' => $data['content']
                );
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to export report');
    }

    /**
     * Get device analytics
     * @return array
     */
    public function devicesAction()
    {
        $days = (int)$this->request->get('days', 'int', 30);

        $backend = new Backend();
        $response = $backend->configdRun("yori report devices", [$days]);

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return array('result' => 'success', 'devices' => $data);
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to get device analytics');
    }

    /**
     * Get endpoint analytics
     * @return array
     */
    public function endpointsAction()
    {
        $days = (int)$this->request->get('days', 'int', 30);

        $backend = new Backend();
        $response = $backend->configdRun("yori report endpoints", [$days]);

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return array('result' => 'success', 'endpoints' => $data);
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to get endpoint analytics');
    }

    /**
     * Get trend data for charts
     * @return array
     */
    public function trendsAction()
    {
        $metric = $this->request->get('metric', 'string', 'requests');
        $days = (int)$this->request->get('days', 'int', 30);

        $backend = new Backend();
        $params = json_encode([
            'metric' => $metric,
            'days' => $days
        ]);
        $response = $backend->configdRun("yori report trends", [$params]);

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return array('result' => 'success', 'trends' => $data);
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to get trend data');
    }

    /**
     * Get summary dashboard data
     * @return array
     */
    public function summaryAction()
    {
        $backend = new Backend();
        $response = $backend->configdRun("yori report summary");

        if ($response) {
            $data = json_decode($response, true);
            if ($data) {
                return array('result' => 'success', 'summary' => $data);
            }
        }

        return array('result' => 'failed', 'message' => 'Failed to get summary');
    }
}
