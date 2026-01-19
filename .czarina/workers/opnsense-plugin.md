# Worker Identity: opnsense-plugin

**Role:** Code
**Agent:** Cursor
**Branch:** cz1/feat/opnsense-plugin
**Phase:** 1
**Dependencies:** python-proxy

## Mission

Create OPNsense plugin structure with service management, web UI for start/stop/status, and package build system. Enable YORI service to run as a managed OPNsense service.

## 🚀 YOUR FIRST ACTION

Research OPNsense plugin structure by examining existing plugins in /usr/local/opnsense/, create opnsense/ directory with +MANIFEST and Makefile, and implement minimal ServiceController.php for service start/stop.

## Objectives

1. Create OPNsense plugin directory structure (opnsense/src/opnsense/mvc/)
2. Write +MANIFEST file with plugin metadata
3. Implement PHP controllers (Api/ServiceController.php, IndexController.php)
4. Create model definition (models/OPNsense/YORI/General.xml)
5. Create Volt templates for web UI (views/OPNsense/YORI/index.volt)
6. Implement rc.d service script for YORI daemon
7. Add service management actions (start, stop, restart, status)
8. Create Makefile for .txz package generation
9. Add auto-start on boot configuration option
10. Implement syslog integration for service logs

## Deliverables

Complete implementation of: Create OPNsense plugin structure with service management, web UI for start/stop/status, and package 

## Dependencies from Upstream Workers

### From python-proxy (Worker 2)

**Required Artifacts:**
- FastAPI service at `python/yori/main.py`
- Service start command: `uvicorn yori.main:app --host 0.0.0.0 --port 8443`
- Configuration file format: `/usr/local/etc/yori/yori.conf` (YAML)
- Health check endpoint: `GET /health`

**Verification Before Starting:**
```bash
# Verify Worker 2 service works
uvicorn yori.main:app --host 127.0.0.1 --port 8443 &
curl http://127.0.0.1:8443/health
# Expected: {"status": "healthy"}
```

## Interface Contract

### Exports for dashboard-ui (Worker 4)

**OPNsense Plugin Structure:**
- Plugin views directory: `opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/`
- Extension point for dashboard: `dashboard.volt` template
- Bootstrap 5 theme variables available
- Service status API: `Api/ServiceController.php`

**Template Variables:**
```php
// Available in Volt templates
$service_status    // 'running' | 'stopped'
$config_path       // '/usr/local/etc/yori/yori.conf'
$database_path     // '/var/db/yori/audit.db'
$version           // '0.1.0'
```

## Files to Create

**Plugin Structure:**
```
opnsense/
├── +MANIFEST                           # Plugin metadata
├── Makefile                            # Package build
└── src/opnsense/mvc/
    ├── app/
    │   ├── controllers/OPNsense/YORI/
    │   │   ├── Api/
    │   │   │   └── ServiceController.php    # Start/stop/status API
    │   │   └── IndexController.php          # Main page controller
    │   ├── models/OPNsense/YORI/
    │   │   └── General.xml                  # Configuration model
    │   └── views/OPNsense/YORI/
    │       ├── index.volt                   # Main page
    │       └── general.volt                 # Settings page
    └── service/conf/
        └── actions.d/
            └── actions_yori.conf            # Service actions
```

**Service Integration:**
- `opnsense/src/etc/rc.d/yori` - FreeBSD rc.d script
- `opnsense/src/opnsense/service/templates/OPNsense/YORI/rc.conf.d` - Config template

**Documentation:**
- `opnsense/README.md` - Plugin installation and usage
- `docs/INSTALLATION.md` - End-user installation guide

## Performance Targets

- **Plugin Load Time:** <2 seconds for UI to load
- **Service Start Time:** <5 seconds for YORI service to start
- **Package Size:** <5MB for .txz package (excluding dependencies)

## Testing Requirements

**Manual Tests:**
- Plugin installs via OPNsense package manager (test on VM)
- Service starts from web UI
- Service stops from web UI
- Service status displays correctly
- Auto-start on boot works

**Integration Tests:**
- Web UI renders correctly (Bootstrap 5)
- Service management API works
- Configuration saves and loads
- Logs appear in syslog

## Verification Commands

### From Worker Branch (cz1/feat/opnsense-plugin)

```bash
# Verify plugin structure
ls -la opnsense/src/opnsense/mvc/app/controllers/OPNsense/YORI/
ls -la opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/

# Build package
make -C opnsense package
# Expected: os-yori-0.1.0.txz created

# Check package contents
tar -tzf opnsense/os-yori-0.1.0.txz

# Verify manifest
cat opnsense/+MANIFEST
# Expected: Valid JSON with plugin metadata
```

### Installation Test (OPNsense VM)

```bash
# Install package
pkg add os-yori-0.1.0.txz

# Verify files installed
ls /usr/local/opnsense/mvc/app/controllers/OPNsense/YORI/
ls /usr/local/etc/rc.d/yori

# Test service start
service yori start

# Check service status
service yori status
# Expected: yori is running

# Test web UI
# Navigate to: System → YORI in OPNsense web interface
```

### Handoff Verification for Worker 4

Worker 4 should be able to:
```bash
# Extend plugin with dashboard views
# File: opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/dashboard.volt

# Access service status API
curl http://localhost/api/yori/service/status
# Expected: {"status": "running", "version": "0.1.0"}
```

## Success Criteria

- [ ] All objectives completed
- [ ] All files created as specified above
- [ ] Dependencies from Worker 2 verified (FastAPI service works)
- [ ] Interface contract implemented (plugin structure, templates)
- [ ] Plugin package builds successfully (.txz)
- [ ] Plugin installs on OPNsense VM
- [ ] Service management works (start/stop/restart/status)
- [ ] Web UI displays correctly (Bootstrap 5)
- [ ] Auto-start on boot configurable
- [ ] Syslog integration works
- [ ] Configuration saves and loads correctly
- [ ] Code committed to branch cz1/feat/opnsense-plugin
- [ ] Installation documentation complete (docs/INSTALLATION.md)
