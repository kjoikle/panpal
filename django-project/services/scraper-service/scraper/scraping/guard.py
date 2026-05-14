"""
Lakera Guard wrapper for prompt injection detection in the scraper service.

Checks webpage visible text against the Lakera Guard API before forwarding it
to the LLM parser. Returns True if input is safe, False if flagged.
Fails open on API errors so a guard outage does not block all recipe imports.

Webpage text is truncated to _MAX_GUARD_CHARS before the API call: injection
payloads appear in prominent visible text, not buried in boilerplate content,
so truncating to the first 10k characters covers the realistic attack surface
while avoiding oversized API payloads.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

_LAKERA_API_URL = "https://api.lakera.ai/v2/guard"
_TIMEOUT_SECONDS = 5
_MAX_GUARD_CHARS = 10_000


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
            json={"messages": [{"role": "user", "content": text[:_MAX_GUARD_CHARS]}]},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        flagged = response.json().get("flagged", False)
        if flagged:
            logger.warning("Lakera Guard flagged scraped page text as prompt injection")
        return not flagged
    except requests.Timeout:
        logger.error("Lakera Guard API timed out — allowing scraper input through")
        return True
    except requests.RequestException as exc:
        logger.error("Lakera Guard API error: %s — allowing scraper input through", exc)
        return True
