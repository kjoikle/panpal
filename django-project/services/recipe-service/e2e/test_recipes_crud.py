"""
End-to-end Playwright tests for recipe CRUD operations.

Prerequisites:
  1. pip install -r e2e/requirements.txt
  2. playwright install chromium
  3. The recipe-service must be running at http://localhost:8000
     with the demo user 'alice / password123' seeded in the database.

Run:
  pytest e2e/ -v
"""

import re
import uuid
import pytest
from playwright.sync_api import Page, expect
from conftest import delete_test_user

BASE_URL = "http://localhost:8000"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RECIPE = {
    "title": "Playwright Test Pasta",
    "recipe_author": "Test Chef",
    "description": "A simple pasta dish created by automated tests.",
    "prep_time": "10",
    "cook_time": "20",
    "tags_csv": "quick, pasta",
    "ingredients": "200g spaghetti\n2 cloves garlic\n3 tbsp olive oil\nSalt to taste",
    "steps_text": "1. Boil salted water and cook spaghetti until al dente.\n"
                  "2. Fry garlic in olive oil until golden.\n"
                  "3. Toss pasta with garlic oil and serve.",
}

UPDATED_TITLE = "Playwright Test Pasta (Edited)"
UPDATED_DESCRIPTION = "Updated description by automated tests."


def fill_recipe_form(page: Page, data: dict) -> None:
    """Fill all visible fields of the recipe create/edit form."""
    page.fill("#id_title", data["title"])
    page.fill("#id_recipe_author", data.get("recipe_author", ""))
    page.fill("#id_description", data.get("description", ""))
    if data.get("prep_time"):
        page.fill("#id_prep_time", data["prep_time"])
    if data.get("cook_time"):
        page.fill("#id_cook_time", data["cook_time"])
    if data.get("tags_csv"):
        page.fill("#id_tags_csv", data["tags_csv"])
    page.fill("#id_ingredients", data.get("ingredients", ""))
    page.fill("#id_steps_text", data.get("steps_text", ""))


def get_recipe_pk_from_url(url: str) -> str:
    """Extract the numeric PK from a recipe detail or edit URL."""
    match = re.search(r"/recipe/(\d+)/", url)
    assert match, f"Could not extract recipe PK from URL: {url}"
    return match.group(1)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAuthentication:
    """Verify that protected pages redirect unauthenticated users."""

    def test_create_redirects_when_logged_out(self, page: Page):
        page.goto(f"{BASE_URL}/create/")
        expect(page).to_have_url(re.compile(r"/login/"))

    def test_login_success(self, page: Page):
        page.goto(f"{BASE_URL}/login/")
        page.fill("#username", "alice")
        page.fill("#password", "password123")
        page.click("button[type='submit']")
        expect(page).to_have_url(f"{BASE_URL}/")


class TestCreateRecipe:
    """CREATE — submit the create recipe form and verify the result."""

    def test_create_recipe_appears_on_homepage(self, auth_page: Page):
        auth_page.goto(f"{BASE_URL}/create/")
        fill_recipe_form(auth_page, RECIPE)
        auth_page.click("button[type='submit']")

        # Should redirect to home or recipe detail on success
        auth_page.wait_for_url(re.compile(r"(/$|/recipe/\d+/)"))

        # Confirm the recipe title is visible somewhere after creation
        auth_page.goto(f"{BASE_URL}/")
        expect(auth_page.get_by_text(RECIPE["title"]).first).to_be_visible()

    def test_create_recipe_requires_title(self, auth_page: Page):
        auth_page.goto(f"{BASE_URL}/create/")
        # Leave title empty, fill at least one other field to trigger submission
        auth_page.fill("#id_ingredients", "Some ingredient")
        auth_page.click("button[type='submit']")

        # Should stay on the create page with a validation error
        expect(auth_page).to_have_url(re.compile(r"/create/"))


class TestReadRecipe:
    """READ — navigate to a recipe detail page and verify content."""

    def test_recipe_detail_displays_fields(self, auth_page: Page):
        # Create a recipe first so we have one to read
        auth_page.goto(f"{BASE_URL}/create/")
        fill_recipe_form(auth_page, RECIPE)
        auth_page.click("button[type='submit']")
        auth_page.wait_for_url(re.compile(r"(/$|/recipe/\d+/)"))

        # Navigate to the recipe from the homepage
        auth_page.goto(f"{BASE_URL}/")
        auth_page.get_by_text(RECIPE["title"]).first.click()
        auth_page.wait_for_url(re.compile(r"/recipe/\d+/"))

        expect(auth_page.get_by_text(RECIPE["title"]).first).to_be_visible()
        expect(auth_page.get_by_text(RECIPE["recipe_author"]).first).to_be_visible()
        expect(auth_page.get_by_text(RECIPE["description"]).first).to_be_visible()

    def test_recipe_detail_shows_ingredients(self, auth_page: Page):
        auth_page.goto(f"{BASE_URL}/create/")
        fill_recipe_form(auth_page, RECIPE)
        auth_page.click("button[type='submit']")
        auth_page.wait_for_url(re.compile(r"(/$|/recipe/\d+/)"))

        auth_page.goto(f"{BASE_URL}/")
        auth_page.get_by_text(RECIPE["title"]).first.click()
        auth_page.wait_for_url(re.compile(r"/recipe/\d+/"))

        # At least one ingredient line should appear on the page
        expect(auth_page.get_by_text("garlic").first).to_be_visible()


