#!/usr/bin/env python3
"""
Seed the Django database with test data.

This script creates sample users, tags, recipes, steps, and favorites for
testing and demonstration purposes. It is safe to run multiple times as it
uses get_or_create() to avoid duplicates.

Usage:
    From repository root:
        python3 django-project/seed_data.py
    
    Or from django-project directory:
        python3 seed_data.py

Environment:
    Uses the Django settings configured in DJANGO_SETTINGS_MODULE
    (recipeapp.settings by default).

Database:
    Works with any database backend (SQLite, PostgreSQL, etc.) configured
    in Django settings.

Created Objects:
    - 2 Users: alice and bob (both with password 'password123')
    - 2 Tags: 'dessert' and 'breakfast'
    - 2 Recipes: 'Simple Pancakes' and 'Chocolate Chip Cookies'
    - 6 Steps: 3 for each recipe
    - 2 Favorites: users have favorited each other's recipes

Notes:
    Passwords are only for local testing. NEVER use these passwords in production.
"""
from pathlib import Path
import os
import sys


BASE_DIR = Path(__file__).resolve().parent
# Ensure the project package (django-project) is on path and settings can be found
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recipeapp.settings')

import django
django.setup()

from django.contrib.auth.models import User
from recipes.models import Tag, Recipe, Step, Favorite
from django.utils import timezone


def create_user(data):
    """
    Create or update a user with the provided data.
    
    Uses get_or_create to ensure idempotency. If the user already exists,
    updates the password (if provided) to allow re-running the script.
    
    Args:
        data (dict): User data containing:
            - username (required): Unique username
            - email (optional): Email address
            - password (optional): Password to set
    
    Returns:
        User: The created or retrieved user object
    """
    username = data.get('username')
    defaults = {'email': data.get('email', '')}
    user, created = User.objects.get_or_create(username=username, defaults=defaults)
    
    # If a password is provided, set it (overwrites existing password on repeated runs)
    if data.get('password'):
        user.set_password(data['password'])
        user.save()
    
    return user


