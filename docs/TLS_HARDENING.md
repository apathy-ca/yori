# TLS/SSL Hardening Guide

This guide explains how to configure YORI with hardened TLS/SSL settings for production deployments.

## Overview

YORI includes a comprehensive TLS configuration module (`yori/tls_config.py`) that implements industry best practices for secure communications.

**Security Features:**
- TLS 1.2+ only (TLS 1.3 preferred)
- Strong cipher suites with perfect forward secrecy (PFS)
- ECDHE and DHE key exchange (forward secrecy)
- Authenticated encryption (GCM, CHACHA20-POLY1305)
- Protection against known attacks (POODLE, CRIME, etc.)
- Configurable security profiles (Modern, Intermediate, Old)

## TLS Security Profiles

Based on [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/):

### Modern Profile (Recommended for new deployments)
- **TLS Version:** 1.3 only
- **Ciphers:** TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256
- **Compatibility:** Modern browsers only (2020+)
- **Security:** Highest

### Intermediate Profile (Recommended for general use)
- **TLS Version:** 1.2 and 1.3
- **Ciphers:** ECDHE+AESGCM, ECDHE+CHACHA20, DHE+AESGCM
- **Compatibility:** All modern clients
- **Security:** High (default for YORI)

### Old Profile (Not recommended)
- **TLS Version:** 1.0+
- **Ciphers:** Includes legacy ciphers
- **Compatibility:** Maximum (including very old clients)
- **Security:** Lower (use only if required for compatibility)

## Quick Start

### 1. Generate Self-Signed Certificate (Development)

```bash
# Generate self-signed certificate (valid for 365 days)
openssl req -x509 -newkey rsa:4096 \
  -keyout yori.key -out yori.crt \
  -days 365 -nodes \
  -subj "/CN=localhost"

# Set proper permissions
chmod 600 yori.key
chmod 644 yori.crt
```

### 2. Use with YORI Proxy

```bash
# Run with TLS enabled
python -m yori --cert yori.crt --key yori.key --port 8443

# Or via proxy_server.py
python python/yori/proxy_server.py \
  --cert /path/to/yori.crt \
  --key /path/to/yori.key \
  --port 8443
```

### 3. Verify TLS Configuration

```bash
# Test with curl
curl -k https://localhost:8443/health

# Check TLS version and cipher
openssl s_client -connect localhost:8443 -tls1_2
openssl s_client -connect localhost:8443 -tls1_3
```

## Production Certificate Setup

### Option 1: Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt-get install certbot

# Generate certificate (requires domain and port 80/443 access)
sudo certbot certonly --standalone \
  -d yori.yourdomain.com \
  --email your@email.com

# Certificates will be at:
# /etc/letsencrypt/live/yori.yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yori.yourdomain.com/privkey.pem

# Use with YORI
python -m yori \
  --cert /etc/letsencrypt/live/yori.yourdomain.com/fullchain.pem \
  --key /etc/letsencrypt/live/yori.yourdomain.com/privkey.pem
```

### Option 2: Internal CA (For home networks)

```bash
# Create CA
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
  -out ca.crt -subj "/CN=YORI Home CA"

# Create server certificate
openssl genrsa -out yori.key 4096
openssl req -new -key yori.key -out yori.csr \
  -subj "/CN=yori.local"

# Sign with CA
openssl x509 -req -in yori.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out yori.crt -days 365 -sha256

# Install ca.crt in client browsers/systems
# Use yori.crt and yori.key for YORI
```

## Advanced Configuration

### Programmatic SSL Context Creation

For advanced use cases, create SSL context directly:

```python
from pathlib import Path
from yori.tls_config import create_ssl_context, TLSProfile

# Create hardened SSL context
ssl_context = create_ssl_context(
    certfile=Path("/path/to/cert.pem"),
    keyfile=Path("/path/to/key.pem"),
    profile=TLSProfile.INTERMEDIATE,
)

# Use with custom server implementations
# (Note: Uvicorn via run() doesn't accept SSLContext directly)
```

### Custom Cipher Suites

```python
from yori.tls_config import TLSProfile, get_cipher_suites

# Get recommended ciphers for a profile
ciphers = get_cipher_suites(TLSProfile.INTERMEDIATE)
print(f"Using {len(ciphers)} cipher suites")

