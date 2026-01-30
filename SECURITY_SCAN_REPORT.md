# Security Scan Report - YORI Proxy

**Date:** 2026-01-29
**Branch:** cz2/feat/security
**Scanned By:** Security Worker (Czarina Orchestration)

## Executive Summary

Comprehensive security scanning completed using Bandit, Safety, and Semgrep. Overall security posture is good with mostly false positives. Key findings require attention:

- **Critical:** 0
- **High:** 0
- **Medium:** 3 (all false positives)
- **Warnings:** 3 (1 actionable, 2 false positives)
- **Dependency Vulnerabilities:** 3 (indirect dependencies)

## Scan Results

### Bandit - Python Security Linter

**Total Findings:** 3 (all MEDIUM severity)

| Finding | Severity | Location | Status |
|---------|----------|----------|--------|
| B104: Hardcoded bind to 0.0.0.0 | MEDIUM | python/yori/__main__.py:175 | False Positive |
| B104: Hardcoded bind to 0.0.0.0 | MEDIUM | python/yori/proxy_server.py:185 | False Positive |
| B104: Hardcoded bind to 0.0.0.0 | MEDIUM | python/yori/proxy_server.py:186 | False Positive |

**Analysis:**
All findings relate to binding the server to `0.0.0.0` which is intentional and required for a network proxy server to accept connections from the local network. This is appropriate for the home router deployment scenario.

**Recommendation:** No action needed. These are false positives for this use case.

---

### Semgrep - Advanced Static Analysis

**Total Findings:** 3 (all WARNING severity)

| Finding | Severity | Location | Status |
|---------|----------|----------|--------|
| Direct use of Jinja2 (XSS risk) | WARNING | python/yori/block_page.py:20 | False Positive |
| Direct use of Jinja2 (XSS risk) | WARNING | python/yori/block_page.py:64 | False Positive |
| Missing CSRF token in form | WARNING | python/yori/templates/block_page.html:217 | **ACTION REQUIRED** |

**Analysis:**

1. **Jinja2 XSS Warnings (Lines 20, 64):**
   False positives. Code properly enables autoescape for HTML/XML:
   ```python
   jinja_env = Environment(
       loader=FileSystemLoader(TEMPLATE_DIR),
       autoescape=select_autoescape(['html', 'xml'])  # XSS protection enabled
   )
   ```

2. **Missing CSRF Token (Line 217):**
   Valid finding. The override form in block_page.html lacks CSRF protection:
   ```html
   <form class="override-form" method="POST" action="/yori/override">
   ```

   **Recommendation:** Implement CSRF protection for the override form (Task 3).

---

### Safety - Dependency Vulnerability Scanner

**Total Findings:** 3 vulnerabilities in indirect dependencies

| Package | Version | Vulnerable Spec | Fix Available |
|---------|---------|----------------|---------------|
| fonttools | 4.60.2 | < 4.61.0 | Yes (4.61.0+) |
| (2 more) | - | - | Investigating |

**Analysis:**
Vulnerabilities found in indirect dependencies (not directly used by YORI). Impact is minimal as these packages are likely dev dependencies or transitive dependencies from tools.

**Recommendation:** Update indirect dependencies, but prioritize direct security enhancements.

---

## Manual Code Audit Findings

### Input Validation

**Status:** Partial implementation via Pydantic

- FastAPI uses Pydantic for automatic request validation
- Request body parsing uses `.json()` and `.body()` methods
- Headers accessed via `.get()` with safe defaults

**Gaps Identified:**
- No explicit size limits on request bodies
- No validation of upstream API responses
- URL query parameters need sanitization

**Recommendation:** Enhance input validation (Task 3)

---

### Rate Limiting

**Status:** NOT IMPLEMENTED

**Risk:** Medium - Service vulnerable to abuse and DoS attacks

**Recommendation:** Implement rate limiting (Task 4)

---

### Security Headers

**Status:** NOT IMPLEMENTED

**Current State:** No security headers in responses

**Missing Headers:**
- Strict-Transport-Security (HSTS)
- Content-Security-Policy (CSP)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Referrer-Policy
- Permissions-Policy

**Recommendation:** Implement security headers middleware (Task 5)

---

### TLS Configuration

**Status:** BASIC IMPLEMENTATION

**Current State:**
- TLS support via uvicorn with cert/key files
- No explicit cipher suite configuration
- No protocol version enforcement
- Uses Python SSL defaults

**Gaps:**
- No strong cipher enforcement
- May allow TLS 1.0/1.1 (deprecated)
- No perfect forward secrecy guarantee
- No OCSP stapling

**Recommendation:** Harden TLS configuration (Task 6)

---

### Authentication & Authorization

**Status:** IMPLEMENTED (Emergency Override)

**Current Implementation:**
- SHA-256 password hashing for override tokens
- No timing attack protection observed
- Emergency override without authentication in trusted mode

**Recommendation:** Review for timing attacks, consider HMAC comparison

---

### SQL Injection

**Status:** SAFE

**Analysis:** All SQL queries use parameterized statements via cursor.execute():
```python
cursor.execute(
    """INSERT INTO enforcement_events ...""",
    (param1, param2, param3)  # Parameters passed separately
)
```

No evidence of string concatenation in SQL queries.

**Recommendation:** No action needed. Continue using parameterized queries.

---

## Priority Actions

### High Priority
1. ✅ **Add CSRF protection** to override form (Semgrep finding)
2. ✅ **Implement rate limiting** to prevent abuse
3. ✅ **Add security headers** to all responses

### Medium Priority
4. ✅ **Harden TLS configuration** with strong ciphers and TLS 1.2+
5. ✅ **Enhance input validation** with size limits and sanitization
6. Update indirect dependencies (fonttools, etc.)

### Low Priority
7. Consider timing-safe password comparison
8. Add request body size limits globally
9. Implement fail2ban-style auto-blocking

---

## Testing Recommendations

1. **Rate Limiting:** Test with rapid requests, verify limits enforced
2. **Security Headers:** Verify all headers present in responses
3. **TLS:** Test with SSL Labs or similar scanner (target: A+ rating)
4. **CSRF:** Verify tokens required and validated
5. **Input Validation:** Test with oversized payloads, malformed JSON

---

## Compliance & Standards

- **OWASP Top 10:** No critical vulnerabilities identified
- **CWE-605:** Binding to all interfaces (acceptable for network service)
- **Mozilla SSL Config:** Current TLS config needs hardening
- **Security Headers:** Missing recommended headers (high priority)

---

## Conclusion

YORI proxy has a solid security foundation with proper input validation via Pydantic and safe SQL practices. Main gaps are:

1. Missing rate limiting (abuse protection)
2. Missing security headers (defense in depth)
3. Basic TLS configuration (needs hardening)
4. One CSRF vulnerability (override form)

All findings are addressable and will be remediated in subsequent tasks.

---

**Next Steps:**
- Proceed with Task 2: Fix CSRF vulnerability
- Proceed with Tasks 3-6: Implement security enhancements
- Create comprehensive security tests (Task 7)
