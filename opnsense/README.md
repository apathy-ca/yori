# OPNsense Plugin

This directory will contain the OPNsense plugin package for YORI.

## Structure (To Be Implemented)

The OPNsense plugin will follow the standard plugin structure:

```
opnsense/
├── src/
│   └── opnsense/
│       ├── mvc/
│       │   └── app/
│       │       ├── controllers/  # PHP controllers
│       │       ├── models/       # PHP models
│       │       └── views/        # Volt templates
│       ├── service/
│       │   ├── conf/
│       │   │   └── actions.d/    # Service actions
│       │   └── templates/        # Config templates
│       └── www/                  # Static assets
├── Makefile                      # FreeBSD port Makefile
└── pkg-descr                     # Package description
```

## Development Plan

This will be implemented by Worker 6 (opnsense-packaging) after the core functionality is complete.

The plugin will provide:
- Web UI for configuration and dashboard
- Service management (start/stop YORI proxy)
- Integration with OPNsense firewall rules
- Log viewer and statistics

## References

- [OPNsense Plugin Development](https://docs.opnsense.org/development/frontend/models.html)
- [Plugin Structure](https://github.com/opnsense/plugins)
