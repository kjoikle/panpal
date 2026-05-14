"""
A/B Testing Proxy Middleware

Proxies A/B test assignment and impression logging to the analytics service.
Gracefully degrades if the analytics service is unreachable — request.ab_tests
will be empty and templates fall through to default behavior.
"""
import json
import logging

import requests
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class ABTestAssignmentProxyMiddleware(MiddlewareMixin):
    """
    Proxy middleware that calls the analytics service to get/create
    A/B test variant assignments for authenticated users.

    Populates request.ab_tests with the same structure as the original
    monolith middleware so templates and context processors work unchanged.
    """

    def process_request(self, request):
        request.ab_tests = {}
        request.ab_tests_applicable = set()

        if not request.user.is_authenticated:
            return None

        try:
            resp = requests.post(
                f'{settings.ANALYTICS_SERVICE_URL}/api/v1/assignments/get-or-create/',
                json={
                    'user_id': request.user.id,
                    'path': request.path,
                },
                headers={'X-Internal-Service-Key': settings.INTERNAL_SERVICE_KEY},
                timeout=settings.ANALYTICS_TIMEOUT,
            )

            if resp.status_code == 200:
                data = resp.json()
                request.ab_tests = data.get('assignments', {})
                request.ab_tests_applicable = set(data.get('applicable_tests', []))
            else:
                logger.warning(
                    'Analytics service returned %s for assignments',
                    resp.status_code
                )
        except requests.RequestException as e:
            logger.warning('Analytics service unreachable for assignments: %s', e)

        return None


class ABTestImpressionProxyMiddleware(MiddlewareMixin):
    """
    Proxy middleware that calls the analytics service to bulk log
    impression events after successful page views.
    """

    def process_response(self, request, response):
        if response.status_code != 200:
            return response

        applicable = getattr(request, 'ab_tests_applicable', set())
        if not applicable:
            return response

        if not request.user.is_authenticated:
            return response

        impressions = []
        for test_name in applicable:
            test_data = request.ab_tests.get(test_name)
            if test_data:
                impressions.append({
                    'user_id': request.user.id,
                    'test_name': test_name,
                    'variant_id': test_data['variant_id'],
                    'path': request.path,
                })

        if not impressions:
            return response

        try:
            requests.post(
                f'{settings.ANALYTICS_SERVICE_URL}/api/v1/impressions/bulk/',
                json={'impressions': impressions},
                headers={'X-Internal-Service-Key': settings.INTERNAL_SERVICE_KEY},
                timeout=settings.ANALYTICS_TIMEOUT,
            )
        except requests.RequestException as e:
            logger.warning('Analytics service unreachable for impressions: %s', e)

        return response
