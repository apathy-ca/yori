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

namespace OPNsense\YORI;

use OPNsense\Base\IndexController as BaseIndexController;

/**
 * Class IndexController
 * @package OPNsense\YORI
 * Routes to all YORI UI pages
 */
class IndexController extends BaseIndexController
{
    /**
     * Default index - redirect to dashboard
     */
    public function indexAction()
    {
        $this->view->pick('OPNsense/YORI/dashboard');
    }

    /**
     * Dashboard page - main overview with widgets
     */
    public function dashboardAction()
    {
        $this->view->pick('OPNsense/YORI/dashboard');
    }

    /**
     * Audit log viewer page
     */
    public function auditlogAction()
    {
        $this->view->pick('OPNsense/YORI/auditlog');
    }

    /**
     * Policies management page
     */
    public function policiesAction()
    {
        $this->view->pick('OPNsense/YORI/policies');
    }

    /**
     * Policy editor page
     * @param string $policy Optional policy name to edit
     */
    public function policyEditorAction($policy = null)
    {
        $this->view->policyName = $policy;
        $this->view->pick('OPNsense/YORI/policy_editor');
    }

    /**
     * Policy library page - pre-built templates
     */
    public function policyLibraryAction()
    {
        $this->view->pick('OPNsense/YORI/policy_library');
    }

    /**
     * Enforcement settings page
     */
    public function enforcementAction()
    {
        $this->view->pick('OPNsense/YORI/enforcement');
    }

    /**
     * Enforcement dashboard with statistics
     */
    public function enforcementDashboardAction()
    {
        $this->view->pick('OPNsense/YORI/enforcement_dashboard');
    }

    /**
     * Enforcement timeline page
     */
    public function enforcementTimelineAction()
    {
        $this->view->pick('OPNsense/YORI/enforcement_timeline');
    }

    /**
     * Allowlist management page
     */
    public function allowlistAction()
    {
        $this->view->pick('OPNsense/YORI/allowlist');
    }

    /**
     * Emergency override page
     */
    public function emergencyAction()
    {
        $this->view->pick('OPNsense/YORI/emergency');
    }

    /**
     * Settings/configuration page
     */
    public function settingsAction()
    {
        $this->view->pick('OPNsense/YORI/settings');
    }

    /**
     * Token usage tracking page
     */
    public function tokensAction()
    {
        $this->view->pick('OPNsense/YORI/tokens');
    }

    /**
     * Cost monitoring and budgets page
     */
    public function costsAction()
    {
        $this->view->pick('OPNsense/YORI/costs');
    }

    /**
     * Reports and analytics page
     */
    public function reportsAction()
    {
        $this->view->pick('OPNsense/YORI/reports');
    }
}
