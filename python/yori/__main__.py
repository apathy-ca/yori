#!/usr/bin/env python3
"""
YORI HTTP/HTTPS Proxy Server

CLI entry point for running YORI as a reverse proxy with LLM policy enforcement.

Usage:
    python -m yori [OPTIONS]

Examples:
    # Run with default settings
    python -m yori

    # Run with custom config
    python -m yori --config /etc/yori/yori.conf

    # Run with custom TLS certificates
    python -m yori --cert /path/to/cert.pem --key /path/to/key.pem

    # Run in HTTP mode for testing (no TLS)
    python -m yori --no-tls --port 8080

    # Run with debug logging
    python -m yori --log-level DEBUG
"""

import argparse
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

import uvicorn

from yori.config import YoriConfig
from yori.proxy import ProxyServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name}, shutting down gracefully...")
    shutdown_requested = True
    sys.exit(0)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="YORI HTTP/HTTPS Proxy Server - Zero-trust LLM governance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to YORI configuration file (YAML format)"
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host to bind to (default: from config or 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to listen on (default: from config or 8443)"
    )
    parser.add_argument(
        "--cert",
        type=Path,
        help="Path to TLS certificate file (PEM format)"
    )
    parser.add_argument(
        "--key",
        type=Path,
        help="Path to TLS private key file (PEM format)"
    )
    parser.add_argument(
        "--no-tls",
        action="store_true",
        help="Run without TLS (HTTP only, for testing)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="YORI 0.2.0"
    )

    return parser.parse_args()


def load_configuration(config_path: Optional[Path]) -> YoriConfig:
    """Load YORI configuration from file or defaults"""
    if config_path:
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)

        logger.info(f"Loading configuration from {config_path}")
        try:
            config = YoriConfig.from_yaml(config_path)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)
    else:
        logger.info("Loading configuration from default locations")
        try:
            config = YoriConfig.from_default_locations()
        except Exception as e:
            logger.warning(f"Could not load default config: {e}")
            logger.info("Using built-in defaults")
            config = YoriConfig()

    return config


def main():
    """Main entry point"""
    args = parse_args()

    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    logger.debug(f"Command line arguments: {args}")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Load configuration
    logger.info("Loading YORI configuration...")
    config = load_configuration(args.config)

    # Initialize proxy server
    logger.info("Initializing proxy server...")
    try:
        proxy = ProxyServer(config)
    except Exception as e:
        logger.error(f"Failed to initialize proxy server: {e}", exc_info=True)
        sys.exit(1)

    # Determine listen address
    if config.listen:
        # Parse from config (format: "host:port")
        try:
            host, port_str = config.listen.rsplit(":", 1)
            port = int(port_str)
        except ValueError:
            logger.error(f"Invalid listen address in config: {config.listen}")
            sys.exit(1)
    else:
        host = "0.0.0.0"
        port = 8443

    # Override with command line arguments
    if args.host:
        host = args.host
    if args.port:
        port = args.port

    # Determine TLS configuration
    ssl_keyfile = None
    ssl_certfile = None

    if not args.no_tls:
        # Try command line args first
        if args.cert and args.key:
            ssl_certfile = str(args.cert)
            ssl_keyfile = str(args.key)

            if not args.cert.exists():
                logger.error(f"Certificate file not found: {args.cert}")
                sys.exit(1)
            if not args.key.exists():
                logger.error(f"Key file not found: {args.key}")
                sys.exit(1)
        # Fall back to config
        elif hasattr(config, 'proxy') and hasattr(config.proxy, 'tls_cert'):
            ssl_certfile = config.proxy.tls_cert
            ssl_keyfile = config.proxy.tls_key

        if not ssl_certfile or not ssl_keyfile:
            logger.warning("TLS certificate/key not provided, running in HTTP mode")
            logger.warning("This is insecure! Use --cert and --key for production.")

    # Log startup information
    protocol = "https" if ssl_certfile and ssl_keyfile else "http"
    logger.info("=" * 80)
    logger.info(f"Starting YORI proxy server")
    logger.info(f"  URL: {protocol}://{host}:{port}")
    logger.info(f"  Mode: {config.mode}")
    if config.enforcement and config.enforcement.enabled:
        logger.info(f"  Enforcement: ACTIVE")
        logger.info(f"  Consent: {config.enforcement.consent_accepted}")
    else:
        logger.info(f"  Enforcement: Disabled")
    logger.info("=" * 80)

    # Start server
    try:
        uvicorn.run(
            proxy.app,
            host=host,
            port=port,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            log_level=args.log_level.lower(),
            access_log=True,
        )
    except KeyboardInterrupt:
        logger.info("Shutdown requested via keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("YORI proxy server stopped")


if __name__ == "__main__":
    main()
