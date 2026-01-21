# YORI OPNsense Integration

This directory contains the OPNsense web UI integration for YORI's enforcement mode.

## Directory Structure

```
opnsense/
├── src/opnsense/mvc/app/
│   ├── controllers/OPNsense/YORI/Api/
│   │   └── EnforcementController.php      # API endpoints for enforcement settings
│   ├── models/OPNsense/YORI/
│   │   ├── Enforcement.xml                 # Data model definition
│   │   └── EnforcementForm.xml             # Form definition for UI
│   └── views/OPNsense/YORI/
│       ├── enforcement.volt                # Enforcement settings page
│       └── widgets/
│           └── enforcement_status.volt     # Dashboard widget
└── README.md                               # This file
```

## Components

### 1. API Controller (`EnforcementController.php`)

Provides REST API endpoints for enforcement mode management:

- `GET /api/yori/enforcement/status` - Get current enforcement status
- `GET /api/yori/enforcement/get` - Get enforcement settings
- `POST /api/yori/enforcement/set` - Update enforcement settings
- `GET /api/yori/enforcement/test/{policy}` - Test policy configuration
- `GET /api/yori/enforcement/getConsentWarning` - Get consent warning text

### 2. Enforcement Settings Page (`enforcement.volt`)

Full-featured enforcement mode configuration interface:

- Real-time status display with color-coded indicators
- Mode switching (observe/advisory/enforce)
- Enforcement enable/disable toggle
- Explicit consent checkbox with warning modal
- Per-policy action configuration (allow/alert/block)
- Policy testing tool
- Comprehensive help and warnings

### 3. Dashboard Widget (`enforcement_status.volt`)

At-a-glance enforcement status widget for the OPNsense dashboard:

- Current mode display (observe/advisory/enforce)
- Active blocking indicator (red warning if enforcement is active)
- Quick link to enforcement settings
- Auto-refreshes every 10 seconds

### 4. Model & Form Definitions (`Enforcement.xml`, `EnforcementForm.xml`)

OPNsense MVC model and form definitions:

- Validates consent requirements
- Defines field types and constraints
- Provides inline help and warnings
- Structured configuration layout

## Installation

### 1. Copy Files to OPNsense System

```bash
# Copy to OPNsense installation
scp -r opnsense/src/* root@opnsense-router:/usr/local/

# Or if developing locally
cp -r opnsense/src/* /usr/local/
```

### 2. Set Permissions

```bash
# On OPNsense router
chown -R root:wheel /usr/local/opnsense/mvc/app/controllers/OPNsense/YORI
chown -R root:wheel /usr/local/opnsense/mvc/app/models/OPNsense/YORI
chown -R root:wheel /usr/local/opnsense/mvc/app/views/OPNsense/YORI

chmod 644 /usr/local/opnsense/mvc/app/controllers/OPNsense/YORI/Api/*.php
chmod 644 /usr/local/opnsense/mvc/app/models/OPNsense/YORI/*.xml
chmod 644 /usr/local/opnsense/mvc/app/views/OPNsense/YORI/*.volt
chmod 644 /usr/local/opnsense/mvc/app/views/OPNsense/YORI/widgets/*.volt
```

### 3. Register with OPNsense

Add YORI menu entries to OPNsense menu configuration:

```xml
<!-- Add to /usr/local/opnsense/mvc/app/config/menu.xml -->
<menu>
    <YORI>
        <label>YORI</label>
        <order>600</order>
        <children>
            <Enforcement>
                <url>/ui/yori/enforcement</url>
                <order>20</order>
            </Enforcement>
        </children>
    </YORI>
</menu>
```

### 4. Configure PHP Dependencies

Ensure YAML support is available:

```bash
# Install PHP YAML extension if not present
pkg install php81-yaml  # or appropriate PHP version
```

### 5. Restart OPNsense Web UI

```bash
# Restart configd (configuration daemon)
service configd restart

# Clear OPNsense template cache
rm -rf /usr/local/opnsense/mvc/app/cache/*

# Restart web UI
service nginx restart
```

## Usage

### Accessing the Enforcement Settings

1. Log in to OPNsense web interface
2. Navigate to **YORI → Enforcement**
3. Configure enforcement mode settings

### Adding Dashboard Widget

1. Go to OPNsense dashboard
2. Click **+ Add Widget**
3. Select **YORI Enforcement Status**
4. Widget will show current enforcement mode at a glance

### API Usage

The enforcement API can be accessed programmatically:

```bash
# Get status
curl -k -u root:password https://opnsense-router/api/yori/enforcement/status

# Test policy
curl -k -u root:password https://opnsense-router/api/yori/enforcement/test/bedtime
```

## Configuration Flow

### Enabling Enforcement Mode (Recommended Steps)

