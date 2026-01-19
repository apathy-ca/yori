"""
YORI Main Entry Point

This is the main entry point for the YORI service.
"""

import argparse
import logging
import sys
from pathlib import Path

import uvicorn

from yori.config import YoriConfig
from yori.proxy import ProxyServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="YORI - Zero-trust LLM governance for home networks")
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (default: /usr/local/etc/yori/yori.conf)",
    )
    parser.add_argument(
        "--host",
        type=str,
        help="Override listen host",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Override listen port",
    )

    args = parser.parse_args()

    # Load configuration
    if args.config:
        config = YoriConfig.from_yaml(args.config)
    else:
        config = YoriConfig.from_default_locations()

    # Create proxy server
    proxy = ProxyServer(config)

    # Parse listen address
    host, port = config.listen.rsplit(":", 1)
    port = int(port)

    # Override if specified
    if args.host:
        host = args.host
    if args.port:
        port = args.port

    logger.info(f"Starting YORI proxy on {host}:{port} (mode: {config.mode})")

    # Run server
    uvicorn.run(
        proxy.app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
