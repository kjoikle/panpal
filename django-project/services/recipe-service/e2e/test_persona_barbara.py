"""
Persona 2 — Barbara Cordero
Working mother, low technical proficiency, wants to manually create and edit a recipe.

Run: pytest e2e/test_persona_barbara.py -v
"""

import re
import uuid
import pytest
from playwright.sync_api import Page, expect
from conftest import delete_test_user

BASE_URL = "http://localhost:8000"

RECIPE = {
    "title": "Barbara's Chicken Soup",
    "recipe_author": "Barbara Cordero",
    "description": "A warm and comforting chicken soup perfect for cold days.",
    "prep_time": "15",
    "cook_time": "45",
    "ingredients": (
        "1 whole chicken\n"
        "3 carrots, chopped\n"
        "2 celery stalks, chopped\n"
        "1 onion, diced\n"
        "Salt and pepper to taste"
    ),
    "steps_text": (
        "1. Place the chicken in a large pot and cover with water.\n"
        "2. Bring to a boil and skim off any foam.\n"
        "3. Add the vegetables and season with salt and pepper.\n"
        "4. Simmer for 45 minutes until the chicken is cooked through.\n"
        "5. Remove the chicken, shred the meat, and return it to the pot."
    ),
}

UPDATED_DESCRIPTION = (
    "A warm and comforting chicken soup perfect for cold days. "
    "Great for the whole family."
)
ADDED_INGREDIENT = "2 cloves garlic, minced"


@pytest.fixture()
def barbara(page: Page):
    """Sign up and log in as Barbara, then delete the account after the test."""
    uid = uuid.uuid4().hex[:8]
    username = f"barbara_{uid}"
    password = "Barbarapass99"

    # Signup logs the user in immediately and redirects to home
    page.goto(f"{BASE_URL}/signup/")
    page.fill("#username", username)
    page.fill("#email", f"{username}@example.com")
    page.fill("#password1", password)
    page.fill("#password2", password)
    page.click("button[type='submit']")
    page.wait_for_url(f"{BASE_URL}/")

    yield page

    delete_test_user(username)


def create_recipe(page: Page) -> str:
    """Create Barbara's chicken soup and return the recipe PK."""
    page.goto(f"{BASE_URL}/create/")
    page.fill("#id_title", RECIPE["title"])
    page.fill("#id_recipe_author", RECIPE["recipe_author"])
    page.fill("#id_description", RECIPE["description"])
    page.fill("#id_prep_time", RECIPE["prep_time"])
    page.fill("#id_cook_time", RECIPE["cook_time"])
    page.fill("#id_ingredients", RECIPE["ingredients"])
    page.fill("#id_steps_text", RECIPE["steps_text"])
    page.click("button[type='submit']")
    page.wait_for_url(re.compile(r"(/$|/recipe/\d+/)"))

    # Navigate to the recipe from the homepage to get its PK
    page.goto(f"{BASE_URL}/")
    page.get_by_text(RECIPE["title"]).first.click()
    page.wait_for_url(re.compile(r"/recipe/\d+/"))

    match = re.search(r"/recipe/(\d+)/", page.url)
    assert match, "Could not find recipe PK in URL"
    return match.group(1)


class TestBarbaraCordero:

    def test_create_recipe_form_loads(self, barbara: Page):
        """Barbara can navigate to the create recipe page and see the form."""
        barbara.goto(f"{BASE_URL}/create/")
        expect(barbara.locator("#id_title")).to_be_visible()
        expect(barbara.locator("#id_ingredients")).to_be_visible()
        expect(barbara.locator("#id_steps_text")).to_be_visible()

    def test_create_recipe_success(self, barbara: Page):
        """Barbara fills in the form and the recipe is created."""
        barbara.goto(f"{BASE_URL}/create/")
        barbara.fill("#id_title", RECIPE["title"])
        barbara.fill("#id_recipe_author", RECIPE["recipe_author"])
        barbara.fill("#id_description", RECIPE["description"])
        barbara.fill("#id_prep_time", RECIPE["prep_time"])
        barbara.fill("#id_cook_time", RECIPE["cook_time"])
        barbara.fill("#id_ingredients", RECIPE["ingredients"])
        barbara.fill("#id_steps_text", RECIPE["steps_text"])
        barbara.click("button[type='submit']")

        barbara.wait_for_url(re.compile(r"(/$|/recipe/\d+/)"))

        # Recipe should appear on homepage
        barbara.goto(f"{BASE_URL}/")
        expect(barbara.get_by_text(RECIPE["title"]).first).to_be_visible()

    def test_recipe_detail_shows_all_fields(self, barbara: Page):
        """The created recipe detail page renders title, author, description and ingredients."""
        pk = create_recipe(barbara)
        barbara.goto(f"{BASE_URL}/recipe/{pk}/")

        expect(barbara.get_by_text(RECIPE["title"]).first).to_be_visible()
        expect(barbara.get_by_text(RECIPE["recipe_author"]).first).to_be_visible()
        expect(barbara.get_by_text(RECIPE["description"]).first).to_be_visible()
        # At least one ingredient line should be present
        expect(barbara.get_by_text("carrots").first).to_be_visible()

    def test_edit_recipe_updates_description(self, barbara: Page):
        """Barbara edits the description and the change is saved."""
        pk = create_recipe(barbara)
        barbara.goto(f"{BASE_URL}/recipe/{pk}/edit/")

        barbara.fill("#id_description", UPDATED_DESCRIPTION)
        barbara.click("button[type='submit']")
        barbara.wait_for_url(re.compile(r"(/$|/recipe/\d+/)"))

        barbara.goto(f"{BASE_URL}/recipe/{pk}/")
        expect(barbara.get_by_text(UPDATED_DESCRIPTION).first).to_be_visible()

    def test_edit_recipe_adds_ingredient(self, barbara: Page):
        """Barbara adds a new ingredient and it appears on the detail page."""
        pk = create_recipe(barbara)
        barbara.goto(f"{BASE_URL}/recipe/{pk}/edit/")

        current = barbara.input_value("#id_ingredients")
        barbara.fill("#id_ingredients", current + f"\n{ADDED_INGREDIENT}")
        barbara.click("button[type='submit']")
        barbara.wait_for_url(re.compile(r"(/$|/recipe/\d+/)"))

        barbara.goto(f"{BASE_URL}/recipe/{pk}/")
        expect(barbara.get_by_text("garlic").first).to_be_visible()

    def test_edit_preserves_existing_fields(self, barbara: Page):
        """Editing description does not wipe out the original title or steps."""
        pk = create_recipe(barbara)
        barbara.goto(f"{BASE_URL}/recipe/{pk}/edit/")

        barbara.fill("#id_description", UPDATED_DESCRIPTION)
        barbara.click("button[type='submit']")
        barbara.wait_for_url(re.compile(r"(/$|/recipe/\d+/)"))

        barbara.goto(f"{BASE_URL}/recipe/{pk}/")
        expect(barbara.get_by_text(RECIPE["title"]).first).to_be_visible()
        expect(barbara.get_by_text("carrots").first).to_be_visible()
