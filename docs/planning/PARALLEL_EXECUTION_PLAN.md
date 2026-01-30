# Parallel Execution Plan: Proxy Build + OPNsense Test

**Duration:** 1-2 days
**Objective:** Get proxy working AND validate OPNsense infrastructure simultaneously

---

## The Plan

### You: OPNsense Infrastructure Testing
**Focus:** Phases 1-6 of OPNSENSE_DEPLOYMENT_TEST_PLAN.md
**Duration:** 4-6 hours
**Outcome:** OPNsense ready for proxy deployment

### Czarina: HTTP Proxy Implementation
**Focus:** Build FastAPI proxy server (4 workers)
**Duration:** 12-16 hours automated
**Outcome:** Working proxy ready to deploy

---

## Your Timeline (Human Tasks)

### Session 1: VM Setup (1-2 hours)
```bash
# 1. Create OPNsense VM
# - 2GB RAM, 20GB disk, 2 NICs
# - Install OPNsense 24.1+

# 2. Initial configuration
# - WAN: DHCP
# - LAN: 10.0.0.1/24
# - Enable SSH

# 3. Access web UI
# - Browse to https://10.0.0.1
# - Skip wizard or configure basics
```

**Checkpoint:** Can SSH to OPNsense, can access web UI

---

### Session 2: Package Preparation (1-2 hours)

```bash
# On your dev machine (not OPNsense)
cd ~/Source/yori

# 1. Build current package (even without proxy)
python -m build --wheel
maturin build --release

# 2. Transfer to OPNsense
scp target/wheels/yori-*.whl root@10.0.0.1:/tmp/
scp examples/yori.conf.example root@10.0.0.1:/tmp/yori.conf

# 3. SSH to OPNsense and install
ssh root@10.0.0.1
pkg install python311 py311-pip py311-sqlite3
python3.11 -m venv /usr/local/yori-venv
source /usr/local/yori-venv/bin/activate
pip install /tmp/yori-*.whl

# 4. Verify installation
python -c "import yori; print('✓')"
python -c "from yori.enforcement import EnforcementEngine; print('✓')"
```

**Checkpoint:** YORI package installed, imports work

---

### Session 3: Network Configuration (1-2 hours)

```bash
# Still SSH'd to OPNsense

# 1. Create directories
mkdir -p /usr/local/etc/yori/policies
mkdir -p /var/db/yori
mkdir -p /var/log/yori

# 2. Copy config
cp /tmp/yori.conf /usr/local/etc/yori/

# 3. Generate TLS certificates
cd /usr/local/etc/yori
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout yori.key -out yori.crt \
  -days 365 -subj "/CN=api.openai.com"
chmod 600 yori.key
```

**Via Web UI:**
```
Services → Unbound DNS → Overrides → Host Overrides

Add:
  Host: api
  Domain: openai.com
  IP: 10.0.0.1

Save and Apply
```

**Test from client:**
```bash
nslookup api.openai.com
# Should return 10.0.0.1
```

**Checkpoint:** DNS override works, certs created

---

### Session 4: Service Stub (30 min)

```bash
# Create placeholder service (will be replaced by Czarina's work)
cat > /usr/local/etc/yori/run_stub.py << 'EOF'
#!/usr/local/yori-venv/bin/python
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('yori')

logger.info("YORI stub running - waiting for proxy implementation")
logger.info("Listening would be on port 8443")

try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    logger.info("Shutdown")
EOF

chmod +x /usr/local/etc/yori/run_stub.py

# Test it
/usr/local/etc/yori/run_stub.py &
sleep 3
pkill -f run_stub.py
```

**Checkpoint:** Can run Python script, logs appear

---

### Session 5: Wait for Czarina (Variable)

**While Czarina builds the proxy:**

1. **Document your setup**
   - Screenshot web UI
   - Save configuration files
   - Note any issues encountered

2. **Prepare test client**
   - Set up laptop/VM on LAN network
   - Get IP from DHCP (should be 10.0.0.100+)
   - Install CA certificate (once proxy ready)
   - Install curl, test tools

3. **Review Czarina's progress**
   - Check commits in feature branches
   - Review code as it's written
   - Test locally if workers complete early

4. **Plan integration testing**
   - Review Phase 7-10 of deployment plan
   - Prepare test scripts
   - Set up monitoring tools

---

### Session 6: Deploy Czarina's Proxy (30-60 min)

