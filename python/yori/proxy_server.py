#!/usr/bin/env python3
"""
YORI Proxy Server - Standalone Entry Point with TLS Support

Enhanced proxy server entry point with TLS/HTTPS support and enforcement integration.
This extends the basic proxy with certificate configuration and CLI arguments.
"""

import sys
import logging
import argparse
from pathlib import Path
from typing import Optional

# Add python directory to path if running directly
if __name__ == "__main__":
    repo_root = Path(__file__).parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

import uvicorn
from yori.config import YoriConfig
from yori.proxy import ProxyServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="YORI LLM Gateway Proxy Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default configuration
  python proxy_server.py

  # Start with custom config file
  python proxy_server.py --config /etc/yori/yori.conf

  # Start with custom TLS certificates
  python proxy_server.py --cert /path/to/cert.pem --key /path/to/key.pem

  # Start on custom host and port
  python proxy_server.py --host 127.0.0.1 --port 9443
        """,
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to YORI configuration file (YAML format)",
    )
    parser.add_argument(
        "--cert",
        type=Path,
        help="Path to TLS certificate file (overrides config)",
    )
    parser.add_argument(
        "--key",
        type=Path,
        help="Path to TLS private key file (overrides config)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host to bind to (overrides config, default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to listen on (overrides config, default: 8443)",
    )
    parser.add_argument(
        "--no-tls",
        action="store_true",
        help="Disable TLS and run HTTP only (for testing)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    return parser.parse_args()


def main():
    """Start the YORI proxy server with TLS support"""
    args = parse_args()

    # Update logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Load configuration
    if args.config:
        if not args.config.exists():
            logger.error(f"Configuration file not found: {args.config}")
            sys.exit(1)
        logger.info(f"Loading configuration from {args.config}")
        config = YoriConfig.from_yaml(args.config)
    else:
        logger.info("Using default configuration (no config file specified)")
        config = YoriConfig.from_default_locations()

    # Create proxy server
    proxy = ProxyServer(config)

    # Register startup/shutdown events
    @proxy.app.on_event("startup")
    async def startup_event():
        await proxy.startup()

    @proxy.app.on_event("shutdown")
    async def shutdown_event():
        await proxy.shutdown()

    # Parse listen address from config or arguments
    if args.host and args.port:
        host = args.host
        port = args.port
    elif args.host:
        host = args.host
        _, port_str = config.listen.rsplit(":", 1)
        port = int(port_str)
    elif args.port:
        host, _ = config.listen.rsplit(":", 1)
        port = args.port
    else:
        host, port_str = config.listen.rsplit(":", 1)
        port = int(port_str)

    # Determine TLS certificate paths
    ssl_keyfile: Optional[Path] = None
    ssl_certfile: Optional[Path] = None

    if not args.no_tls:
        # Priority: CLI args > config > None
        ssl_certfile = args.cert or config.proxy.tls_cert
        ssl_keyfile = args.key or config.proxy.tls_key

        # Validate certificate files exist
        if ssl_certfile and not ssl_certfile.exists():
            logger.warning(f"TLS certificate not found: {ssl_certfile}")
            logger.warning("TLS will be disabled. Generate a certificate or use --no-tls flag.")
            ssl_certfile = None
            ssl_keyfile = None

        if ssl_keyfile and not ssl_keyfile.exists():
            logger.warning(f"TLS key not found: {ssl_keyfile}")
            logger.warning("TLS will be disabled. Generate a key or use --no-tls flag.")
            ssl_certfile = None
            ssl_keyfile = None

    # Log startup information
    logger.info("=" * 80)
    logger.info("YORI LLM Gateway - Starting Proxy Server")
    logger.info("=" * 80)
    logger.info(f"Mode: {config.mode}")
    logger.info(f"Listen address: {host}:{port}")

    if ssl_certfile and ssl_keyfile:
        logger.info(f"TLS: ENABLED (HTTPS)")
        logger.info(f"  Certificate: {ssl_certfile}")
        logger.info(f"  Private key: {ssl_keyfile}")
        protocol = "https"
    else:
        logger.warning(f"TLS: DISABLED (HTTP only)")
        logger.warning("  ⚠️  Traffic is NOT encrypted")
        logger.warning("  ⚠️  Use --cert and --key to enable TLS")
        protocol = "http"

    logger.info(f"Enforcement: {'ENABLED' if (config.enforcement and config.enforcement.enabled) else 'DISABLED'}")
    logger.info(f"Endpoints: {len(config.endpoints)} configured")
    logger.info("")
    logger.info(f"Access the proxy at: {protocol}://{host if host != '0.0.0.0' else 'localhost'}:{port}")
    logger.info(f"Health check: {protocol}://{host if host != '0.0.0.0' else 'localhost'}:{port}/health")
    logger.info("=" * 80)
    logger.info("Press Ctrl+C to stop")
    logger.info("")

    # Run server with or without TLS
    uvicorn.run(
        proxy.app,
        host=host,
        port=port,
        ssl_keyfile=str(ssl_keyfile) if ssl_keyfile else None,
        ssl_certfile=str(ssl_certfile) if ssl_certfile else None,
        log_level=args.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
