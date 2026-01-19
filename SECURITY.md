# Security Policy

## Supported Versions

YORI is currently in early development (v0.1.0 alpha). Security updates will be provided for the latest release only.

| Version | Supported          | Notes |
| ------- | ------------------ | ----- |
| 0.1.x   | :white_check_mark: | Current development version |
| < 0.1.0 | :x:                | Pre-release, not supported |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in YORI, please report it privately.

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, use one of these methods:

1. **GitHub Security Advisories (Preferred)**
   - Go to [https://github.com/apathy-ca/yori/security/advisories/new](https://github.com/apathy-ca/yori/security/advisories/new)
   - This allows secure, private disclosure

2. **Direct Contact**
   - Email: jamesrahenry@henrynet.ca
   - Subject: "YORI Security Vulnerability"
   - Include detailed description and reproduction steps

### What to Include

Please provide:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)
- Your contact information

### Response Timeline

- **Initial Response:** Within 48 hours
- **Status Update:** Within 7 days
- **Fix Target:** Within 30 days (depending on severity)

## Security Considerations

### TLS Interception

YORI performs TLS interception to analyze LLM traffic. This requires:
- Installing a custom CA certificate on client devices
- Proper certificate management
- Understanding the security implications

**Important:** TLS interception can be detected and may break:
- Certificate pinning
- HSTS (HTTP Strict Transport Security)
- Some mobile apps

### Data Storage

YORI stores audit logs in SQLite:
- Logs contain prompt previews (first 200 chars by default)
- Logs may contain sensitive information
- Default retention: 365 days
- No encryption at rest (router storage)

**Recommendation:** Regularly review audit logs and retention policies.

### Network Security

YORI runs on your OPNsense router:
- Listen on internal network only (default: 0.0.0.0:8443)
- Do not expose to internet
- Use firewall rules to restrict access

### Dependency Security

YORI uses:
- **Rust crates** from SARK (sark-opa, sark-cache)
- **Python packages** (FastAPI, uvicorn, etc.)

We monitor dependencies via:
- Dependabot (GitHub)
- `cargo audit` (Rust)
- `pip-audit` (Python)

## Security Features

### Observe Mode (Default)

- Logs only, never blocks
- Safe for initial deployment
- Learn usage patterns before enforcing

### Advisory Mode

- Logs and alerts
- No blocking
- Test policies before enforcement

### Enforcement Mode

- Optional blocking (requires explicit opt-in)
- Policy-based request denial
- Audit trail of all blocks

## Known Limitations

### v0.1.0

- SQLite has no access control (filesystem permissions only)
- No encryption at rest for audit logs
- CA certificate management is manual
- No built-in authentication (relies on OPNsense)

### Future Enhancements

- Encrypted audit logs
- Role-based access control
- Automated CA certificate rotation
- Integration with OPNsense authentication

## Security Audits

| Version | Audit Date | Auditor | Status |
|---------|-----------|---------|--------|
| 0.1.0   | TBD       | TBD     | Not yet audited |

Security audits will be conducted before v1.0.0 release.

## Compliance

YORI is designed for home use and does not currently target specific compliance frameworks. For enterprise compliance requirements, see [SARK](https://github.com/apathy-ca/sark).

## Acknowledgments

We appreciate responsible disclosure from security researchers. Contributors who report valid security issues will be acknowledged (unless they prefer to remain anonymous).

---

**Last Updated:** 2026-01-19
**Next Review:** 2026-04-19