**Once Czarina completes all 4 workers:**

```bash
# On your dev machine
cd ~/Source/yori

# 1. Pull Czarina's completed work
git pull
git checkout feature/proxy-testing-cli  # Or whatever final branch

# 2. Rebuild package with proxy
python -m build --wheel
maturin build --release

# 3. Transfer to OPNsense
scp target/wheels/yori-*.whl root@10.0.0.1:/tmp/

# 4. Reinstall on OPNsense
ssh root@10.0.0.1
source /usr/local/yori-venv/bin/activate
pip install --force-reinstall /tmp/yori-*.whl

# 5. Test proxy works
python -m yori --help
# Should show CLI options

# 6. Start proxy
python -m yori \
  --config /usr/local/etc/yori/yori.conf \
  --cert /usr/local/etc/yori/yori.crt \
  --key /usr/local/etc/yori/yori.key &

# 7. Verify listening
sockstat -l | grep 8443
# Should show python listening on 8443
```

**Checkpoint:** Proxy running, listening on port 8443

---

### Session 7: Live Testing (1-2 hours)

**From test client:**

```bash
# 1. Test DNS resolution
nslookup api.openai.com
# Should return 10.0.0.1

# 2. Test connection
telnet api.openai.com 443
# Should connect

# 3. Test HTTP
curl -k https://api.openai.com/
# Should get response from proxy (or forwarded response)

# 4. Test with real API key
export OPENAI_API_KEY="sk-your-key"

curl -k https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'

# Should either:
# - Forward to real API and get response
# - Return block page if enforcement enabled
```

**Check OPNsense logs:**
```bash
ssh root@10.0.0.1
tail -f /var/log/yori/yori.log

# Should see:
# - Request received
# - Enforcement decision
# - Forward or block action
# - Response logged
```

**Check audit database:**
```bash
sqlite3 /var/db/yori/audit.db \
  "SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT 5;"

# Should have event entries
```

**Checkpoint:** Live traffic intercepted and logged!

---

## Czarina Timeline (Automated)

### Worker 1: Basic Proxy (Hours 0-4)
**Files:** `python/yori/proxy_server.py`
**Outcome:** FastAPI app that forwards requests

**Tests:**
```bash
# You can test locally as soon as this completes
git checkout feature/proxy-basic-server
pip install -e .
python -m yori.proxy_server &

curl http://localhost:8443/test
# Should forward somewhere
```

---

### Worker 2: TLS + Enforcement (Hours 4-8)
**Files:** Extends `proxy_server.py`
**Outcome:** HTTPS support, enforcement integration

**Tests:**
```bash
git checkout feature/proxy-tls-enforcement
pip install -e .

# Generate test cert
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout /tmp/test.key -out /tmp/test.crt \
  -days 1 -subj "/CN=localhost"

python -m yori --cert /tmp/test.crt --key /tmp/test.key &

curl -k https://localhost:8443/test
# Should work with HTTPS
```

---

### Worker 3: Block Page + Audit (Hours 8-12)
**Files:** `proxy_handlers.py`, extends `proxy_server.py`
**Outcome:** Block page serving, audit logging

**Tests:**
```bash
git checkout feature/proxy-block-audit
pip install -e .

# Start with blocking config
python -m yori --config /tmp/block_config.yaml &

curl -k https://localhost:8443/test
# Should return HTML block page

sqlite3 /var/db/yori/audit.db "SELECT * FROM audit_events;"
# Should have entries
```

---

### Worker 4: Testing + CLI (Hours 12-16)
**Files:** `tests/integration/test_proxy.py`, `__main__.py`
**Outcome:** Complete tested system

**Tests:**
```bash
git checkout feature/proxy-testing-cli
pip install -e .

# Run integration tests
pytest tests/integration/test_proxy.py -v
# All should pass

# Run full test suite
pytest tests/ -v
# Should maintain >80% passing
```

---

## Synchronization Points

### Morning (Start)
**You:** Start OPNsense VM setup
**Czarina:** Launch workers

### Mid-Day (Worker 1-2 Complete)
**You:** Package prep, network config
**Czarina:** Working on Worker 3

### Afternoon (Worker 3 Complete)
**You:** Review code, prepare test client
**Czarina:** Working on Worker 4

### Evening (Worker 4 Complete)
**You:** Deploy proxy to OPNsense
**Czarina:** Done! Code merged

