"""
YORI TLS Configuration

Secure TLS/SSL configuration following Mozilla SSL Configuration Generator
recommendations and industry best practices.

Provides hardened SSL context with:
- TLS 1.2+ only (TLS 1.3 preferred)
- Strong cipher suites with perfect forward secrecy
- Secure protocol options
- Certificate validation
"""

import ssl
import logging
from pathlib import Path
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class TLSProfile(Enum):
    """
    TLS security profiles based on Mozilla recommendations.

    MODERN: TLS 1.3 only, strongest security (may break old clients)
    INTERMEDIATE: TLS 1.2+, balanced security and compatibility (recommended)
    OLD: TLS 1.0+, maximum compatibility (not recommended for production)
    """
    MODERN = "modern"
    INTERMEDIATE = "intermediate"
    OLD = "old"


# Cipher suites following Mozilla SSL Configuration Generator
# https://ssl-config.mozilla.org/

# Modern profile: TLS 1.3 ciphers only
MODERN_CIPHERS = [
    "TLS_AES_128_GCM_SHA256",
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
]

# Intermediate profile: TLS 1.2+ ciphers (recommended)
# Prioritizes forward secrecy (ECDHE) and authenticated encryption (GCM, CHACHA20)
INTERMEDIATE_CIPHERS = [
    # TLS 1.3 ciphers (preferred)
    "TLS_AES_128_GCM_SHA256",
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
    # TLS 1.2 ciphers with forward secrecy
    "ECDHE-ECDSA-AES128-GCM-SHA256",
    "ECDHE-RSA-AES128-GCM-SHA256",
    "ECDHE-ECDSA-AES256-GCM-SHA384",
    "ECDHE-RSA-AES256-GCM-SHA384",
    "ECDHE-ECDSA-CHACHA20-POLY1305",
    "ECDHE-RSA-CHACHA20-POLY1305",
    # Fallback for compatibility (still secure)
    "DHE-RSA-AES128-GCM-SHA256",
    "DHE-RSA-AES256-GCM-SHA384",
]

# Old profile: TLS 1.0+ (not recommended - for compatibility only)
OLD_CIPHERS = INTERMEDIATE_CIPHERS + [
    "ECDHE-ECDSA-AES128-SHA256",
    "ECDHE-RSA-AES128-SHA256",
    "ECDHE-ECDSA-AES256-SHA384",
    "ECDHE-RSA-AES256-SHA384",
]


def create_ssl_context(
    certfile: Path,
    keyfile: Path,
    profile: TLSProfile = TLSProfile.INTERMEDIATE,
    ca_certs: Optional[Path] = None,
    check_hostname: bool = False,
) -> ssl.SSLContext:
    """
    Create a hardened SSL context for TLS connections.

    Args:
        certfile: Path to TLS certificate file (PEM format)
        keyfile: Path to TLS private key file (PEM format)
        profile: TLS security profile (default: INTERMEDIATE)
        ca_certs: Optional path to CA certificates for client verification
        check_hostname: Enable hostname checking (for client connections)

    Returns:
        Configured SSLContext ready for use

    Raises:
        FileNotFoundError: If certificate or key files don't exist
        ssl.SSLError: If SSL context configuration fails
    """
    # Validate certificate and key files exist
    if not certfile.exists():
        raise FileNotFoundError(f"TLS certificate not found: {certfile}")
    if not keyfile.exists():
        raise FileNotFoundError(f"TLS private key not found: {keyfile}")

    # Create SSL context with secure defaults
    # Use PROTOCOL_TLS_SERVER for server sockets
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    # Set minimum TLS version based on profile
    if profile == TLSProfile.MODERN:
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        logger.info("TLS profile: MODERN (TLS 1.3 only)")
    elif profile == TLSProfile.INTERMEDIATE:
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        logger.info("TLS profile: INTERMEDIATE (TLS 1.2+)")
    else:  # OLD profile
        context.minimum_version = ssl.TLSVersion.TLSv1
        logger.warning(
            "TLS profile: OLD (TLS 1.0+) - Not recommended for production!"
        )

    # Configure cipher suites based on profile
    if profile == TLSProfile.MODERN:
        # TLS 1.3 doesn't use cipher suite strings the same way
        # Just ensure we're using TLS 1.3
        pass
    elif profile == TLSProfile.INTERMEDIATE:
        cipher_string = ":".join(INTERMEDIATE_CIPHERS)
        context.set_ciphers(cipher_string)
        logger.info(f"Configured {len(INTERMEDIATE_CIPHERS)} cipher suites")
    else:  # OLD profile
        cipher_string = ":".join(OLD_CIPHERS)
        context.set_ciphers(cipher_string)
        logger.info(f"Configured {len(OLD_CIPHERS)} cipher suites")

    # Load server certificate and private key
    try:
        context.load_cert_chain(
            certfile=str(certfile),
            keyfile=str(keyfile),
        )
        logger.info(f"Loaded certificate: {certfile}")
        logger.info(f"Loaded private key: {keyfile}")
    except ssl.SSLError as e:
        logger.error(f"Failed to load certificate/key: {e}")
        raise

    # Security options (following Mozilla recommendations)
    context.options |= ssl.OP_NO_SSLv2  # Disable SSL 2.0 (insecure)
    context.options |= ssl.OP_NO_SSLv3  # Disable SSL 3.0 (POODLE attack)
    context.options |= ssl.OP_NO_TLSv1  # Disable TLS 1.0 (weak)
    context.options |= ssl.OP_NO_TLSv1_1  # Disable TLS 1.1 (weak)
    context.options |= ssl.OP_NO_COMPRESSION  # Disable compression (CRIME attack)
    context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE  # Prefer server cipher order
    context.options |= ssl.OP_SINGLE_DH_USE  # Use ephemeral DH keys
    context.options |= ssl.OP_SINGLE_ECDH_USE  # Use ephemeral ECDH keys

    # Enable session tickets for performance (optional)
    # context.options |= ssl.OP_NO_TICKET  # Uncomment to disable session tickets

    # Configure certificate verification if CA certs provided
    if ca_certs:
        if not ca_certs.exists():
            logger.warning(f"CA certificates not found: {ca_certs}")
        else:
            context.load_verify_locations(cafile=str(ca_certs))
            context.verify_mode = ssl.CERT_REQUIRED
            context.check_hostname = check_hostname
            logger.info(f"Loaded CA certificates: {ca_certs}")

    # Set hostname checking
    context.check_hostname = check_hostname

    # Log final configuration
    logger.info("SSL context configured successfully")
    logger.info(f"  Minimum TLS version: {context.minimum_version.name}")
    logger.info(f"  Maximum TLS version: {context.maximum_version.name}")
    logger.info(f"  Check hostname: {context.check_hostname}")
    logger.info(f"  Verify mode: {context.verify_mode.name}")

    return context


