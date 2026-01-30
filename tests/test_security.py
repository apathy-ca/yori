"""
Security Tests for YORI Proxy

Comprehensive test suite for security features including:
- CSRF protection
- Rate limiting
- Security headers
- Input validation
- TLS configuration
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import ssl

from yori.csrf import CSRFProtection, CSRFMiddleware
from yori.rate_limit import SlidingWindowRateLimiter, RateLimitMiddleware
from yori.security_headers import SecurityHeadersMiddleware, validate_csp
from yori.input_validation import (
    validate_json_depth,
    sanitize_string,
    validate_api_key_format,
    validate_endpoint_path,
    sanitize_filename,
    validate_ip_address,
    validate_port_number,
    sanitize_log_message,
    InputValidator,
)
from yori.tls_config import (
    create_ssl_context,
    TLSProfile,
    validate_certificate,
    get_cipher_suites,
)


class TestCSRFProtection:
    """Test CSRF token generation and validation"""

    def test_generate_token(self):
        """Test CSRF token generation"""
        csrf = CSRFProtection()
        token = csrf.generate_token()

        assert token is not None
        assert len(token) > 0
        assert isinstance(token, str)

    def test_validate_valid_token(self):
        """Test validating a valid CSRF token"""
        csrf = CSRFProtection()
        token = csrf.generate_token()

        # Should validate successfully
        assert csrf.validate_token(token) is True

    def test_validate_invalid_token(self):
        """Test validating invalid CSRF tokens"""
        csrf = CSRFProtection()

        # Empty token
        assert csrf.validate_token("") is False

        # Too short
        assert csrf.validate_token("abc123") is False

        # Invalid characters
        assert csrf.validate_token("x" * 96) is False

    def test_token_uniqueness(self):
        """Test that tokens are unique"""
        csrf = CSRFProtection()
        tokens = [csrf.generate_token() for _ in range(10)]

        # All tokens should be unique
        assert len(tokens) == len(set(tokens))


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_basic_rate_limit(self):
        """Test basic rate limiting"""
        limiter = SlidingWindowRateLimiter(
            requests_per_minute=5,
            requests_per_hour=100
        )

        client_id = "test_client"

        # First 5 requests should succeed
        for i in range(5):
            allowed, _ = limiter.check_rate_limit(client_id)
            assert allowed is True

        # 6th request should be blocked
        allowed, limits = limiter.check_rate_limit(client_id)
        assert allowed is False
        assert limits["requests_remaining_minute"] == 0

    def test_rate_limit_reset(self):
        """Test rate limit reset"""
        limiter = SlidingWindowRateLimiter(
            requests_per_minute=5,
            requests_per_hour=100
        )

        client_id = "test_client"

        # Use up limit
        for i in range(5):
            limiter.check_rate_limit(client_id)

        # Reset client
        limiter.reset_client(client_id)

        # Should be able to make requests again
        allowed, _ = limiter.check_rate_limit(client_id)
        assert allowed is True

    def test_multiple_clients(self):
        """Test rate limiting with multiple clients"""
        limiter = SlidingWindowRateLimiter(
            requests_per_minute=5,
            requests_per_hour=100
        )

        # Each client should have independent limits
        for client_num in range(3):
            client_id = f"client_{client_num}"
            for i in range(5):
                allowed, _ = limiter.check_rate_limit(client_id)
                assert allowed is True

    def test_get_client_stats(self):
        """Test getting client statistics"""
        limiter = SlidingWindowRateLimiter(
            requests_per_minute=10,
            requests_per_hour=100
        )

        client_id = "test_client"

        # Make some requests
        for i in range(3):
            limiter.check_rate_limit(client_id)

        # Get stats
        stats = limiter.get_client_stats(client_id)

        assert stats["minute_count"] == 3
        assert stats["minute_limit"] == 10
        assert stats["hour_count"] == 3
        assert stats["hour_limit"] == 100


class TestSecurityHeaders:
    """Test security headers generation"""

    def test_hsts_header(self):
        """Test HSTS header generation"""
        from fastapi import FastAPI

        app = FastAPI()
        middleware = SecurityHeadersMiddleware(
            app,
            hsts_max_age=31536000,
            hsts_include_subdomains=True,
            hsts_preload=True,
        )

        hsts = middleware._get_hsts_header()

        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts
        assert "preload" in hsts

    def test_csp_header(self):
        """Test CSP header generation"""
        from fastapi import FastAPI

        app = FastAPI()
        middleware = SecurityHeadersMiddleware(app)

        csp = middleware._get_csp_header()

        # Check for important directives
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "upgrade-insecure-requests" in csp

    def test_validate_csp(self):
        """Test CSP validation"""
        # Valid CSP
        assert validate_csp("default-src 'self'; script-src 'self'") is True

        # Missing default-src
        assert validate_csp("script-src 'self'") is False

    def test_permissions_policy(self):
        """Test Permissions-Policy header generation"""
        from fastapi import FastAPI

        app = FastAPI()
        middleware = SecurityHeadersMiddleware(app)

        policy = middleware._get_permissions_policy_header()

        # Should disable dangerous features
        assert "camera=()" in policy
        assert "microphone=()" in policy
        assert "geolocation=()" in policy


class TestInputValidation:
    """Test input validation and sanitization"""

    def test_validate_json_depth(self):
        """Test JSON depth validation"""
        # Valid shallow object
        shallow = {"a": {"b": {"c": 1}}}
        assert validate_json_depth(shallow) is True

        # Too deep (exceeds MAX_JSON_DEPTH = 20)
        def create_deep_json(depth):
            result = {"value": 1}
            for i in range(depth):
                result = {"nested": result}
            return result

        # Should fail for depth > 20
        with pytest.raises(ValueError, match="JSON depth exceeds maximum"):
            validate_json_depth(create_deep_json(25))

    def test_sanitize_string(self):
        """Test string sanitization"""
        # Null bytes removed
        assert sanitize_string("test\x00string") == "teststring"

        # Control characters removed
        assert sanitize_string("test\x01\x02string") == "teststring"

        # Newlines and tabs preserved
        assert sanitize_string("test\nstring\t") == "test\nstring\t"

        # Max length enforced
        long_string = "a" * 2000
        result = sanitize_string(long_string, max_length=100)
        assert len(result) == 100

    def test_validate_api_key_format(self):
        """Test API key format validation"""
        # Valid API keys
        assert validate_api_key_format("sk-" + "a" * 30) is True
        assert validate_api_key_format("pk-" + "b" * 40) is True

        # Too short
        with pytest.raises(ValueError, match="length invalid"):
            validate_api_key_format("short")

        # Too long
        with pytest.raises(ValueError, match="length invalid"):
            validate_api_key_format("a" * 200)

        # Invalid characters
        with pytest.raises(ValueError, match="invalid characters"):
            validate_api_key_format("sk-test@key#invalid!")

    def test_validate_endpoint_path(self):
        """Test endpoint path validation"""
        # Valid paths
        assert validate_endpoint_path("/api/v1/chat") is True
        assert validate_endpoint_path("/health") is True

        # Path traversal attempts
        with pytest.raises(ValueError, match="dangerous pattern"):
            validate_endpoint_path("/api/../etc/passwd")

        with pytest.raises(ValueError, match="dangerous pattern"):
            validate_endpoint_path("/api//admin")

        # Must start with /
        with pytest.raises(ValueError, match="must start with"):
            validate_endpoint_path("api/test")

    def test_sanitize_filename(self):
        """Test filename sanitization"""
        # Path separators removed
        assert sanitize_filename("../../etc/passwd") == ".._.._ etc_passwd"

        # Null bytes removed
        assert sanitize_filename("test\x00.txt") == "test.txt"

        # Special characters replaced
        assert sanitize_filename("test<>|.txt") == "test___.txt"

        # Hidden files prevented
        assert sanitize_filename(".hidden") == "__hidden"

        # Empty names handled
        assert sanitize_filename("") == "unnamed_file"

    def test_validate_ip_address(self):
        """Test IP address validation"""
        # Valid IPv4
        assert validate_ip_address("192.168.1.1") is True
        assert validate_ip_address("10.0.0.1") is True

        # Valid IPv6
        assert validate_ip_address("::1") is True
        assert validate_ip_address("2001:db8::1") is True

        # Invalid
        with pytest.raises(ValueError, match="Invalid IP address"):
            validate_ip_address("999.999.999.999")

        with pytest.raises(ValueError, match="Invalid IP address"):
            validate_ip_address("not_an_ip")

    def test_validate_port_number(self):
        """Test port number validation"""
        # Valid ports
        assert validate_port_number(80) is True
        assert validate_port_number(8443) is True
        assert validate_port_number(65535) is True

        # Invalid ports
        with pytest.raises(ValueError, match="out of range"):
            validate_port_number(0)

        with pytest.raises(ValueError, match="out of range"):
            validate_port_number(99999)

        # Type check
        with pytest.raises(TypeError, match="must be an integer"):
            validate_port_number("8080")

    def test_sanitize_log_message(self):
        """Test log message sanitization"""
        # Newlines escaped
        assert sanitize_log_message("line1\nline2") == "line1\\nline2"
        assert sanitize_log_message("line1\rline2") == "line1\\rline2"

        # ANSI codes removed
        ansi_text = "\x1b[31mRed Text\x1b[0m"
        assert "\x1b" not in sanitize_log_message(ansi_text)

    def test_input_validator_proxy_request(self):
        """Test complete proxy request validation"""
        validator = InputValidator()

        # Valid request
        body = {"prompt": "test"}
        headers = {"content-type": "application/json"}
        path = "/v1/chat/completions"

        assert validator.validate_proxy_request(body, headers, path) is True

        # Invalid path
        with pytest.raises(ValueError):
            validator.validate_proxy_request(
                body, headers, "/../../etc/passwd"
            )

    def test_input_validator_api_response(self):
        """Test API response validation"""
        validator = InputValidator()

        # Valid response
        response = {"id": "123", "object": "chat.completion"}
        assert validator.validate_api_response(response, dict) is True

        # Type mismatch
        with pytest.raises(ValueError, match="type mismatch"):
            validator.validate_api_response("string", dict)


class TestTLSConfiguration:
    """Test TLS/SSL configuration"""

    @pytest.fixture
    def temp_cert_files(self):
        """Create temporary certificate files for testing"""
        # Note: These are dummy files for testing structure only
        # Real tests would use actual certificates
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_file = Path(tmpdir) / "test.crt"
            key_file = Path(tmpdir) / "test.key"

            # Create placeholder files
            cert_file.write_text("DUMMY CERT")
            key_file.write_text("DUMMY KEY")

            yield cert_file, key_file

    def test_tls_profile_enum(self):
        """Test TLS profile enumeration"""
        assert TLSProfile.MODERN.value == "modern"
        assert TLSProfile.INTERMEDIATE.value == "intermediate"
        assert TLSProfile.OLD.value == "old"

    def test_get_cipher_suites(self):
        """Test cipher suite retrieval"""
        # Modern profile
        modern_ciphers = get_cipher_suites(TLSProfile.MODERN)
        assert len(modern_ciphers) > 0
        assert "TLS_AES_256_GCM_SHA384" in modern_ciphers

        # Intermediate profile
        intermediate_ciphers = get_cipher_suites(TLSProfile.INTERMEDIATE)
        assert len(intermediate_ciphers) > len(modern_ciphers)
        assert "ECDHE-RSA-AES128-GCM-SHA256" in intermediate_ciphers

    def test_validate_certificate_missing_files(self):
        """Test certificate validation with missing files"""
        cert_file = Path("/nonexistent/cert.pem")
        key_file = Path("/nonexistent/key.pem")

        # Should return False for missing files
        assert validate_certificate(cert_file, key_file) is False

    def test_create_ssl_context_missing_cert(self):
        """Test SSL context creation with missing certificate"""
        cert_file = Path("/nonexistent/cert.pem")
        key_file = Path("/nonexistent/key.pem")

        with pytest.raises(FileNotFoundError):
            create_ssl_context(cert_file, key_file)


class TestSecurityIntegration:
    """Integration tests for security features"""

    def test_middleware_stack_order(self):
        """Test that security middlewares are applied in correct order"""
        # This would require a running FastAPI app
        # Placeholder for integration test
        pass

    def test_rate_limit_with_csrf(self):
        """Test rate limiting works with CSRF protection"""
        # Integration test placeholder
        pass

    def test_all_security_headers_present(self):
        """Test that all security headers are present in responses"""
        # Integration test placeholder
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
