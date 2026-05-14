"""
HTTP fetcher for the scraper service.

Fetches raw HTML from a given URL with a browser-like User-Agent
to reduce the chance of being blocked by simple bot detection.
"""
import requests
from django.conf import settings


FETCH_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def fetch_html(url: str) -> str:
    """
    Fetch HTML content from url.

    Returns the decoded text body on success.
    Raises requests.RequestException on network/timeout errors.
    Raises ValueError if the response is not HTML.
    """
    timeout = getattr(settings, 'SCRAPER_FETCH_TIMEOUT', 10)
    response = requests.get(url, headers=FETCH_HEADERS, timeout=timeout, allow_redirects=True)
    response.raise_for_status()

    content_type = response.headers.get('Content-Type', '')
    if 'html' not in content_type:
        raise ValueError(f'Expected HTML content, got: {content_type}')

    return response.text
