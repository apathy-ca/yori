# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-01-20

### Added
- **Enforcement Mode** - Optional blocking of LLM requests
  - Explicit user consent required
  - Per-policy enforcement toggles (allow/alert/block)
  - Mode switching UI (observe → advisory → enforce)
- **Block Page** - Friendly explanation when requests are blocked
  - Shows policy name, reason, timestamp
  - Override mechanism with password authentication
  - Rate limiting on override attempts (3/minute)
- **Allowlist System** - Prevent blocking trusted devices
  - Device allowlist (IP/MAC addresses)
  - Time-based exceptions (allow 9am-5pm for homework)
  - Emergency override (disable all enforcement instantly)
- **Enhanced Audit** - Complete enforcement event logging
  - Log all blocks, overrides, allowlist bypasses
  - Enforcement dashboard widget
  - Enforcement timeline view
  - Weekly enforcement summary reports

### Changed
- SQLite schema extended with enforcement columns
- Dashboard updated with enforcement metrics
- Configuration expanded with enforcement settings

### Performance
- Enforcement adds <1ms latency (still <10ms total p95)
- Memory usage unchanged (<256MB RSS)
- Block decision: <1ms (faster than proxying)

### Security
- Enforcement disabled by default (safe)
- Explicit consent required to enable
- Override passwords stored as hashes
- Rate limiting prevents brute force
- All enforcement events audited

[0.2.0]: https://github.com/apathy-ca/yori/releases/tag/v0.2.0