def create_client_ssl_context(
    ca_certs: Optional[Path] = None,
    profile: TLSProfile = TLSProfile.INTERMEDIATE,
) -> ssl.SSLContext:
    """
    Create SSL context for outgoing client connections.

    Used when YORI proxy makes requests to upstream APIs.

    Args:
        ca_certs: Path to CA certificates bundle (uses system default if None)
        profile: TLS security profile

    Returns:
        Configured SSLContext for client connections
    """
    # Create client SSL context
    context = ssl.create_default_context()

    # Set minimum TLS version based on profile
    if profile == TLSProfile.MODERN:
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        logger.info("Client TLS profile: MODERN (TLS 1.3 only)")
    elif profile == TLSProfile.INTERMEDIATE:
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        logger.info("Client TLS profile: INTERMEDIATE (TLS 1.2+)")
    else:
        context.minimum_version = ssl.TLSVersion.TLSv1
        logger.warning("Client TLS profile: OLD (TLS 1.0+)")

    # Load custom CA certificates if provided
    if ca_certs and ca_certs.exists():
        context.load_verify_locations(cafile=str(ca_certs))
        logger.info(f"Loaded custom CA certificates: {ca_certs}")

    # Verify certificates by default
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED

    logger.info("Client SSL context configured")
    return context


def get_tls_info(ssl_object: ssl.SSLSocket) -> dict:
    """
    Get TLS connection information for monitoring/debugging.

    Args:
        ssl_object: Active SSL socket/connection

    Returns:
        Dictionary with TLS connection details
    """
    try:
        return {
            "version": ssl_object.version(),
            "cipher": ssl_object.cipher(),
            "compression": ssl_object.compression(),
            "peer_certificate": ssl_object.getpeercert(),
        }
    except Exception as e:
        logger.error(f"Failed to get TLS info: {e}")
        return {}


def validate_certificate(
    certfile: Path,
    keyfile: Path,
) -> bool:
    """
    Validate that certificate and key are valid and match.

    Args:
        certfile: Path to certificate file
        keyfile: Path to private key file

    Returns:
        True if certificate and key are valid and match
    """
    try:
        # Try to create SSL context - will fail if cert/key invalid
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(certfile), str(keyfile))
        logger.info("Certificate and key validation successful")
        return True
    except Exception as e:
        logger.error(f"Certificate validation failed: {e}")
        return False


def get_cipher_suites(profile: TLSProfile = TLSProfile.INTERMEDIATE) -> list:
    """
    Get list of cipher suites for a given profile.

    Args:
        profile: TLS security profile

    Returns:
        List of cipher suite names
    """
    if profile == TLSProfile.MODERN:
        return MODERN_CIPHERS.copy()
    elif profile == TLSProfile.INTERMEDIATE:
        return INTERMEDIATE_CIPHERS.copy()
    else:
        return OLD_CIPHERS.copy()


# Recommended TLS configuration for YORI
RECOMMENDED_TLS_CONFIG = {
    "profile": TLSProfile.INTERMEDIATE,
    "min_version": "TLS 1.2",
    "ciphers": "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM",
    "options": [
        "no_sslv2",
        "no_sslv3",
        "no_tlsv1",
        "no_tlsv1_1",
        "no_compression",
        "cipher_server_preference",
        "single_dh_use",
        "single_ecdh_use",
    ],
}
