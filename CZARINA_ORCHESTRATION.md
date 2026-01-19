# YORI Czarina Orchestration Guide

**Version:** 1.0
**Project:** YORI v0.1.0 - Home LLM Gateway
**Workers:** 8 AI agents (Claude Code, Aider, Cursor, Windsurf)
**Timeline:** 6-8 weeks
**Autonomy Target:** 95-98%

---

## Overview & Quick Start

### What is This Guide?

This orchestration guide shows how to coordinate 8 AI coding agents working in parallel to build YORI, a lightweight LLM gateway for OPNsense routers. The czarina multi-agent system enables 3-4x faster delivery compared to sequential development.

### Czarina Role

The **Czar** (you, Claude Code, or another agent) coordinates all workers, monitors progress, unblocks dependencies, validates quality gates, and integrates work into releases.

### Prerequisites

**Required:**
- Czarina installed: `~/Source/czarina/czarina` or `~/.local/bin/czarina`
- Agents available: Claude Code, Aider, Cursor, Windsurf (as configured)
- Git worktrees configured for workers
- YORI repository at `/home/jhenry/Source/yori`

**Verify Setup:**
```bash
cd /home/jhenry/Source/yori
czarina status  # Check worker status
git branch -a   # Verify worker branches exist (cz1/feat/*)
```

### Launch Commands

```bash
# Launch all workers
cd /home/jhenry/Source/yori
czarina launch

# Launch daemon for 95-98% autonomy
czarina daemon start

# Check status
czarina status

# View daemon logs
czarina daemon logs
```

### Daemon Configuration

The daemon auto-approves file operations to achieve 95-98% autonomy. Current settings from `.czarina/config.json`:

```json
{
  "daemon": {
    "enabled": true,
    "auto_approve": ["read", "write", "commit"]
  }
}
```

**Manual Review Required:**
- Cross-worker file changes (conflicts)
- Build system modifications
- Configuration changes affecting other workers

---

## Worker Architecture

### Dependency Graph

```
                    ┌──────────────────┐
                    │   Worker 1       │
                    │ rust-foundation  │
                    │  (Claude Code)   │
                    └────────┬─────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
        ┌───────────────┐         ┌──────────────┐
        │   Worker 2    │         │  Worker 5    │
        │ python-proxy  │         │policy-engine │
        │    (Aider)    │         │(Claude Code) │
        └───────┬───────┘         └──────┬───────┘
                │                        │
                ▼                        │
        ┌───────────────┐                │
        │   Worker 3    │                │
        │opnsense-plugin│                │
        │   (Cursor)    │                │
        └───────┬───────┘                │
                │                        │
                ▼                        │
        ┌───────────────┐                │
        │   Worker 4    │                │
        │ dashboard-ui  │                │
        │  (Windsurf)   │                │
        └───────┬───────┘                │
                │                        │
                └────────────┬───────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
        ┌───────────────┐         ┌──────────────┐
        │   Worker 6    │         │  Worker 7    │
        │ documentation │         │ testing-qa   │
        │(Claude Code)  │         │   (Cursor)   │
        └───────┬───────┘         └──────┬───────┘
                │                        │
                └────────────┬───────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   Worker 8       │
                    │integration-release│
                    │  (Claude Code)   │
                    └──────────────────┘
```

### Worker Roles

| Worker | Role | Agent | Branch | Dependencies |
|--------|------|-------|--------|--------------|
| 1 | rust-foundation | Claude Code | cz1/feat/rust-foundation | None |
| 2 | python-proxy | Aider | cz1/feat/python-proxy | Worker 1 |
| 3 | opnsense-plugin | Cursor | cz1/feat/opnsense-plugin | Worker 2 |
| 4 | dashboard-ui | Windsurf | cz1/feat/dashboard-ui | Worker 3 |
| 5 | policy-engine | Claude Code | cz1/feat/policy-engine | Workers 1, 2 |
| 6 | documentation | Claude Code | cz1/feat/documentation | Workers 4, 5 |
| 7 | testing-qa | Cursor | cz1/feat/testing-qa | Worker 5 |
| 8 | integration-release | Claude Code | cz1/feat/integration-release | Workers 1-7 |

### Parallel vs Sequential Execution

**Critical Path (Sequential):** Workers 1 → 2 → 3 → 4
- Worker 1 must complete first (foundation for all)
- Worker 2 needs Worker 1's PyO3 bindings
- Worker 3 needs Worker 2's FastAPI service
- Worker 4 needs Worker 3's OPNsense plugin

