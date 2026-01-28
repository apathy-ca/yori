"""
YORI Proxy Request Handlers

Handlers for creating block responses and processing proxy requests.
"""

from fastapi import Request
from fastapi.responses import HTMLResponse
from datetime import datetime, timezone
import logging

from yori.models import EnforcementDecision, BlockDecision
from yori.block_page import render_block_page

logger = logging.getLogger(__name__)


async def create_block_response(
    request: Request,
    decision: EnforcementDecision,
    policy_name: str,
    request_id: str,
) -> HTMLResponse:
    """
    Create HTML block page response from enforcement decision.

    Args:
        request: Original FastAPI request
        decision: Enforcement decision with block reason
        policy_name: Name of the policy that triggered the block
        request_id: Unique request identifier

    Returns:
        HTMLResponse with block page HTML and 403 status
    """
    # Convert EnforcementDecision to BlockDecision for rendering
    block_decision = BlockDecision(
        should_block=True,
        policy_name=policy_name,
        reason=decision.reason,
        timestamp=datetime.now(timezone.utc),
        request_id=request_id,
        allow_override=True,  # Can be configured based on policy
        client_ip=request.client.host if request.client else "unknown",
        request_path=str(request.url.path),
    )

    # Render HTML block page
    try:
        html_content = render_block_page(block_decision)
    except Exception as e:
        logger.error(f"Failed to render block page: {e}")
        # Fallback to simple HTML if template rendering fails
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Request Blocked</title></head>
        <body>
            <h1>Request Blocked</h1>
            <p>Policy: {policy_name}</p>
            <p>Reason: {decision.reason}</p>
            <p>Request ID: {request_id}</p>
        </body>
        </html>
        """

    # Return HTML response with 403 status
    return HTMLResponse(
        content=html_content,
        status_code=403,
    )


async def get_body_preview(request: Request, max_bytes: int = 1024) -> str:
    """
    Extract first N bytes of request body for audit logging.

    Args:
        request: FastAPI request
        max_bytes: Maximum number of bytes to read (default 1024)

    Returns:
        String preview of request body or error message
    """
    try:
        body = await request.body()
        if not body:
            return ""

        if len(body) <= max_bytes:
            return body.decode('utf-8', errors='ignore')

        return body[:max_bytes].decode('utf-8', errors='ignore') + "..."
    except Exception as e:
        logger.warning(f"Failed to read request body for preview: {e}")
        return "<unable to read body>"
