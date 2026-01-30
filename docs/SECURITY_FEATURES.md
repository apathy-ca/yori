# YORI Security Features

Comprehensive security hardening for production deployment of the YORI LLM governance proxy.

## Overview

YORI implements defense-in-depth security with multiple layers of protection:

1. **CSRF Protection** - Prevents cross-site request forgery attacks
2. **Rate Limiting** - Prevents abuse and DoS attacks
3. **Security Headers** - Adds comprehensive HTTP security headers
4. **TLS Hardening** - Strong encryption with TLS 1.2+
5. **Input Validation** - Sanitizes and validates all user inputs
6. **Audit Logging** - Tracks all security events

## Security Features

### 1. CSRF Protection

**What it does:**
- Generates unique tokens for each session
- Validates tokens on state-changing requests (POST, PUT, DELETE)
- Uses HMAC-based tokens with secret key
- Implements constant-time comparison to prevent timing attacks

**Implementation:**
- Module: `yori/csrf.py`
- Middleware: `CSRFMiddleware`
- Cookie-based token storage with HttpOnly and SameSite flags

**Protected endpoints:**
- `/yori/override` - Override password submission
- All POST/PUT/DELETE requests (except exempt paths)

**Configuration:**
```python
# Exempt paths from CSRF (e.g., API endpoints with token auth)
CSRFMiddleware.EXEMPT_PATHS = {"/health", "/metrics", "/api/webhook"}
```

**Usage in templates:**
```html
<form method="POST">
  <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
  <!-- form fields -->
</form>
```

---

### 2. Rate Limiting

**What it does:**
- Prevents abuse through request throttling
- Implements sliding window algorithm
- Tracks per-IP and per-endpoint limits
- Returns 429 Too Many Requests when exceeded

**Implementation:**
- Module: `yori/rate_limit.py`
- Middleware: `RateLimitMiddleware`
- Algorithm: Sliding window with automatic cleanup

**Default limits:**
- **Global:** 60 requests/minute, 1000 requests/hour per IP
- **Override endpoint:** 5 requests/minute, 20 requests/hour
- **API endpoints:** 30 requests/minute, 500 requests/hour

**Rate limit headers:**
```
X-RateLimit-Limit-Minute: 60
X-RateLimit-Limit-Hour: 1000
X-RateLimit-Remaining-Minute: 45
X-RateLimit-Remaining-Hour: 873
Retry-After: 42
```

**Customization:**
```python
# Custom limits for specific endpoints
RateLimitMiddleware.ENDPOINT_LIMITS = {
    "/api/expensive-operation": (10, 100),  # 10/min, 100/hour
}
```

---

### 3. Security Headers

**What it does:**
- Adds comprehensive HTTP security headers to all responses
- Implements OWASP best practices
- Provides defense against common web attacks

**Implementation:**
- Module: `yori/security_headers.py`
- Middleware: `SecurityHeadersMiddleware`

**Headers added:**

| Header | Value | Purpose |
|--------|-------|---------|
| Strict-Transport-Security | max-age=31536000; includeSubDomains; preload | Force HTTPS for 1 year |
| Content-Security-Policy | default-src 'self'; ... | Prevent XSS attacks |
| X-Frame-Options | DENY | Prevent clickjacking |
| X-Content-Type-Options | nosniff | Prevent MIME sniffing |
| X-XSS-Protection | 1; mode=block | Enable XSS filter (legacy) |
| Referrer-Policy | strict-origin-when-cross-origin | Control referrer info |
| Permissions-Policy | camera=(), microphone=(), ... | Disable browser features |

**CSP Policy:**
```
default-src 'self';
script-src 'self' 'unsafe-inline';
style-src 'self' 'unsafe-inline';
img-src 'self' data:;
frame-ancestors 'none';
upgrade-insecure-requests
```

**Custom CSP:**
```python
middleware = SecurityHeadersMiddleware(
    app,
    custom_csp="default-src 'self'; script-src 'self' https://cdn.example.com"
)
```

---

### 4. TLS/SSL Hardening

**What it does:**
- Enforces TLS 1.2+ (disables TLS 1.0/1.1, SSL 2.0/3.0)
- Uses strong cipher suites with perfect forward secrecy
- Implements Mozilla SSL Configuration recommendations
- Prevents downgrade attacks

**Implementation:**
- Module: `yori/tls_config.py`
- Documentation: `docs/TLS_HARDENING.md`

**Security profiles:**
- **MODERN:** TLS 1.3 only (highest security)
- **INTERMEDIATE:** TLS 1.2+ (recommended, balanced)
- **OLD:** TLS 1.0+ (not recommended)

**Cipher suite priorities:**
1. Perfect forward secrecy (ECDHE, DHE)
2. Authenticated encryption (GCM, CHACHA20)
3. 256-bit keys over 128-bit

**Disabled features:**
- SSL 2.0, SSL 3.0 (vulnerable to POODLE)
- TLS 1.0, TLS 1.1 (weak protocols)
- Compression (vulnerable to CRIME)
- Weak ciphers (RC4, DES, 3DES, MD5)

**Usage:**
```bash
# Run with TLS
python -m yori --cert /path/to/cert.pem --key /path/to/key.pem

# Generate self-signed cert for testing
openssl req -x509 -newkey rsa:4096 -keyout yori.key -out yori.crt -days 365 -nodes
```

---

### 5. Input Validation