**Parallel Opportunities:**
- Worker 5 can run alongside Workers 3-4 (after Worker 2 completes)
- Workers 6-7 can run alongside each other (after Worker 5 completes)
- Maximum parallelism: 2-3 workers simultaneously

**Timeline Impact:**
- Sequential: ~13 weeks (PROJECT_PLAN.md baseline)
- Parallel (czarina): 6-8 weeks (3-4x speedup)

---

## Phase-by-Phase Execution Plan

### Week 1-2: Foundation Phase

**Active Workers:** Worker 1 only

**Objectives:**
- Establish Rust workspace with SARK crate integration
- Create PyO3 bindings for Python integration
- Set up FreeBSD cross-compilation pipeline
- Configure CI/CD (GitHub Actions)

**Worker Assignments:**
- **Worker 1 (rust-foundation):** Full focus, no blockers

**Quality Gates:**
- ✅ Rust builds successfully for FreeBSD (x86_64-unknown-freebsd)
- ✅ PyO3 bindings callable from Python (`import yori_core`)
- ✅ CI/CD pipeline green (all tests pass)
- ✅ FreeBSD binary <10MB (stripped)

**Success Criteria:**
- Worker 2 can import `yori_core` module
- Worker 5 can access policy evaluation functions
- Build time <3 minutes for release build

**Czar Tasks:**
- Monitor Worker 1 daily commits
- Review PyO3 interface design
- Validate FreeBSD build artifacts
- Approve Worker 1 PR when quality gates met

---

### Week 3-4: Core Services Phase

**Active Workers:** Workers 2 and 5 (parallel after Worker 1)

**Objectives:**
- Build FastAPI transparent proxy service (Worker 2)
- Implement SQLite audit logging (Worker 2)
- Integrate sark-opa policy engine (Worker 5)
- Create advisory alert system (Worker 5)

**Worker Assignments:**
- **Worker 2 (python-proxy):** FastAPI, SQLite, LLM endpoint detection
- **Worker 5 (policy-engine):** Rego evaluation, alerts (email, web, push)

**Dependencies:**
- Both workers need Worker 1's `yori_core` module
- Worker 5 needs Worker 2's proxy integration points

**Quality Gates:**
- ✅ Worker 2: Proxy logs real LLM traffic to SQLite
- ✅ Worker 2: Health check endpoint responds (GET /health)
- ✅ Worker 2: <10ms latency overhead (p95)
- ✅ Worker 5: Policies evaluate correctly (test with bedtime.rego)
- ✅ Worker 5: Alert triggers successfully (test email/web notification)

**Success Criteria:**
- End-to-end test: LLM request → proxy → log → policy check → forward
- SQLite database populated with audit_events
- At least 4 pre-built policy templates working

**Czar Tasks:**
- Coordinate interface between Workers 2 and 5
- Monitor both workers' progress daily
- Validate integration of Rust policy engine
- Ensure Workers 3-4 can start when Worker 2 completes

---

### Week 5-6: User Interface Phase

**Active Workers:** Workers 3, 4, 6, 7 (mixed parallel)

**Objectives:**
- Create OPNsense plugin structure (Worker 3)
- Build web dashboard with charts (Worker 4)
- Write comprehensive documentation (Worker 6)
- Develop test suite and benchmarks (Worker 7)

**Worker Assignments:**
- **Worker 3 (opnsense-plugin):** PHP controllers, service management, .txz package
- **Worker 4 (dashboard-ui):** Volt templates, Chart.js, SQL queries
- **Worker 6 (documentation):** User guides, policy cookbook, architecture docs
- **Worker 7 (testing-qa):** Unit tests, integration tests, performance benchmarks

**Dependencies:**
- Worker 3 needs Worker 2's FastAPI service
- Worker 4 needs Worker 3's OPNsense plugin
- Worker 6 needs Workers 4+5 features to document
- Worker 7 needs Worker 5's code to test

**Parallelism:**
- Workers 3+7 can run in parallel (independent)
- Worker 4 starts after Worker 3
- Worker 6 starts after Workers 4+5

**Quality Gates:**
- ✅ Worker 3: OPNsense plugin installs via package manager
- ✅ Worker 3: Service start/stop works from web UI
- ✅ Worker 4: Dashboard displays LLM usage statistics
- ✅ Worker 4: Charts render correctly (24h requests, endpoint distribution)
- ✅ Worker 6: All documentation complete (installation, config, policy guide)
- ✅ Worker 7: >80% code coverage (pytest, cargo test)
- ✅ Worker 7: Performance targets met (<10ms latency, <256MB RAM)

