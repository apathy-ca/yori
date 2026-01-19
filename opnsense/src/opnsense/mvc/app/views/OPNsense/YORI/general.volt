{#
 # Copyright (C) 2024 YORI Project
 # All rights reserved.
 #
 # Redistribution and use in source and binary forms, with or without
 # modification, are permitted provided that the following conditions are met:
 #
 # 1. Redistributions of source code must retain the above copyright notice,
 #    this list of conditions and the following disclaimer.
 #
 # 2. Redistributions in binary form must reproduce the above copyright
 #    notice, this list of conditions and the following disclaimer in the
 #    documentation and/or other materials provided with the distribution.
 #
 # THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
 # INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
 # AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 # AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
 # OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 # SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 # INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 # CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 # ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 # POSSIBILITY OF SUCH DAMAGE.
 #}

<div class="content-box" style="padding-bottom: 1.5em;">
    <div class="content-box-main">
        <div class="table-responsive">
            <div class="container-fluid">
                <h1>{{ lang._('YORI - General Settings') }}</h1>
                <p>{{ lang._('Configure YORI LLM gateway settings') }}</p>

                <hr/>

                <div class="row">
                    <div class="col-md-12">
                        <div class="alert alert-info">
                            <strong>{{ lang._('Note:') }}</strong>
                            {{ lang._('Configuration management will be implemented in a future update. For now, edit the configuration file directly at /usr/local/etc/yori/yori.conf') }}
                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-12">
                        <h2>{{ lang._('Current Configuration') }}</h2>
                        <table class="table table-striped">
                            <tbody>
                                <tr>
                                    <td style="width:30%"><strong>{{ lang._('Configuration File') }}</strong></td>
                                    <td><code>/usr/local/etc/yori/yori.conf</code></td>
                                </tr>
                                <tr>
                                    <td><strong>{{ lang._('Audit Database') }}</strong></td>
                                    <td><code>/var/db/yori/audit.db</code></td>
                                </tr>
                                <tr>
                                    <td><strong>{{ lang._('Policy Directory') }}</strong></td>
                                    <td><code>/usr/local/etc/yori/policies</code></td>
                                </tr>
                                <tr>
                                    <td><strong>{{ lang._('Log Directory') }}</strong></td>
                                    <td><code>/var/log/yori</code></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="row" style="margin-top: 20px;">
                    <div class="col-md-12">
                        <h2>{{ lang._('Configuration Options') }}</h2>
                        <dl class="dl-horizontal">
                            <dt>{{ lang._('mode') }}</dt>
                            <dd>{{ lang._('Operation mode: observe, advisory, or enforce') }}</dd>

                            <dt>{{ lang._('listen') }}</dt>
                            <dd>{{ lang._('Listen address and port (e.g., 0.0.0.0:8443)') }}</dd>

                            <dt>{{ lang._('endpoints') }}</dt>
                            <dd>{{ lang._('List of LLM API endpoints to intercept') }}</dd>

                            <dt>{{ lang._('audit.database') }}</dt>
                            <dd>{{ lang._('Path to SQLite audit database') }}</dd>

                            <dt>{{ lang._('audit.retention_days') }}</dt>
                            <dd>{{ lang._('Number of days to retain audit logs') }}</dd>

                            <dt>{{ lang._('policies.directory') }}</dt>
                            <dd>{{ lang._('Directory containing OPA policy files (.rego)') }}</dd>

                            <dt>{{ lang._('policies.default') }}</dt>
                            <dd>{{ lang._('Default policy file to use') }}</dd>
                        </dl>
                    </div>
                </div>

                <div class="row" style="margin-top: 20px;">
                    <div class="col-md-12">
                        <h2>{{ lang._('Example Configuration') }}</h2>
                        <pre style="background-color: #f5f5f5; padding: 15px; border-radius: 4px;">mode: observe
listen: 0.0.0.0:8443

endpoints:
  - domain: api.openai.com
    enabled: true
  - domain: api.anthropic.com
    enabled: true
  - domain: gemini.google.com
    enabled: true
  - domain: api.mistral.ai
    enabled: true

audit:
  database: /var/db/yori/audit.db
  retention_days: 365

policies:
  directory: /usr/local/etc/yori/policies
  default: home_default.rego</pre>
                    </div>
                </div>

                <div class="row" style="margin-top: 20px;">
                    <div class="col-md-12">
                        <a href="/ui/yori" class="btn btn-primary">
                            <i class="fa fa-arrow-left fa-fw"></i> {{ lang._('Back to Service Management') }}
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
