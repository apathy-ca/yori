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
 * Class PolicyController
 * @package OPNsense\YORI\Api
 * Handles Rego policy management
 */
class PolicyController extends ApiControllerBase
{
    private $policyDir = '/usr/local/etc/yori/policies';
    private $libraryDir = '/usr/local/share/yori/policy-library';

    /**
     * List installed policies
     * @return array policy list
     */
    public function listAction()
    {
        $result = array('result' => 'success', 'policies' => array());

        if (!is_dir($this->policyDir)) {
            return $result;
        }

        $files = glob($this->policyDir . '/*.rego');
        foreach ($files as $file) {
            $name = basename($file, '.rego');
            $content = file_get_contents($file);
            $metadata = $this->extractMetadata($content);

            $result['policies'][] = array(
                'name' => $name,
                'filename' => basename($file),
                'path' => $file,
                'size' => filesize($file),
                'modified' => date('c', filemtime($file)),
                'description' => $metadata['description'] ?? '',
                'author' => $metadata['author'] ?? '',
                'version' => $metadata['version'] ?? ''
            );
        }

        return $result;
    }

    /**
     * Get policy content
     * @param string $name Policy name (without .rego)
     * @return array policy content
     */
    public function getAction($name)
    {
        $result = array('result' => 'failed');

        if (!$this->isValidPolicyName($name)) {
            $result['message'] = 'Invalid policy name';
            return $result;
        }

        $path = $this->policyDir . '/' . $name . '.rego';
        if (!file_exists($path)) {
            $result['message'] = 'Policy not found';
            return $result;
        }

        $content = file_get_contents($path);
        $metadata = $this->extractMetadata($content);

        $result['result'] = 'success';
        $result['policy'] = array(
            'name' => $name,
            'content' => $content,
            'metadata' => $metadata
        );

        return $result;
    }

    /**
     * Save/update policy
     * @param string $name Policy name
     * @return array result
     */
    public function setAction($name)
    {
        $result = array('result' => 'failed');

        if (!$this->request->isPost()) {
            $result['message'] = 'POST request required';
            return $result;
        }

        if (!$this->isValidPolicyName($name)) {
            $result['message'] = 'Invalid policy name';
            return $result;
        }

        $data = $this->request->getJsonRawBody(true);
        if (!isset($data['content'])) {
            $result['message'] = 'Policy content required';
            return $result;
        }

        // Validate Rego syntax (basic check)
        $validation = $this->validateRego($data['content']);
        if (!$validation['valid']) {
            $result['message'] = 'Invalid Rego syntax: ' . $validation['error'];
            return $result;
        }

        // Ensure directory exists
        if (!is_dir($this->policyDir)) {
            mkdir($this->policyDir, 0755, true);
        }

        $path = $this->policyDir . '/' . $name . '.rego';
        if (file_put_contents($path, $data['content']) === false) {
            $result['message'] = 'Failed to save policy';
            return $result;
        }

        syslog(LOG_NOTICE, "YORI: Policy '{$name}' saved via web UI");

        $result['result'] = 'success';
        $result['message'] = 'Policy saved successfully';
        return $result;
    }

    /**
     * Delete policy
     * @param string $name Policy name
     * @return array result
     */
    public function deleteAction($name)
    {
        $result = array('result' => 'failed');

        if (!$this->request->isPost()) {
            $result['message'] = 'POST request required';
            return $result;
        }

        if (!$this->isValidPolicyName($name)) {
            $result['message'] = 'Invalid policy name';
            return $result;
        }

        $path = $this->policyDir . '/' . $name . '.rego';
        if (!file_exists($path)) {
            $result['message'] = 'Policy not found';
            return $result;
        }

        // Don't allow deleting home_default
        if ($name === 'home_default') {
            $result['message'] = 'Cannot delete the default policy';
            return $result;
        }

        if (!unlink($path)) {
            $result['message'] = 'Failed to delete policy';
            return $result;
        }

        syslog(LOG_NOTICE, "YORI: Policy '{$name}' deleted via web UI");

        $result['result'] = 'success';
        $result['message'] = 'Policy deleted';
        return $result;
    }

