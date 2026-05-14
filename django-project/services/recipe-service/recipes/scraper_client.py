from __future__ import annotations

"""
Client for calling the scraper microservice.

Mirrors the pattern used by abtest_proxy.py for the analytics service.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SCRAPER_TIMEOUT = 90  # scraping can be slow; LLM fallback adds significant latency


def scrape_url(url: str) -> dict | None:
    """
    POST the given URL to the scraper service and return the parsed recipe dict.

    Returns None if the scraper service is unreachable or returns an error,
    so callers can degrade gracefully.
    """
    scraper_url = getattr(settings, 'SCRAPER_SERVICE_URL', 'http://localhost:8002')
    try:
        response = requests.post(
            f'{scraper_url}/api/v1/scrape/',
            json={'url': url},
            headers={'X-Internal-Service-Key': settings.INTERNAL_SERVICE_KEY},
            timeout=SCRAPER_TIMEOUT,
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning('Scraper service returned %s for %s', response.status_code, url)
            return None
    except requests.RequestException as e:
        logger.warning('Scraper service unreachable: %s', e)
        return None
