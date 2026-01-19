# YORI OPNsense Plugin

OPNsense plugin for YORI - Zero-trust LLM governance for home networks.

## Overview

This plugin integrates YORI with OPNsense, providing a web-based management interface for the YORI LLM gateway service. YORI transparently intercepts and governs LLM API traffic from your home network devices.

## Features

- **Service Management**: Start, stop, restart, and monitor the YORI service from the OPNsense web UI
- **Configuration**: Configure YORI operation modes (observe, advisory, enforce)
- **Status Monitoring**: Real-time service status updates
- **Auto-start**: Configure YORI to start automatically on boot
- **Integration**: Full integration with OPNsense service management

## Architecture

### Plugin Structure

```
opnsense/
├── +MANIFEST                    # Plugin metadata
├── Makefile                     # Package build system
├── src/
│   ├── opnsense/mvc/
│   │   └── app/
│   │       ├── controllers/OPNsense/YORI/
│   │       │   ├── Api/
│   │       │   │   └── ServiceController.php    # API for service control
│   │       │   └── IndexController.php          # Web UI controller
│   │       ├── models/OPNsense/YORI/
│   │       │   ├── General.xml                  # Configuration schema
│   │       │   └── General.php                  # Model class
│   │       └── views/OPNsense/YORI/
│   │           └── index.volt                   # Main web UI
│   ├── opnsense/service/
│   │   └── conf/actions.d/
│   │       └── actions_yori.conf                # Service actions
│   └── etc/
│       ├── inc/plugins.inc.d/
│       │   └── yori.inc                         # Plugin registration
│       └── rc.d/
│           └── yori                             # FreeBSD service script
```

### Component Description

#### Controllers

- **IndexController.php**: Handles web UI rendering and passes service status to templates
- **Api/ServiceController.php**: Provides REST API endpoints for service management:
  - `POST /api/yori/service/start` - Start the service
  - `POST /api/yori/service/stop` - Stop the service
  - `POST /api/yori/service/restart` - Restart the service
  - `GET /api/yori/service/status` - Get service status

#### Models

- **General.xml**: Defines the configuration schema for YORI including:
  - Operation mode (observe/advisory/enforce)
  - Listen address and port
  - Audit database settings
  - Policy configuration
  - LLM endpoint configuration

- **General.php**: Model class that wraps the XML configuration

#### Views

- **index.volt**: Web UI template with:
  - Service status display
  - Control buttons (start/stop/restart)
  - Auto-refresh status updates
  - Real-time feedback messages

#### Service Integration

- **rc.d/yori**: FreeBSD service script that:
  - Creates required directories
  - Manages service lifecycle
  - Generates default configuration
  - Runs YORI as a daemon

- **actions_yori.conf**: Maps configd actions to service commands

- **yori.inc**: Registers the plugin with OPNsense:
  - Adds service to system management
  - Enables configuration regeneration
  - Provides bootup hooks

## Building the Plugin

### Prerequisites

- OPNsense build environment (or standalone build with `make`)
- Python 3.9+ with required dependencies

### Build Package

```bash
cd opnsense
make package
```

This creates `os-yori-0.1.0.txz` package file.

### List Package Contents

```bash
make list
```

### Clean Build Artifacts

```bash
make clean
```

## Installation

### On OPNsense System

1. Copy the package to your OPNsense system:
   ```bash
   scp os-yori-0.1.0.txz root@opnsense:/tmp/
   ```

2. Install the package:
   ```bash
   ssh root@opnsense
   pkg add /tmp/os-yori-0.1.0.txz
   ```

3. Access the web UI:
   - Navigate to **Services → YORI** in the OPNsense web interface

### Manual Installation (Development)

For development testing:

```bash
make dev-install
```

To uninstall:

```bash
make dev-uninstall
```

## Configuration

### Default Configuration

The plugin creates a default configuration at `/usr/local/etc/yori/yori.conf`:

```yaml
mode: observe
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
  default: home_default.rego
```

### Operation Modes

- **observe**: Monitor LLM traffic without blocking (default)
- **advisory**: Log policy violations but allow requests
- **enforce**: Block requests that violate policies