    /**
     * Test policy with sample input
     * @param string $name Policy name
     * @return array test result
     */
    public function testAction($name)
    {
        $result = array('result' => 'failed');

        if (!$this->isValidPolicyName($name)) {
            $result['message'] = 'Invalid policy name';
            return $result;
        }

        $data = $this->request->getJsonRawBody(true);
        $testInput = $data['input'] ?? array(
            'timestamp' => date('c'),
            'client_ip' => '192.168.1.100',
            'endpoint' => 'api.openai.com',
            'prompt' => 'Test prompt'
        );

        // Use backend to test policy
        $backend = new Backend();
        $response = $backend->configdRun("yori policy test {$name}", array(json_encode($testInput)));

        if ($response) {
            $decoded = json_decode($response, true);
            if ($decoded) {
                $result['result'] = 'success';
                $result['test_result'] = $decoded;
            } else {
                $result['result'] = 'success';
                $result['test_result'] = array('raw' => $response);
            }
        } else {
            $result['message'] = 'Policy test failed';
        }

        return $result;
    }

    /**
     * List available policy templates in library
     * @return array library list
     */
    public function libraryAction()
    {
        $result = array('result' => 'success', 'templates' => array());

        // Built-in templates
        $templates = array(
            array(
                'name' => 'home_default',
                'title' => 'Home Default',
                'description' => 'Allow all LLM requests - base policy for home use',
                'category' => 'Basic'
            ),
            array(
                'name' => 'bedtime',
                'title' => 'Bedtime Restrictions',
                'description' => 'Block LLM access after 9 PM and before 7 AM',
                'category' => 'Time-based'
            ),
            array(
                'name' => 'high_usage',
                'title' => 'High Usage Alert',
                'description' => 'Alert when device exceeds 50 requests per day',
                'category' => 'Usage Limits'
            ),
            array(
                'name' => 'homework_helper',
                'title' => 'Homework Helper',
                'description' => 'Track educational keywords in prompts',
                'category' => 'Educational'
            ),
            array(
                'name' => 'privacy_check',
                'title' => 'Privacy Check',
                'description' => 'Alert on potential PII in prompts (emails, phones, SSN)',
                'category' => 'Privacy'
            ),
            array(
                'name' => 'cost_limit',
                'title' => 'Cost Limit',
                'description' => 'Alert when estimated daily cost exceeds threshold',
                'category' => 'Cost Control'
            ),
            array(
                'name' => 'device_restrict',
                'title' => 'Device Restrictions',
                'description' => 'Allow/deny specific devices by IP address',
                'category' => 'Access Control'
            ),
            array(
                'name' => 'weekend_only',
                'title' => 'Weekend Only',
                'description' => 'Only allow LLM access on weekends',
                'category' => 'Time-based'
            ),
            array(
                'name' => 'work_hours',
                'title' => 'Work Hours',
                'description' => 'Only allow LLM access during business hours (9 AM - 5 PM)',
                'category' => 'Time-based'
            ),
            array(
                'name' => 'content_filter',
                'title' => 'Content Filter',
                'description' => 'Block prompts containing inappropriate keywords',
                'category' => 'Content'
            )
        );

        $result['templates'] = $templates;
        return $result;
    }

    /**
     * Install policy from library
     * @param string $name Template name
     * @return array result
     */
    public function installAction($name)
    {
        $result = array('result' => 'failed');

        if (!$this->request->isPost()) {
            $result['message'] = 'POST request required';
            return $result;
        }

        if (!$this->isValidPolicyName($name)) {
            $result['message'] = 'Invalid policy name';
            return $result;
        }

        // Get template content
        $template = $this->getTemplateContent($name);
        if (!$template) {
            $result['message'] = 'Template not found';
            return $result;
        }

        // Ensure directory exists
        if (!is_dir($this->policyDir)) {
            mkdir($this->policyDir, 0755, true);
        }

        $path = $this->policyDir . '/' . $name . '.rego';
        if (file_put_contents($path, $template) === false) {
            $result['message'] = 'Failed to install policy';
            return $result;
        }

        syslog(LOG_NOTICE, "YORI: Policy '{$name}' installed from library");

        $result['result'] = 'success';
        $result['message'] = 'Policy installed successfully';
        return $result;
    }

    /**
     * Validate Rego syntax
     * @return array validation result
     */
    public function validateAction()
    {
        $result = array('result' => 'failed');

        if (!$this->request->isPost()) {
            $result['message'] = 'POST request required';
            return $result;
        }

        $data = $this->request->getJsonRawBody(true);
        if (!isset($data['content'])) {
            $result['message'] = 'Content required';
            return $result;
        }

        $validation = $this->validateRego($data['content']);
        $result['result'] = 'success';
        $result['valid'] = $validation['valid'];
        $result['message'] = $validation['valid'] ? 'Syntax is valid' : $validation['error'];

        return $result;
    }

