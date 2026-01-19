# Worker Identity: integration-release

**Role:** Integration
**Agent:** Claude
**Branch:** cz1/feat/integration-release
**Phase:** 1
**Dependencies:** rust-foundation, python-proxy, opnsense-plugin, dashboard-ui, policy-engine, documentation, testing-qa

## Mission

Integrate all components, resolve conflicts, perform final QA, build release packages, and prepare v0.1.0 for public release.

## 🚀 YOUR FIRST ACTION

Create omnibus branch cz1/release/v0.1.0, merge all worker branches in dependency order (rust-foundation → python-proxy → opnsense-plugin → dashboard-ui → policy-engine → documentation → testing-qa), and resolve any merge conflicts.

## Objectives

1. Create release branch (cz1/release/v0.1.0)
2. Merge all worker branches in dependency order
3. Resolve merge conflicts and integration issues
4. Verify all tests pass on integrated codebase
5. Build release artifacts:

## Deliverables

Complete implementation of: Integrate all components, resolve conflicts, perform final QA, build release packages, and prepare v

## Dependencies from All Workers (1-7)

**Integration Checklist:**

### Worker 1: rust-foundation
- [ ] Rust builds for FreeBSD
- [ ] PyO3 bindings tested (`import yori_core` works)
- [ ] CI/CD green
- [ ] All unit tests passing

### Worker 2: python-proxy
- [ ] Proxy logs LLM traffic to SQLite
- [ ] FastAPI service starts (`uvicorn yori.main:app`)
- [ ] Health check responds (`GET /health`)
- [ ] <10ms latency verified
- [ ] All unit tests passing

### Worker 3: opnsense-plugin
- [ ] OPNsense plugin package builds (`.txz`)
- [ ] Plugin installs on OPNsense VM
- [ ] Service management works (start/stop/status)
- [ ] Web UI displays correctly

### Worker 4: dashboard-ui
- [ ] Dashboard displays all charts
- [ ] Audit log viewer functional
- [ ] CSV export works
- [ ] SQL queries optimized (<500ms)

### Worker 5: policy-engine
- [ ] Policies evaluate correctly (test with bedtime.rego)
- [ ] Alerts trigger successfully (test email/web)
- [ ] 4+ policy templates included
- [ ] All unit tests passing

### Worker 6: documentation
- [ ] All 12 documentation files complete
- [ ] Screenshots current and accurate
- [ ] Installation tested on fresh OPNsense VM
- [ ] All links working (no 404s)

### Worker 7: testing-qa
- [ ] >80% code coverage (Rust and Python)
- [ ] All tests passing (unit, integration, e2e)
- [ ] Performance targets met:
  - [ ] Latency <10ms (p95)
  - [ ] Memory <256MB RSS
  - [ ] Throughput >50 req/sec
- [ ] Benchmark reports generated

## Merge Order & Commands

```bash
# Create omnibus branch
git checkout main
git pull origin main
git checkout -b cz1/release/v0.1.0

# Merge in dependency order
git merge cz1/feat/rust-foundation --no-ff -m "Integrate: Rust foundation"
git merge cz1/feat/python-proxy --no-ff -m "Integrate: Python proxy"
git merge cz1/feat/opnsense-plugin --no-ff -m "Integrate: OPNsense plugin"
git merge cz1/feat/dashboard-ui --no-ff -m "Integrate: Dashboard UI"
git merge cz1/feat/policy-engine --no-ff -m "Integrate: Policy engine"
git merge cz1/feat/documentation --no-ff -m "Integrate: Documentation"
git merge cz1/feat/testing-qa --no-ff -m "Integrate: Testing & QA"

# Run full test suite
echo "Running Rust tests..."
cargo test --workspace

echo "Running Python tests..."
pytest tests/ -v

# Build release artifacts
echo "Building FreeBSD binary..."
./scripts/build-freebsd.sh

echo "Building Python wheel..."
python -m build

echo "Building OPNsense package..."
make -C opnsense package

# Verify artifacts
ls -lh target/x86_64-unknown-freebsd/release/libyori_core.so
ls -lh dist/yori-0.1.0-py3-none-any.whl
ls -lh opnsense/os-yori-0.1.0.txz
```

## Conflict Resolution Procedures

**If Merge Conflicts Occur:**

1. **Identify Conflict Owner:**
   - Files in `rust/`: Consult Worker 1 (check commit history)
   - Files in `python/`: Consult Worker 2
   - Files in `opnsense/`: Consult Workers 3 or 4
   - Files in `policies/`: Consult Worker 5
   - Files in `docs/`: Consult Worker 6
   - Files in `tests/`: Consult Worker 7

2. **Resolution Strategy:**
   ```bash
   # View conflict
   git diff --name-only --diff-filter=U

   # For each conflicted file
   git checkout --ours <file>    # If current worker is correct
   git checkout --theirs <file>  # If incoming worker is correct
   # Or manually merge in editor

   # Mark resolved
   git add <file>
   git commit
   ```

3. **Validation After Resolution:**
   ```bash
   # Re-run tests
   cargo test --workspace
   pytest tests/
   ```

## Final QA Checklist

