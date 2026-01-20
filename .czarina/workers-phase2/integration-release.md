# Worker Identity: integration-release

**Role:** Integration
**Agent:** Claude
**Branch:** cz2/release/v0.2.0
**Phase:** 2
**Dependencies:** enforcement-mode, block-page, allowlist-blocklist, enhanced-audit

## Mission

Integrate all Phase 2 enforcement components, merge with Phase 1 stable code, perform comprehensive enforcement testing, build v0.2.0 release artifacts, and prepare public release with updated documentation.

## 🚀 YOUR FIRST ACTION

Create omnibus branch cz2/release/v0.2.0 from main (which has Phase 1), merge all Phase 2 worker branches in dependency order, and run full test suite to validate integration.

## Dependencies from All Phase 2 Workers

### Worker 9: enforcement-mode
- [ ] Enforcement mode configuration complete
- [ ] Explicit consent mechanism working
- [ ] Per-policy enforcement toggles functional
- [ ] Mode switching UI operational
- [ ] Block logic integrated into proxy
- [ ] All unit tests passing

### Worker 10: block-page
- [ ] Block page HTML template created
- [ ] Override mechanism functional (password auth)
- [ ] Override attempts logged
- [ ] Rate limiting working (3 attempts/min)
- [ ] All unit tests passing

### Worker 11: allowlist-blocklist
- [ ] Device allowlist configuration working
- [ ] Allowlist bypass functional
- [ ] Time-based exceptions operational
- [ ] Emergency override mechanism working
- [ ] Allowlist management UI complete
- [ ] All unit tests passing

### Worker 12: enhanced-audit
- [ ] SQLite schema extended
- [ ] All enforcement events logged
- [ ] Enforcement dashboard widget functional
- [ ] Enforcement timeline view complete
- [ ] Statistics accurate
- [ ] All unit tests passing

## Merge Order & Commands

```bash
# Create omnibus branch from main (Phase 1 stable)
git checkout main
git pull origin main
git checkout -b cz2/release/v0.2.0

# Merge Phase 2 workers in dependency order
git merge cz2/feat/enforcement-mode --no-ff -m "Integrate: Enforcement mode"
git merge cz2/feat/block-page --no-ff -m "Integrate: Block page and overrides"
git merge cz2/feat/allowlist-blocklist --no-ff -m "Integrate: Allowlist and emergency override"
git merge cz2/feat/enhanced-audit --no-ff -m "Integrate: Enhanced enforcement audit"

# Run full test suite
echo "Running Rust tests..."
cargo test --workspace

echo "Running Python tests..."
pytest tests/ -v

echo "Running enforcement-specific tests..."
pytest tests/integration/test_enforcement.py -v

# Build release artifacts
echo "Building FreeBSD binary..."
./scripts/build-freebsd.sh

echo "Building Python wheel..."
python -m build

echo "Building OPNsense package..."
make -C opnsense package

# Verify artifacts
ls -lh target/x86_64-unknown-freebsd/release/libyori_core.so
ls -lh dist/yori-0.2.0-py3-none-any.whl
ls -lh opnsense/os-yori-0.2.0.txz
```

## Final QA Checklist

### Enforcement Mode Testing

```bash
# 1. Fresh OPNsense VM installation
pkg add os-yori-0.2.0.txz

# 2. Verify enforcement mode disabled by default
cat /usr/local/etc/yori/yori.conf | grep "enforcement:"
# Expected: enabled: false, consent_accepted: false

# 3. Try to enable enforcement without consent
# Navigate to: System → YORI → Enforcement Settings
# Expected: Cannot enable (consent checkbox required)

# 4. Accept consent and enable enforcement
# Check consent box
# Click: Enable Enforcement
# Expected: Mode changes to "enforce"

# 5. Test policy blocking
# Configure bedtime policy with action: block
# Generate test traffic after 21:00
curl -X POST http://router-ip:8443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"test"}]}'

# Expected: Block page returned, request NOT forwarded
```

### Block Page Testing

