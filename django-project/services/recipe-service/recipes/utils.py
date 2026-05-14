from django.db.models import Count, Case, When, IntegerField, Q
from .models import Recipe, SavedRecipe


def get_recommendations(user, limit=6):
    # Step 1: recipes the user has already saved
    saved_ids = set(SavedRecipe.objects.filter(user=user).values_list('recipe_id', flat=True))

    if not saved_ids:
        return _popular_fallback(already_interacted=set(), limit=limit)

    # Step 2: find neighbors — users who saved any of the same recipes
    overlap_counts = {}
    for row in (SavedRecipe.objects
                .filter(recipe_id__in=saved_ids)
                .exclude(user=user)
                .values('user_id')
                .annotate(n=Count('recipe_id'))):
        overlap_counts[row['user_id']] = overlap_counts.get(row['user_id'], 0) + row['n']

    if not overlap_counts:
        return _tag_similarity_fallback(saved_ids=saved_ids, already_interacted=saved_ids, limit=limit)

    top_neighbor_ids = sorted(overlap_counts, key=overlap_counts.get, reverse=True)[:50]

    # Step 3: score candidate recipes from neighbors the user hasn't saved
    candidate_scores = {}
    for row in (SavedRecipe.objects
                .filter(user_id__in=top_neighbor_ids)
                .exclude(recipe_id__in=saved_ids)
                .values('recipe_id')
                .annotate(s=Count('user_id'))):
        candidate_scores[row['recipe_id']] = candidate_scores.get(row['recipe_id'], 0) + row['s']

    if not candidate_scores:
        return _tag_similarity_fallback(saved_ids=saved_ids, already_interacted=saved_ids, limit=limit)

    top_ids = sorted(candidate_scores, key=candidate_scores.get, reverse=True)[:limit]

    # Step 4: fetch in ranked order
    ordering = [When(pk=pk, then=pos) for pos, pk in enumerate(top_ids)]
    recs = list(
        Recipe.objects
        .filter(pk__in=top_ids)
        .select_related('author')
        .prefetch_related('tags', 'steps')
        .annotate(cf_order=Case(*ordering, output_field=IntegerField()))
        .order_by('cf_order')
    )

    # Pad with tag-similarity if fewer than limit
    if len(recs) < limit:
        already_seen = saved_ids | set(top_ids)
        pad = _tag_similarity_fallback(saved_ids=saved_ids, already_interacted=already_seen, limit=limit - len(recs))
        return recs + list(pad)

    return recs


def _tag_similarity_fallback(saved_ids, already_interacted, limit):
    """Rank unseen recipes by how many tags overlap with the user's saved recipes."""
    tag_ids = list(
        Recipe.objects.filter(pk__in=saved_ids).values_list('tags', flat=True).distinct()
    )

    if tag_ids:
        qs = (
            Recipe.objects
            .exclude(pk__in=already_interacted)
            .annotate(
                tag_overlap=Count('tags', filter=Q(tags__in=tag_ids), distinct=True),
                save_count=Count('saved_by', distinct=True),
            )
            .filter(tag_overlap__gt=0)
            .select_related('author')
            .prefetch_related('tags', 'steps')
            .order_by('-tag_overlap', '-save_count')
            [:limit]
        )
        results = list(qs)
        if results:
            return results

    return _popular_fallback(already_interacted=already_interacted, limit=limit)


def _popular_fallback(already_interacted, limit):
    return (
        Recipe.objects
        .exclude(pk__in=already_interacted)
        .annotate(save_count=Count('saved_by'))
        .select_related('author')
        .prefetch_related('tags', 'steps')
        .order_by('-save_count')
        [:limit]
    )
