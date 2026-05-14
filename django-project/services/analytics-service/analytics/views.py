"""
REST API views for the analytics service.

All endpoints require the X-Internal-Service-Key header for authentication.
"""
import json
from functools import wraps

from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from analytics.models import ABTestAssignment, ABTestEvent
from analytics.services import get_or_create_assignments


def require_service_key(view_func):
    """Decorator to validate the internal service key."""
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
def assignments_get_or_create(request):
    """
    POST /api/v1/assignments/get-or-create/

    Get or create variant assignments for a user on a given path.

    Request body:
    {
        "user_id": 1,
        "path": "/"
    }

    Response:
    {
        "assignments": {
            "test_name": {
                "variant_id": "control",
                "config": {"button_text": "Click Me"},
                "test_config": { ... }
            }
        },
        "applicable_tests": ["test_name"]
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user_id = data.get('user_id')
    path = data.get('path', '/')

    if not user_id:
        return JsonResponse({'error': 'user_id is required'}, status=400)

    ab_tests, applicable_test_names = get_or_create_assignments(user_id, path)

    return JsonResponse({
        'assignments': ab_tests,
        'applicable_tests': list(applicable_test_names),
    })


@csrf_exempt
@require_GET
@require_service_key
def assignments_list(request):
    """
    GET /api/v1/assignments/?user_id=N

    List all assignments for a user.
    """
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'user_id query parameter is required'}, status=400)

    try:
        user_id = int(user_id)
    except ValueError:
        return JsonResponse({'error': 'user_id must be an integer'}, status=400)

    assignments = ABTestAssignment.objects.filter(user_id=user_id)
    data = [
        {
            'user_id': a.user_id,
            'test_name': a.test_name,
            'variant_id': a.variant_id,
            'assigned_at': a.assigned_at.isoformat(),
        }
        for a in assignments
    ]
    return JsonResponse({'assignments': data})


@csrf_exempt
@require_POST
@require_service_key
def impressions_bulk(request):
    """
    POST /api/v1/impressions/bulk/

    Bulk log impression events.

    Request body:
    {
        "impressions": [
            {
                "user_id": 1,
                "test_name": "homepage_test",
                "variant_id": "control",
                "path": "/"
            }
        ]
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    impressions = data.get('impressions', [])
    if not impressions:
        return JsonResponse({'error': 'impressions array is required'}, status=400)

    events_to_create = []
    for imp in impressions:
        user_id = imp.get('user_id')
        test_name = imp.get('test_name')
        variant_id = imp.get('variant_id')
        path = imp.get('path', '')

        if not all([user_id, test_name, variant_id]):
            continue

        events_to_create.append(ABTestEvent(
            user_id=user_id,
            test_name=test_name,
            variant_id=variant_id,
            event_type='impression',
            path=path,
        ))

    if events_to_create:
        ABTestEvent.objects.bulk_create(events_to_create)

    return JsonResponse({'created': len(events_to_create)})


@csrf_exempt
@require_POST
@require_service_key
def events_create(request):
    """
    POST /api/v1/events/

    Log a single analytics event.

    Request body:
    {
        "user_id": 1,
        "test_name": "homepage_test",
        "variant_id": "control",
        "event_type": "create_recipe_click",
        "path": "/",
        "metadata": {}
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user_id = data.get('user_id')
    test_name = data.get('test_name')
    variant_id = data.get('variant_id')
    event_type = data.get('event_type')
    path = data.get('path', '')
    metadata = data.get('metadata', {})

    if not all([user_id, test_name, variant_id, event_type]):
        return JsonResponse({
            'error': 'user_id, test_name, variant_id, and event_type are required'
        }, status=400)

    ABTestEvent.objects.create(
        user_id=user_id,
        test_name=test_name,
        variant_id=variant_id,
        event_type=event_type,
        path=path,
        metadata=metadata,
    )

    return JsonResponse({'success': True})


@require_http_methods(["GET"])
def health_check(request):
    """
    GET /api/v1/health/

    Health check endpoint (no auth required).
    """
    return JsonResponse({'status': 'ok'})