### File Locations

- Configuration: `/usr/local/etc/yori/yori.conf`
- Audit database: `/var/db/yori/audit.db`
- Policy files: `/usr/local/etc/yori/policies/`
- Service logs: `/var/log/yori/`
- PID file: `/var/run/yori.pid`

## Usage

### Web Interface

1. Navigate to **Services → YORI**
2. View current service status
3. Use control buttons to manage the service:
   - **Start**: Start the YORI service
   - **Stop**: Stop the YORI service
   - **Restart**: Restart the YORI service
   - **Refresh Status**: Update status display

### Command Line

```bash
# Start service
service yori start

# Stop service
service yori stop

# Restart service
service yori restart

# Check status
service yori status
```

### Enable Auto-start

Edit `/etc/rc.conf.local`:

```bash
yori_enable="YES"
```

## API Endpoints

The plugin provides REST API endpoints for programmatic access:

### Get Status
```bash
curl http://localhost/api/yori/service/status
```

Response:
```json
{
  "status": "running",
  "version": "0.1.0",
  "response": "yori is running as pid 12345"
}
```

### Start Service
```bash
curl -X POST http://localhost/api/yori/service/start
```

### Stop Service
```bash
curl -X POST http://localhost/api/yori/service/stop
```

### Restart Service
```bash
curl -X POST http://localhost/api/yori/service/restart
```

## Troubleshooting

### Service Won't Start

1. Check service status:
   ```bash
   service yori status
   ```

2. Check configuration:
   ```bash
   cat /usr/local/etc/yori/yori.conf
   ```

3. Check logs:
   ```bash
   tail -f /var/log/yori/yori.log
   ```

4. Verify Python dependencies:
   ```bash
   pkg info | grep py39-
   ```

### Web UI Not Accessible

1. Verify plugin is installed:
   ```bash
   pkg info os-yori
   ```

2. Check OPNsense web server logs:
   ```bash
   tail -f /var/log/lighttpd/error.log
   ```

3. Clear OPNsense cache:
   ```bash
   rm -rf /var/cache/opnsense/*
   /usr/local/etc/rc.restart_webgui
   ```

### Permission Issues

Ensure correct ownership:
```bash
chown -R nobody:nobody /usr/local/etc/yori
chown -R nobody:nobody /var/db/yori
chown -R nobody:nobody /var/log/yori
```

## Development

### Extension Points for Worker 4 (dashboard-ui)

The plugin provides extension points for the dashboard UI:

- **Template Variables**: Available in Volt templates:
  - `$service_status` - Current service status
  - `$config_path` - Configuration file path
  - `$database_path` - Audit database path
  - `$version` - Plugin version

- **API Endpoints**: Service status API for integration

- **View Directory**: `src/opnsense/mvc/app/views/OPNsense/YORI/`

### Adding New Views

1. Create new Volt template in `views/OPNsense/YORI/`
2. Add action method in `IndexController.php`
3. Update menu registration if needed

### Adding API Endpoints

1. Add new action method in `Api/ServiceController.php`
2. Follow naming convention: `methodNameAction()`
3. Return associative arrays (converted to JSON)

## Dependencies

### Runtime Dependencies

- Python 3.9+
- py39-fastapi
- py39-uvicorn
- py39-httpx
- py39-pydantic
- py39-yaml

These are automatically installed when the package is installed via `pkg`.

## Version

Current version: **0.1.0**

## License

MIT License - See LICENSE file for details

## Maintainer

yori@example.com

## Links

- GitHub: https://github.com/yourusername/yori
- Documentation: See `docs/INSTALLATION.md`

## Interface Contract for Worker 4

Worker 4 (dashboard-ui) can extend this plugin by:

1. Adding new views in `src/opnsense/mvc/app/views/OPNsense/YORI/`
2. Accessing service status via API: `GET /api/yori/service/status`
3. Using Bootstrap 5 theme variables for consistent styling
4. Reading template variables passed from IndexController

Expected handoff artifacts:
- Plugin structure in place
- Service API operational
- Web UI rendering correctly
- Template system ready for extension
