"""
Persona 1 — Jerry Smith
Student, new to cooking, wants to find and save a quick recipe using search and filters.

Run: pytest e2e/test_persona_jerry.py -v
"""

import re
import uuid
import pytest
from playwright.sync_api import Page, expect
from conftest import delete_test_user

BASE_URL = "http://localhost:8000"


@pytest.fixture()
def jerry(page: Page):
    """Sign up and log in as a fresh Jerry Smith account, then delete it after the test."""
    uid = uuid.uuid4().hex[:8]
    username = f"jerry_{uid}"
    password = "Jerrypass99"

    # Sign up — redirects straight to home on success
    page.goto(f"{BASE_URL}/signup/")
    page.fill("#username", username)
    page.fill("#email", f"{username}@example.com")
    page.fill("#password1", password)
    page.fill("#password2", password)
    page.click("button[type='submit']")
    page.wait_for_url(f"{BASE_URL}/")

    yield page

    delete_test_user(username)


class TestJerrySmith:

    def test_signup_and_login(self, page: Page, request):
        """Jerry can register a new account and land on the homepage."""
        uid = uuid.uuid4().hex[:8]
        username = f"jerry_{uid}"
        request.addfinalizer(lambda: delete_test_user(username))
        page.goto(f"{BASE_URL}/signup/")
        page.fill("#username", username)
        page.fill("#email", f"{username}@example.com")
        page.fill("#password1", "Jerrypass99")
        page.fill("#password2", "Jerrypass99")
        page.click("button[type='submit']")
        # Signup logs the user in immediately and redirects to home
        expect(page).to_have_url(f"{BASE_URL}/")

    def test_search_for_recipe(self, jerry: Page):
        """Jerry types a search term and gets filtered results."""
        jerry.goto(f"{BASE_URL}/")
        jerry.fill("input[name='q']", "pasta")
        jerry.press("input[name='q']", "Enter")
        jerry.wait_for_load_state("networkidle")

        # URL should reflect the search query
        expect(jerry).to_have_url(re.compile(r"q=pasta"))

    def test_apply_cuisine_filter(self, jerry: Page):
        """Jerry opens the cuisine dropdown and selects the first available option."""
        jerry.goto(f"{BASE_URL}/")

        # Open the custom cuisine dropdown
        jerry.click("#cuisineDisplay")
        jerry.wait_for_selector("#cuisineDropdown .select-option")

        # Click the first non-"All Cuisines" option
        options = jerry.query_selector_all("#cuisineDropdown .select-option")
        non_default = [o for o in options if o.inner_text().strip() != "All Cuisines"]
        assert non_default, "No cuisine options available to select"
        non_default[0].click()

        # Submit the filter form
        jerry.click("button.btn-filter")
        jerry.wait_for_load_state("networkidle")

        # A cuisine filter chip should now be visible
        expect(jerry.locator(".filter-chip").first).to_be_visible()

    def test_apply_time_filter(self, jerry: Page):
        """Jerry filters recipes to under 30 minutes."""
        jerry.goto(f"{BASE_URL}/")

        # Open the custom time dropdown
        jerry.click("#timeDisplay")
        jerry.wait_for_selector("#timeDropdown .select-option")
        jerry.locator("#timeDropdown .select-option", has_text="Under 30 min").click()

        jerry.click("button.btn-filter")
        jerry.wait_for_load_state("networkidle")

        expect(jerry).to_have_url(re.compile(r"max_time=30"))

    def test_apply_dietary_filter(self, jerry: Page):
        """Jerry checks a dietary restriction checkbox."""
        jerry.goto(f"{BASE_URL}/")

        # Open the dietary multi-select dropdown
        jerry.click("#dietaryDisplay")
        jerry.wait_for_selector("#dietaryDropdown input[type='checkbox']")

        checkboxes = jerry.query_selector_all("#dietaryDropdown input[type='checkbox']")
        assert checkboxes, "No dietary filter options available"
        checkboxes[0].check()

        jerry.click("button.btn-filter")
        jerry.wait_for_load_state("networkidle")

        expect(jerry).to_have_url(re.compile(r"dietary="))

    def test_view_recipe_detail(self, jerry: Page):
        """Jerry clicks a recipe card and the detail page loads with content."""
        # Create a recipe first so the homepage is not empty
        jerry.goto(f"{BASE_URL}/create/")
        jerry.fill("#id_title", "Jerry Test Soup")
        jerry.fill("#id_description", "A simple test soup.")
        jerry.fill("#id_ingredients", "1 potato\n2 cups water")
        jerry.fill("#id_steps_text", "1. Boil potato in water for 20 minutes.")
        jerry.click("button[type='submit']")
        jerry.wait_for_url(f"{BASE_URL}/")

        jerry.wait_for_selector(".recipe-card-title")
        jerry.locator(".recipe-card-title").first.click()
        jerry.wait_for_url(re.compile(r"/recipe/\d+/"))

        expect(jerry.locator("h1, h2").first).to_be_visible()

    def test_save_recipe_from_card(self, jerry: Page):
        """Jerry saves a recipe from the homepage card."""
        jerry.goto(f"{BASE_URL}/create/")
        jerry.fill("#id_title", "Jerry Saveable Recipe")
        jerry.fill("#id_description", "A saveable test recipe.")
        jerry.fill("#id_ingredients", "1 cup rice\n2 cups water")
        jerry.fill("#id_steps_text", "1. Cook rice in water for 18 minutes.")
        jerry.click("button[type='submit']")
        jerry.wait_for_url(f"{BASE_URL}/")

        jerry.goto(f"{BASE_URL}/")
        jerry.wait_for_selector("button.btn-save")

        save_btn = jerry.locator("button.btn-save:not([disabled])").first
        expect(save_btn).to_be_visible()
        save_btn.click()
        jerry.wait_for_load_state("networkidle")

        expect(jerry.locator("button.btn-save.saved, button.btn-save[disabled]").first).to_be_visible()