```bash
# 6. Verify block page displays correctly
# Send blocked request, capture response
response=$(curl -s http://router-ip:8443/v1/chat/completions \
  -X POST -H "Content-Type: application/json" \
  -d '{"model":"gpt-4"}')

echo "$response" | grep "Request Blocked by YORI"
# Expected: Block page HTML

# 7. Test override mechanism
# Enter correct password in block page
# Expected: Request forwarded to LLM

# 8. Test wrong password
# Enter incorrect password
# Expected: Block page shown again, attempt logged

# 9. Test rate limiting
# Try 4 wrong passwords in 1 minute
# Expected: Locked out after 3 attempts
```

### Allowlist Testing

```bash
# 10. Add device to allowlist
# Navigate to: System → YORI → Allowlist
# Add: Dad's Laptop (192.168.1.100)

# 11. Test allowlist bypass
# Generate blocked request from allowlisted IP
curl -X POST http://router-ip:8443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-For: 192.168.1.100" \
  -d '{"model":"gpt-4"}'

# Expected: Request forwarded (NOT blocked)

# 12. Test time-based exception
# Configure: Mon-Fri 3pm-6pm for 192.168.1.102
# Generate request at 4pm on Monday
# Expected: Allowed (not blocked)

# 13. Test emergency override
# Navigate to: System → YORI → Emergency Override
# Enter admin password, click: Disable All Enforcement
# Expected: All policies bypassed, all requests allowed
```

### Audit Testing

```bash
# 14. Verify enforcement events logged
sqlite3 /var/db/yori/audit.db "
SELECT COUNT(*) FROM audit_events
WHERE enforcement_action IS NOT NULL;
"
# Expected: >0 (enforcement events exist)

# 15. Check enforcement dashboard
# Navigate to: System → YORI → Dashboard
# Expected: Enforcement Status widget shows:
#   - Total blocks
#   - Overrides (success/fail)
#   - Allowlist bypasses

# 16. View enforcement timeline
# Navigate to: System → YORI → Enforcement Timeline
# Expected: Chronological list of blocks, overrides, bypasses

# 17. Generate enforcement report
# Navigate to: System → YORI → Reports
# Click: Generate Weekly Enforcement Summary
# Expected: PDF/HTML report downloads
```

### Performance Validation

```bash
# 18. Test enforcement performance
wrk -t4 -c100 -d30s http://router-ip:8443/health
# Expected: Still <10ms p95 latency (enforcement adds <1ms)

# 19. Memory check
ps aux | grep yori | awk '{print $6/1024 " MB"}'
# Expected: Still <256MB RSS

# 20. Load test with enforcement
ab -n 1000 -c 10 http://router-ip:8443/v1/chat/completions
# Expected: >50 req/sec (same as Phase 1)
```

## Release Artifacts

**Files to Build:**

1. **Rust Binary:**
   - `target/x86_64-unknown-freebsd/release/libyori_core.so`
   - No changes from Phase 1 (enforcement is Python-side)

2. **Python Wheel:**
   - `dist/yori-0.2.0-py3-none-any.whl`
   - Includes enforcement, block-page, allowlist, enhanced-audit modules

3. **OPNsense Package:**
   - `opnsense/os-yori-0.2.0.txz`
   - Includes updated UI with enforcement settings

4. **Documentation Updates:**
   - `docs/ENFORCEMENT_GUIDE.md` - New guide for enforcement mode
   - `CHANGELOG.md` - v0.2.0 release notes
   - `README.md` - Updated with enforcement features

## Release Process