# Ciphers are prioritized by:
# 1. Forward secrecy (ECDHE, DHE)
# 2. Authenticated encryption (GCM, CHACHA20)
# 3. Key size (256-bit > 128-bit)
```

### Configuration File

Add TLS settings to `yori.yaml`:

```yaml
proxy:
  host: "0.0.0.0"
  port: 8443
  tls_cert: "/etc/yori/yori.crt"
  tls_key: "/etc/yori/yori.key"
```

## Security Best Practices

### 1. Certificate Management

- **Never commit private keys to version control**
- Use proper file permissions: `chmod 600 *.key`
- Rotate certificates before expiry (Let's Encrypt: 90 days)
- Use strong key sizes: 2048-bit RSA minimum, 4096-bit preferred
- Consider ECDSA certificates for better performance

### 2. TLS Version Policy

```
✅ TLS 1.3 (Preferred)
✅ TLS 1.2 (Acceptable)
❌ TLS 1.1 (Deprecated)
❌ TLS 1.0 (Insecure)
❌ SSL 3.0 (Insecure - POODLE)
❌ SSL 2.0 (Insecure)
```

### 3. Cipher Suite Priorities

1. **Forward Secrecy:** ECDHE/DHE key exchange
2. **Authenticated Encryption:** GCM, CHACHA20-POLY1305
3. **Key Size:** 256-bit > 128-bit
4. **Avoid:** RC4, DES, 3DES, MD5, NULL ciphers

### 4. HSTS (HTTP Strict Transport Security)

YORI automatically adds HSTS headers via `SecurityHeadersMiddleware`:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

This forces browsers to always use HTTPS.

### 5. Certificate Pinning (Advanced)

For maximum security in controlled environments:

```python
# Not yet implemented - future enhancement
# Would validate specific certificate fingerprints
```

## Testing TLS Configuration

### 1. SSL Labs Test

For public servers, use [SSL Labs Server Test](https://www.ssllabs.com/ssltest/):

**Target Rating:** A or A+

### 2. OpenSSL Testing

```bash
# Test TLS 1.2
openssl s_client -connect localhost:8443 -tls1_2

# Test TLS 1.3
openssl s_client -connect localhost:8443 -tls1_3

# Should fail (TLS 1.1 disabled)
openssl s_client -connect localhost:8443 -tls1_1

# List supported ciphers
nmap --script ssl-enum-ciphers -p 8443 localhost
```

### 3. testssl.sh

```bash
# Install testssl.sh
git clone https://github.com/drwetter/testssl.sh.git
cd testssl.sh

# Run comprehensive test
./testssl.sh localhost:8443
```

## Troubleshooting

### Certificate Not Found

```
ERROR: TLS certificate not found: /path/to/cert.pem
```

**Solution:**
- Verify certificate path is correct
- Check file permissions
- Use absolute paths, not relative

### Certificate/Key Mismatch

```
ERROR: Certificate validation failed
```

**Solution:**
- Ensure certificate and key are from the same generation
- Verify certificate chain is complete
- Check for encrypted keys (YORI expects unencrypted keys)

### Client Can't Connect

```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solutions:**
- For self-signed certs: Add CA certificate to client trust store
- For Let's Encrypt: Ensure fullchain.pem is used, not cert.pem
- Check certificate expiration: `openssl x509 -in cert.pem -noout -dates`

### Performance Issues

**Solutions:**
- Enable session resumption (enabled by default)
- Use ECDSA certificates (faster than RSA)
- Enable HTTP/2 (requires TLS 1.2+)
- Consider hardware acceleration for SSL

## Monitoring

### TLS Connection Info

```python
from yori.tls_config import get_tls_info

# Get connection details
info = get_tls_info(ssl_socket)
print(f"TLS Version: {info['version']}")
print(f"Cipher: {info['cipher']}")
```

### Metrics to Track

- TLS version distribution (should be mostly 1.2/1.3)
- Cipher suite usage
- Handshake failures
- Certificate expiration dates
- SSL/TLS error rates

## References

- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [OWASP TLS Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
- [SSL Labs Server Test](https://www.ssllabs.com/ssltest/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Python ssl module](https://docs.python.org/3/library/ssl.html)

## Future Enhancements

- [ ] OCSP stapling
- [ ] Certificate pinning
- [ ] mTLS (mutual TLS) for client authentication
- [ ] Automatic certificate renewal (Let's Encrypt integration)
- [ ] TLS 1.3 0-RTT (with replay protection)
- [ ] Session ticket rotation