**Success Criteria:**
- OPNsense plugin package (.txz) ready for distribution
- Dashboard functional with 100k+ audit records
- Documentation reviewed and accurate
- All tests passing in CI/CD

**Czar Tasks:**
- Coordinate Worker 3→4 handoff (plugin ready for UI)
- Validate Worker 4 UI integrates with Worker 3 plugin
- Review Worker 6 documentation for completeness
- Monitor Worker 7 performance benchmarks
- Prepare for Worker 8 integration

---

### Week 7-8: Integration & Release Phase

**Active Workers:** Worker 8 only

**Objectives:**
- Merge all worker branches into omnibus branch
- Resolve integration conflicts
- Build release artifacts (Rust binary, Python wheel, OPNsense package)
- Perform final QA on OPNsense VM
- Tag and release v0.1.0

**Worker Assignments:**
- **Worker 8 (integration-release):** Full focus on integration

**Dependencies:**
- All workers 1-7 must meet exit criteria

**Quality Gates:**
- ✅ All worker branches merged to cz1/release/v0.1.0
- ✅ All tests passing on integrated codebase
- ✅ Release artifacts build successfully
- ✅ Fresh installation works on OPNsense VM
- ✅ Performance targets validated (<10ms latency, <256MB RAM)
- ✅ Documentation accuracy verified

**Success Criteria:**
- GitHub release created with all artifacts
- CHANGELOG.md complete
- README updated with installation instructions
- OPNsense plugin ready for submission

**Czar Tasks:**
- Review Worker 8 merge strategy
- Assist with conflict resolution if needed
- Validate final QA results
- Approve release to main branch
- Create GitHub release

---

## Worker Handoff Protocols

### Worker 1 → Worker 2: PyO3 Bindings

**Handoff Artifact:** `rust/yori-core/src/lib.rs` with PyO3 bindings

**Interface Contract:**
```python
import yori_core

# Policy evaluation
result = yori_core.evaluate_policy(
    request={"method": "POST", "path": "/v1/chat/completions"},
    policy_path="/usr/local/etc/yori/policies/bedtime.rego"
)

# Logger initialization
yori_core.init_logger({"level": "info", "path": "/var/log/yori.log"})

# HTTP parsing
http_req = yori_core.parse_http_request(raw_bytes)
```

**Verification:**
```bash
# Worker 2 runs from cz1/feat/python-proxy branch
python3 -c "import yori_core; print(yori_core.__version__)"
# Expected: "0.1.0" or similar
```

**Communication:**
- Worker 1 documents API in `rust/yori-core/README.md`
- Worker 1 provides usage examples in code comments
- Worker 2 confirms import works before proceeding

---

### Worker 2 → Worker 3: FastAPI Service

**Handoff Artifact:** `python/yori/main.py` with FastAPI application

**Interface Contract:**
```bash
# Service start command
uvicorn yori.main:app --host 0.0.0.0 --port 8443

# Health check endpoint
curl http://localhost:8443/health
# Response: {"status": "healthy", "version": "0.1.0"}

# Configuration file
/usr/local/etc/yori/yori.conf  # YAML format
```

**Verification:**
```bash
# Worker 3 runs from cz1/feat/opnsense-plugin branch
cd /home/jhenry/Source/yori
git worktree list  # Find python-proxy worktree
cd <python-proxy-worktree>
uvicorn yori.main:app --host 127.0.0.1 --port 8443 &
curl http://127.0.0.1:8443/health
# Expected: {"status": "healthy"}
```

**Communication:**
- Worker 2 provides service lifecycle documentation
- Worker 2 documents configuration file format
- Worker 3 confirms service starts before building plugin

---

### Worker 2 → Worker 5: Policy Integration Point

**Handoff Artifact:** `python/yori/proxy.py` with policy evaluation hook

**Interface Contract:**
```python
# In proxy.py
from yori_core import evaluate_policy

async def handle_request(request):
    # Policy evaluation hook
    policy_result = evaluate_policy(
        request=request.dict(),
        policy_path=config.policy_path
    )

    if policy_result.action == "block":
        return {"error": "Request blocked by policy"}

    # Continue with proxy logic
```

**Verification:**
```bash
# Worker 5 runs test policy
python3 -c "
from python.yori.proxy import handle_request
import asyncio
# Test policy evaluation integration
"
```