```bash
# Fresh OPNsense VM installation test
# 1. Install plugin package
pkg add os-yori-0.1.0.txz

# 2. Verify files installed
ls /usr/local/opnsense/mvc/app/controllers/OPNsense/YORI/
ls /usr/local/etc/rc.d/yori

# 3. Start YORI service from web UI
# Navigate to: System → YORI → Service Management
# Click: Start Service

# 4. Generate test LLM traffic
curl -X POST http://router-ip:8443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"test"}]}'

# 5. Verify traffic logged
sqlite3 /var/db/yori/audit.db "SELECT COUNT(*) FROM audit_events;"
# Expected: >0

# 6. Check dashboard displays data
# Navigate to: System → YORI → Dashboard
# Expected: Charts show request data

# 7. Test policy evaluation
# Navigate to: System → YORI → Policies
# Enable bedtime.rego policy
# Generate traffic after 21:00
# Expected: Alert appears in dashboard

# 8. Verify alert triggers
# Check: Recent Alerts widget
# Expected: Alert from bedtime policy

# 9. Export audit logs to CSV
# Navigate to: System → YORI → Audit Logs
# Click: Export CSV
# Expected: File downloads successfully

# 10. Validate performance
# Run load test: ab -n 1000 -c 10 http://router-ip:8443/health
# Expected: <10ms latency, >50 req/sec
```

## Release Artifacts

**Files to Create:**

1. **Rust Binary:**
   - `target/x86_64-unknown-freebsd/release/libyori_core.so`
   - FreeBSD x86_64 shared library
   - Size: <10MB (stripped)

2. **Python Wheel:**
   - `dist/yori-0.1.0-py3-none-any.whl`
   - Platform-independent wheel
   - Includes Python proxy and dependencies

3. **OPNsense Package:**
   - `opnsense/os-yori-0.1.0.txz`
   - FreeBSD package with plugin, service, UI
   - Size: <5MB

4. **Documentation:**
   - `README.md` - Included in package
   - `CHANGELOG.md` - v0.1.0 release notes
   - `LICENSE` - MIT license

## Release Process

```bash
# On omnibus branch cz1/release/v0.1.0

# 1. Create CHANGELOG.md
cat > CHANGELOG.md <<'EOF'
# Changelog

## [0.1.0] - 2026-01-19

### Added
- Transparent proxy for LLM traffic (OpenAI, Anthropic, Gemini, Mistral)
- SQLite audit logging with 365-day retention
- Rust-based policy engine (sark-opa integration)
- OPNsense web UI (dashboard, audit viewer, policy editor)
- Advisory alert system (email, web, push notifications)
- 4+ pre-built policy templates (bedtime, high usage, privacy, homework)
- Comprehensive documentation (installation, configuration, policy guide)
- Performance: <10ms latency, <256MB RAM, 50 req/sec throughput

### Performance
- Latency overhead: <10ms (p95)
- Memory usage: <256MB RSS
- Throughput: >50 requests/sec
- SQLite queries: <100ms (100k+ records)

### Testing
- Code coverage: >80% (Rust and Python)
- All tests passing (unit, integration, e2e)
- Performance benchmarks validated

[0.1.0]: https://github.com/apathy-ca/yori/releases/tag/v0.1.0
EOF

# 2. Update version in files
# - Cargo.toml: version = "0.1.0"
# - pyproject.toml: version = "0.1.0"
# - opnsense/+MANIFEST: version = "0.1.0"

# 3. Commit final changes
git add CHANGELOG.md Cargo.toml pyproject.toml opnsense/+MANIFEST
git commit -m "chore: Prepare v0.1.0 release"

# 4. Merge to main
git checkout main
git merge cz1/release/v0.1.0 --no-ff -m "Release: v0.1.0"

# 5. Tag release
git tag -a v0.1.0 -m "YORI v0.1.0: Home LLM Gateway

Zero-trust LLM governance for home networks.

Features:
- Transparent proxy for LLM APIs
- SQLite audit logging
- Policy-based governance
- OPNsense integration
- Advisory alerts

Performance:
- <10ms latency overhead
- <256MB memory usage
- 50+ req/sec throughput

See CHANGELOG.md for full details."

# 6. Create GitHub release
gh release create v0.1.0 \
  --title "YORI v0.1.0: Home LLM Gateway" \
  --notes-file CHANGELOG.md \
  target/x86_64-unknown-freebsd/release/libyori_core.so \
  dist/yori-0.1.0-py3-none-any.whl \
  opnsense/os-yori-0.1.0.txz

# 7. Publish to GitHub (no push yet per user request)
# git push origin main --tags  # SKIP: User said no push
```

## Success Criteria

- [ ] All 7 worker branches merged to cz1/release/v0.1.0
- [ ] All merge conflicts resolved
- [ ] All tests passing on integrated codebase (100% success rate)
- [ ] Release artifacts built successfully:
  - [ ] Rust binary (libyori_core.so, <10MB)
  - [ ] Python wheel (yori-0.1.0-py3-none-any.whl)
  - [ ] OPNsense package (os-yori-0.1.0.txz, <5MB)
- [ ] Fresh installation tested on OPNsense VM
- [ ] All features functional (proxy, logging, policies, alerts, dashboard)
- [ ] Performance targets validated (<10ms, <256MB, 50 req/sec)
- [ ] Documentation complete and accurate
- [ ] CHANGELOG.md created for v0.1.0
- [ ] Version updated in all files (Cargo.toml, pyproject.toml, +MANIFEST)
- [ ] omnibus branch merged to main
- [ ] v0.1.0 tagged
- [ ] GitHub release created with artifacts
- [ ] Code committed to branch cz1/release/v0.1.0
- [ ] Ready for OPNsense plugins repository submission
