"""
Database models for the recipes application.

This module defines the core data models:
    - Recipe: Main recipe entity with title, description, author, and image
    - Tag: Labels for categorizing recipes (vegan, dessert, gluten-free, etc.)
    - Step: Numbered cooking instructions for recipes
    - Favorite: User favorites with personal notes about recipes
    - SavedRecipe: User saved recipes
"""
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User


class Recipe(models.Model):
    title = models.CharField(
        max_length=200,
        help_text="The name of the recipe (e.g., 'Chocolate Chip Cookies')"
    )
    description = models.TextField(
        help_text="A brief description of the recipe"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="The user who created this recipe"
    )
    recipe_author = models.CharField(
        max_length=200,
        blank=True,
        help_text="The original recipe author or creator"
    )
    source_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL to the original recipe source (optional)"
    )
    image_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL to an image of the finished recipe (optional)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this recipe was first created"
    )
    tags = models.ManyToManyField(
        'Tag',
        blank=True,
        help_text="Tags that categorize this recipe"
    )
    ingredients = models.TextField(
        blank=True,
        help_text="Recipe ingredients, one per line"
    )
    prep_time = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Preparation time in minutes"
    )
    cook_time = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Cooking time in minutes"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def total_time(self):
        prep = self.prep_time or 0
        cook = self.cook_time or 0
        total = prep + cook
        return total if total > 0 else None

    def __str__(self):
        return self.title


class SavedRecipe(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_recipes'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='saved_by'
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'recipe']
        ordering = ['-saved_at']


class Tag(models.Model):
    CATEGORY_CHOICES = [
        ('cuisine', 'Cuisine Type'),
        ('dietary', 'Dietary Restriction'),
        ('other', 'Other'),
    ]

    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="The tag name"
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other',
        help_text="The category of this tag"
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Step(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='steps',
        help_text="The recipe this step belongs to"
    )
    step_number = models.PositiveIntegerField(
        help_text="The order of this step"
    )
    instruction_text = models.TextField(
        help_text="The instruction for this step"
    )

    class Meta:
        ordering = ['step_number']
        unique_together = ['recipe', 'step_number']

    def __str__(self):
        return f"{self.recipe.title} - Step {self.step_number}"


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        help_text="The user who favorited this recipe"
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        help_text="The recipe that was favorited"
    )
    notes = models.TextField(
        blank=True,
        help_text="Personal notes about this recipe"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this recipe was added to favorites"
    )

    class Meta:
        unique_together = ['user', 'recipe']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} favorited {self.recipe.title}"


class ApproachELO(models.Model):
    """Global ELO rating per (feature, approach) pair across all users and recipes."""
    feature = models.CharField(max_length=50)   # e.g. 'description'
    approach = models.CharField(max_length=50)  # e.g. 'casual'
    rating = models.IntegerField(default=1000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('feature', 'approach')

    def __str__(self):
        return f"{self.feature}/{self.approach}: {self.rating}"


class DescriptionPreference(models.Model):
    APPROACHES = [
        ('casual', 'Casual'),
        ('professional', 'Professional'),
        ('poetic', 'Poetic'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='description_preferences',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='description_preferences',
    )
    preferred_approach = models.CharField(max_length=20, choices=APPROACHES)
    rejected_approach = models.CharField(max_length=20, choices=APPROACHES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'recipe')

    def __str__(self):
        return f"{self.user.username} prefers {self.preferred_approach} over {self.rejected_approach} for {self.recipe.title}"
