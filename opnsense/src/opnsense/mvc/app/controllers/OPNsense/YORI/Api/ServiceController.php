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

namespace OPNsense\YORI\Api;

use OPNsense\Base\ApiMutableServiceControllerBase;
use OPNsense\Core\Backend;

/**
 * Class ServiceController
 * @package OPNsense\YORI\Api
 */
class ServiceController extends ApiMutableServiceControllerBase
{
    protected static $internalServiceClass = '\OPNsense\YORI\General';
    protected static $internalServiceTemplate = 'OPNsense/YORI';
    protected static $internalServiceEnabled = 'enabled';
    protected static $internalServiceName = 'yori';

    /**
     * Start YORI service
     * @return array service start result
     */
    public function startAction()
    {
        if ($this->request->isPost()) {
            $backend = new Backend();
            $response = $backend->configdRun("yori start");
            return array("response" => $response);
        } else {
            return array("response" => array());
        }
    }

    /**
     * Stop YORI service
     * @return array service stop result
     */
    public function stopAction()
    {
        if ($this->request->isPost()) {
            $backend = new Backend();
            $response = $backend->configdRun("yori stop");
            return array("response" => $response);
        } else {
            return array("response" => array());
        }
    }

    /**
     * Restart YORI service
     * @return array service restart result
     */
    public function restartAction()
    {
        if ($this->request->isPost()) {
            $backend = new Backend();
            $response = $backend->configdRun("yori restart");
            return array("response" => $response);
        } else {
            return array("response" => array());
        }
    }

    /**
     * Get YORI service status
     * @return array service status
     */
    public function statusAction()
    {
        $backend = new Backend();
        $response = $backend->configdRun("yori status");

        // Parse status response
        $status = "stopped";
        if (strpos($response, "is running") !== false) {
            $status = "running";
        }

        return array(
            "status" => $status,
            "version" => "0.1.0",
            "response" => trim($response)
        );
    }

    /**
     * Reconfigure YORI service
     * @return array reconfiguration result
     */
    public function reconfigureAction()
    {
        if ($this->request->isPost()) {
            $backend = new Backend();
            $response = $backend->configdRun("template reload OPNsense/YORI");

            // Restart service if it's running
            $statusResponse = $backend->configdRun("yori status");
            if (strpos($statusResponse, "is running") !== false) {
                $backend->configdRun("yori restart");
            }

            return array("status" => "ok", "response" => $response);
        } else {
            return array("status" => "failed", "response" => "POST required");
        }
    }
}
