import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.db.models import Q
from django.db import connection
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from urllib.parse import urlparse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils.timezone import now
from django.core.paginator import Paginator, EmptyPage
import json
import logging
import requests

from .models import Recipe, Tag, Step, SavedRecipe, ApproachELO, DescriptionPreference
from .forms import RecipeForm
from .scraper_client import scrape_url
from .genai_abtest import description as description_generator
from .genai_abtest.elo import update_elos, DEFAULT_ELO

logger = logging.getLogger(__name__)


def _search_recipes_postgres(query, recipes):
    try:
        from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
    except ImportError:
        return None

    # Only annotate rank from direct (non-joined) fields to avoid duplicate rows.
    # Tags/steps are still searched via Q filters but don't affect rank computation.
    vector = SearchVector('title', weight='A') + SearchVector('description', weight='B')
    search_query = SearchQuery(query)
    return (
        recipes
        .annotate(rank=SearchRank(vector, search_query))
        .filter(
            Q(rank__gte=0.001)
            | Q(tags__name__icontains=query)
            | Q(steps__instruction_text__icontains=query)
        )
        .order_by('-rank', 'id')
        .distinct()
    )


def _search_recipes_fallback(query, recipes):
    matching_ids = recipes.filter(
        Q(title__icontains=query)
        | Q(description__icontains=query)
        | Q(tags__name__icontains=query)
        | Q(steps__instruction_text__icontains=query)
    ).values_list('id', flat=True).distinct()

    return Recipe.objects.filter(id__in=matching_ids)


def _search_recipes(query, recipes):
    if not query:
        return recipes

    is_postgres = 'postgresql' in connection.settings_dict.get('ENGINE', '')
    if is_postgres:
        results = _search_recipes_postgres(query, recipes)
        if results is not None:
            return results

    return _search_recipes_fallback(query, recipes)


def _get_filtered_recipes(request, query_params=None):
    if query_params is None:
        query_params = request.GET

    query = query_params.get('q', '').strip()
    cuisine_filter = query_params.get('cuisine', '').strip()
    dietary_filters = query_params.getlist('dietary')
    max_time_filter = query_params.get('max_time', '').strip()

    view_mode = query_params.get('view', '').strip()
    if not view_mode and request.user.is_authenticated:
        view_mode = 'my_recipes'
    show_my_recipes = view_mode == 'my_recipes' and request.user.is_authenticated
    show_saved_recipes = view_mode == 'saved_recipes' and request.user.is_authenticated

    if show_my_recipes:
        recipes = Recipe.objects.filter(author=request.user)
    elif show_saved_recipes:
        recipes = Recipe.objects.filter(
            saved_by__user=request.user
        ).distinct()
    else:
        recipes = Recipe.objects.all()

    if query:
        recipes = _search_recipes(query, recipes)

    if cuisine_filter and cuisine_filter.strip():
        try:
            tag_name = Tag.objects.get(pk=int(cuisine_filter)).name
            recipes = recipes.filter(tags__name__iexact=tag_name)
        except (ValueError, TypeError, Tag.DoesNotExist):
            pass

    if dietary_filters:
        for dietary_id in dietary_filters:
            if dietary_id and dietary_id.strip():
                try:
                    tag_name = Tag.objects.get(pk=int(dietary_id)).name
                    recipes = recipes.filter(tags__name__iexact=tag_name)
                except (ValueError, TypeError, Tag.DoesNotExist):
                    pass

    if max_time_filter:
        try:
            max_time = int(max_time_filter)
            recipes = recipes.filter(
                Q(prep_time__isnull=False) | Q(cook_time__isnull=False)
            ).extra(
                where=["COALESCE(prep_time, 0) + COALESCE(cook_time, 0) <= %s"],
                params=[max_time]
            )
        except ValueError:
            pass

    recipes = recipes.distinct()
    recipes = recipes.select_related('author').prefetch_related('tags', 'steps')

    return recipes