### End of Day
**You + Proxy:** Live traffic testing! 🎉

---

## Communication Protocol

### Check Czarina Progress
```bash
# List feature branches
git branch -r | grep feature/proxy

# Check latest commits
git log --oneline feature/proxy-basic-server
git log --oneline feature/proxy-tls-enforcement

# Pull latest work
git fetch origin
git checkout feature/proxy-basic-server
```

### Early Testing
```bash
# Test workers as they complete
# Don't wait for all 4 - test incrementally!

# After Worker 1:
git checkout feature/proxy-basic-server
pip install -e .
python -m yori.proxy_server
# Test basic forwarding

# After Worker 2:
git checkout feature/proxy-tls-enforcement
pip install -e .
# Test TLS + enforcement

# Etc.
```

---

## Risk Mitigation

### If Czarina Gets Stuck

**Option 1: Help the stuck worker**
- Review code in branch
- Check error messages
- Provide guidance
- Let worker continue

**Option 2: Take over**
- Grab incomplete work from branch
- Finish implementation manually
- Merge and continue

**Option 3: Simplify scope**
- Skip nice-to-have features
- Focus on must-haves
- Defer polish to later

### If OPNsense Setup Fails

**Option 1: Use Docker instead**
```bash
# Run proxy in Docker container
docker run -it --rm \
  -p 8443:8443 \
  -v /tmp/yori:/etc/yori \
  python:3.11 bash

# Install and run YORI in container
# Still proves proxy works
```

**Option 2: Test on Linux directly**
```bash
# Run proxy on Linux dev machine
# Use iptables for port forwarding
# Test with local curl requests
```

---

## Success Criteria

### At End of Day 1

**OPNsense Infrastructure:**
- ✅ VM running and accessible
- ✅ YORI package installed
- ✅ Directories and config created
- ✅ DNS override configured
- ✅ TLS certificates generated
- ✅ Ready for proxy deployment

**Proxy Implementation:**
- ✅ All 4 workers complete
- ✅ Code merged to main
- ✅ Integration tests passing
- ✅ Can run `python -m yori`
- ✅ Listens on port 8443
- ✅ Forwards requests
- ✅ Serves block pages
- ✅ Logs to audit database

### At End of Day 2

**Live System:**
- ✅ Proxy deployed to OPNsense
- ✅ Intercepts LLM API traffic
- ✅ Enforcement decisions work
- ✅ Block page shown to clients
- ✅ Allowlist bypass works
- ✅ Emergency override works
- ✅ Audit log has real entries
- ✅ **ACTUAL UTILITY DEMONSTRATED!** 🎉

---

## Next Steps After Success

1. **Document successful setup**
   - Screenshot everything
   - Save working configuration
   - Create installation guide

2. **Record demo video**
   - Show traffic interception
   - Demonstrate blocking
   - Show audit logs

3. **Plan v0.3.0**
   - SARK integration (real OPA)
   - Streaming support
   - Performance optimization
   - OPNsense web UI

4. **Share with community**
   - Blog post
   - GitHub release
   - Demo video
   - Documentation

---

## Quick Reference

### Start Czarina
```bash
cd ~/Source/yori

# Review the orchestration plan
cat CZARINA_PROXY_IMPLEMENTATION.md

# Launch Czarina with the plan
# (Assuming you have czarina CLI or orchestration system)
czarina orchestrate CZARINA_PROXY_IMPLEMENTATION.md
```

### Monitor Progress
```bash
# Watch for new branches
watch -n 30 'git fetch && git branch -r | grep proxy'

# Check latest commits
git log --all --oneline --graph | head -20

# Pull and test
git checkout feature/proxy-basic-server
pip install -e .
python -m yori.proxy_server
```

### Deploy to OPNsense
```bash
# After all workers complete
cd ~/Source/yori
git pull
python -m build --wheel

scp target/wheels/yori-*.whl root@10.0.0.1:/tmp/
ssh root@10.0.0.1

source /usr/local/yori-venv/bin/activate
pip install --force-reinstall /tmp/yori-*.whl

python -m yori \
  --config /usr/local/etc/yori/yori.conf \
  --cert /usr/local/etc/yori/yori.crt \
  --key /usr/local/etc/yori/yori.key
```

---

**Ready to execute in parallel!**

You focus on infrastructure, Czarina builds the proxy, and you'll have a working system by end of tomorrow! 🚀

