from django.contrib import admin
from .models import Recipe, Step, Tag, Favorite


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'created_at']
    list_filter = ['created_at', 'tags']
    search_fields = ['title', 'description']
    filter_horizontal = ['tags']


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ['recipe', 'step_number', 'instruction_text']
    list_filter = ['recipe']
    ordering = ['recipe', 'step_number']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'recipe', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'recipe__title']