#
#     if not view_mode and request.user.is_authenticated:
#         view_mode = 'my_recipes'
#     show_my_recipes = view_mode == 'my_recipes' and request.user.is_authenticated
#     show_saved_recipes = view_mode == 'saved_recipes' and request.user.is_authenticated
#
#     cuisine_tags = Tag.objects.filter(category='cuisine').order_by('name')
#     dietary_tags = Tag.objects.filter(category='dietary').order_by('name')
#
#     context = {
#         'recipes': page_obj,
#         'pagination': {
#             'has_next': page_obj.has_next(),
#             'total_count': paginator.count,
#         },
#         'query': query,
#         'cuisine_tags': cuisine_tags,
#         'dietary_tags': dietary_tags,
#         'selected_cuisine': cuisine_filter,
#         'selected_dietary': dietary_filters,
#         'selected_max_time': max_time_filter,
#         'show_filter_warning': show_filter_warning,
#         'active_filter_count': active_filter_count,
#         'view_mode': 'my_recipes' if show_my_recipes else 'saved_recipes' if show_saved_recipes else 'all',
#         'show_view_tabs': request.user.is_authenticated,
#     }
#     return render(request, 'home.html', context)

def home(request):
    from .utils import get_recommendations

    query = request.GET.get('q', '').strip()
    cuisine_filter = request.GET.get('cuisine', '').strip()
    dietary_filters = request.GET.getlist('dietary')
    max_time_filter = request.GET.get('max_time', '').strip()
    view_mode = request.GET.get('view', '').strip()

    if not view_mode and request.user.is_authenticated:
        view_mode = 'my_recipes'

    show_recommended = view_mode == 'recommended' and request.user.is_authenticated

    if show_recommended:
        from django.db.models import Q as _Q, Case, When, IntegerField
        recipes_list = get_recommendations(request.user, limit=500)
        rec_ids = [r.pk for r in recipes_list]
        ordering = [When(pk=pk, then=pos) for pos, pk in enumerate(rec_ids)]
        recipes = (
            Recipe.objects
            .filter(pk__in=rec_ids)
            .select_related('author')
            .prefetch_related('tags', 'steps')
            .annotate(rec_order=Case(*ordering, output_field=IntegerField()))
            .order_by('rec_order')
        )

        # Apply filters to recommended recipes
        if query:
            recipes = _search_recipes(query, recipes)
        if cuisine_filter:
            try:
                tag_name = Tag.objects.get(pk=int(cuisine_filter)).name
                recipes = recipes.filter(tags__name__iexact=tag_name)
            except (ValueError, TypeError, Tag.DoesNotExist):
                pass
        if dietary_filters:
            for dietary_id in dietary_filters:
                if dietary_id and dietary_id.strip():
                    try:
                        tag_name = Tag.objects.get(pk=int(dietary_id)).name
                        recipes = recipes.filter(tags__name__iexact=tag_name)
                    except (ValueError, TypeError, Tag.DoesNotExist):
                        pass
        if max_time_filter:
            try:
                max_time = int(max_time_filter)
                recipes = recipes.filter(
                    _Q(prep_time__isnull=False) | _Q(cook_time__isnull=False)
                ).extra(
                    where=["COALESCE(prep_time, 0) + COALESCE(cook_time, 0) <= %s"],
                    params=[max_time]
                )
            except ValueError:
                pass

        recipes = recipes.distinct()

        for recipe in recipes:
            recipe.is_saved = SavedRecipe.objects.filter(user=request.user, recipe=recipe).exists()
            cuisine_tag_obj = recipe.tags.filter(category='cuisine').first()
            recipe.cuisine_tag = cuisine_tag_obj.name if cuisine_tag_obj else None

        active_filter_count = (
                (1 if cuisine_filter else 0) +
                len(dietary_filters) +
                (1 if max_time_filter else 0)
        )
        show_filter_warning = (active_filter_count > 0 or query) and not recipes.exists()

        context = {
            'recipes': recipes,
            'pagination': {'has_next': False, 'total_count': recipes.count()},
            'query': query,
            'cuisine_tags': Tag.objects.filter(category='cuisine').order_by('name'),
            'dietary_tags': Tag.objects.filter(category='dietary').order_by('name'),
            'selected_cuisine': cuisine_filter,
            'selected_dietary': dietary_filters,
            'selected_max_time': max_time_filter,
            'show_filter_warning': show_filter_warning,
            'active_filter_count': active_filter_count,
            'view_mode': 'recommended',
            'show_view_tabs': True,
        }
        return render(request, 'home.html', context)

    recipes = _get_filtered_recipes(request)

    paginator = Paginator(recipes, 27)
    page_obj = paginator.page(1)

    for recipe in page_obj:
        cuisine_tag = recipe.tags.filter(category='cuisine').first()
        if request.user.is_authenticated:
            recipe.is_saved = SavedRecipe.objects.filter(user=request.user, recipe=recipe).exists()
        recipe.cuisine_tag = cuisine_tag.name if cuisine_tag else None

    active_filter_count = (
        (1 if cuisine_filter else 0) +
        len(dietary_filters) +
        (1 if max_time_filter else 0)
    )
    show_filter_warning = (active_filter_count > 0 or query) and not recipes.exists()

    show_my_recipes = view_mode == 'my_recipes' and request.user.is_authenticated
    show_saved_recipes = view_mode == 'saved_recipes' and request.user.is_authenticated

    cuisine_tags = Tag.objects.filter(category='cuisine').order_by('name')
    dietary_tags = Tag.objects.filter(category='dietary').order_by('name')

    context = {
        'recipes': page_obj,
        'pagination': {
            'has_next': page_obj.has_next(),
            'total_count': paginator.count,
        },
        'query': query,
        'cuisine_tags': cuisine_tags,
        'dietary_tags': dietary_tags,
        'selected_cuisine': cuisine_filter,
        'selected_dietary': dietary_filters,
        'selected_max_time': max_time_filter,
        'show_filter_warning': show_filter_warning,
        'active_filter_count': active_filter_count,
        'view_mode': 'my_recipes' if show_my_recipes else 'saved_recipes' if show_saved_recipes else 'all',
        'show_view_tabs': request.user.is_authenticated,
    }
    return render(request, 'home.html', context)


