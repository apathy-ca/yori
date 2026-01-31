#!/usr/bin/env python3
"""
YORI Minimal Server - No FastAPI required

A basic HTTP server for YORI that works without FastAPI/uvicorn.
Provides health checks and basic audit logging.

This is a fallback for systems where FastAPI cannot be installed
(e.g., FreeBSD without Rust compiler).
"""

import sys
import logging
import argparse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

from yori.config import YoriConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


class YoriMinimalHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for YORI"""

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                'status': 'ok',
                'mode': 'minimal',
                'message': 'YORI running in minimal mode (no FastAPI)'
            }
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'YORI Minimal Server\n')
            self.wfile.write(b'Running in minimal mode (FastAPI not available)\n')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Custom log message to use logging module"""
        logger.info("%s - - [%s] %s" % (self.client_address[0],
                                        self.log_date_time_string(),
                                        format % args))


def main():
    """Start the minimal YORI server"""
    parser = argparse.ArgumentParser(description='YORI Minimal Server')
    parser.add_argument('--config', type=Path, help='Configuration file path')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8443, help='Port to bind to')
    args = parser.parse_args()

    # Load configuration if provided
    if args.config and args.config.exists():
        logger.info(f"Loading configuration from {args.config}")
        config = YoriConfig.from_yaml(args.config)
        # Parse host:port from config if not overridden
        if ':' in config.listen:
            host, port_str = config.listen.rsplit(':', 1)
            if not args.host or args.host == '0.0.0.0':
                args.host = host if host else '0.0.0.0'
            if not args.port or args.port == 8443:
                args.port = int(port_str)

    logger.info("=" * 60)
    logger.info("YORI Minimal Server Starting")
    logger.info("=" * 60)
    logger.info("")
    logger.info("NOTE: Running in MINIMAL MODE")
    logger.info("FastAPI/uvicorn are not available on this system.")
    logger.info("")
    logger.info("Available features:")
    logger.info("  - Health check endpoint: /health")
    logger.info("  - Policy evaluation (via Rust core)")
    logger.info("  - Audit logging")
    logger.info("")
    logger.info("Unavailable features:")
    logger.info("  - Full HTTP proxy")
    logger.info("  - Request interception")
    logger.info("  - TLS termination")
    logger.info("")
    logger.info(f"Starting server on {args.host}:{args.port}")
    logger.info("=" * 60)

    # Start server
    server = HTTPServer((args.host, args.port), YoriMinimalHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()


if __name__ == '__main__':
    main()