**What it does:**
- Validates and sanitizes all user inputs
- Prevents injection attacks
- Enforces size and format limits
- Protects against resource exhaustion

**Implementation:**
- Module: `yori/input_validation.py`
- Middleware: `RequestSizeLimitMiddleware`

**Protections:**

| Attack Vector | Protection |
|---------------|------------|
| Path traversal | Path validation, blocks ../, \\, etc. |
| JSON bomb | Max nesting depth (20 levels) |
| Buffer overflow | Max request size (10 MB) |
| Header injection | Max header size (8 KB each) |
| Query parameter flood | Max parameters (50) |
| Log injection | Newline/ANSI code sanitization |
| Filename attacks | Sanitization, blocks traversal |

**Validators:**
```python
from yori.input_validation import (
    sanitize_string,
    validate_endpoint_path,
    sanitize_filename,
    validate_api_key_format,
)

# Sanitize user input
safe_text = sanitize_string(user_input, max_length=1000)

# Validate API path
validate_endpoint_path("/api/v1/chat")  # OK
validate_endpoint_path("/api/../etc/passwd")  # Raises ValueError

# Sanitize filename
safe_name = sanitize_filename("../../secret.txt")  # Returns: ".._.._ secret.txt"
```

**Size limits:**
- Max request body: 10 MB
- Max URL length: 2048 characters
- Max header size: 8 KB per header
- Max query parameters: 50
- Max JSON nesting: 20 levels

---

## Security Testing

### Running Security Tests

```bash
# Run all security tests
pytest tests/test_security.py -v

# Run specific test class
pytest tests/test_security.py::TestCSRFProtection -v

# Run with coverage
pytest tests/test_security.py --cov=yori --cov-report=html
```

### Security Scanning

```bash
# Python security linter
bandit -r python/yori/

# Dependency vulnerability scanner
safety check

# Advanced static analysis
semgrep --config=auto python/yori/
```

### Manual Testing

```bash
# Test rate limiting
for i in {1..70}; do curl https://localhost:8443/health; done

# Test CSRF protection (should fail without token)
curl -X POST https://localhost:8443/yori/override \
  -d "password=test" -i

# Test TLS configuration
openssl s_client -connect localhost:8443 -tls1_2
nmap --script ssl-enum-ciphers -p 8443 localhost

# Test security headers
curl -I https://localhost:8443/health
```

---

## Security Best Practices

### 1. Certificate Management

- ✅ Use Let's Encrypt for production certificates
- ✅ Rotate certificates before expiry
- ✅ Use 4096-bit RSA or 256-bit ECDSA keys
- ✅ Set proper file permissions (600 for keys)
- ❌ Never commit private keys to version control

### 2. Secret Management

- ✅ Use environment variables for secrets
- ✅ Rotate CSRF secret keys regularly
- ✅ Use strong, random passwords for override
- ❌ Don't hardcode secrets in code

### 3. Network Security

- ✅ Run YORI behind a firewall
- ✅ Use HTTPS only (no HTTP)
- ✅ Enable HSTS with preload
- ✅ Restrict access to trusted IPs (if possible)
- ❌ Don't expose directly to the internet

### 4. Monitoring

Monitor these security metrics:
- Rate limit violations per IP
- CSRF validation failures
- TLS handshake failures
- Invalid input attempts
- Override password failures

### 5. Updates

- ✅ Keep dependencies updated
- ✅ Monitor security advisories
- ✅ Test updates in staging first
- ✅ Review security scan reports regularly

---

## Security Checklist

Before deploying to production:

- [ ] TLS certificate installed and valid
- [ ] HSTS header enabled
- [ ] Rate limiting configured appropriately
- [ ] CSRF protection tested and working
- [ ] All security headers present
- [ ] Input validation tested
- [ ] Security scans show no critical issues
- [ ] Audit logging enabled
- [ ] Firewall rules configured
- [ ] Strong passwords set
- [ ] Secrets not in version control
- [ ] Monitoring and alerting configured
- [ ] Backup and recovery tested

---

## Threat Model

**Assets:**
- API keys (OpenAI, Anthropic)
- Override passwords
- Request/response data
- Audit logs

**Threats:**
1. **DoS/DDoS** → Mitigated by rate limiting
2. **CSRF attacks** → Mitigated by CSRF tokens
3. **XSS attacks** → Mitigated by CSP and sanitization
4. **Injection attacks** → Mitigated by input validation
5. **MITM attacks** → Mitigated by TLS encryption
6. **Brute force** → Mitigated by rate limiting
7. **Data exfiltration** → Mitigated by TLS and audit logging

**Trust Boundaries:**
- Home network (semi-trusted)
- Upstream APIs (trusted)
- Router/OPNsense (trusted)
- Family members (trusted but rate-limited)

---

## Incident Response

If you detect a security incident:

1. **Isolate:** Stop the proxy server
2. **Assess:** Check audit logs for scope
3. **Contain:** Reset rate limits, revoke compromised tokens
4. **Recover:** Rotate secrets, update firewall rules
5. **Review:** Analyze logs, improve defenses

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Mozilla SSL Config](https://ssl-config.mozilla.org/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

## Support

For security issues:
- Review the security scan report: `SECURITY_SCAN_REPORT.md`
- Check TLS hardening guide: `docs/TLS_HARDENING.md`
- Run security tests: `pytest tests/test_security.py`
- Report vulnerabilities: See SECURITY.md

**Do not** publicly disclose security vulnerabilities. Report them privately through the channels specified in SECURITY.md.