def recipes_api(request):
    try:
        page_num = request.GET.get('page', 1)
        page_size = int(request.GET.get('page_size', 18))

        try:
            page_num = int(page_num)
        except ValueError:
            return JsonResponse({'error': 'Invalid page number'}, status=400)

        if page_size not in [18, 27]:
            page_size = 18

        recipes = _get_filtered_recipes(request)

        paginator = Paginator(recipes, page_size)

        try:
            page_obj = paginator.page(page_num)
        except EmptyPage:
            return JsonResponse({
                'recipes': [],
                'pagination': {
                    'page': page_num,
                    'page_size': page_size,
                    'total_count': paginator.count,
                    'total_pages': paginator.num_pages,
                    'has_next': False,
                    'has_previous': page_num > 1
                }
            })

        page_recipe_ids = [r.pk for r in page_obj]
        saved_ids = set()
        if request.user.is_authenticated:
            saved_ids = set(
                SavedRecipe.objects
                .filter(user=request.user, recipe_id__in=page_recipe_ids)
                .values_list('recipe_id', flat=True)
            )

        recipes_data = []
        for recipe in page_obj:
            cuisine_tags = [tag for tag in recipe.tags.all() if tag.category == 'cuisine']
            cuisine_tag = cuisine_tags[0] if cuisine_tags else None
            steps_count = len(recipe.steps.all())

            recipes_data.append({
                'id': recipe.pk,
                'title': recipe.title,
                'description': recipe.description,
                'image_url': recipe.image_url or '',
                'recipe_author': recipe.recipe_author or '',
                'author_username': recipe.author.username,
                'cuisine_tag': cuisine_tag.name if cuisine_tag else None,
                'prep_time': recipe.prep_time,
                'cook_time': recipe.cook_time,
                'steps_count': steps_count,
                'url': f'/recipe/{recipe.pk}/',
                'is_saved': recipe.pk in saved_ids,
            })

        return JsonResponse({
            'recipes': recipes_data,
            'pagination': {
                'page': page_num,
                'page_size': page_size,
                'total_count': paginator.count,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        })
    except Exception as e:
        import traceback
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


def create_recipe(request):
    if request.method == 'POST':
        form = RecipeForm(request.POST)
        if form.is_valid():
            author = request.user if request.user.is_authenticated else User.objects.first()
            recipe = form.save(commit=False)
            recipe.author = author
            recipe.save()

            cuisine_tag = form.cleaned_data.get('cuisine_type')
            if cuisine_tag:
                recipe.tags.add(cuisine_tag)

            tag_names = form.cleaned_data.get('tags_csv', [])
            for name in tag_names:
                tag_obj, _ = Tag.objects.get_or_create(name=name)
                recipe.tags.add(tag_obj)

            steps_text = form.cleaned_data.get('steps_text', '')
            for idx, line in enumerate([s.strip() for s in steps_text.splitlines() if s.strip()], start=1):
                Step.objects.create(recipe=recipe, step_number=idx, instruction_text=line)

            if request.headers.get("Accept") == "application/json":
                return JsonResponse({"id": recipe.id}, status=201)

            messages.success(request, 'Recipe created successfully.')
            return redirect('home')
    else:
        form = RecipeForm()

    return render(request, 'create_recipe.html', {'form': form, 'now': now()})


def recipe_detail(request, pk):
    recipe = (
        Recipe.objects.select_related('author')
        .prefetch_related('tags', 'steps')
        .filter(pk=pk)
        .first()
    )
    if not recipe:
        from django.http import Http404
        raise Http404("Recipe not found")

    tags = recipe.tags.all()
    cuisine_tags = tags.filter(category='cuisine')
    dietary_tags = tags.filter(category='dietary')
    other_tags = tags.filter(category='other')

    steps_qs = recipe.steps.all()
    steps_json = json.dumps([
        {'step_number': s.step_number, 'instruction_text': s.instruction_text}
        for s in steps_qs
    ])

    context = {
        'recipe': recipe,
        'steps': steps_qs,
        'tags': tags,
        'cuisine_tags': cuisine_tags,
        'dietary_tags': dietary_tags,
        'other_tags': other_tags,
        'steps_json': steps_json,
        'copilot_ws_url': settings.COPILOT_SERVICE_WS_URL,
    }
    return render(request, 'recipe_detail.html', context)


@login_required
def edit_recipe(request, pk):
    from django.http import Http404

    recipe = (
        Recipe.objects.select_related('author')
        .prefetch_related('tags', 'steps')
        .filter(pk=pk)
        .first()
    )
    if not recipe:
        raise Http404("Recipe not found")

    if request.user != recipe.author and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to edit this recipe")

    if request.method == 'POST':
        form = RecipeForm(request.POST, instance=recipe)
        if form.is_valid():
            form_timestamp = form.cleaned_data.get('updated_at')
            db_timestamp = recipe.updated_at

            if form_timestamp and form_timestamp != db_timestamp:
                messages.error(
                    request,
                    "This recipe was modified by another user. Please reload and try again."
                )
                return HttpResponse(
                    "Concurrent modification detected",
                    status=409
                )

            recipe = form.save()

            recipe.tags.clear()
            recipe.steps.all().delete()

            cuisine_tag = form.cleaned_data.get('cuisine_type')
            if cuisine_tag:
                recipe.tags.add(cuisine_tag)

            tag_names = form.cleaned_data.get('tags_csv', [])
            for name in tag_names:
                tag_obj, _ = Tag.objects.get_or_create(name=name)
                recipe.tags.add(tag_obj)

            steps_text = form.cleaned_data.get('steps_text', '')
            for idx, line in enumerate([s.strip() for s in steps_text.splitlines() if s.strip()], start=1):
                Step.objects.create(recipe=recipe, step_number=idx, instruction_text=line)

            messages.success(request, 'Recipe updated successfully.')
            return redirect('recipe_detail', pk=recipe.pk)
        else:
            messages.error(request, 'Please correct the errors in the form below.')
    else:
        cuisine_tag = recipe.tags.filter(category='cuisine').first()
        other_tags = recipe.tags.exclude(category='cuisine')
        tags_csv = ', '.join([tag.name for tag in other_tags])
        steps_text = '\n'.join([step.instruction_text for step in recipe.steps.all()])

        form = RecipeForm(instance=recipe, initial={
            'updated_at': recipe.updated_at,
            'cuisine_type': cuisine_tag,
            'tags_csv': tags_csv,
            'steps_text': steps_text,
        })

    return render(request, 'edit_recipe.html', {'form': form, 'recipe': recipe, 'now': now()})


@login_required()
def save_recipe(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    SavedRecipe.objects.get_or_create(user=request.user, recipe=recipe)
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def delete_recipe(request, pk):
    from django.http import Http404, HttpResponseNotAllowed

    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    recipe = (
        Recipe.objects.select_related('author')
        .filter(pk=pk)
        .first()
    )
    if not recipe:
        raise Http404("Recipe not found")

    if request.user != recipe.author and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to delete this recipe")

    recipe_title = recipe.title
    recipe.delete()

    messages.success(request, f'Recipe "{recipe_title}" has been deleted successfully.')
    return redirect('home')


@require_POST
@login_required
def ab_test_event(request):
    """
    AJAX endpoint to log A/B test events (conversions).
    Proxies to the analytics service.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    test_name = data.get('test_name')
    variant_id = data.get('variant_id')
    event_type = data.get('event_type')
    metadata = data.get('metadata', {})

    if not test_name or not variant_id or not event_type:
        return JsonResponse({
            'success': False,
            'error': 'test_name, variant_id, and event_type are required'
        }, status=400)

    referer = request.META.get('HTTP_REFERER', '')
    path = urlparse(referer).path if referer else ''

    # Proxy to analytics service
    try:
        resp = requests.post(
            f'{settings.ANALYTICS_SERVICE_URL}/api/v1/events/',
            json={
                'user_id': request.user.id,
                'test_name': test_name,
                'variant_id': variant_id,
                'event_type': event_type,
                'path': path,
                'metadata': metadata,
            },
            headers={'X-Internal-Service-Key': settings.INTERNAL_SERVICE_KEY},
            timeout=settings.ANALYTICS_TIMEOUT,
        )
        if resp.status_code == 200:
            return JsonResponse({'success': True})
        else:
            logger.warning('Analytics service returned %s', resp.status_code)
            return JsonResponse({'success': False, 'error': 'Analytics service error'}, status=502)
    except requests.RequestException as e:
        logger.warning('Analytics service unreachable: %s', e)
        return JsonResponse({'success': False, 'error': 'Analytics service unavailable'}, status=503)


@login_required
@csrf_exempt
def describe_recipe(request, recipe_id):
    """
    GET  /api/recipes/<id>/describe/              — generate a description (one approach)
    GET  /api/recipes/<id>/describe/?approach=X   — use a specific approach
    GET  /api/recipes/<id>/describe/?compare=true — generate two descriptions side-by-side
    POST /api/recipes/<id>/describe/              — record user preference, update ELO ratings
    """
    recipe = get_object_or_404(Recipe, pk=recipe_id)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        preferred = data.get('preferred_approach')
        rejected = data.get('rejected_approach')

        valid = description_generator.APPROACHES
        if preferred not in valid or rejected not in valid or preferred == rejected:
            return JsonResponse({'error': 'Invalid approaches'}, status=400)

        DescriptionPreference.objects.update_or_create(
            user=request.user,
            recipe=recipe,
            defaults={'preferred_approach': preferred, 'rejected_approach': rejected},
        )

        winner_elo, _ = ApproachELO.objects.get_or_create(
            feature='description', approach=preferred, defaults={'rating': DEFAULT_ELO}
        )
        loser_elo, _ = ApproachELO.objects.get_or_create(
            feature='description', approach=rejected, defaults={'rating': DEFAULT_ELO}
        )
        new_winner, new_loser = update_elos(winner_elo.rating, loser_elo.rating)
        winner_elo.rating = new_winner
        loser_elo.rating = new_loser
        winner_elo.save()
        loser_elo.save()

        return JsonResponse({
            'status': 'saved',
            'elo': {preferred: new_winner, rejected: new_loser},
        })

    # GET
    if request.GET.get('compare') == 'true':
        return JsonResponse(description_generator.compare(recipe))

    approach = request.GET.get('approach')
    return JsonResponse(description_generator.generate(recipe, approach))


def describe_rankings(request):
    """GET /api/recipes/describe/rankings/ — ELO leaderboard for description approaches."""
    rankings = list(
        ApproachELO.objects
        .filter(feature='description')
        .order_by('-rating')
        .values('approach', 'rating')
    )
    return JsonResponse({'rankings': rankings})


def description_test_page(request, recipe_id):
    """Simple test page for comparing description approaches and voting."""
    import json as _json
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    result = description_generator.compare(recipe)
    descriptions = result['descriptions']
    approaches_json = _json.dumps([d['approach'] for d in descriptions])
    rankings = list(
        ApproachELO.objects
        .filter(feature='description')
        .order_by('-rating')
        .values('approach', 'rating')
    )
    return render(request, 'description_test.html', {
        'recipe': recipe,
        'descriptions': descriptions,
        'approaches_json': approaches_json,
        'rankings': rankings,
    })


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html', {'show_signup': False})


def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'login.html', {'show_signup': True})

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'login.html', {'show_signup': True})

        user = User.objects.create_user(username=username, email=email, password=password1)
        auth_login(request, user)
        messages.success(request, f'Welcome to PanPal, {user.username}!')
        return redirect('home')

    return render(request, 'login.html', {'show_signup': True})


def logout_view(request):
    auth_logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')


def autologin(request, token):
    expected = getattr(settings, 'ADMIN_AUTOLOGIN_TOKEN', 'autologin')
    if not token or token != expected:
        return HttpResponseForbidden('Invalid token')

    UserModel = get_user_model()
    try:
        admin = UserModel.objects.get(username='admin')
    except UserModel.DoesNotExist:
        return HttpResponseForbidden('Admin user not found')

    admin.backend = 'django.contrib.auth.backends.ModelBackend'
    auth_login(request, admin)
    return redirect('/admin/')


@login_required
def import_recipe(request):
    """
    Two-step import flow:
      GET              — show URL input form
      POST step=1      — call scraper, render pre-filled recipe form for review
      POST step=2      — save the confirmed recipe and redirect home
    """
    if request.method == 'POST' and request.POST.get('step') == '2':
        form = RecipeForm(request.POST)
        if form.is_valid():
            author = request.user if request.user.is_authenticated else User.objects.first()
            recipe = form.save(commit=False)
            recipe.author = author
            recipe.save()

            cuisine_tag = form.cleaned_data.get('cuisine_type')
            if cuisine_tag:
                recipe.tags.add(cuisine_tag)

            for name in form.cleaned_data.get('tags_csv', []):
                tag_obj, _ = Tag.objects.get_or_create(name=name)
                recipe.tags.add(tag_obj)

            steps_text = form.cleaned_data.get('steps_text', '')
            for idx, line in enumerate([s.strip() for s in steps_text.splitlines() if s.strip()], start=1):
                Step.objects.create(recipe=recipe, step_number=idx, instruction_text=line)

            messages.success(request, 'Recipe imported successfully.')
            return redirect('home')
        else:
            return render(request, 'import_recipe.html', {'form': form, 'step': 2})

    if request.method == 'POST' and request.POST.get('step') == '1':
        url = request.POST.get('url', '').strip()
        if not url:
            messages.error(request, 'Please enter a URL.')
            return render(request, 'import_recipe.html', {'step': 1})

        scraped = scrape_url(url)
        if scraped is None:
            messages.error(
                request,
                'We couldn\'t extract a recipe from that URL. '
                'The scraper service may be unavailable, or the page may not contain a recognizable recipe. '
                'Please try a different link.',
            )
            return render(request, 'import_recipe.html', {'step': 1, 'url': url})

        steps_text = '\n'.join(
            s['instruction_text'] for s in sorted(scraped.get('steps', []), key=lambda s: s['step_number'])
        )
        tags_csv = ', '.join(scraped.get('tags', []))

        form = RecipeForm(initial={
            'title': scraped.get('title', ''),
            'description': scraped.get('description', ''),
            'recipe_author': scraped.get('recipe_author', ''),
            'source_url': scraped.get('source_url', ''),
            'image_url': scraped.get('image_url', ''),
            'ingredients': scraped.get('ingredients', ''),
            'prep_time': scraped.get('prep_time'),
            'cook_time': scraped.get('cook_time'),
            'steps_text': steps_text,
            'tags_csv': tags_csv,
        })
        return render(request, 'import_recipe.html', {
            'form': form,
            'step': 2,
            'extraction_method': scraped.get('extraction_method'),
        })

    return render(request, 'import_recipe.html', {'step': 1})


from django.contrib.auth import update_session_auth_hash
from django.db.models import Count


@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Access denied.")

    users = (
        User.objects.annotate(recipe_count=Count('recipe'))
        .order_by('username')
    )
    return render(request, 'admin_dashboard.html', {'users': users})


@require_POST
@login_required
def admin_delete_user(request, user_id):
    if not request.user.is_staff:
        return HttpResponseForbidden("Access denied.")

    target_user = get_object_or_404(User, pk=user_id)
    if target_user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('admin_dashboard')

    username = target_user.username
    recipe_count = Recipe.objects.filter(author=target_user).count()
    target_user.delete()
    messages.success(request, f'User "{username}" and their {recipe_count} recipe(s) have been deleted.')
    return redirect('admin_dashboard')


@login_required
def profile_view(request):

    user_recipes = (
        Recipe.objects
        .filter(author=request.user)
        .select_related('author')
        .prefetch_related('tags', 'steps')
        .order_by('-created_at')
    )

    saved_qs = (
        SavedRecipe.objects
        .filter(user=request.user)
        .select_related('recipe__author')
        .prefetch_related('recipe__tags', 'recipe__steps')
        .order_by('-saved_at')
    )
    saved_recipes = [s.recipe for s in saved_qs]

    saved_ids = set(s.recipe_id for s in saved_qs)
    for recipe in user_recipes:
        recipe.is_saved = recipe.pk in saved_ids

    return render(request, 'profile.html', {
        'user_recipes': user_recipes,
        'saved_recipes': saved_recipes,
    })


@login_required
def change_password_view(request):
    error = None
    success = None
    if request.method == 'POST':
        current = request.POST.get('current_password')
        new = request.POST.get('new_password')
        confirm = request.POST.get('confirm_password')
        if not request.user.check_password(current):
            error = 'Current password is incorrect.'
        elif new != confirm:
            error = 'New passwords do not match.'
        elif len(new) < 8:
            error = 'Password must be at least 8 characters.'
        else:
            request.user.set_password(new)
            request.user.save()
            update_session_auth_hash(request, request.user)
            success = 'Password changed successfully.'
    return render(request, 'change_password.html', {'error': error, 'success': success})
