"""
YORI Block Page Rendering

Renders user-friendly block pages when requests are denied by policy.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

from yori.enforcement import EnforcementDecision


# Template directory
TEMPLATE_DIR = Path(__file__).parent / "templates"

# Initialize Jinja2 environment
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)


# Custom messages per policy
CUSTOM_MESSAGES = {
    "bedtime.rego": "LLM access is restricted after bedtime. Please try again tomorrow morning.",
    "privacy.rego": "This request may contain sensitive information. Please review your prompt.",
    "rate_limit.rego": "You've exceeded your request limit. Please wait before trying again.",
    "content_filter.rego": "Your request was flagged by content filters. Please modify your prompt.",
}


def render_block_page(
    decision: EnforcementDecision,
    custom_message: Optional[str] = None
) -> str:
    """
    Render a block page HTML from an enforcement decision.

    Args:
        decision: The enforcement decision containing block details
        custom_message: Optional custom message to display (overrides default)

    Returns:
        HTML string for the block page

    Raises:
        ValueError: If decision indicates request should not be blocked
    """
    if not decision.should_block:
        raise ValueError("Cannot render block page for allowed request")

    # Get custom message for this policy if not provided
    if custom_message is None:
        custom_message = CUSTOM_MESSAGES.get(decision.policy_name, "")

    # Format timestamp for display
    timestamp_str = decision.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    # Load and render template
    template = jinja_env.get_template("block_page.html")
    html = template.render(
        policy_name=decision.policy_name,
        reason=decision.reason,
        timestamp=timestamp_str,
        request_id=decision.request_id,
        allow_override=decision.allow_override,
        custom_message=custom_message,
    )

    return html


def get_custom_message(policy_name: str) -> Optional[str]:
    """
    Get the custom message for a specific policy.

    Args:
        policy_name: The name of the policy

    Returns:
        Custom message string or None if no custom message exists
    """
    return CUSTOM_MESSAGES.get(policy_name)


def add_custom_message(policy_name: str, message: str) -> None:
    """
    Add or update a custom message for a policy.

    Args:
        policy_name: The name of the policy
        message: The custom message to display
    """
    CUSTOM_MESSAGES[policy_name] = message


def remove_custom_message(policy_name: str) -> None:
    """
    Remove a custom message for a policy.

    Args:
        policy_name: The name of the policy
    """
    CUSTOM_MESSAGES.pop(policy_name, None)
