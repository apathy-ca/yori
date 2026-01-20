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

use OPNsense\Base\ApiMutableModelControllerBase;
use OPNsense\Core\Config;

/**
 * Class EnforcementController
 * @package OPNsense\YORI
 */
class EnforcementController extends ApiMutableModelControllerBase
{
    protected static $internalModelName = 'enforcement';
    protected static $internalModelClass = 'OPNsense\YORI\Enforcement';

    /**
     * Get enforcement mode status
     * @return array enforcement status information
     */
    public function statusAction()
    {
        $result = array();

        // Read YORI configuration
        $configFile = '/usr/local/etc/yori/yori.conf';
        if (file_exists($configFile)) {
            $config = yaml_parse_file($configFile);

            $result['mode'] = $config['mode'] ?? 'observe';
            $result['enforcement_enabled'] = $config['enforcement']['enabled'] ?? false;
            $result['consent_accepted'] = $config['enforcement']['consent_accepted'] ?? false;

            // Enforcement is active only if ALL conditions are met
            $result['enforcement_active'] = (
                $result['mode'] === 'enforce' &&
                $result['enforcement_enabled'] === true &&
                $result['consent_accepted'] === true
            );

            $result['policies_configured'] = count($config['policies']['files'] ?? []);
        } else {
            $result['mode'] = 'observe';
            $result['enforcement_enabled'] = false;
            $result['consent_accepted'] = false;
            $result['enforcement_active'] = false;
            $result['policies_configured'] = 0;
            $result['error'] = 'Configuration file not found';
        }

        return $result;
    }

    /**
     * Get enforcement settings
     * @return array current enforcement configuration
     */
    public function getAction()
    {
        $result = array();

        $configFile = '/usr/local/etc/yori/yori.conf';
        if (file_exists($configFile)) {
            $config = yaml_parse_file($configFile);

            $result['enforcement'] = array(
                'enabled' => $config['enforcement']['enabled'] ?? false,
                'consent_accepted' => $config['enforcement']['consent_accepted'] ?? false
            );

            $result['mode'] = $config['mode'] ?? 'observe';

            // Get per-policy settings
            $result['policies'] = $config['policies']['files'] ?? [];
        }

        return $result;
    }

    /**
     * Set enforcement settings
     * @return array result status
     */
    public function setAction()
    {
        $result = array('result' => 'failed');

        if ($this->request->isPost()) {
            $configFile = '/usr/local/etc/yori/yori.conf';

            // Read current config
            if (file_exists($configFile)) {
                $config = yaml_parse_file($configFile);
            } else {
                $config = $this->getDefaultConfig();
            }

            // Update enforcement settings
            $postData = $this->request->getPost();

            if (isset($postData['enforcement'])) {
                $config['enforcement']['enabled'] =
                    filter_var($postData['enforcement']['enabled'] ?? false, FILTER_VALIDATE_BOOLEAN);
                $config['enforcement']['consent_accepted'] =
                    filter_var($postData['enforcement']['consent_accepted'] ?? false, FILTER_VALIDATE_BOOLEAN);
            }

            if (isset($postData['mode'])) {
                $validModes = ['observe', 'advisory', 'enforce'];
                if (in_array($postData['mode'], $validModes)) {
                    $config['mode'] = $postData['mode'];
                }
            }

            // Update per-policy settings
            if (isset($postData['policies'])) {
                foreach ($postData['policies'] as $policyName => $settings) {
                    if (!isset($config['policies']['files'][$policyName])) {
                        $config['policies']['files'][$policyName] = [];
                    }

                    $config['policies']['files'][$policyName]['enabled'] =
                        filter_var($settings['enabled'] ?? true, FILTER_VALIDATE_BOOLEAN);

                    $validActions = ['allow', 'alert', 'block'];
                    if (isset($settings['action']) && in_array($settings['action'], $validActions)) {
                        $config['policies']['files'][$policyName]['action'] = $settings['action'];
                    }
                }
            }

            // Validate consent requirement
            if (!$this->validateConsent($config)) {
                return array(
                    'result' => 'failed',
                    'error' => 'Consent validation failed. Cannot enable enforcement without consent_accepted=true.'
                );
            }

            // Write config back
            if (yaml_emit_file($configFile, $config)) {
                $result = array('result' => 'saved');

                // Log the change
                syslog(LOG_WARNING,
                    "YORI enforcement settings changed: mode={$config['mode']}, " .
                    "enabled={$config['enforcement']['enabled']}, " .
                    "consent={$config['enforcement']['consent_accepted']}"
                );
            } else {
                $result = array('result' => 'failed', 'error' => 'Failed to write configuration');
            }
        }

        return $result;
    }