1. **Start in Observe Mode**
   - Mode: `observe`
   - Enforcement Enabled: `unchecked`
   - Monitor for several days

2. **Review Audit Logs**
   - Go to **YORI → Audit Logs**
   - Understand what would be blocked
   - Identify false positives

3. **Configure Policy Actions**
   - Go to **YORI → Enforcement**
   - Set per-policy actions carefully
   - Use `alert` for testing, `block` for enforcement

4. **Switch to Advisory Mode** (Optional)
   - Mode: `advisory`
   - See alerts without blocking
   - Verify configuration is correct

5. **Enable Enforcement Mode**
   - Mode: `enforce`
   - Enforcement Enabled: `checked`
   - **Accept Consent:** `checked` (WARNING modal will appear)
   - Save settings

6. **Monitor and Adjust**
   - Watch for blocked requests
   - Adjust policy actions as needed
   - Add allowlist exceptions (Worker 11)

### Emergency Disable

If enforcement is causing problems:

**Option 1: Via Web UI**
- Go to **YORI → Enforcement**
- Uncheck **Enforcement Enabled**
- OR change Mode to **observe**

**Option 2: Via Configuration File**
```bash
# Edit config
vi /usr/local/etc/yori/yori.conf

# Set enforcement.enabled to false
enforcement:
  enabled: false

# Restart YORI
service yori restart
```

**Option 3: Via API**
```bash
curl -k -u root:password -X POST \
  -d 'enforcement[enabled]=false' \
  https://opnsense-router/api/yori/enforcement/set
```

## Safety Features

The UI implements multiple safety mechanisms:

1. **Explicit Consent Modal**
   - Displayed when checking consent checkbox
   - Lists all risks and requirements
   - Requires explicit acceptance

2. **Color-Coded Status**
   - Red: Enforcement active (blocking requests)
   - Yellow: Enforcement configured but not active
   - Blue: Advisory mode (alerts only)
   - Green: Observe mode (monitoring only)

3. **Real-Time Validation**
   - Consent requirement enforced
   - Cannot enable without all requirements met
   - JavaScript validation before form submission

4. **Comprehensive Help**
   - Inline help for every setting
   - Dedicated help tab
   - Testing tools to verify configuration

## Troubleshooting

### Enforcement Not Activating

Check all requirements are met:
```bash
# Via API
curl -k https://opnsense-router/api/yori/enforcement/status

# Should return:
# {
#   "mode": "enforce",
#   "enforcement_enabled": true,
#   "consent_accepted": true,
#   "enforcement_active": true
# }
```

### Configuration Not Saving

Check file permissions:
```bash
ls -la /usr/local/etc/yori/yori.conf
# Should be writable by www user
chown www:www /usr/local/etc/yori/yori.conf
```

### Widget Not Appearing

Clear template cache:
```bash
rm -rf /usr/local/opnsense/mvc/app/cache/*
service nginx restart
```

### API Errors

Check PHP error log:
```bash
tail -f /var/log/nginx/error.log
```

## Development

### Testing Changes

After modifying Volt templates:
```bash
# Clear cache
rm -rf /usr/local/opnsense/mvc/app/cache/*

# Reload page in browser (Ctrl+F5 for hard refresh)
```

After modifying PHP controllers:
```bash
# No cache clear needed for PHP
# Just reload the page
```

### Debugging

Enable verbose logging in controller:
```php
syslog(LOG_DEBUG, "YORI: " . print_r($data, true));
```

View logs:
```bash
tail -f /var/log/messages | grep YORI
```

## Security Considerations

1. **Authentication Required**
   - All API endpoints require OPNsense authentication
   - Use HTTPS for web UI access

2. **Audit Logging**
   - All enforcement changes are logged to syslog
   - Format: `YORI enforcement settings changed: mode=X, enabled=Y, consent=Z`

3. **Consent Validation**
   - Server-side validation in PHP
   - Cannot bypass via API manipulation
   - Configuration file changes also validated on service start

4. **Safe Defaults**
   - Enforcement disabled by default
   - Consent not accepted by default
   - Mode defaults to observe

## Future Enhancements

- Integration with OPNsense's built-in authentication system
- RBAC support for different user roles
- Enhanced audit log viewer in UI
- Policy editor with syntax highlighting
- Real-time blocking statistics dashboard

## Support

For issues related to the OPNsense integration:

1. Check OPNsense logs: `/var/log/nginx/error.log`
2. Check YORI logs: `/var/log/yori.log`
3. Review configuration: `/usr/local/etc/yori/yori.conf`
4. Test API directly: `curl -k https://localhost/api/yori/enforcement/status`

## License

Copyright (C) 2026 YORI Project. All rights reserved.
