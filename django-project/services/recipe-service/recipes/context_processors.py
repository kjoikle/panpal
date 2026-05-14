"""
Context processors for the recipes application.

This module provides template context processors including A/B test data.
"""
import json


def ab_tests(request):
    """
    Context processor to make A/B test variants available in templates.

    The proxy middleware populates request.ab_tests with the same structure
    as the original monolith middleware, so templates work unchanged.
    """
    ab_tests_data = getattr(request, 'ab_tests', {})

    simplified = {}
    for test_name, test_data in ab_tests_data.items():
        simplified[test_name] = {
            'variant_id': test_data['variant_id'],
            'config': test_data['config'],
        }

    json_data = {
        test_name: {
            'variant_id': data['variant_id'],
            'config': data['config'],
        }
        for test_name, data in ab_tests_data.items()
    }

    return {
        'ab_tests': simplified,
        'ab_tests_json': json.dumps(json_data),
    }
