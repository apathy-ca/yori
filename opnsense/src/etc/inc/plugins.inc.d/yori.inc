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

/**
 * YORI Plugin Registration
 *
 * This file registers the YORI plugin with OPNsense, adding it to the
 * system menu and service management.
 */

function yori_services()
{
    $services = array();

    $services[] = array(
        'description' => gettext('YORI LLM Gateway'),
        'configd' => array(
            'restart' => array('yori restart'),
            'start' => array('yori start'),
            'stop' => array('yori stop'),
        ),
        'name' => 'yori',
        'pidfile' => '/var/run/yori.pid'
    );

    return $services;
}

function yori_configure()
{
    return array(
        'bootup' => array('yori_configure_do'),
        'local' => array('yori_configure_do'),
    );
}

function yori_configure_do()
{
    // Generate configuration files from templates
    configd_run('template reload OPNsense/YORI');
}
