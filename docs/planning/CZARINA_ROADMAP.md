# YORI Czarina Orchestration Roadmap

**Quick Reference for Multi-Agent Development**
**Current:** v0.2.1 → **Target:** v1.0.0
**Method:** 5 Czarina Phases, 22 Workers Total

---

## Phase Overview

| Phase | Version | Workers | Duration | Focus |
|-------|---------|---------|----------|-------|
| **1** | v0.2.2 | 5 | 2-3 days | Production Hardening |
| **2** | v0.3.0 | 6 | 5-7 days | OPNsense Integration |
| **3** | v0.4.0 | 4 | 3-4 days | Enhanced Features |
| **4** | v0.5.0 | 4 | 2-3 days | Documentation |
| **5** | v1.0.0 | 3 | 2-3 days | Release Prep |
| | | **22 total** | **14-20 days** | |

---

## Phase 1: Production Hardening (v0.2.2)

**Goal:** Make proxy server production-ready
**Execution:** Parallel workers
**Base Branch:** `main`

### Workers

```
W1 (performance)     ──┐
W2 (monitoring)      ──┤
W3 (security)        ──┼─→ W5 (load-testing) → v0.2.2
W4 (resilience)      ──┘
```

| # | Worker | Branch | Dependencies | Key Deliverables |
|---|--------|--------|--------------|------------------|
| 1 | performance | `cz2/feat/performance` | None | Connection pooling, caching, benchmarks |
| 2 | monitoring | `cz2/feat/monitoring` | None | Prometheus metrics, Grafana dashboard |
| 3 | security | `cz2/feat/security` | None | Rate limiting, TLS hardening, security scan |
| 4 | resilience | `cz2/feat/resilience` | None | Circuit breaker, graceful shutdown, retry logic |
| 5 | load-testing | `cz2/test/load-validation` | W1-W4 | Load tests, soak tests, performance report |

### Success Criteria
- [ ] 100+ req/sec sustained throughput
- [ ] <50ms added latency
- [ ] <100MB memory usage
- [ ] No high/critical security findings
- [ ] All load tests passing

---

## Phase 2: OPNsense Integration (v0.3.0)

**Goal:** Deploy as OPNsense plugin
**Execution:** Sequential with parallel branches
**Base Branch:** `main`

### Workers

```
W1 (freebsd-base)
  ↓
W2 (opnsense-scaffold)
  ↓
  ├─→ W3 (web-config)
  ├─→ W4 (web-dashboard)
  └─→ W5 (web-policies)
       ↓
     W6 (integration) → v0.3.0
```

| # | Worker | Branch | Dependencies | Key Deliverables |
|---|--------|--------|--------------|------------------|
| 1 | freebsd-base | `cz3/feat/freebsd-base` | None | FreeBSD package, rc.d script |
| 2 | opnsense-scaffold | `cz3/feat/opnsense-scaffold` | W1 | Plugin structure, PHP/MVC base |
| 3 | web-config | `cz3/feat/web-config` | W2 | Configuration UI, validation |
| 4 | web-dashboard | `cz3/feat/web-dashboard` | W2 | Dashboard, log viewer, audit browser |
| 5 | web-policies | `cz3/feat/web-policies` | W2 | Policy editor, library, testing tool |
| 6 | integration | `cz3/release/v0_3_0` | W3-W5 | Merge, package, OPNsense submission |

### Success Criteria
- [ ] Installs via OPNsense plugins UI
- [ ] All features accessible via web UI
- [ ] Service management works (start/stop/restart)
- [ ] Works on FreeBSD 13.x
- [ ] Ready for OPNsense plugins submission

---

## Phase 3: Enhanced Features (v0.4.0)

**Goal:** Add production features
**Execution:** Parallel workers
**Base Branch:** `main`

### Workers

```
W1 (token-tracking) ──┐
                      ├─→ W2 (cost-monitoring)
W3 (reporting)      ──┤
W4 (policy-library) ──┘
                    ↓
                  v0.4.0
```

| # | Worker | Branch | Dependencies | Key Deliverables |
|---|--------|--------|--------------|------------------|
| 1 | token-tracking | `cz4/feat/token-tracking` | None | Token extraction, usage DB, API |
| 2 | cost-monitoring | `cz4/feat/cost-monitoring` | W1 | Cost calculation, alerts, budgets |
| 3 | reporting | `cz4/feat/reporting` | None | Enhanced audit, exports, analytics |
| 4 | policy-library | `cz4/feat/policy-library` | None | 20+ policies, templates, docs |

### Success Criteria
- [ ] Token usage tracked per device
- [ ] Cost reports accurate
- [ ] 20+ pre-built policies available
- [ ] Reports export to CSV/JSON
- [ ] All policies tested and documented

---

## Phase 4: Documentation (v0.5.0)

**Goal:** Complete all documentation
**Execution:** Parallel workers
**Base Branch:** `main`

### Workers

```
W1 (user-guide)      ──┐
W2 (admin-guide)     ──┤
W3 (policy-cookbook) ──┼─→ v0.5.0
W4 (multimedia)      ──┘
```

