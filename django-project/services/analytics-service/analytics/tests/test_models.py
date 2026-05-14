"""Tests for analytics models."""
from django.test import TestCase
from analytics.models import ABTestAssignment, ABTestEvent


class ABTestAssignmentModelTests(TestCase):

    def test_create_assignment(self):
        assignment = ABTestAssignment.objects.create(
            user_id=1,
            test_name='test_experiment',
            variant_id='control'
        )
        self.assertEqual(assignment.user_id, 1)
        self.assertEqual(assignment.test_name, 'test_experiment')
        self.assertEqual(assignment.variant_id, 'control')
        self.assertIsNotNone(assignment.assigned_at)

    def test_unique_constraint_user_test_name(self):
        ABTestAssignment.objects.create(
            user_id=1,
            test_name='test_experiment',
            variant_id='control'
        )
        with self.assertRaises(Exception):
            ABTestAssignment.objects.create(
                user_id=1,
                test_name='test_experiment',
                variant_id='treatment'
            )

    def test_same_user_different_tests(self):
        ABTestAssignment.objects.create(user_id=1, test_name='test_a', variant_id='control')
        ABTestAssignment.objects.create(user_id=1, test_name='test_b', variant_id='treatment')
        self.assertEqual(ABTestAssignment.objects.filter(user_id=1).count(), 2)

    def test_different_users_same_test(self):
        ABTestAssignment.objects.create(user_id=1, test_name='test_experiment', variant_id='control')
        ABTestAssignment.objects.create(user_id=2, test_name='test_experiment', variant_id='treatment')
        self.assertEqual(
            ABTestAssignment.objects.filter(test_name='test_experiment').count(), 2
        )

    def test_str_representation(self):
        assignment = ABTestAssignment.objects.create(
            user_id=1, test_name='homepage_btn', variant_id='control'
        )
        self.assertEqual(str(assignment), 'user_1 -> homepage_btn:control')


class ABTestEventModelTests(TestCase):

    def test_create_impression_event(self):
        event = ABTestEvent.objects.create(
            user_id=1,
            test_name='homepage_test',
            variant_id='control',
            event_type='impression',
            path='/'
        )
        self.assertEqual(event.user_id, 1)
        self.assertEqual(event.event_type, 'impression')
        self.assertEqual(event.metadata, {})
        self.assertIsNotNone(event.created_at)

    def test_create_conversion_event_with_metadata(self):
        event = ABTestEvent.objects.create(
            user_id=1,
            test_name='homepage_test',
            variant_id='treatment',
            event_type='create_recipe_click',
            path='/',
            metadata={'element_id': 'create-btn'}
        )
        self.assertEqual(event.metadata, {'element_id': 'create-btn'})

    def test_multiple_events_same_user_test(self):
        for _ in range(5):
            ABTestEvent.objects.create(
                user_id=1,
                test_name='homepage_test',
                variant_id='control',
                event_type='impression',
                path='/'
            )
        self.assertEqual(
            ABTestEvent.objects.filter(user_id=1, test_name='homepage_test').count(), 5
        )

    def test_str_representation(self):
        event = ABTestEvent.objects.create(
            user_id=1,
            test_name='homepage_test',
            variant_id='control',
            event_type='impression',
            path='/'
        )
        self.assertIn('impression', str(event))
        self.assertIn('homepage_test', str(event))