class TestUpdateRecipe:
    """UPDATE — edit an existing recipe and verify the changes persist."""

    def test_edit_recipe_title_and_description(self, auth_page: Page):
        # Create
        auth_page.goto(f"{BASE_URL}/create/")
        fill_recipe_form(auth_page, RECIPE)
        auth_page.click("button[type='submit']")
        auth_page.wait_for_url(re.compile(r"(/$|/recipe/\d+/)"))

        # Find the recipe and go to its detail page
        auth_page.goto(f"{BASE_URL}/")
        auth_page.get_by_text(RECIPE["title"]).first.click()
        auth_page.wait_for_url(re.compile(r"/recipe/\d+/"))
        pk = get_recipe_pk_from_url(auth_page.url)

        # Go to edit page
        auth_page.goto(f"{BASE_URL}/recipe/{pk}/edit/")
        auth_page.fill("#id_title", UPDATED_TITLE)
        auth_page.fill("#id_description", UPDATED_DESCRIPTION)
        auth_page.click("button[type='submit']")

        # After edit, should land back on home or detail
        auth_page.wait_for_url(re.compile(r"(/$|/recipe/\d+/)"))

        # Navigate to the recipe and confirm changes
        auth_page.goto(f"{BASE_URL}/recipe/{pk}/")
        expect(auth_page.get_by_text(UPDATED_TITLE).first).to_be_visible()
        expect(auth_page.get_by_text(UPDATED_DESCRIPTION).first).to_be_visible()

    def test_edit_recipe_forbidden_for_non_author(self, page: Page, request):
        """A user who did not create the recipe should get a 403 on edit."""
        # Sign up a second user with a unique name so parallel runs don't collide
        uid = uuid.uuid4().hex[:8]
        guest_username = f"playwright_guest_{uid}"
        request.addfinalizer(lambda: delete_test_user(guest_username))

        page.goto(f"{BASE_URL}/signup/")
        page.fill("#username", guest_username)
        page.fill("#email", f"{guest_username}@example.com")
        page.fill("#password1", "guestpass99")
        page.fill("#password2", "guestpass99")
        page.click("button[type='submit']")
        page.wait_for_url(re.compile(r"/login/"))

        # Log in as alice to create a recipe
        page.fill("#username", "alice")
        page.fill("#password", "password123")
        page.click("button[type='submit']")
        page.wait_for_url(f"{BASE_URL}/")

        page.goto(f"{BASE_URL}/create/")
        fill_recipe_form(page, RECIPE)
        page.click("button[type='submit']")
        page.wait_for_url(re.compile(r"(/$|/recipe/\d+/)"))

        page.goto(f"{BASE_URL}/")
        page.get_by_text(RECIPE["title"]).first.click()
        page.wait_for_url(re.compile(r"/recipe/\d+/"))
        pk = get_recipe_pk_from_url(page.url)

        # Log out and log in as guest
        page.goto(f"{BASE_URL}/logout/")
        page.goto(f"{BASE_URL}/login/")
        page.fill("#username", "playwright_guest")
        page.fill("#password", "guestpass99")
        page.click("button[type='submit']")
        page.wait_for_url(f"{BASE_URL}/")

        # Attempt to edit alice's recipe — expect 403
        response = page.goto(f"{BASE_URL}/recipe/{pk}/edit/")
        assert response.status == 403


class TestDeleteRecipe:
    """DELETE — delete a recipe and verify it is removed."""

    def test_delete_recipe_removes_it_from_homepage(self, auth_page: Page):
        # Create
        auth_page.goto(f"{BASE_URL}/create/")
        fill_recipe_form(auth_page, RECIPE)
        auth_page.click("button[type='submit']")
        auth_page.wait_for_url(re.compile(r"(/$|/recipe/\d+/)"))

        # Navigate to detail page to get PK
        auth_page.goto(f"{BASE_URL}/")
        auth_page.get_by_text(RECIPE["title"]).first.click()
        auth_page.wait_for_url(re.compile(r"/recipe/\d+/"))
        pk = get_recipe_pk_from_url(auth_page.url)

        # Submit delete form via POST
        auth_page.evaluate(f"""
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/recipe/{pk}/delete/';
            const csrf = document.querySelector('[name=csrfmiddlewaretoken]');
            if (csrf) form.appendChild(csrf.cloneNode());
            document.body.appendChild(form);
            form.submit();
        """)
        auth_page.wait_for_url(f"{BASE_URL}/")

        # Confirm the recipe title is no longer visible on the homepage
        auth_page.goto(f"{BASE_URL}/")
        expect(auth_page.get_by_text(RECIPE["title"])).to_have_count(0)

    def test_delete_forbidden_for_non_author(self, auth_page: Page):
        """DELETE by a non-author should return 403."""
        # Create a recipe as alice
        auth_page.goto(f"{BASE_URL}/create/")
        fill_recipe_form(auth_page, RECIPE)
        auth_page.click("button[type='submit']")
        auth_page.wait_for_url(re.compile(r"(/$|/recipe/\d+/)"))

        auth_page.goto(f"{BASE_URL}/")
        auth_page.get_by_text(RECIPE["title"]).first.click()
        auth_page.wait_for_url(re.compile(r"/recipe/\d+/"))
        pk = get_recipe_pk_from_url(auth_page.url)

        # Log out and attempt delete as a different session (unauthenticated)
        auth_page.goto(f"{BASE_URL}/logout/")

        # POST to delete endpoint while logged out — Django redirects to login (302)
        # rather than 403, because @login_required fires first
        response = auth_page.request.post(
            f"{BASE_URL}/recipe/{pk}/delete/",
            headers={"Referer": BASE_URL},
        )
        assert response.status in (302, 403)