**Communication:**
- Worker 2 documents policy evaluation points in proxy flow
- Worker 5 implements Rego policies that work with proxy
- Both workers coordinate on PolicyResult data structure

---

### Worker 3 → Worker 4: OPNsense Plugin UI

**Handoff Artifact:** OPNsense plugin structure in `opnsense/`

**Interface Contract:**
```php
// Extension point for dashboard
opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/index.volt

// Template variables available:
// - $service_status (running/stopped)
// - $config_path (/usr/local/etc/yori/yori.conf)
// - $database_path (/var/db/yori/audit.db)
```

**Verification:**
```bash
# Worker 4 checks plugin structure
ls -la opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/
# Expected: index.volt, dashboard.volt, etc.
```

**Communication:**
- Worker 3 provides Volt template structure
- Worker 4 extends templates with dashboard widgets
- Worker 3 coordinates on Bootstrap 5 theme

---

### Worker 5 → Worker 6: Policy Documentation

**Handoff Artifact:** Working policy templates in `policies/`

**Interface Contract:**
```
policies/
├── home_default.rego    # Default allow-all
├── bedtime.rego         # Time-based alerts
├── privacy.rego         # PII detection
└── high_usage.rego      # Threshold alerts
```

**Verification:**
```bash
# Worker 6 tests all policies
for policy in policies/*.rego; do
    python3 -c "from yori_core import evaluate_policy; \
                evaluate_policy({}, '$policy')"
done
```

**Communication:**
- Worker 5 provides policy descriptions and examples
- Worker 6 writes POLICY_GUIDE.md with usage examples
- Worker 5 reviews documentation for accuracy

---

### Workers 1-7 → Worker 8: Integration Readiness

**Handoff Checklist:**

**Worker 1:**
- [ ] Rust builds for FreeBSD
- [ ] PyO3 bindings tested
- [ ] CI/CD green
- [ ] All tests passing

**Worker 2:**
- [ ] Proxy logs LLM traffic
- [ ] SQLite database functional
- [ ] <10ms latency verified
- [ ] All tests passing

**Worker 3:**
- [ ] OPNsense plugin installs
- [ ] Service management works
- [ ] .txz package builds
- [ ] All tests passing

**Worker 4:**
- [ ] Dashboard displays data
- [ ] Charts render correctly
- [ ] SQL queries optimized
- [ ] All tests passing

**Worker 5:**
- [ ] Policies evaluate correctly
- [ ] Alerts trigger successfully
- [ ] 4+ policy templates included
- [ ] All tests passing

**Worker 6:**
- [ ] All documentation complete
- [ ] Screenshots included
- [ ] Accuracy verified
- [ ] Links working

**Worker 7:**
- [ ] >80% code coverage
- [ ] Performance targets met
- [ ] All tests passing
- [ ] Benchmarks documented

**Verification:**
```bash
# Worker 8 runs integration checklist
./scripts/integration-check.sh
# Validates all worker exit criteria
```

---

## Czar Responsibilities

### Daily Tasks

**Morning (10 minutes):**
```bash
# Check worker status
czarina status

# Review commits from last 24h
for branch in cz1/feat/*; do
    git log $branch --since="24 hours ago" --oneline
done

# Check CI/CD status
# (GitHub Actions, if configured)
```

**Afternoon (15 minutes):**
```bash
# Monitor daemon logs
czarina daemon logs | tail -100

# Check for blocking issues
czarina status | grep "blocked"

# Review worker progress vs milestones
```

**Actions:**
- Unblock workers waiting on dependencies
- Review and approve quality gates
- Update project timeline if needed
- Communicate with workers via prompt updates

---

### Weekly Tasks

**Integration Checkpoint (30 minutes):**
- Review all worker branches
- Test cross-worker interfaces
- Validate dependency handoffs
- Update IMPLEMENTATION_PLAN.md status

**Performance Validation (20 minutes):**
- Review Worker 7 benchmarks
- Validate <10ms latency target
- Check <256MB RAM usage
- Monitor SQLite performance

**Timeline Review (15 minutes):**
- Update phase completion estimates
- Adjust worker priorities if needed
- Identify risks and blockers
- Plan next week's focus

**Actions:**
- Hold virtual standup (review commit messages)
- Validate quality gates
- Prepare for phase transitions

---

### Phase Transitions

**Before Launching New Phase:**
1. Verify all workers in previous phase met exit criteria
2. Review handoff artifacts (verify interfaces work)
3. Update worker prompts if scope changed
4. Communicate dependencies to new workers

