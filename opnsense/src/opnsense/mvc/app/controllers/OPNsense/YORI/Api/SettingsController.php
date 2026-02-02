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
 * Class SettingsController
 * @package OPNsense\YORI\Api
 * Handles YORI configuration settings
 */
class SettingsController extends ApiControllerBase
{
    private $configFile = '/usr/local/etc/yori/yori.conf';

    /**
     * Get current settings
     * @return array configuration data
     */
    public function getAction()
    {
        $result = array('result' => 'failed');

        if (file_exists($this->configFile)) {
            $config = yaml_parse_file($this->configFile);
            if ($config !== false) {
                $result['result'] = 'success';
                $result['settings'] = $config;
            } else {
                $result['message'] = 'Failed to parse configuration file';
            }
        } else {
            // Return default configuration
            $result['result'] = 'success';
            $result['settings'] = $this->getDefaultConfig();
        }

        return $result;
    }

    /**
     * Update settings
     * @return array result status
     */
    public function setAction()
    {
        $result = array('result' => 'failed');

        if (!$this->request->isPost()) {
            $result['message'] = 'POST request required';
            return $result;
        }

        $data = $this->request->getJsonRawBody(true);
        if (empty($data)) {
            $result['message'] = 'No configuration data provided';
            return $result;
        }

        // Validate configuration
        $validation = $this->validateConfig($data);
        if (!$validation['valid']) {
            $result['message'] = $validation['message'];
            return $result;
        }

        // Merge with existing config
        $existingConfig = array();
        if (file_exists($this->configFile)) {
            $existingConfig = yaml_parse_file($this->configFile) ?: array();
        }

        $newConfig = array_replace_recursive($existingConfig, $data);

        // Write configuration
        $yaml = yaml_emit($newConfig, YAML_UTF8_ENCODING);
        if (file_put_contents($this->configFile, $yaml) === false) {
            $result['message'] = 'Failed to write configuration file';
            return $result;
        }

        // Log the change
        syslog(LOG_NOTICE, "YORI: Configuration updated via web UI");

        // Trigger reconfigure if service is running
        $backend = new Backend();
        $backend->configdRun("yori reconfigure");

        $result['result'] = 'success';
        $result['message'] = 'Configuration saved successfully';
        return $result;
    }

    /**
     * Test configuration validity
     * @return array validation result
     */
    public function testAction()
    {
        $result = array('result' => 'failed');

        if (!$this->request->isPost()) {
            $result['message'] = 'POST request required';
            return $result;
        }

        $data = $this->request->getJsonRawBody(true);
        if (empty($data)) {
            $result['message'] = 'No configuration data provided';
            return $result;
        }

        $validation = $this->validateConfig($data);
        $result['result'] = $validation['valid'] ? 'success' : 'failed';
        $result['valid'] = $validation['valid'];
        $result['message'] = $validation['message'];
        $result['warnings'] = $validation['warnings'] ?? array();

        return $result;
    }

    /**
     * Get configured endpoints
     * @return array endpoint list
     */
    public function endpointsAction()
    {
        $result = array('result' => 'success', 'endpoints' => array());

        if (file_exists($this->configFile)) {
            $config = yaml_parse_file($this->configFile);
            if ($config && isset($config['endpoints'])) {
                $result['endpoints'] = $config['endpoints'];
            }
        }

        // Add defaults if none configured
        if (empty($result['endpoints'])) {
            $result['endpoints'] = $this->getDefaultEndpoints();
        }

        return $result;
    }

    /**
     * Toggle endpoint enabled status
     * @param string $name Endpoint name/domain
     * @return array result
     */
    public function endpointAction($name)
    {
        $result = array('result' => 'failed');

        if (!$this->request->isPost()) {
            $result['message'] = 'POST request required';
            return $result;
        }

        $data = $this->request->getJsonRawBody(true);
        $enabled = isset($data['enabled']) ? (bool)$data['enabled'] : true;

        $config = array();
        if (file_exists($this->configFile)) {
            $config = yaml_parse_file($this->configFile) ?: array();
        }

        // Find and update endpoint
        $found = false;
        if (isset($config['endpoints'])) {
            foreach ($config['endpoints'] as $key => $endpoint) {
                if ($endpoint['domain'] === $name) {
                    $config['endpoints'][$key]['enabled'] = $enabled;
                    $found = true;
                    break;
                }
            }
        }

        if (!$found) {
            $result['message'] = 'Endpoint not found: ' . htmlspecialchars($name);
            return $result;
        }

        // Save config
        $yaml = yaml_emit($config, YAML_UTF8_ENCODING);
        if (file_put_contents($this->configFile, $yaml) === false) {
            $result['message'] = 'Failed to save configuration';
            return $result;
        }

        syslog(LOG_NOTICE, "YORI: Endpoint {$name} " . ($enabled ? 'enabled' : 'disabled'));

        $result['result'] = 'success';
        $result['endpoint'] = $name;
        $result['enabled'] = $enabled;
        return $result;
    }

