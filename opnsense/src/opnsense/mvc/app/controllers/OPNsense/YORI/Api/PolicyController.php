<?php

/**
 * YORI Policy API Controller
 *
 * RESTful API for policy management in OPNsense
 */

namespace OPNsense\YORI\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Backend;

class PolicyController extends ApiControllerBase
{
    /**
     * List all loaded policies
     *
     * @return array
     */
    public function listAction()
    {
        $backend = new Backend();

        // Call YORI service to list policies
        $response = $backend->configdRun('yori policy list');
        $policies = json_decode($response, true);

        if ($policies === null) {
            return [
                'result' => 'failed',
                'message' => 'Failed to parse policy list',
                'policies' => []
            ];
        }

        return [
            'result' => 'success',
            'policies' => $policies
        ];
    }

    /**
     * Reload policies from disk
     *
     * @return array
     */
    public function reloadAction()
    {
        if ($this->request->isPost()) {
            $backend = new Backend();

            // Call YORI service to reload policies
            $response = $backend->configdRun('yori policy reload');
            $result = json_decode($response, true);

            if ($result === null) {
                return [
                    'result' => 'failed',
                    'message' => 'Failed to reload policies'
                ];
            }

            return [
                'result' => 'success',
                'count' => $result['count'] ?? 0,
                'message' => sprintf('Loaded %d policies', $result['count'] ?? 0)
            ];
        }

        return ['result' => 'failed', 'message' => 'Method not allowed'];
    }

    /**
     * Test a policy with sample input (dry run)
     *
     * @return array
     */
    public function testAction()
    {
        if ($this->request->isPost()) {
            $data = $this->request->getJsonRawBody(true);

            if (!isset($data['policy']) || !isset($data['input'])) {
                return [
                    'result' => 'failed',
                    'message' => 'Missing policy or input'
                ];
            }

            $backend = new Backend();

            // Encode test data as JSON for backend
            $testData = json_encode([
                'policy' => $data['policy'],
                'input' => $data['input']
            ]);

            // Call YORI service to test policy
            $response = $backend->configdRun('yori policy test', $testData);
            $result = json_decode($response, true);

            if ($result === null) {
                return [
                    'result' => 'failed',
                    'message' => 'Policy test failed'
                ];
            }

            return [
                'result' => 'success',
                'evaluation' => $result
            ];
        }

        return ['result' => 'failed', 'message' => 'Method not allowed'];
    }

    /**
     * Enable a policy template
     *
     * @return array
     */
    public function enableAction()
    {
        if ($this->request->isPost()) {
            $data = $this->request->getJsonRawBody(true);

            if (!isset($data['template'])) {
                return [
                    'result' => 'failed',
                    'message' => 'Missing template name'
                ];
            }

            $backend = new Backend();

            // Call YORI service to enable template
            $response = $backend->configdRun('yori policy enable', $data['template']);
            $result = json_decode($response, true);

            if ($result === null) {
                return [
                    'result' => 'failed',
                    'message' => 'Failed to enable policy'
                ];
            }

            return [
                'result' => 'success',
                'message' => sprintf('Enabled policy: %s', $data['template'])
            ];
        }

        return ['result' => 'failed', 'message' => 'Method not allowed'];
    }

    /**
     * Disable a policy
     *
     * @return array
     */
    public function disableAction()
    {
        if ($this->request->isPost()) {
            $data = $this->request->getJsonRawBody(true);

            if (!isset($data['policy'])) {
                return [
                    'result' => 'failed',
                    'message' => 'Missing policy name'
                ];
            }

            $backend = new Backend();

            // Call YORI service to disable policy
            $response = $backend->configdRun('yori policy disable', $data['policy']);
            $result = json_decode($response, true);

            if ($result === null) {
                return [
                    'result' => 'failed',
                    'message' => 'Failed to disable policy'
                ];
            }

            return [
                'result' => 'success',
                'message' => sprintf('Disabled policy: %s', $data['policy'])
            ];
        }

        return ['result' => 'failed', 'message' => 'Method not allowed'];
    }

    /**
     * Get alert configuration
     *
     * @return array
     */
    public function getAlertConfigAction()
    {
        $backend = new Backend();

        $response = $backend->configdRun('yori alert config get');
        $config = json_decode($response, true);

        if ($config === null) {
            return [
                'result' => 'failed',
                'message' => 'Failed to get alert configuration'
            ];
        }

        return [
            'result' => 'success',
            'config' => $config
        ];
    }

    /**
     * Save alert configuration
     *
     * @return array
     */
    public function setAlertConfigAction()
    {
        if ($this->request->isPost()) {
            $data = $this->request->getJsonRawBody(true);

            $backend = new Backend();

            // Save alert configuration
            $configData = json_encode($data);
            $response = $backend->configdRun('yori alert config set', $configData);
            $result = json_decode($response, true);

            if ($result === null) {
                return [
                    'result' => 'failed',
                    'message' => 'Failed to save alert configuration'
                ];
            }

            return [
                'result' => 'success',
                'message' => 'Alert configuration saved'
            ];
        }

        return ['result' => 'failed', 'message' => 'Method not allowed'];
    }
}
