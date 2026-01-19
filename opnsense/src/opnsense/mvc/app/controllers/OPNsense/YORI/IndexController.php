<?php

/**
 * Copyright (C) 2024 YORI Project
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
 * AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 * AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
 * OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

namespace OPNsense\YORI;

use OPNsense\Base\IndexController as BaseIndexController;
use OPNsense\Core\Backend;

/**
 * Class IndexController
 * @package OPNsense\YORI
 */
class IndexController extends BaseIndexController
{
    /**
     * Main page - Service Management
     */
    public function indexAction()
    {
        // Get service status
        $backend = new Backend();
        $statusResponse = $backend->configdRun("yori status");

        // Parse status
        $isRunning = strpos($statusResponse, "is running") !== false;

        // Pass variables to view
        $this->view->service_status = $isRunning ? 'running' : 'stopped';
        $this->view->config_path = '/usr/local/etc/yori/yori.conf';
        $this->view->database_path = '/var/db/yori/audit.db';
        $this->view->version = '0.1.0';

        // Pick the template to render
        $this->view->pick('OPNsense/YORI/index');
    }

    /**
     * General settings page
     */
    public function generalAction()
    {
        $this->view->pick('OPNsense/YORI/general');
    }
}