**Example: Week 2→3 Transition (Worker 1 → Workers 2+5)**
```bash
# Verify Worker 1 complete
cd /home/jhenry/Source/yori
git checkout cz1/feat/rust-foundation
cargo test --workspace  # All tests pass?
cargo build --release --target x86_64-unknown-freebsd  # Builds?
python3 -c "import yori_core"  # Imports?

# If all pass, approve Workers 2+5 to start
czarina launch  # Will start Workers 2+5 automatically
```

---

### Crisis Management

**Worker Stuck >3 Days:**
1. Review worker's commit history
2. Check daemon logs for errors
3. Read worker's branch to identify blocker
4. Update worker prompt with clarifications
5. Consider reassigning to different agent

**Test Failures:**
1. Review CI/CD logs
2. Identify failing test category (unit/integration/e2e)
3. Assign worker to fix (usually original worker)
4. Block dependent workers until fixed

**Merge Conflicts:**
1. Identify conflicting files
2. Determine which worker "owns" the file
3. Consult original worker for resolution
4. Worker 8 merges with guidance

**Performance Targets Missed:**
1. Review Worker 7 benchmarks
2. Identify bottleneck (Rust, Python, SQLite)
3. Assign optimization to relevant worker
4. Re-benchmark after fixes

---

## Quality Gates & Testing

### Worker 1: rust-foundation

**Exit Criteria:**
- ✅ Rust workspace builds successfully
- ✅ FreeBSD cross-compilation works (`cargo build --target x86_64-unknown-freebsd`)
- ✅ PyO3 bindings importable from Python
- ✅ Binary size <10MB (stripped)
- ✅ Build time <3 minutes (release)
- ✅ All unit tests pass (`cargo test --workspace`)
- ✅ CI/CD pipeline green

**Performance Targets:**
- Policy evaluation: <5ms per request (p95)
- Memory: <100MB for Rust components

**Testing:**
```bash
cargo test --workspace
cargo build --release --target x86_64-unknown-freebsd
python3 -c "import yori_core; print(yori_core.__version__)"
```

---

### Worker 2: python-proxy

**Exit Criteria:**
- ✅ FastAPI application starts successfully
- ✅ Health check endpoint responds (GET /health)
- ✅ Proxy logs LLM traffic to SQLite
- ✅ Request latency <10ms overhead (p95)
- ✅ Throughput: 50 requests/sec sustained
- ✅ Memory: <150MB for Python service
- ✅ All unit tests pass (`pytest`)

**Performance Targets:**
- Request latency: <10ms overhead
- Throughput: 50 req/sec
- Database writes: <5ms per record

**Testing:**
```bash
pytest tests/
uvicorn yori.main:app --host 127.0.0.1 --port 8443 &
curl http://127.0.0.1:8443/health
ab -n 1000 -c 10 http://127.0.0.1:8443/health  # Load test
```

---

### Worker 7: testing-qa

**Exit Criteria:**
- ✅ >80% code coverage (Python and Rust)
- ✅ All unit tests pass
- ✅ All integration tests pass
- ✅ All e2e tests pass
- ✅ Performance benchmarks meet targets:
  - Latency: <10ms (p95)
  - Memory: <256MB RSS
  - Throughput: 50 req/sec
- ✅ Load test: 50 req/sec for 60 seconds

**Benchmarks:**
```bash
# Latency
wrk -t4 -c100 -d30s http://localhost:8443/health

# Memory
ps aux | grep yori | awk '{print $6}'  # RSS in KB

# Load test
ab -n 3000 -c 50 http://localhost:8443/v1/chat/completions
```

---

### Worker 8: integration-release

**Exit Criteria:**
- ✅ All worker branches merged to cz1/release/v0.1.0
- ✅ All tests passing on integrated codebase
- ✅ Release artifacts built:
  - Rust binary (yori-core for FreeBSD)
  - Python wheel (yori-0.1.0-py3-none-any.whl)
  - OPNsense package (os-yori-0.1.0.txz)
- ✅ Fresh installation works on OPNsense VM
- ✅ All features functional
- ✅ Documentation accurate
- ✅ GitHub release created

**Final QA Checklist:**
- [ ] Install OPNsense plugin from .txz package
- [ ] Start YORI service from web UI
- [ ] Generate LLM traffic (test with curl)
- [ ] Verify traffic logged in SQLite
- [ ] Check dashboard displays data
- [ ] Test policy evaluation
- [ ] Verify alert triggers
- [ ] Export audit logs to CSV
- [ ] Validate performance targets (<10ms, <256MB)

