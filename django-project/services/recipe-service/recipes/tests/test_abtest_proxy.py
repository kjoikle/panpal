"""Tests for A/B test proxy middleware and proxied ab_test_event view."""
import json
import logging
from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse
from django.urls import reverse

from recipes.middleware.abtest_proxy import (
    ABTestAssignmentProxyMiddleware,
    ABTestImpressionProxyMiddleware,
)
from recipes.context_processors import ab_tests as ab_tests_context_processor


ANALYTICS_SETTINGS = {
    'ANALYTICS_SERVICE_URL': 'http://analytics:8001',
    'INTERNAL_SERVICE_KEY': 'test-key',
    'ANALYTICS_TIMEOUT': 2,
}


class ABTestAssignmentProxyMiddlewareTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = ABTestAssignmentProxyMiddleware(get_response=lambda r: HttpResponse())
        self.user = User.objects.create_user(username='testuser', password='testpass')

    def test_skips_anonymous_users(self):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        self.middleware.process_request(request)
        self.assertEqual(request.ab_tests, {})
        self.assertEqual(request.ab_tests_applicable, set())

    @override_settings(**ANALYTICS_SETTINGS)
    @patch('recipes.middleware.abtest_proxy.requests.post')
    def test_populates_ab_tests_on_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'assignments': {
                'homepage_create_recipe_btn': {
                    'variant_id': 'control',
                    'config': {'button_text': 'Create Recipe'},
                    'test_config': {'name': 'homepage_create_recipe_btn'},
                }
            },
            'applicable_tests': ['homepage_create_recipe_btn'],
        }
        mock_post.return_value = mock_response

        request = self.factory.get('/')
        request.user = self.user
        self.middleware.process_request(request)

        self.assertIn('homepage_create_recipe_btn', request.ab_tests)
        self.assertEqual(
            request.ab_tests['homepage_create_recipe_btn']['variant_id'],
            'control'
        )
        self.assertIn('homepage_create_recipe_btn', request.ab_tests_applicable)

        # Verify the correct API call was made
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        self.assertIn('user_id', json.loads(call_kwargs[1]['json'] if isinstance(call_kwargs[1].get('json'), str) else json.dumps(call_kwargs[1]['json'])))

    @override_settings(**ANALYTICS_SETTINGS)
    @patch('recipes.middleware.abtest_proxy.requests.post')
    def test_graceful_degradation_on_timeout(self, mock_post):
        import requests as req_lib
        mock_post.side_effect = req_lib.Timeout('Connection timed out')

        request = self.factory.get('/')
        request.user = self.user
        self.middleware.process_request(request)

        # Should degrade gracefully — empty ab_tests
        self.assertEqual(request.ab_tests, {})
        self.assertEqual(request.ab_tests_applicable, set())

    @override_settings(**ANALYTICS_SETTINGS)
    @patch('recipes.middleware.abtest_proxy.requests.post')
    def test_graceful_degradation_on_connection_error(self, mock_post):
        import requests as req_lib
        mock_post.side_effect = req_lib.ConnectionError('Connection refused')

        request = self.factory.get('/')
        request.user = self.user
        self.middleware.process_request(request)

        self.assertEqual(request.ab_tests, {})

    @override_settings(**ANALYTICS_SETTINGS)
    @patch('recipes.middleware.abtest_proxy.requests.post')
    def test_graceful_degradation_on_non_200(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        request = self.factory.get('/')
        request.user = self.user
        self.middleware.process_request(request)

        self.assertEqual(request.ab_tests, {})


class ABTestImpressionProxyMiddlewareTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = ABTestImpressionProxyMiddleware(get_response=lambda r: HttpResponse())
        self.user = User.objects.create_user(username='testuser', password='testpass')

    @override_settings(**ANALYTICS_SETTINGS)
    @patch('recipes.middleware.abtest_proxy.requests.post')
    def test_logs_impressions_on_200(self, mock_post):
        request = self.factory.get('/')
        request.user = self.user
        request.ab_tests = {
            'homepage_test': {'variant_id': 'control', 'config': {}}
        }
        request.ab_tests_applicable = {'homepage_test'}

        response = HttpResponse(status=200)
        self.middleware.process_response(request, response)

        mock_post.assert_called_once()

    def test_skips_non_200_responses(self):
        request = self.factory.get('/')
        request.user = self.user
        request.ab_tests = {'homepage_test': {'variant_id': 'control', 'config': {}}}
        request.ab_tests_applicable = {'homepage_test'}

        response = HttpResponse(status=404)
        result = self.middleware.process_response(request, response)
        self.assertEqual(result.status_code, 404)

    def test_skips_anonymous_users(self):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        request.ab_tests = {}
        request.ab_tests_applicable = set()

        response = HttpResponse(status=200)
        result = self.middleware.process_response(request, response)
        self.assertEqual(result, response)

    @override_settings(**ANALYTICS_SETTINGS)
    @patch('recipes.middleware.abtest_proxy.requests.post')
    def test_graceful_degradation_on_error(self, mock_post):
        import requests as req_lib
        mock_post.side_effect = req_lib.ConnectionError('refused')

        request = self.factory.get('/')
        request.user = self.user
        request.ab_tests = {'homepage_test': {'variant_id': 'control', 'config': {}}}
        request.ab_tests_applicable = {'homepage_test'}

        response = HttpResponse(status=200)
        # Should not raise
        result = self.middleware.process_response(request, response)
        self.assertEqual(result, response)


class ABTestsContextProcessorTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_returns_empty_when_no_ab_tests(self):
        request = self.factory.get('/')
        request.ab_tests = {}
        context = ab_tests_context_processor(request)
        self.assertEqual(context['ab_tests'], {})
        self.assertEqual(context['ab_tests_json'], '{}')

    def test_returns_simplified_ab_tests(self):
        request = self.factory.get('/')
        request.ab_tests = {
            'test_name': {
                'variant_id': 'control',
                'config': {'button_text': 'Click Me'},
                'test_config': {'name': 'test_name'},
            }
        }
        context = ab_tests_context_processor(request)
        self.assertIn('test_name', context['ab_tests'])
        self.assertEqual(context['ab_tests']['test_name']['variant_id'], 'control')
        self.assertNotIn('test_config', context['ab_tests']['test_name'])

    def test_handles_missing_ab_tests_attribute(self):
        request = self.factory.get('/')
        context = ab_tests_context_processor(request)
        self.assertEqual(context['ab_tests'], {})


@override_settings(**ANALYTICS_SETTINGS)
class ABTestEventProxyViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.url = reverse('ab_test_event')

    def test_requires_authentication(self):
        response = self.client.post(
            self.url,
            data=json.dumps({'test_name': 'test', 'variant_id': 'c', 'event_type': 'click'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)

    def test_requires_post(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    @patch('requests.post')
    def test_proxies_to_analytics_service(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'assignments': {}, 'applicable_tests': []}
        mock_post.return_value = mock_response

        self.client.login(username='testuser', password='testpass')
        response = self.client.post(
            self.url,
            data=json.dumps({
                'test_name': 'homepage_test',
                'variant_id': 'control',
                'event_type': 'create_recipe_click'
            }),
            content_type='application/json',
            HTTP_REFERER='http://testserver/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        # Should have been called twice: once by middleware, once by view
        self.assertEqual(mock_post.call_count, 2)
        # Second call should be to events endpoint
        event_call = mock_post.call_args_list[1]
        self.assertIn('/api/v1/events/', event_call[0][0])

    @patch('requests.post')
    def test_returns_503_when_analytics_unavailable(self, mock_post):
        import requests as req_lib
        mock_post.side_effect = req_lib.ConnectionError('refused')

        self.client.login(username='testuser', password='testpass')
        # Disable logging to avoid Django/Python 3.14 copy() bug in error reporter
        logging.disable(logging.CRITICAL)
        try:
            response = self.client.post(
                self.url,
                data=json.dumps({
                    'test_name': 'homepage_test',
                    'variant_id': 'control',
                    'event_type': 'click'
                }),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 503)
        finally:
            logging.disable(logging.NOTSET)

    def test_invalid_json(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(
            self.url,
            data='not json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_required_fields(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(
            self.url,
            data=json.dumps({'test_name': 'test'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