    /**
     * Check if policy name is valid
     * @param string $name Policy name
     * @return bool
     */
    private function isValidPolicyName($name)
    {
        return preg_match('/^[a-zA-Z0-9_-]+$/', $name) && strlen($name) <= 64;
    }

    /**
     * Extract metadata from Rego policy comments
     * @param string $content Policy content
     * @return array metadata
     */
    private function extractMetadata($content)
    {
        $metadata = array();

        if (preg_match('/# @description\s+(.+)/i', $content, $m)) {
            $metadata['description'] = trim($m[1]);
        }
        if (preg_match('/# @author\s+(.+)/i', $content, $m)) {
            $metadata['author'] = trim($m[1]);
        }
        if (preg_match('/# @version\s+(.+)/i', $content, $m)) {
            $metadata['version'] = trim($m[1]);
        }

        return $metadata;
    }

    /**
     * Basic Rego syntax validation
     * @param string $content Rego content
     * @return array validation result
     */
    private function validateRego($content)
    {
        // Check for package declaration
        if (!preg_match('/^package\s+[\w.]+/m', $content)) {
            return array('valid' => false, 'error' => 'Missing package declaration');
        }

        // Check for balanced braces
        $open = substr_count($content, '{');
        $close = substr_count($content, '}');
        if ($open !== $close) {
            return array('valid' => false, 'error' => 'Unbalanced braces');
        }

        // Check for at least one rule
        if (!preg_match('/^\s*(allow|deny|alert|block)\s*[=:{]/m', $content)) {
            return array('valid' => false, 'error' => 'No allow/deny/alert/block rule found');
        }

        return array('valid' => true);
    }

    /**
     * Get template content by name
     * @param string $name Template name
     * @return string|null Template content
     */
    private function getTemplateContent($name)
    {
        $templates = array(
            'home_default' => $this->getHomeDefaultTemplate(),
            'bedtime' => $this->getBedtimeTemplate(),
            'high_usage' => $this->getHighUsageTemplate(),
            'homework_helper' => $this->getHomeworkHelperTemplate(),
            'privacy_check' => $this->getPrivacyCheckTemplate(),
            'cost_limit' => $this->getCostLimitTemplate(),
            'device_restrict' => $this->getDeviceRestrictTemplate(),
            'weekend_only' => $this->getWeekendOnlyTemplate(),
            'work_hours' => $this->getWorkHoursTemplate(),
            'content_filter' => $this->getContentFilterTemplate()
        );

        return $templates[$name] ?? null;
    }

    private function getHomeDefaultTemplate()
    {
        return <<<'REGO'
# YORI Policy: Home Default
# @description Allow all LLM requests - base policy for home use
# @author YORI Team
# @version 1.0.0

package yori.policies.home_default

# Default allow - no restrictions
default allow = true

# No alerts
default alert = false

# No blocking
default block = false
REGO;
    }

    private function getBedtimeTemplate()
    {
        return <<<'REGO'
# YORI Policy: Bedtime Restrictions
# @description Block LLM access after 9 PM and before 7 AM
# @author YORI Team
# @version 1.0.0

package yori.policies.bedtime

import future.keywords.if

default allow = true
default block = false

# Block requests between 9 PM (21:00) and 7 AM (07:00)
block if {
    hour := time.clock([time.now_ns(), "Local"])[0]
    hour >= 21
}

block if {
    hour := time.clock([time.now_ns(), "Local"])[0]
    hour < 7
}

# Allow during normal hours
allow if {
    not block
}
REGO;
    }

    private function getHighUsageTemplate()
    {
        return <<<'REGO'
# YORI Policy: High Usage Alert
# @description Alert when device exceeds 50 requests per day
# @author YORI Team
# @version 1.0.0

package yori.policies.high_usage

default allow = true
default alert = false
default block = false

# Alert if daily request count exceeds threshold
alert if {
    input.daily_request_count > 50
}

# Additional alert for very high usage
alert if {
    input.daily_request_count > 100
}
REGO;
    }

    private function getHomeworkHelperTemplate()
    {
        return <<<'REGO'
# YORI Policy: Homework Helper
# @description Track educational keywords in prompts
# @author YORI Team
# @version 1.0.0

package yori.policies.homework_helper

default allow = true
default alert = false

# Educational keywords to track
educational_keywords = {
    "homework", "essay", "math", "science", "history",
    "solve", "explain", "calculate", "write my", "help with"
}

# Alert when educational keywords detected
alert if {
    some keyword in educational_keywords
    contains(lower(input.prompt), keyword)
}
REGO;
    }