---

## Integration Strategy

### Branch Merge Order

Worker 8 merges in **dependency order:**

```bash
git checkout -b cz1/release/v0.1.0 main

# Merge in dependency order
git merge cz1/feat/rust-foundation       # Worker 1 (foundation)
git merge cz1/feat/python-proxy          # Worker 2 (depends on 1)
git merge cz1/feat/opnsense-plugin       # Worker 3 (depends on 2)
git merge cz1/feat/dashboard-ui          # Worker 4 (depends on 3)
git merge cz1/feat/policy-engine         # Worker 5 (depends on 1, 2)
git merge cz1/feat/documentation         # Worker 6 (depends on 4, 5)
git merge cz1/feat/testing-qa            # Worker 7 (depends on 5)

# Run full test suite
pytest tests/
cargo test --workspace

# Build release artifacts
./scripts/build-freebsd.sh
python -m build
make -C opnsense package
```

---

### Conflict Resolution Procedures

**Step 1: Identify Conflict Owner**
- File in `rust/`: Worker 1 (rust-foundation)
- File in `python/`: Worker 2 (python-proxy)
- File in `opnsense/`: Worker 3 or 4
- File in `policies/`: Worker 5 (policy-engine)
- File in `docs/`: Worker 6 (documentation)
- File in `tests/`: Worker 7 (testing-qa)

**Step 2: Resolution Strategy**
1. Worker 8 reads both versions of conflicting file
2. Identifies semantic conflict vs formatting conflict
3. If semantic: Consults original worker (read their commits)
4. If formatting: Uses automated tools (black, rustfmt)
5. Merges with resolution
6. Commits with message: "Merge worker X: resolve conflict in file.py"

**Step 3: Validation**
```bash
# After conflict resolution
pytest tests/  # Verify tests still pass
cargo test     # Verify Rust tests pass
```

---

### Omnibus Branch Management

**Worker 8 Owns:** `cz1/release/v0.1.0`

**Responsibilities:**
- Merge worker branches in correct order
- Resolve all conflicts
- Run full test suite
- Build release artifacts
- Create GitHub release
- Tag v0.1.0
- Update CHANGELOG.md

**No Direct Commits:**
- Workers 1-7 never commit directly to omnibus branch
- All work happens on feature branches
- Worker 8 integrates via merges

---

### Final PR to Main

**After Integration:**
```bash
# From cz1/release/v0.1.0
git checkout main
git merge cz1/release/v0.1.0

# Tag release
git tag -a v0.1.0 -m "YORI v0.1.0: Home LLM Gateway"
git push origin main --tags

# Create GitHub release
gh release create v0.1.0 \
    --title "YORI v0.1.0" \
    --notes-file CHANGELOG.md \
    rust/target/x86_64-unknown-freebsd/release/yori-core \
    dist/yori-0.1.0-py3-none-any.whl \
    opnsense/os-yori-0.1.0.txz
```

---

## Timeline Summary

| Week | Phase | Workers | Key Deliverables |
|------|-------|---------|------------------|
| 1-2 | Foundation | 1 | Rust workspace, PyO3 bindings, FreeBSD builds |
| 3-4 | Core Services | 2, 5 | FastAPI proxy, policy engine, SQLite logging |
| 5-6 | User Interface | 3, 4, 6, 7 | OPNsense plugin, dashboard, docs, tests |
| 7-8 | Integration | 8 | Merge all, QA, release v0.1.0 |

**Total:** 6-8 weeks (vs 13 weeks sequential)

**Speedup:** 3-4x through parallel execution

---

## Success Metrics

**Technical:**
- ✅ <10ms latency overhead (p95)
- ✅ <256MB memory usage (RSS)
- ✅ >80% code coverage
- ✅ All tests passing

**Process:**
- ✅ 95-98% autonomy (daemon auto-approval)
- ✅ No worker blocked >3 days
- ✅ All quality gates met
- ✅ 6-8 week delivery

**Release:**
- ✅ GitHub release with all artifacts
- ✅ OPNsense plugin installable
- ✅ Documentation complete
- ✅ v0.1.0 tagged

---

**Orchestration Guide Version:** 1.0
**Last Updated:** 2026-01-19
**Status:** Ready for Execution
**Next:** Enhance worker prompts with interface contracts
