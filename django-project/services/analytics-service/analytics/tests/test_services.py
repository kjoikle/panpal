"""Tests for analytics service business logic."""
from django.test import TestCase

from analytics.models import ABTestAssignment
from analytics.services import (
    load_tests_config,
    reload_tests_config,
    get_applicable_tests,
    get_global_tests,
    assign_variant,
    get_or_create_assignments,
)


class LoadTestsConfigTests(TestCase):

    def setUp(self):
        reload_tests_config()

    def test_load_tests_config_returns_dict(self):
        config = load_tests_config()
        self.assertIsInstance(config, dict)

    def test_load_tests_config_keyed_by_name(self):
        config = load_tests_config()
        self.assertIn('homepage_create_recipe_btn', config)
        self.assertIn('homepage_layout_test', config)

    def test_reload_tests_config_clears_cache(self):
        config1 = load_tests_config()
        config2 = reload_tests_config()
        self.assertIsInstance(config1, dict)
        self.assertIsInstance(config2, dict)


class GetApplicableTestsTests(TestCase):

    def setUp(self):
        reload_tests_config()

    def test_returns_tests_for_matching_path(self):
        tests = get_applicable_tests('/')
        test_names = [t['name'] for t in tests]
        self.assertIn('homepage_create_recipe_btn', test_names)
        self.assertIn('homepage_layout_test', test_names)

    def test_returns_empty_for_non_matching_path(self):
        tests = get_applicable_tests('/some/random/path/')
        self.assertEqual(tests, [])

    def test_exact_path_matching(self):
        tests = get_applicable_tests('/create/')
        test_names = [t['name'] for t in tests]
        self.assertNotIn('homepage_create_recipe_btn', test_names)


class GetGlobalTestsTests(TestCase):

    def setUp(self):
        reload_tests_config()

    def test_returns_global_tests(self):
        tests = get_global_tests()
        test_names = [t['name'] for t in tests]
        self.assertIn('homepage_create_recipe_btn', test_names)
        self.assertNotIn('homepage_layout_test', test_names)


class AssignVariantTests(TestCase):

    def test_assigns_valid_variant(self):
        test_config = {
            'variants': [
                {'id': 'control', 'weight': 50},
                {'id': 'treatment', 'weight': 50}
            ]
        }
        variant = assign_variant(test_config)
        self.assertIn(variant, ['control', 'treatment'])

    def test_returns_none_for_empty_variants(self):
        self.assertIsNone(assign_variant({'variants': []}))

    def test_returns_none_for_missing_variants(self):
        self.assertIsNone(assign_variant({}))

    def test_respects_weights(self):
        test_config = {
            'variants': [
                {'id': 'control', 'weight': 100},
                {'id': 'treatment', 'weight': 0}
            ]
        }
        for _ in range(20):
            self.assertEqual(assign_variant(test_config), 'control')

    def test_handles_single_variant(self):
        test_config = {'variants': [{'id': 'only_variant', 'weight': 100}]}
        self.assertEqual(assign_variant(test_config), 'only_variant')


class GetOrCreateAssignmentsTests(TestCase):

    def setUp(self):
        reload_tests_config()

    def test_creates_assignments_for_homepage(self):
        ab_tests, applicable = get_or_create_assignments(user_id=1, request_path='/')
        self.assertIn('homepage_create_recipe_btn', ab_tests)
        self.assertIn('homepage_layout_test', ab_tests)
        self.assertIn('homepage_create_recipe_btn', applicable)
        self.assertEqual(ABTestAssignment.objects.filter(user_id=1).count(), 2)

    def test_reuses_existing_assignment(self):
        ABTestAssignment.objects.create(
            user_id=1, test_name='homepage_create_recipe_btn', variant_id='treatment'
        )
        ab_tests, _ = get_or_create_assignments(user_id=1, request_path='/')
        self.assertEqual(ab_tests['homepage_create_recipe_btn']['variant_id'], 'treatment')
        self.assertEqual(
            ABTestAssignment.objects.filter(
                user_id=1, test_name='homepage_create_recipe_btn'
            ).count(), 1
        )

    def test_loads_global_tests_on_other_pages(self):
        # First visit homepage to create assignment
        get_or_create_assignments(user_id=1, request_path='/')
        # Then visit another page
        ab_tests, applicable = get_or_create_assignments(user_id=1, request_path='/create/')
        # Global test should be loaded from existing assignment
        self.assertIn('homepage_create_recipe_btn', ab_tests)
        # Non-global test should not be loaded
        self.assertNotIn('homepage_layout_test', ab_tests)
        # No tests applicable to /create/
        self.assertEqual(len(applicable), 0)

    def test_no_assignment_for_unvisited_global_test(self):
        # Visit non-homepage without prior homepage visit
        ab_tests, _ = get_or_create_assignments(user_id=1, request_path='/create/')
        # No assignments should exist
        self.assertNotIn('homepage_create_recipe_btn', ab_tests)
        self.assertEqual(ABTestAssignment.objects.filter(user_id=1).count(), 0)

    def test_variant_config_included(self):
        ab_tests, _ = get_or_create_assignments(user_id=1, request_path='/')
        test_data = ab_tests['homepage_create_recipe_btn']
        self.assertIn('button_text', test_data['config'])
        self.assertIn('button_class', test_data['config'])
