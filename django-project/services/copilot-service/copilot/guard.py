"""
Lakera Guard wrapper for prompt injection detection in the copilot service.

Checks user input against the Lakera Guard API before forwarding it to the LLM.
Returns True if input is safe, False if a prompt injection attempt is detected.
Fails open on API errors so a guard outage does not break the copilot for all users.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

_LAKERA_API_URL = "https://api.lakera.ai/v2/guard"
_TIMEOUT_SECONDS = 5


def is_safe(text: str) -> bool:
    """Return True if the text passes the Lakera Guard prompt injection check."""
    api_key = os.getenv("LAKERA_GUARD_API_KEY", "")
    if not api_key:
        logger.warning("LAKERA_GUARD_API_KEY not set — skipping guard check")
        return True

    try:
        response = requests.post(
            _LAKERA_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"messages": [{"role": "user", "content": text}]},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        flagged = response.json().get("flagged", False)
        if flagged:
            logger.warning("Lakera Guard flagged copilot user input as prompt injection")
        return not flagged
    except requests.Timeout:
        logger.error("Lakera Guard API timed out — allowing copilot input through")
        return True
    except requests.RequestException as exc:
        logger.error("Lakera Guard API error: %s — allowing copilot input through", exc)
        return True