    /**
     * Export configuration as JSON for backup
     * @return array configuration backup
     */
    public function backupAction()
    {
        $result = array('result' => 'failed');

        if (file_exists($this->configFile)) {
            $config = yaml_parse_file($this->configFile);
            if ($config !== false) {
                $result['result'] = 'success';
                $result['backup'] = array(
                    'version' => '0.4.0',
                    'timestamp' => date('c'),
                    'config' => $config
                );
            } else {
                $result['message'] = 'Failed to parse configuration';
            }
        } else {
            $result['message'] = 'No configuration file found';
        }

        return $result;
    }

    /**
     * Restore configuration from backup
     * @return array result
     */
    public function restoreAction()
    {
        $result = array('result' => 'failed');

        if (!$this->request->isPost()) {
            $result['message'] = 'POST request required';
            return $result;
        }

        $data = $this->request->getJsonRawBody(true);
        if (!isset($data['backup']) || !isset($data['backup']['config'])) {
            $result['message'] = 'Invalid backup format';
            return $result;
        }

        $config = $data['backup']['config'];

        // Validate the config
        $validation = $this->validateConfig($config);
        if (!$validation['valid']) {
            $result['message'] = 'Backup contains invalid configuration: ' . $validation['message'];
            return $result;
        }

        // Create backup of current config
        if (file_exists($this->configFile)) {
            $backupPath = $this->configFile . '.bak.' . date('YmdHis');
            copy($this->configFile, $backupPath);
        }

        // Write restored config
        $yaml = yaml_emit($config, YAML_UTF8_ENCODING);
        if (file_put_contents($this->configFile, $yaml) === false) {
            $result['message'] = 'Failed to write configuration';
            return $result;
        }

        syslog(LOG_NOTICE, "YORI: Configuration restored from backup");

        // Trigger reconfigure
        $backend = new Backend();
        $backend->configdRun("yori reconfigure");

        $result['result'] = 'success';
        $result['message'] = 'Configuration restored successfully';
        return $result;
    }

    /**
     * Validate configuration data
     * @param array $config Configuration to validate
     * @return array validation result with 'valid', 'message', and 'warnings'
     */
    private function validateConfig($config)
    {
        $warnings = array();

        // Check mode
        if (isset($config['mode'])) {
            $validModes = array('observe', 'advisory', 'enforce');
            if (!in_array($config['mode'], $validModes)) {
                return array(
                    'valid' => false,
                    'message' => 'Invalid mode. Must be one of: ' . implode(', ', $validModes)
                );
            }
        }

        // Check listen address
        if (isset($config['listen'])) {
            if (!preg_match('/^[\w\.\*]+:\d+$/', $config['listen'])) {
                return array(
                    'valid' => false,
                    'message' => 'Invalid listen address format. Expected: host:port'
                );
            }
        }

        // Check endpoints
        if (isset($config['endpoints'])) {
            if (!is_array($config['endpoints'])) {
                return array(
                    'valid' => false,
                    'message' => 'Endpoints must be an array'
                );
            }
            foreach ($config['endpoints'] as $endpoint) {
                if (!isset($endpoint['domain'])) {
                    return array(
                        'valid' => false,
                        'message' => 'Each endpoint must have a domain'
                    );
                }
            }
        }

        // Check audit settings
        if (isset($config['audit'])) {
            if (isset($config['audit']['retention_days'])) {
                $days = (int)$config['audit']['retention_days'];
                if ($days < 1 || $days > 3650) {
                    return array(
                        'valid' => false,
                        'message' => 'Retention days must be between 1 and 3650'
                    );
                }
            }
        }

        // Check enforcement settings
        if (isset($config['enforcement'])) {
            if (isset($config['enforcement']['enabled']) && $config['enforcement']['enabled']) {
                if (!isset($config['enforcement']['consent_accepted']) || !$config['enforcement']['consent_accepted']) {
                    $warnings[] = 'Enforcement enabled but consent not accepted. Enforcement will not be active.';
                }
            }
        }

        return array(
            'valid' => true,
            'message' => 'Configuration is valid',
            'warnings' => $warnings
        );
    }

    /**
     * Get default configuration
     * @return array default config
     */
    private function getDefaultConfig()
    {
        return array(
            'mode' => 'observe',
            'listen' => '0.0.0.0:8443',
            'endpoints' => $this->getDefaultEndpoints(),
            'audit' => array(
                'database' => '/var/db/yori/audit.db',
                'retention_days' => 365
            ),
            'policies' => array(
                'directory' => '/usr/local/etc/yori/policies'
            ),
            'enforcement' => array(
                'enabled' => false,
                'consent_accepted' => false
            )
        );
    }

    /**
     * Get default endpoint list
     * @return array default endpoints
     */
    private function getDefaultEndpoints()
    {
        return array(
            array('domain' => 'api.openai.com', 'enabled' => true, 'name' => 'OpenAI'),
            array('domain' => 'api.anthropic.com', 'enabled' => true, 'name' => 'Anthropic'),
            array('domain' => 'generativelanguage.googleapis.com', 'enabled' => true, 'name' => 'Google Gemini'),
            array('domain' => 'api.mistral.ai', 'enabled' => true, 'name' => 'Mistral')
        );
    }
}