```bash
# On omnibus branch cz2/release/v0.2.0

# 1. Create/Update CHANGELOG.md
cat >> CHANGELOG.md <<'EOF'

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
EOF

# 2. Update version in files
# - pyproject.toml: version = "0.2.0"
# - opnsense/+MANIFEST: version = "0.2.0"

# 3. Create ENFORCEMENT_GUIDE.md
cat > docs/ENFORCEMENT_GUIDE.md <<'EOF'
# YORI Enforcement Mode Guide

## Overview

Enforcement mode allows YORI to actually block LLM requests based on policies.
This is an **opt-in feature** requiring explicit user consent.

## Enabling Enforcement

1. Navigate to: System → YORI → Enforcement Settings
2. Read the warning about potential functionality breakage
3. Check: "I understand and accept the risks"
4. Click: Enable Enforcement
5. Set per-policy actions (allow/alert/block)

## Per-Policy Enforcement

Each policy can have different actions:
- **Allow:** Always allow (no enforcement)
- **Alert:** Log and alert, but don't block
- **Block:** Actually block the request

## Allowlist

Prevent blocking trusted devices:
1. Navigate to: System → YORI → Allowlist
2. Add devices by IP or MAC address
3. Devices on allowlist bypass all policies

## Emergency Override

Disable all enforcement instantly:
1. Navigate to: System → YORI → Emergency Override
2. Enter admin password
3. Click: Disable All Enforcement
4. All requests allowed until re-enabled

## See Also
- Configuration Guide (CONFIGURATION.md)
- Policy Guide (POLICY_GUIDE.md)
- Troubleshooting (TROUBLESHOOTING.md)
EOF

# 4. Commit final changes
git add CHANGELOG.md docs/ENFORCEMENT_GUIDE.md pyproject.toml opnsense/+MANIFEST
git commit -m "chore: Prepare v0.2.0 release with enforcement mode"

# 5. Merge to main
git checkout main
git merge cz2/release/v0.2.0 --no-ff -m "Release: v0.2.0 - Enforcement Mode"

# 6. Tag release
git tag -a v0.2.0 -m "YORI v0.2.0: Enforcement Mode

Optional blocking of LLM requests with allowlist and override.

New Features:
- Enforcement mode (opt-in)
- Block page with friendly explanation
- Device allowlist and time exceptions
- Emergency override mechanism
- Enhanced audit logging

Security:
- Disabled by default
- Explicit consent required
- Password-protected overrides
- Complete audit trail

See CHANGELOG.md and docs/ENFORCEMENT_GUIDE.md for details."

# 7. Create GitHub release
gh release create v0.2.0 \
  --title "YORI v0.2.0: Enforcement Mode" \
  --notes-file CHANGELOG.md \
  dist/yori-0.2.0-py3-none-any.whl \
  opnsense/os-yori-0.2.0.txz

# 8. Publish to GitHub (no push per user preference)
# git push origin main --tags  # SKIP: User preference
```

## Success Criteria

- [ ] All 4 Phase 2 worker branches merged to cz2/release/v0.2.0
- [ ] All merge conflicts resolved
- [ ] All tests passing on integrated codebase (100% success rate)
- [ ] Enforcement mode functional:
  - [ ] Requests can be blocked by policies
  - [ ] Block page displays correctly
  - [ ] Override mechanism works (password auth)
  - [ ] Allowlist bypasses enforcement
  - [ ] Emergency override disables all policies
- [ ] Release artifacts built successfully:
  - [ ] Python wheel (yori-0.2.0-py3-none-any.whl)
  - [ ] OPNsense package (os-yori-0.2.0.txz)
- [ ] Fresh installation tested on OPNsense VM
- [ ] All enforcement features functional
- [ ] Performance targets maintained (<10ms, <256MB, 50 req/sec)
- [ ] Documentation updated (CHANGELOG, ENFORCEMENT_GUIDE)
- [ ] Version updated in all files
- [ ] v0.2.0 tagged
- [ ] GitHub release created with artifacts
- [ ] Code committed to branch cz2/release/v0.2.0
- [ ] Ready for v0.2.0 deployment

## Post-Release

### Monitoring
- Track enforcement mode adoption (how many enable it)
- Monitor override usage (are users overriding often?)
- Check for false positives (allowlist additions)
- Gather user feedback on block page UX

### Future Enhancements (v0.3.0+)
Based on PROJECT_PLAN.md future roadmap:
- v1.1.0: OpenSearch integration
- v1.2.0: Local LLM support (Ollama)
- v1.3.0: Multi-router federation
- v1.4.0: Advanced threat detection (prompt injection, secrets)

---

**End of Phase 2 Integration Worker**