def main():
    """
    Main entry point for seeding the database.
    
    Creates or verifies the existence of all test data objects and
    prints a summary of created/verified items.
    """
    print('Seeding database...')

    # Create users
    alice = create_user({
        'username': 'alice',
        'email': 'alice@example.com',
        'password': 'password123'
    })
    bob = create_user({
        'username': 'bob',
        'email': 'bob@example.com',
        'password': 'password123'
    })
    # Create a default admin user for development if it doesn't exist
    admin_user, created = User.objects.get_or_create(username='admin', defaults={'email': 'admin@example.com'})
    # For the school project we always reset the admin password on seed so
    # the team can reliably log in on each deploy without extra steps.
    admin_user.set_password('adminpass')
    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.save()
    print('✓ Admin user: username=admin password=adminpass')
    print(f'✓ Users: alice and bob')

    # Create cuisine tags
    italian, _ = Tag.objects.get_or_create(name='Italian', defaults={'category': 'cuisine'})
    italian.category = 'cuisine'
    italian.save()

    indian, _ = Tag.objects.get_or_create(name='Indian', defaults={'category': 'cuisine'})
    indian.category = 'cuisine'
    indian.save()

    american, _ = Tag.objects.get_or_create(name='American', defaults={'category': 'cuisine'})
    american.category = 'cuisine'
    american.save()

    greek, _ = Tag.objects.get_or_create(name='Greek', defaults={'category': 'cuisine'})
    greek.category = 'cuisine'
    greek.save()

    mexican, _ = Tag.objects.get_or_create(name='Mexican', defaults={'category': 'cuisine'})
    mexican.category = 'cuisine'
    mexican.save()

    asian, _ = Tag.objects.get_or_create(name='Asian', defaults={'category': 'cuisine'})
    asian.category = 'cuisine'
    asian.save()

    # Create dietary restriction tags
    vegetarian, _ = Tag.objects.get_or_create(name='Vegetarian', defaults={'category': 'dietary'})
    vegetarian.category = 'dietary'
    vegetarian.save()

    vegan, _ = Tag.objects.get_or_create(name='Vegan', defaults={'category': 'dietary'})
    vegan.category = 'dietary'
    vegan.save()

    gluten_free, _ = Tag.objects.get_or_create(name='Gluten-Free', defaults={'category': 'dietary'})
    gluten_free.category = 'dietary'
    gluten_free.save()

    dairy_free, _ = Tag.objects.get_or_create(name='Dairy-Free', defaults={'category': 'dietary'})
    dairy_free.category = 'dietary'
    dairy_free.save()

    print(f'✓ Tags: Cuisine (Italian, Indian, American, Greek, Mexican, Asian) + Dietary (Vegetarian, Vegan, Gluten-Free, Dairy-Free)')

    # Create 7 diverse recipes
    recipes_data = [
        {
            'title': 'Classic Spaghetti Carbonara',
            'description': 'Traditional Roman pasta dish with eggs, pecorino cheese, guanciale, and black pepper. Simple ingredients create a creamy, luxurious sauce without cream.',
            'author': alice,
            'image_url': 'https://placehold.co/400x300/FFD700/333333?text=Spaghetti+Carbonara',
            'tags': [italian],
            'prep_time': 10,
            'cook_time': 20,
            'ingredients': '''1 lb spaghetti
6 oz pancetta or guanciale, diced
4 large eggs
1 cup freshly grated Parmesan cheese
1 cup freshly grated Pecorino Romano cheese
Freshly ground black pepper
Salt for pasta water''',
            'steps': [
                'Bring a large pot of salted water to boil and cook spaghetti according to package directions until al dente.',
                'While pasta cooks, heat a large skillet over medium heat. Add pancetta and cook until crispy, about 8-10 minutes.',
                'In a bowl, whisk together eggs, Parmesan, Pecorino Romano, and plenty of black pepper.',
                'Reserve 1 cup of pasta cooking water, then drain pasta.',
                'Remove skillet from heat. Add hot pasta to the skillet with pancetta and toss to combine.',
                'Quickly add egg mixture to pasta, tossing constantly. Add reserved pasta water a little at a time until sauce is creamy.',
            ]
        },
        {
            'title': 'Creamy Chicken Curry',
            'description': 'Rich and aromatic Indian curry with tender chicken pieces in a tomato-based sauce with cream and warming spices like garam masala.',
            'author': bob,
            'image_url': 'https://placehold.co/400x300/FF8C00/333333?text=Chicken+Curry',
            'tags': [indian, gluten_free],
            'prep_time': 15,
            'cook_time': 35,
            'ingredients': '''2 lbs boneless chicken thighs, cut into pieces
2 large onions, finely chopped
3 tbsp ginger-garlic paste
2 cups tomato puree
1 cup coconut cream
2 tsp turmeric powder
2 tsp chili powder
3 tsp garam masala
3 tbsp cooking oil
Fresh cilantro for garnish
Salt to taste''',
            'steps': [
                'Heat oil in a large pan and sauté onions until golden brown.',
                'Add ginger-garlic paste and cook for 2 minutes until fragrant.',
                'Add tomato puree, turmeric, chili powder, and garam masala. Cook for 5 minutes.',
                'Add chicken pieces and coat well with the sauce. Cook for 10 minutes.',
                'Pour in coconut cream and simmer for 15 minutes until chicken is cooked through.',
                'Garnish with fresh cilantro and serve with rice or naan.',
            ]
        },
        {
            'title': 'Perfect Chocolate Chip Cookies',
            'description': 'The ultimate chocolate chip cookies with crispy edges and a soft, chewy center. Loaded with chocolate chips in every bite.',
            'author': alice,
            'image_url': 'https://placehold.co/400x300/8B4513/FFFFFF?text=Chocolate+Cookies',
            'tags': [american, vegetarian],
            'prep_time': 15,
            'cook_time': 12,
            'ingredients': '''2 1/4 cups all-purpose flour
1 cup unsalted butter, softened
3/4 cup granulated sugar
3/4 cup brown sugar
2 large eggs
2 tsp vanilla extract
1 tsp baking soda
1 tsp salt
2 cups chocolate chips''',
            'steps': [
                'Preheat oven to 350°F (175°C). Line baking sheets with parchment paper.',
                'Cream together butter and both sugars until light and fluffy.',
                'Beat in eggs one at a time, then add vanilla extract.',
                'In a separate bowl, whisk together flour, baking soda, and salt.',
                'Gradually mix dry ingredients into wet ingredients until just combined.',
                'Fold in chocolate chips.',
                'Drop rounded tablespoons of dough onto prepared baking sheets.',
                'Bake for 10-12 minutes until edges are golden. Cool on baking sheet for 5 minutes.',
            ]
        },
        {
            'title': 'Fresh Greek Salad',
            'description': 'Crisp vegetables, tangy feta cheese, and Kalamata olives dressed simply with olive oil and lemon juice.',
            'author': bob,
            'image_url': 'https://placehold.co/400x300/32CD32/333333?text=Greek+Salad',
            'tags': [greek, vegetarian, gluten_free],
            'prep_time': 15,
            'cook_time': 0,
            'ingredients': '''4 large tomatoes, chopped
2 cucumbers, sliced
1 red onion, thinly sliced
1 cup Kalamata olives
8 oz feta cheese, crumbled
1/4 cup olive oil
2 tbsp lemon juice
1 tsp dried oregano
Salt and pepper to taste''',
            'steps': [
                'Chop tomatoes, cucumbers, and red onion into bite-sized pieces.',
                'Add to a large bowl with Kalamata olives.',
                'Whisk together olive oil, lemon juice, oregano, salt, and pepper.',
                'Pour dressing over salad and toss gently.',
                'Top with crumbled feta cheese and serve immediately.',
            ]
        },
        {
            'title': 'Street-Style Chicken Tacos',
            'description': 'Authentic Mexican street tacos with marinated grilled chicken, fresh cilantro, onions, and a squeeze of lime on soft corn tortillas.',
            'author': alice,
            'image_url': 'https://placehold.co/400x300/FF6347/FFFFFF?text=Chicken+Tacos',
            'tags': [mexican, gluten_free, dairy_free],
            'prep_time': 70,
            'cook_time': 15,
            'ingredients': '''2 lbs boneless chicken thighs
12 small corn tortillas
Juice of 3 limes
4 garlic cloves, minced
2 tsp cumin
2 tsp chili powder
1 tsp dried oregano
1 white onion, diced
1/2 cup fresh cilantro, chopped
Lime wedges for serving
Salt to taste''',
            'steps': [
                'Marinate chicken thighs in lime juice, garlic, cumin, chili powder, and oregano for at least 1 hour.',
                'Heat a grill or cast iron skillet over high heat.',
                'Grill chicken for 6-7 minutes per side until charred and cooked through.',
                'Let chicken rest for 5 minutes, then chop into small pieces.',
                'Warm corn tortillas on the grill.',
                'Assemble tacos with chicken, diced onions, fresh cilantro, and lime wedges.',
            ]
        },
        {
            'title': 'Asian Beef Stir-Fry',
            'description': 'Quick and flavorful stir-fry with tender beef strips, crisp vegetables, and a savory soy-ginger sauce served over rice.',
            'author': bob,
            'image_url': 'https://placehold.co/400x300/8B0000/FFFFFF?text=Beef+Stir-Fry',
            'tags': [asian, dairy_free],
            'prep_time': 20,
            'cook_time': 15,
            'ingredients': '''1.5 lbs flank steak, thinly sliced
1/4 cup soy sauce
2 tbsp cornstarch
1 tbsp sesame oil
2 bell peppers, sliced
2 cups broccoli florets
1 cup snap peas
3 garlic cloves, minced
2 tbsp fresh ginger, minced
2 tbsp honey
3 tbsp vegetable oil
Cooked rice for serving''',
            'steps': [
                'Slice beef thinly against the grain and marinate in soy sauce, cornstarch, and sesame oil.',
                'Heat wok over high heat until smoking. Add oil.',
                'Stir-fry beef in batches until browned, about 2 minutes per batch. Remove and set aside.',
                'Add vegetables (bell peppers, broccoli, snap peas) and stir-fry for 3-4 minutes.',
                'Return beef to wok. Add sauce mixture of soy sauce, ginger, garlic, and a touch of honey.',
                'Toss everything together for 1-2 minutes until heated through and coated in sauce.',
                'Serve immediately over steamed rice.',
            ]
        },
        {
            'title': 'Colorful Buddha Bowl',
            'description': 'Nourishing vegetarian bowl packed with roasted vegetables, quinoa, chickpeas, and creamy tahini dressing.',
            'author': alice,
            'image_url': 'https://placehold.co/400x300/9370DB/FFFFFF?text=Buddha+Bowl',
            'tags': [vegetarian, vegan, gluten_free, dairy_free],
            'prep_time': 20,
            'cook_time': 30,
            'ingredients': '''1 cup quinoa
1 can (15 oz) chickpeas, drained
1 large sweet potato, cubed
2 cups broccoli florets
2 cups cauliflower florets
2 cups kale, chopped
1/4 cup tahini
2 tbsp lemon juice
2 garlic cloves, minced
3 tbsp olive oil
2 tbsp sesame seeds
Salt and pepper to taste''',
            'steps': [
                'Cook quinoa according to package directions and set aside.',
                'Roast chickpeas and vegetables (sweet potato, broccoli, cauliflower) at 425°F for 25-30 minutes.',
                'Prepare tahini dressing by whisking tahini, lemon juice, garlic, and water until smooth.',
                'Massage kale with a bit of olive oil and lemon juice.',
                'Assemble bowls with quinoa, roasted vegetables, chickpeas, and kale.',
                'Drizzle with tahini dressing and garnish with sesame seeds.',
            ]
        },
    ]

    recipes = []
    for recipe_data in recipes_data:
        recipe, created = Recipe.objects.get_or_create(
            title=recipe_data['title'],
            defaults={
                'description': recipe_data['description'],
                'author': recipe_data['author'],
                'image_url': recipe_data['image_url'],
                'ingredients': recipe_data.get('ingredients', ''),
                'prep_time': recipe_data.get('prep_time'),
                'cook_time': recipe_data.get('cook_time'),
                'created_at': timezone.now(),
            }
        )
        recipe.author = recipe_data['author']
        recipe.image_url = recipe_data['image_url']
        recipe.description = recipe_data['description']
        recipe.ingredients = recipe_data.get('ingredients', '')
        recipe.prep_time = recipe_data.get('prep_time')
        recipe.cook_time = recipe_data.get('cook_time')
        recipe.save()

        for tag in recipe_data['tags']:
            recipe.tags.add(tag)

        # Add steps
        for idx, step_text in enumerate(recipe_data['steps'], start=1):
            Step.objects.get_or_create(
                recipe=recipe,
                step_number=idx,
                defaults={'instruction_text': step_text}
            )

        recipes.append(recipe)

    print(f'✓ Recipes: Created/updated 7 recipes with steps')

    # Create favorites
    if len(recipes) >= 2:
        Favorite.objects.get_or_create(
            user=bob,
            recipe=recipes[0],  # Spaghetti Carbonara
            defaults={'notes': 'Family favorite'}
        )
        Favorite.objects.get_or_create(
            user=alice,
            recipe=recipes[1],  # Chicken Curry
            defaults={'notes': 'Perfect for dinner parties'}
        )
        print(f'✓ Favorites: Created sample favorites for users')

    # Print verification summary
    print('\n' + '='*60)
    print('DATABASE SEEDING SUMMARY')
    print('='*60)
    print(f'\nUsers ({User.objects.count()}):')
    for user in User.objects.all():
        print(f'  - {user.username} ({user.email})')

    print(f'\nTags ({Tag.objects.count()}):')
    for tag in Tag.objects.all().order_by('name'):
        print(f'  - {tag.name}')

    print(f'\nRecipes ({Recipe.objects.count()}):')
    for recipe in Recipe.objects.all().order_by('created_at'):
        tags = ', '.join([t.name for t in recipe.tags.all()])
        step_count = recipe.steps.count()
        print(f'  - {recipe.title} by {recipe.author.username}')
        print(f'    Tags: {tags or "(none)"}')
        print(f'    Steps: {step_count}')

    print(f'\nFavorites ({Favorite.objects.count()}):')
    for fav in Favorite.objects.all().order_by('-created_at'):
        print(f'  - {fav.user.username} → {fav.recipe.title}')
        if fav.notes:
            print(f'    Notes: {fav.notes}')

    print('\n' + '='*60)
    print('✓ Seeding complete!')
    print('='*60)


if __name__ == '__main__':
    main()