    private function getPrivacyCheckTemplate()
    {
        return <<<'REGO'
# YORI Policy: Privacy Check
# @description Alert on potential PII in prompts (emails, phones, SSN)
# @author YORI Team
# @version 1.0.0

package yori.policies.privacy_check

default allow = true
default alert = false

# Check for email patterns
alert if {
    regex.match(`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`, input.prompt)
}

# Check for phone number patterns
alert if {
    regex.match(`\b\d{3}[-.]?\d{3}[-.]?\d{4}\b`, input.prompt)
}

# Check for SSN patterns
alert if {
    regex.match(`\b\d{3}-\d{2}-\d{4}\b`, input.prompt)
}

# Check for credit card patterns
alert if {
    regex.match(`\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b`, input.prompt)
}
REGO;
    }

    private function getCostLimitTemplate()
    {
        return <<<'REGO'
# YORI Policy: Cost Limit
# @description Alert when estimated daily cost exceeds threshold
# @author YORI Team
# @version 1.0.0

package yori.policies.cost_limit

default allow = true
default alert = false
default block = false

# Cost threshold in cents (default $5 = 500 cents)
cost_threshold = 500

# Alert if daily cost exceeds threshold
alert if {
    input.daily_cost_cents > cost_threshold
}

# Block if cost exceeds 2x threshold
block if {
    input.daily_cost_cents > (cost_threshold * 2)
}
REGO;
    }

    private function getDeviceRestrictTemplate()
    {
        return <<<'REGO'
# YORI Policy: Device Restrictions
# @description Allow/deny specific devices by IP address
# @author YORI Team
# @version 1.0.0

package yori.policies.device_restrict

default allow = true
default block = false

# Blocked devices (add IPs to block)
blocked_devices = {
    # "192.168.1.100",  # Example: Kids tablet
    # "192.168.1.101",  # Example: Guest device
}

# Block requests from blocked devices
block if {
    input.client_ip in blocked_devices
}

# Allowed devices bypass all other policies
allowed_devices = {
    # "192.168.1.1",    # Example: Admin workstation
}

allow if {
    input.client_ip in allowed_devices
}
REGO;
    }

    private function getWeekendOnlyTemplate()
    {
        return <<<'REGO'
# YORI Policy: Weekend Only
# @description Only allow LLM access on weekends
# @author YORI Team
# @version 1.0.0

package yori.policies.weekend_only

import future.keywords.if

default allow = false
default block = false
default alert = false

# Get day of week (0 = Sunday, 6 = Saturday)
is_weekend if {
    day := time.weekday(time.now_ns())
    day == "Saturday"
}

is_weekend if {
    day := time.weekday(time.now_ns())
    day == "Sunday"
}

# Allow on weekends
allow if {
    is_weekend
}

# Block on weekdays
block if {
    not is_weekend
}
REGO;
    }

    private function getWorkHoursTemplate()
    {
        return <<<'REGO'
# YORI Policy: Work Hours
# @description Only allow LLM access during business hours (9 AM - 5 PM)
# @author YORI Team
# @version 1.0.0

package yori.policies.work_hours

import future.keywords.if

default allow = false
default block = false

# Check if within work hours (9 AM to 5 PM)
is_work_hours if {
    hour := time.clock([time.now_ns(), "Local"])[0]
    hour >= 9
    hour < 17
}

# Allow during work hours
allow if {
    is_work_hours
}

# Block outside work hours
block if {
    not is_work_hours
}
REGO;
    }

    private function getContentFilterTemplate()
    {
        return <<<'REGO'
# YORI Policy: Content Filter
# @description Block prompts containing inappropriate keywords
# @author YORI Team
# @version 1.0.0

package yori.policies.content_filter

default allow = true
default block = false
default alert = false

# Add inappropriate keywords to block
blocked_keywords = {
    # Add keywords here
    # "example_bad_word",
}

# Alert keywords (less severe)
alert_keywords = {
    # "example_concerning_word",
}

# Block if blocked keyword found
block if {
    some keyword in blocked_keywords
    contains(lower(input.prompt), keyword)
}

# Alert if concerning keyword found
alert if {
    some keyword in alert_keywords
    contains(lower(input.prompt), keyword)
}

# Allow if no blocked keywords
allow if {
    not block
}
REGO;
    }
}
