from django import forms
from django.contrib.auth.models import User

from .models import Recipe, Tag


class RecipeForm(forms.ModelForm):
    cuisine_type = forms.ModelChoiceField(
        queryset=Tag.objects.filter(category='cuisine').order_by('name'),
        required=False,
        empty_label="Select a cuisine type (optional)",
        label='Cuisine Type',
        help_text='Optional: Select the cuisine type for this recipe'
    )

    tags_csv = forms.CharField(
        required=False,
        label='Additional Tags (comma-separated)',
        widget=forms.TextInput(attrs={'placeholder': 'vegan, dessert, quick-meal'}),
        help_text='Enter additional tags separated by commas. Tags will be created if they don\'t exist.'
    )

    steps_text = forms.CharField(
        required=False,
        label='Steps (one per line)',
        widget=forms.Textarea(attrs={'rows': 6, 'placeholder': '1. Preheat oven\n2. Mix ingredients\n3. Bake'}),
        help_text='Enter each cooking step on a new line. Steps will be numbered automatically.'
    )

    updated_at = forms.DateTimeField(
        widget=forms.HiddenInput(),
        required=False
    )

    class Meta:
        model = Recipe
        fields = ['title', 'recipe_author', 'description', 'source_url', 'image_url', 'ingredients', 'prep_time', 'cook_time']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Brief description of the recipe'}),
            'ingredients': forms.Textarea(attrs={'rows': 8, 'placeholder': '1 cup flour\n2 eggs\n1/2 cup sugar'}),
            'recipe_author': forms.TextInput(attrs={'placeholder': 'e.g., Jamie Oliver, Grandma\'s Recipe'}),
            'source_url': forms.URLInput(attrs={'placeholder': 'https://example.com/recipe'}),
            'image_url': forms.URLInput(attrs={'placeholder': 'https://example.com/image.jpg'}),
            'prep_time': forms.NumberInput(attrs={'placeholder': 'Minutes', 'min': '0'}),
            'cook_time': forms.NumberInput(attrs={'placeholder': 'Minutes', 'min': '0'}),
        }
        help_texts = {
            'title': 'The name of your recipe',
            'recipe_author': 'Optional: The original recipe author or creator',
            'description': 'A brief description of what this recipe is',
            'source_url': 'Optional: URL to the original recipe source',
            'image_url': 'Optional: URL to an image of the finished dish',
            'ingredients': 'Optional: List ingredients, one per line',
            'prep_time': 'Optional: Preparation time in minutes',
            'cook_time': 'Optional: Cooking time in minutes',
        }

    def clean_tags_csv(self):
        data = self.cleaned_data.get('tags_csv', '')
        tag_names = [t.strip() for t in data.split(',') if t.strip()]
        return tag_names

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError('Recipe title cannot be empty.')
        return title

    def clean_image_url(self):
        url = (self.cleaned_data.get('image_url') or '').strip()
        return url if url else None

    def clean_source_url(self):
        url = (self.cleaned_data.get('source_url') or '').strip()
        return url if url else None
