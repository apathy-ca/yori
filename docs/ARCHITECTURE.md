# YORI Architecture

Technical architecture and design documentation for the YORI Home LLM Gateway.

---

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Principles](#architecture-principles)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Performance Considerations](#performance-considerations)
- [Security Architecture](#security-architecture)
- [Deployment Architecture](#deployment-architecture)
- [Scalability and Limitations](#scalability-and-limitations)

---

## System Overview

YORI is a transparent LLM traffic interceptor that runs as a lightweight service on OPNsense routers. It provides visibility and optional control over LLM API usage in home networks.

### Design Goals

1. **Low Resource Footprint:** Run on commodity home router hardware (512MB RAM, 1 CPU core)
2. **Zero Configuration:** Work out-of-the-box with sensible defaults
3. **Privacy First:** All data stays on-premise, no cloud dependencies
4. **Progressive Disclosure:** Start with observation, optionally enable enforcement
5. **Educational:** Help families understand AI usage patterns

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                        Home Network                          │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Laptop   │  │ Phone    │  │ Tablet   │  │  IoT     │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │              │             │          │
│       └─────────────┴──────────────┴─────────────┘          │
│                          │                                   │
│                          ▼                                   │
│       ┌─────────────────────────────────────────┐           │
│       │    OPNsense Router (YORI Installed)    │           │
│       │  - Transparent LLM Interception         │           │
│       │  - Policy Evaluation                    │           │
│       │  - Audit Logging                        │           │
│       │  - Dashboard & Alerts                   │           │
│       └──────────────┬──────────────────────────┘           │
│                      │                                       │
└──────────────────────┼───────────────────────────────────────┘
                       │
                       ▼ Internet
         ┌──────────────────────────────────┐
         │   LLM Providers (Cloud APIs)     │
         │  - OpenAI (api.openai.com)       │
         │  - Anthropic (api.anthropic.com) │
         │  - Google (gemini.google.com)    │
         │  - Mistral (api.mistral.ai)      │
         └──────────────────────────────────┘
```

---

## Architecture Principles

### 1. Separation of Concerns

YORI separates functionality into distinct layers:

- **Presentation Layer:** OPNsense plugin web UI (PHP/Volt)
- **Application Layer:** Python proxy and routing logic (FastAPI)
- **Business Logic Layer:** Policy evaluation (Rust + OPA)
- **Data Layer:** SQLite audit database, file-based configuration

### 2. Language Selection Rationale

| Component | Language | Rationale |
|-----------|----------|-----------|
| Proxy Core | Python | Rapid development, extensive HTTP libraries, easy to debug |
| Policy Engine | Rust | Performance critical, resource constrained, PyO3 bindings |
| Web UI | PHP | OPNsense standard, existing ecosystem, rapid UI development |
| Policies | Rego | Industry standard for policy-as-code, declarative, testable |

### 3. Resource Constraints

Target hardware: Protectli Vault FW4B, PC Engines APU2, or similar

- **RAM:** 512MB available (after OPNsense base)
- **CPU:** 1 core @ 1GHz+
- **Disk:** 1GB for binary + 5GB for logs
- **Network:** 1Gbps LAN, 100Mbps+ WAN

### 4. Failure Modes

**Fail-Open Philosophy:**
- If YORI service crashes, traffic flows normally (no interception)
- OPNsense firewall rules are non-blocking by default
- Degraded mode: logging disabled, policy evaluation skipped, traffic allowed

**Rationale:** Home internet must be reliable. LLM governance is valuable but not critical path.

---

## Component Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│              OPNsense Router (FreeBSD)                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  OPNsense Plugin (os-yori)                         │ │
│  │                                                     │ │
│  │  ┌──────────────┐  ┌──────────────┐               │ │
│  │  │ Web UI       │  │ Service      │               │ │
│  │  │ (PHP/Volt)   │  │ Control      │               │ │
│  │  │              │  │ (rc.d)       │               │ │
│  │  │ - Dashboard  │  │              │               │ │
│  │  │ - Settings   │  │ start/stop/  │               │ │
│  │  │ - Logs       │  │ restart      │               │ │
│  │  │ - Alerts     │  │              │               │ │
│  │  └──────┬───────┘  └──────┬───────┘               │ │
│  └─────────┼──────────────────┼───────────────────────┘ │
│            │                  │                          │
│            │ (HTTP/JSON)      │ (rc script)              │
│            │                  │                          │
│  ┌─────────▼──────────────────▼───────────────────────┐ │
│  │  YORI Service Process                              │ │
│  │  (/usr/local/bin/yori)                             │ │
│  │                                                     │ │
│  │  ┌───────────────────────────────────────────────┐ │ │
│  │  │  FastAPI Application (Python 3.11)            │ │ │
│  │  │                                                │ │ │
│  │  │  ┌─────────────┐  ┌─────────────┐            │ │ │
│  │  │  │ HTTP Proxy  │  │ Config      │            │ │ │
│  │  │  │ (httpx)     │  │ (Pydantic)  │            │ │ │
│  │  │  └─────────────┘  └─────────────┘            │ │ │
│  │  │                                                │ │ │
│  │  │  ┌─────────────┐  ┌─────────────┐            │ │ │
│  │  │  │ Audit Log   │  │ Alert       │            │ │ │
│  │  │  │ (SQLite)    │  │ (Email/Push)│            │ │ │
│  │  │  └─────────────┘  └─────────────┘            │ │ │
│  │  │                                                │ │ │
│  │  │  ┌─────────────────────────────────────────┐ │ │ │
│  │  │  │ Rust Core (via PyO3)                    │ │ │ │
│  │  │  │                                          │ │ │ │
│  │  │  │  ┌────────────┐  ┌────────────┐        │ │ │ │
│  │  │  │  │ PolicyEng  │  │ Cache      │        │ │ │ │
│  │  │  │  │ (sark-opa) │  │ (sark-     │        │ │ │ │
│  │  │  │  │            │  │  cache)    │        │ │ │ │
│  │  │  │  └────────────┘  └────────────┘        │ │ │ │
│  │  │  └─────────────────────────────────────────┘ │ │ │
│  │  └───────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Data Storage (Filesystem)                          │ │
│  │                                                      │ │
│  │  - /usr/local/etc/yori/yori.conf (YAML)            │ │
│  │  - /usr/local/etc/yori/policies/*.rego             │ │
│  │  - /var/db/yori/audit.db (SQLite)                  │ │
│  │  - /var/log/yori/yori.log (Service logs)           │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### 1. OPNsense Plugin (PHP)

**Location:** `/usr/local/opnsense/mvc/app/controllers/OPNsense/YORI/`

**Responsibilities:**
- Render web UI pages using Volt templates
- Provide RESTful API for configuration
- Service lifecycle management (start/stop/restart)
- Dashboard data aggregation (query SQLite via PHP PDO)
- Alert viewing and management

**Key Files:**
- `IndexController.php` - Main dashboard and settings pages
- `Api/ServiceController.php` - RESTful API for service control
- `views/index.volt` - Dashboard template
- `models/General.xml` - Configuration schema

#### 2. Python Application Layer

**Location:** `/usr/local/lib/python3.11/site-packages/yori/`

**Responsibilities:**
- HTTP request interception and forwarding
- TLS termination and re-encryption
- Audit log writing to SQLite
- Configuration loading and validation
- Alert dispatching (email, push notifications)
- Policy orchestration (call Rust core for evaluation)

**Key Modules:**
- `main.py` - FastAPI application entry point
- `proxy.py` - Transparent proxy logic (intercept/forward)
- `config.py` - Pydantic configuration models
- `audit.py` - SQLite audit logging
- `alerts.py` - Email/Pushover/webhook alerts

#### 3. Rust Core (PyO3 Bindings)

**Location:** `/usr/local/lib/python3.11/site-packages/yori_core.so`

**Responsibilities:**
- High-performance policy evaluation (sark-opa wrapper)
- In-memory caching for policy results (sark-cache)
- Audit log primitives (sark-audit, if used)

**Exported Classes (PyO3):**
```python
from yori_core import PolicyEngine, Cache

# Policy evaluation
engine = PolicyEngine()
engine.load_policies("/usr/local/etc/yori/policies")
result = engine.evaluate({"request": {...}})

# Caching
cache = Cache()
cache.set("key", "value", ttl=60)
value = cache.get("key")
```

**Source Location:** `yori/rust/yori-core/src/`

#### 4. Data Storage

**SQLite Database Schema:**

**Location:** `/var/db/yori/audit.db`

```sql
CREATE TABLE audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    request_id TEXT UNIQUE NOT NULL,

    -- Device info
    device_ip TEXT NOT NULL,
    device_mac TEXT,
    device_hostname TEXT,
    user_agent TEXT,

    -- Request details
    endpoint_domain TEXT NOT NULL,
    http_method TEXT NOT NULL,
    http_path TEXT NOT NULL,
    model TEXT,

    -- Request/response bodies (JSON)
    request_body TEXT,
    response_body TEXT,

    -- Metadata
    policy_decision TEXT, -- allow, deny, alert
    policy_message TEXT,
    latency_ms INTEGER,

    -- Indexing for dashboard queries
    INDEX idx_timestamp (timestamp),
    INDEX idx_device_ip (device_ip),
    INDEX idx_endpoint (endpoint_domain),
    INDEX idx_model (model)
);
```

**Configuration File Format:**

**Location:** `/usr/local/etc/yori/yori.conf`

```yaml
mode: observe
listen: 0.0.0.0:8443

endpoints:
  - domain: api.openai.com
    enabled: true

audit:
  database: /var/db/yori/audit.db
  retention_days: 365

policies:
  directory: /usr/local/etc/yori/policies
  default: home_default.rego
```

---

## Data Flow

### Request Processing Flow

```
1. Client Request
   │
   │ HTTPS request to api.openai.com:443
   │
   ▼
2. OPNsense NAT Rule
   │
   │ Firewall rule: dst=api.openai.com port=443 → rdr-to 127.0.0.1:8443
   │
   ▼
3. YORI Proxy Receives Request
   │
   ├─ TLS handshake with YORI CA certificate
   ├─ Parse HTTP request (method, path, headers, body)
   │
   ▼
4. Audit Log (Pre-Request)
   │
   ├─ Extract metadata: device IP, model, prompt, etc.
   ├─ Generate request_id (UUID)
   ├─ INSERT INTO audit_events (...)
   │
   ▼
5. Policy Evaluation (Rust Core)
   │
   ├─ Build input JSON for OPA
   ├─ Call PolicyEngine.evaluate(input)
   ├─ Rego policies return: {allow, deny, alert, message}
   │
   ▼
6. Apply Policy Decision
   │
   ├─ If deny (enforce mode): Return 403 Forbidden
   ├─ If alert: Trigger alert (email/push)
   ├─ If allow: Continue to forward
   │
   ▼
7. Forward to Real LLM API
   │
   ├─ Establish TLS connection to api.openai.com:443
   ├─ Forward original request (rewrite Host header)
   ├─ Await response from LLM provider
   │
   ▼
8. Process Response
   │
   ├─ Parse response (status, headers, body)
   ├─ Measure latency (end-to-end)
   │
   ▼
9. Audit Log (Post-Response)
   │
   ├─ UPDATE audit_events SET response_body=..., latency_ms=...
   │
   ▼
10. Return to Client
    │
    ├─ Forward response through TLS tunnel
    ├─ Client receives response (transparent to application)
```

### Configuration Update Flow

```
1. User Updates Config (Web UI)
   │
   │ POST /api/yori/service/set
   │
   ▼
2. OPNsense Plugin Validates Input
   │
   ├─ Validate YAML schema
   ├─ Check enum values (mode: observe/advisory/enforce)
   │
   ▼
3. Write to yori.conf
   │
   ├─ Atomic write to /usr/local/etc/yori/yori.conf
   ├─ Set ownership: root:wheel, permissions: 644
   │
   ▼
4. Trigger Service Reload
   │
   ├─ service yori reload (or restart if needed)
   │
   ▼
5. YORI Service Reloads Config
   │
   ├─ Re-parse yori.conf (Pydantic validation)
   ├─ Reload Rego policies (PolicyEngine.load_policies())
   ├─ Update runtime configuration (no downtime)
```

---

## Technology Stack

### Runtime Dependencies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| OS | FreeBSD | 13.2+ | OPNsense base OS |
| Python | CPython | 3.11 | Application runtime |
| Rust | rustc | 1.92+ | Core libraries (compiled to .so) |
| Web Server | PHP-FPM | 8.2 | OPNsense web UI |
| Database | SQLite | 3.40+ | Audit log storage |
| HTTP Client | httpx | 0.26+ | Async HTTP forwarding |
| Web Framework | FastAPI | 0.109+ | Proxy server |
| ASGI Server | uvicorn | 0.27+ | Production HTTP server |

### Build Dependencies

| Tool | Version | Purpose |
|------|---------|---------|
| cargo | 1.92+ | Rust compiler |
| maturin | 1.4+ | PyO3 package builder |
| FreeBSD SDK | 13.2 | Cross-compilation target |

### External Libraries (Rust)

**From SARK (vendored or path dependencies):**
- `sark-opa` - Embedded Open Policy Agent (Rego evaluation)
- `sark-cache` - Lock-free in-memory cache
- `sark-audit` - Logging primitives (optional)

**From crates.io:**
- `pyo3` - Python bindings
- `tokio` - Async runtime
- `hyper` - HTTP client/server
- `rustls` - TLS library
- `serde` - Serialization

---

## Performance Considerations

### Latency Budget

Target end-to-end latency: **<50ms p95**

| Stage | Target | Notes |
|-------|--------|-------|
| NAT redirect | <1ms | Kernel-level packet rewrite |
| TLS handshake | <10ms | Cached session resumption |
| Policy evaluation | <5ms | Rust sark-opa, in-memory |
| SQLite write | <5ms | Async, batched writes |
| LLM API call | Variable | Network-dependent (100-500ms typical) |
| Response proxy | <5ms | Streaming response |

**Total YORI overhead:** <25ms p95 (excluding LLM API call)

### Memory Usage

Target: **<100MB RSS**

| Component | Est. RAM |
|-----------|----------|
| Python process | ~40MB |
| Rust core (.so) | ~10MB |
| SQLite buffer cache | ~20MB |
| HTTP connection pool | ~10MB |
| Policy cache | ~10MB |
| Overhead | ~10MB |
| **Total** | **~100MB** |

### Throughput

Target: **100 req/sec** (sustained)

- Typical home usage: <10 req/sec peak
- Stress test target: 100 req/sec
- Bottleneck: SQLite writes (async mitigates)

**Optimization Strategies:**
1. **Batched SQLite Writes:** Accumulate 10 events, write in transaction
2. **Policy Result Caching:** Cache policy decisions for identical prompts (TTL 60s)
3. **Connection Pooling:** Reuse HTTPS connections to LLM APIs
4. **Async I/O:** All network and disk I/O is non-blocking (asyncio)

---

## Security Architecture

### Threat Model

**In Scope:**
- ✅ Passive eavesdropping on LLM traffic (defeated by home network trust)
- ✅ Unauthorized access to audit logs (file permissions, OPNsense auth)
- ✅ Policy bypass via alternate endpoints (user must configure endpoints)
- ✅ MITM attacks on LLM API (TLS cert pinning not implemented, use HTTPS)

**Out of Scope:**
- ❌ Attacks on OPNsense itself (rely on OPNsense security)
- ❌ Physical access to router (out of band)
- ❌ Compromised client devices (YORI can't protect infected devices)
- ❌ DDoS attacks (home router limitation)

### TLS Interception Security

**How It Works:**

1. **YORI CA Certificate:** Self-signed CA generated during installation
2. **Device Trust:** Devices manually trust YORI CA (user action required)
3. **Dynamic Certificate Generation:** YORI generates server certs on-the-fly for intercepted domains
4. **Trust Chain:** Device → YORI CA → YORI-generated cert for api.openai.com

**Security Considerations:**

- ✅ **Pros:**
  - Visibility into encrypted LLM traffic
  - All data stays on-premise
  - User has full control (can remove CA trust anytime)

- ⚠️ **Cons:**
  - YORI can see plaintext prompts/responses
  - If router compromised, attacker can intercept traffic
  - Relies on users properly installing CA cert

**Best Practices:**
- Store CA private key encrypted at rest (future enhancement)
- Rotate CA certificate annually
- Monitor for unexpected CA trust additions on devices

### Data Protection

**Data at Rest:**
- **Audit Database:** Plaintext SQLite (future: SQLCipher encryption)
- **Configuration:** Plaintext YAML (contains no secrets)
- **Rego Policies:** Plaintext (user-defined logic)

**Data in Transit:**
- **Client ↔ YORI:** TLS 1.3 (YORI CA)
- **YORI ↔ LLM API:** TLS 1.3 (LLM provider's CA)
- **User ↔ OPNsense UI:** HTTPS (OPNsense web UI cert)

**Data Retention:**
- Audit logs purged after `retention_days` (default 365)
- Automatic cleanup via cron job (daily at 3:00 AM)
- Manual cleanup: `sqlite3 /var/db/yori/audit.db "DELETE FROM audit_events WHERE timestamp < datetime('now', '-365 days');"`

---

## Deployment Architecture

### Package Distribution

**OPNsense Package (.pkg):**

```
os-yori-0.1.0.pkg
├── /usr/local/bin/yori                    # Python entry point
├── /usr/local/lib/python3.11/site-packages/
│   ├── yori/                              # Python package
│   └── yori_core.so                       # Rust compiled binary
├── /usr/local/opnsense/mvc/app/
│   ├── controllers/OPNsense/YORI/        # PHP controllers
│   ├── models/OPNsense/YORI/             # XML models
│   └── views/OPNsense/YORI/              # Volt templates
├── /usr/local/etc/rc.d/yori              # Service script
└── /usr/local/share/examples/yori/
    ├── yori.conf.sample                  # Example config
    └── policies/                         # Default policies
```

### Service Management

**rc.d Service Script:**

```bash
#!/bin/sh
# /usr/local/etc/rc.d/yori

. /etc/rc.subr

name="yori"
rcvar="${name}_enable"
command="/usr/local/bin/yori"
command_args="--config /usr/local/etc/yori/yori.conf"
pidfile="/var/run/yori.pid"

load_rc_config $name
run_rc_command "$1"
```

**Service Control:**
```bash
service yori start
service yori stop
service yori restart
service yori status
```

---

## Scalability and Limitations

### Current Limitations

1. **Single Router:** Not designed for multi-router setups
2. **No High Availability:** If router reboots, YORI is unavailable
3. **SQLite Concurrency:** Limited write throughput (~1000 req/sec max)
4. **No Distributed Policies:** Each router has independent policy state
5. **Manual CA Installation:** Requires user action on each device

### When to Use SARK Instead

| Metric | YORI | SARK (Enterprise) |
|--------|------|-------------------|
| Users | <50 | 50+ |
| Devices | <20 | Unlimited |
| Availability | Best-effort | 99.9% SLA |
| Database | SQLite | PostgreSQL + TimescaleDB |
| Cache | In-memory | Valkey cluster |
| Deployment | Single router | Kubernetes |
| Cost | Free (DIY) | Paid license |

**Migration Path:** YORI audit logs can be exported to CSV and imported into SARK for long-term archival or advanced analytics.

---

## Future Architecture Enhancements

### v0.2.0 (Planned)

- **Policy Bundles:** Pre-packaged policy templates (download from repo)
- **Web-Based Policy Editor:** No-code policy builder in OPNsense UI
- **Encrypted Audit DB:** SQLCipher integration for at-rest encryption
- **Multi-Router Sync:** Sync policies across multiple YORI instances

### v0.3.0 (Planned)

- **Local LLM Integration:** Prefer local Ollama over cloud APIs
- **Cost Tracking Dashboard:** Real-time spend tracking with budget alerts
- **Advanced Analytics:** Usage patterns, topic analysis (LDA)
- **SIEM Integration:** Export logs to Splunk, Datadog, etc.

---

## See Also

- **[Developer Guide](DEVELOPER_GUIDE.md)** - Building and contributing to YORI
- **[Configuration Reference](CONFIGURATION.md)** - Detailed config options
- **[Policy Guide](POLICY_GUIDE.md)** - Writing Rego policies
- **[Project Plan](PROJECT_PLAN.md)** - Milestones and roadmap

---

**Architecture document version:** v0.1.0 (2026-01-19)
