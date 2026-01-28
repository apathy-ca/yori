#!/usr/bin/env python3
"""
YORI Proxy Server - Standalone Entry Point

Simple standalone script to start the YORI proxy server.
This is a convenience wrapper around the main entry point.
"""

import sys
import logging
from pathlib import Path

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


def main():
    """Start the YORI proxy server with default configuration"""
    # Load configuration (uses defaults if no config file found)
    config = YoriConfig()

    # Create proxy server
    proxy = ProxyServer(config)

    # Parse listen address
    host, port = config.listen.rsplit(":", 1)
    port = int(port)

    logger.info(f"Starting YORI proxy on {host}:{port} (mode: {config.mode})")
    logger.info("Press Ctrl+C to stop")

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
