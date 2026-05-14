"""
REST API views for the scraper service.

All endpoints require the X-Internal-Service-Key header.
"""
from __future__ import annotations

import json
import logging
from functools import wraps

import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .scraping.fetcher import fetch_html
from .scraping import parser as recipe_parser

logger = logging.getLogger(__name__)


def require_service_key(view_func):
    """Validate the internal service key header."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        key = request.headers.get('X-Internal-Service-Key', '')
        if key != settings.INTERNAL_SERVICE_KEY:
            return JsonResponse({'error': 'Forbidden'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


@csrf_exempt
@require_POST
@require_service_key
def scrape(request):
    """
    POST /api/v1/scrape/

    Accept a food blog URL and return structured recipe data.

    Request body:
        {"url": "https://example.com/recipe/pasta"}

    Response (200):
        {
            "title": "...",
            "description": "...",
            "recipe_author": "...",
            "source_url": "https://...",
            "image_url": "https://...",
            "ingredients": "1 cup flour\\n2 eggs",
            "prep_time": 15,
            "cook_time": 30,
            "steps": [{"step_number": 1, "instruction_text": "..."}],
            "tags": ["italian"],
            "extraction_method": "schema_org"
        }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    url = (data.get('url') or '').strip()
    if not url:
        return JsonResponse({'error': 'url is required'}, status=400)

    if not url.startswith(('http://', 'https://')):
        return JsonResponse({'error': 'url must start with http:// or https://'}, status=400)

    try:
        html = fetch_html(url)
    except requests.Timeout:
        return JsonResponse({'error': 'Request to target URL timed out'}, status=504)
    except requests.RequestException as e:
        logger.warning('Failed to fetch %s: %s', url, e)
        return JsonResponse({'error': f'Could not fetch URL: {e}'}, status=400)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)

    result = recipe_parser.parse(html, url=url)

    if result is None:
        return JsonResponse({'error': 'No recipe content found on this page'}, status=400)

    result['source_url'] = url

    return JsonResponse(result)


@require_GET
def health(request):
    """GET /api/v1/health/ — no auth required."""
    return JsonResponse({'status': 'ok'})
