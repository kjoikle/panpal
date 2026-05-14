"""Tests for analytics service REST API views."""
import json

from django.test import TestCase, override_settings
from django.urls import reverse

from analytics.models import ABTestAssignment, ABTestEvent
from analytics.services import reload_tests_config

SERVICE_KEY = 'test-service-key'


@override_settings(INTERNAL_SERVICE_KEY=SERVICE_KEY)
class ServiceKeyAuthTests(TestCase):

    def test_missing_key_returns_403(self):
        response = self.client.get(reverse('assignments_list') + '?user_id=1')
        self.assertEqual(response.status_code, 403)

    def test_wrong_key_returns_403(self):
        response = self.client.get(
            reverse('assignments_list') + '?user_id=1',
            HTTP_X_INTERNAL_SERVICE_KEY='wrong-key'
        )
        self.assertEqual(response.status_code, 403)

    def test_correct_key_succeeds(self):
        response = self.client.get(
            reverse('assignments_list') + '?user_id=1',
            HTTP_X_INTERNAL_SERVICE_KEY=SERVICE_KEY
        )
        self.assertEqual(response.status_code, 200)


@override_settings(INTERNAL_SERVICE_KEY=SERVICE_KEY)
class AssignmentsGetOrCreateViewTests(TestCase):

    def setUp(self):
        reload_tests_config()
        self.url = reverse('assignments_get_or_create')
        self.headers = {'HTTP_X_INTERNAL_SERVICE_KEY': SERVICE_KEY}

    def test_creates_assignments(self):
        response = self.client.post(
            self.url,
            data=json.dumps({'user_id': 1, 'path': '/'}),
            content_type='application/json',
            **self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('assignments', data)
        self.assertIn('homepage_create_recipe_btn', data['assignments'])
        self.assertIn('applicable_tests', data)

    def test_missing_user_id(self):
        response = self.client.post(
            self.url,
            data=json.dumps({'path': '/'}),
            content_type='application/json',
            **self.headers
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_json(self):
        response = self.client.post(
            self.url,
            data='not json',
            content_type='application/json',
            **self.headers
        )
        self.assertEqual(response.status_code, 400)


@override_settings(INTERNAL_SERVICE_KEY=SERVICE_KEY)
class AssignmentsListViewTests(TestCase):

    def setUp(self):
        self.url = reverse('assignments_list')
        self.headers = {'HTTP_X_INTERNAL_SERVICE_KEY': SERVICE_KEY}

    def test_list_assignments(self):
        ABTestAssignment.objects.create(user_id=1, test_name='test_a', variant_id='control')
        ABTestAssignment.objects.create(user_id=1, test_name='test_b', variant_id='treatment')

        response = self.client.get(
            self.url + '?user_id=1',
            **self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['assignments']), 2)

    def test_missing_user_id(self):
        response = self.client.get(self.url, **self.headers)
        self.assertEqual(response.status_code, 400)

    def test_invalid_user_id(self):
        response = self.client.get(self.url + '?user_id=abc', **self.headers)
        self.assertEqual(response.status_code, 400)


@override_settings(INTERNAL_SERVICE_KEY=SERVICE_KEY)
class ImpressionsBulkViewTests(TestCase):

    def setUp(self):
        self.url = reverse('impressions_bulk')
        self.headers = {'HTTP_X_INTERNAL_SERVICE_KEY': SERVICE_KEY}

    def test_bulk_create_impressions(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                'impressions': [
                    {'user_id': 1, 'test_name': 'test_a', 'variant_id': 'control', 'path': '/'},
                    {'user_id': 1, 'test_name': 'test_b', 'variant_id': 'treatment', 'path': '/'},
                ]
            }),
            content_type='application/json',
            **self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['created'], 2)
        self.assertEqual(ABTestEvent.objects.filter(event_type='impression').count(), 2)

    def test_empty_impressions(self):
        response = self.client.post(
            self.url,
            data=json.dumps({'impressions': []}),
            content_type='application/json',
            **self.headers
        )
        self.assertEqual(response.status_code, 400)

    def test_skips_incomplete_impressions(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                'impressions': [
                    {'user_id': 1, 'test_name': 'test_a', 'variant_id': 'control'},
                    {'user_id': 1},  # incomplete, should be skipped
                ]
            }),
            content_type='application/json',
            **self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['created'], 1)


@override_settings(INTERNAL_SERVICE_KEY=SERVICE_KEY)
class EventsCreateViewTests(TestCase):

    def setUp(self):
        self.url = reverse('events_create')
        self.headers = {'HTTP_X_INTERNAL_SERVICE_KEY': SERVICE_KEY}

    def test_create_event(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                'user_id': 1,
                'test_name': 'homepage_test',
                'variant_id': 'control',
                'event_type': 'create_recipe_click',
                'path': '/',
                'metadata': {'button_id': 'cta'}
            }),
            content_type='application/json',
            **self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        event = ABTestEvent.objects.get(test_name='homepage_test')
        self.assertEqual(event.event_type, 'create_recipe_click')
        self.assertEqual(event.metadata, {'button_id': 'cta'})

    def test_missing_required_fields(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                'user_id': 1,
                'test_name': 'homepage_test',
            }),
            content_type='application/json',
            **self.headers
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_json(self):
        response = self.client.post(
            self.url,
            data='bad json',
            content_type='application/json',
            **self.headers
        )
        self.assertEqual(response.status_code, 400)


class HealthCheckViewTests(TestCase):

    def test_health_check(self):
        response = self.client.get(reverse('health_check'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')
