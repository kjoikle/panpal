"""
A/B Testing business logic.

Extracted from the monolith's middleware to serve as the core logic
for the analytics service's REST API.
"""
import json
import random
from pathlib import Path
from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def load_tests_config():
    """
    Load and cache the tests.json configuration.
    Returns dict with test definitions keyed by test name.
    """
    config_path = Path(settings.BASE_DIR) / 'analytics' / 'config' / 'tests.json'
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
        return {
            test['name']: test
            for test in data.get('tests', [])
            if test.get('enabled', True)
        }
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def reload_tests_config():
    """Force reload of tests config (call when tests.json changes)."""
    load_tests_config.cache_clear()
    return load_tests_config()


def get_applicable_tests(path):
    """
    Return list of test configs that apply to the given request path.
    Uses exact path matching.
    """
    tests = load_tests_config()
    applicable = []
    for test_name, test_config in tests.items():
        paths = test_config.get('paths', [])
        if path in paths:
            applicable.append(test_config)
    return applicable


def get_global_tests():
    """
    Return list of test configs marked as global.
    Global tests are used in base templates and need to be
    loaded on all pages, not just their assignment paths.
    """
    tests = load_tests_config()
    return [
        test_config for test_config in tests.values()
        if test_config.get('global', False)
    ]


def assign_variant(test_config):
    """
    Randomly assign a variant based on weights.
    Returns variant_id string.
    """
    variants = test_config.get('variants', [])
    if not variants:
        return None

    total_weight = sum(v.get('weight', 1) for v in variants)
    roll = random.random() * total_weight

    cumulative = 0
    for variant in variants:
        cumulative += variant.get('weight', 1)
        if roll <= cumulative:
            return variant['id']

    return variants[-1]['id']


def get_or_create_assignments(user_id, request_path):
    """
    Get or create variant assignments for a user on a given path.

    Returns a dict of test assignments in the format:
    {
        'test_name': {
            'variant_id': 'control',
            'config': {'button_text': 'Click Me'},
            'test_config': { ... full test config ... },
        }
    }

    Also returns the set of applicable test names for impression logging.
    """
    from analytics.models import ABTestAssignment

    ab_tests = {}
    applicable_test_names = set()

    # Get applicable tests for this path (for new assignments)
    applicable_tests = get_applicable_tests(request_path)

    for test_config in applicable_tests:
        test_name = test_config['name']
        applicable_test_names.add(test_name)

        assignment = ABTestAssignment.objects.filter(
            user_id=user_id,
            test_name=test_name
        ).first()

        if assignment:
            variant_id = assignment.variant_id
        else:
            variant_id = assign_variant(test_config)
            if variant_id:
                ABTestAssignment.objects.create(
                    user_id=user_id,
                    test_name=test_name,
                    variant_id=variant_id
                )

        variant_config = next(
            (v for v in test_config.get('variants', []) if v['id'] == variant_id),
            {}
        )

        ab_tests[test_name] = {
            'variant_id': variant_id,
            'config': variant_config.get('config', {}),
            'test_config': test_config,
        }

    # Load existing assignments for global tests
    global_tests = get_global_tests()
    for test_config in global_tests:
        test_name = test_config['name']
        if test_name in ab_tests:
            continue

        assignment = ABTestAssignment.objects.filter(
            user_id=user_id,
            test_name=test_name
        ).first()

        if assignment:
            variant_id = assignment.variant_id
            variant_config = next(
                (v for v in test_config.get('variants', []) if v['id'] == variant_id),
                {}
            )
            ab_tests[test_name] = {
                'variant_id': variant_id,
                'config': variant_config.get('config', {}),
                'test_config': test_config,
            }

    return ab_tests, applicable_test_names