| # | Worker | Branch | Dependencies | Key Deliverables |
|---|--------|--------|--------------|------------------|
| 1 | user-guide | `cz5/docs/user-guide` | None | Installation, quick start, FAQ, troubleshooting |
| 2 | admin-guide | `cz5/docs/admin-guide` | None | Advanced config, tuning, security, monitoring |
| 3 | policy-cookbook | `cz5/docs/policy-cookbook` | None | Tutorial, 30+ examples, patterns |
| 4 | multimedia | `cz5/docs/multimedia` | None | Videos, interactive demo, screenshots |

### Success Criteria
- [ ] Non-technical user can install
- [ ] All features documented
- [ ] 30+ policy examples
- [ ] Videos published
- [ ] Documentation reviewed and tested

---

## Phase 5: Release Preparation (v1.0.0)

**Goal:** Package and release v1.0.0
**Execution:** Sequential
**Base Branch:** `main`

### Workers

```
W1 (cicd)
  ↓
W2 (release)
  ↓
W3 (community) → v1.0.0
```

| # | Worker | Branch | Dependencies | Key Deliverables |
|---|--------|--------|--------------|------------------|
| 1 | cicd | `cz6/infra/cicd` | None | GitHub Actions, automated builds/tests |
| 2 | release | `cz6/release/v1_0_0` | W1 | Changelog, migration guide, v1.0.0 tag |
| 3 | community | `cz6/community/setup` | W2 | Issue templates, Discussions, submission |

### Success Criteria
- [ ] CI/CD pipeline working
- [ ] v1.0.0 tagged and released
- [ ] Available in OPNsense plugins
- [ ] Community platforms ready
- [ ] Announcement published

---

## Execution Commands

### Start Phase 1

```bash
cd ~/Source/yori
czarina init yori-v0.2.2 --workers 5 --mode parallel

# Add workers (see detailed plan)
czarina worker add performance --branch cz2/feat/performance
czarina worker add monitoring --branch cz2/feat/monitoring
czarina worker add security --branch cz2/feat/security
czarina worker add resilience --branch cz2/feat/resilience
czarina worker add load-testing --branch cz2/test/load-validation --depends performance,monitoring,resilience

czarina start
```

### Start Phase 2

```bash
czarina init yori-v0.3.0 --workers 6 --mode sequential

czarina worker add freebsd-base --branch cz3/feat/freebsd-base
czarina worker add opnsense-scaffold --branch cz3/feat/opnsense-scaffold --depends freebsd-base
czarina worker add web-config --branch cz3/feat/web-config --depends opnsense-scaffold
czarina worker add web-dashboard --branch cz3/feat/web-dashboard --depends opnsense-scaffold
czarina worker add web-policies --branch cz3/feat/web-policies --depends opnsense-scaffold
czarina worker add integration --branch cz3/release/v0_3_0 --depends web-config,web-dashboard,web-policies

czarina start
```

### Continue with Phases 3-5
Follow same pattern using worker definitions from YORI_COMPLETION_PLAN.md

---

## Timeline

### Optimistic (Full Parallelization)
- **Week 1:** Phase 1 (days 1-3) + Phase 2 start (days 4-5)
- **Week 2:** Phase 2 complete (days 6-10) + Phase 3 (days 11-12)
- **Week 3:** Phase 4 (days 13-14) + Phase 5 (days 15-16)
- **Total:** 16-18 days

### Realistic (With Testing)
- **Weeks 1-2:** Phase 1 + Phase 2
- **Week 3:** Phase 3 + Phase 4
- **Week 4:** Phase 5 + buffer
- **Total:** 3-4 weeks

---

## Progress Tracking

### Milestones

- [ ] **v0.2.2** - Production hardening complete
- [ ] **v0.3.0** - OPNsense plugin working
- [ ] **v0.4.0** - Enhanced features deployed
- [ ] **v0.5.0** - Documentation complete
- [ ] **v1.0.0** - Production release

### Current Status

**Phase 0 (Complete):**
- [x] v0.2.1 - HTTP/HTTPS Proxy Server
- [x] 156/156 automated tests passing
- [x] Documentation organized

**Next Phase:**
- [ ] Phase 1: Production Hardening (v0.2.2)

---

## Quick Links

- **Full Plan:** [YORI_COMPLETION_PLAN.md](./YORI_COMPLETION_PLAN.md)
- **Worker Instructions:** `.czarina/workers/*.md` (to be created per phase)
- **Test Plans:** `docs/testing/`
- **Current Status:** `docs/testing/V0.2.1_TEST_STATUS.md`

---

## Decision Log

Track major decisions as phases progress:

### Pre-Phase 1 Decisions
- [ ] Monitoring: Prometheus vs custom
- [ ] Caching: Redis vs in-memory
- [ ] Security scanner: bandit + safety

### Pre-Phase 2 Decisions
- [ ] OPNsense plugin framework
- [ ] Web UI framework (vanilla PHP vs Vue.js)
- [ ] FreeBSD package manager

### Pre-Phase 3 Decisions
- [ ] Token storage approach
- [ ] Cost monitoring implementation
- [ ] Reporting format

### Pre-Phase 4 Decisions
- [ ] Documentation platform
- [ ] Video hosting
- [ ] Screenshot tooling

### Pre-Phase 5 Decisions
- [ ] CI/CD platform
- [ ] Release cadence
- [ ] Community platforms

---

**Ready to Start:** Phase 1 (v0.2.2)
**Estimated Completion:** v1.0.0 in 3-4 weeks