    /**
     * Test policy configuration
     * @param string $policyName policy to test
     * @return array policy configuration and enforcement decision
     */
    public function testAction($policyName = '')
    {
        $result = array();

        if (empty($policyName)) {
            return array('error' => 'Policy name required');
        }

        $configFile = '/usr/local/etc/yori/yori.conf';
        if (file_exists($configFile)) {
            $config = yaml_parse_file($configFile);

            $policyKey = str_replace('.rego', '', $policyName);

            if (isset($config['policies']['files'][$policyKey])) {
                $policyConfig = $config['policies']['files'][$policyKey];

                $result['policy_name'] = $policyName;
                $result['enabled'] = $policyConfig['enabled'] ?? true;
                $result['action'] = $policyConfig['action'] ?? 'alert';

                // Determine if this would block
                $enforcementActive = (
                    ($config['mode'] ?? 'observe') === 'enforce' &&
                    ($config['enforcement']['enabled'] ?? false) === true &&
                    ($config['enforcement']['consent_accepted'] ?? false) === true
                );

                $result['would_block'] = (
                    $enforcementActive &&
                    $result['enabled'] &&
                    $result['action'] === 'block'
                );
            } else {
                // Policy not configured - use defaults
                $result['policy_name'] = $policyName;
                $result['enabled'] = false;
                $result['action'] = 'alert'; // Default safe action
                $result['would_block'] = false;
                $result['note'] = 'Policy not configured - using defaults';
            }
        } else {
            return array('error' => 'Configuration file not found');
        }

        return $result;
    }

    /**
     * Get consent warning text
     * @return array warning message
     */
    public function getConsentWarningAction()
    {
        return array(
            'warning' =>
                "WARNING: Enforcement mode will actively BLOCK LLM requests based on your policies.\n\n" .
                "This can break:\n" .
                "- AI-powered applications and services\n" .
                "- ChatGPT, Claude, and other LLM interfaces\n" .
                "- Development tools that use LLM APIs\n" .
                "- Any software relying on intercepted endpoints\n\n" .
                "Before enabling enforcement mode:\n" .
                "1. Test ALL policies in 'observe' mode first\n" .
                "2. Review audit logs to understand what will be blocked\n" .
                "3. Configure per-policy actions carefully (allow/alert/block)\n" .
                "4. Have a plan to quickly disable enforcement if needed\n\n" .
                "By checking 'consent_accepted', you acknowledge these risks."
        );
    }

    /**
     * Validate consent requirements
     * @param array $config configuration to validate
     * @return bool true if valid, false otherwise
     */
    private function validateConsent($config)
    {
        $mode = $config['mode'] ?? 'observe';
        $enabled = $config['enforcement']['enabled'] ?? false;
        $consent = $config['enforcement']['consent_accepted'] ?? false;

        // If trying to enable enforcement without consent, reject
        if (($mode === 'enforce' || $enabled) && !$consent) {
            return false;
        }

        return true;
    }

    /**
     * Get default configuration structure
     * @return array default config
     */
    private function getDefaultConfig()
    {
        return array(
            'mode' => 'observe',
            'listen' => '0.0.0.0:8443',
            'endpoints' => array(
                array('domain' => 'api.openai.com', 'enabled' => true),
                array('domain' => 'api.anthropic.com', 'enabled' => true),
                array('domain' => 'gemini.google.com', 'enabled' => true),
                array('domain' => 'api.mistral.ai', 'enabled' => true)
            ),
            'audit' => array(
                'database' => '/var/db/yori/audit.db',
                'retention_days' => 365
            ),
            'policies' => array(
                'directory' => '/usr/local/etc/yori/policies',
                'default' => 'home_default.rego',
                'files' => array()
            ),
            'enforcement' => array(
                'enabled' => false,
                'consent_accepted' => false
            )
        );
    }
}
