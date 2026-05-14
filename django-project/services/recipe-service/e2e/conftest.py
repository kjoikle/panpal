import subprocess
from pathlib import Path

import pytest
from playwright.sync_api import Page

# Path to the directory containing docker-compose.yml
_DOCKER_COMPOSE_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Disable COOP enforcement so Playwright can interact with pages that set
    Cross-Origin-Opener-Policy: same-origin (Django 4.x default)."""
    return {
        **browser_type_launch_args,
        "args": [
            *(browser_type_launch_args.get("args") or []),
            "--disable-features=CrossOriginOpenerPolicy",
        ],
    }

BASE_URL = "http://localhost:8000"

# Demo credentials seeded in the dev database
TEST_USER = "alice"
TEST_PASSWORD = "password123"


def delete_test_user(username: str) -> None:
    """Delete a user from the database via the running recipe-service container."""
    subprocess.run(
        [
            "docker-compose", "exec", "-T", "recipe-service",
            "python", "manage.py", "shell", "-c",
            (
                "from django.contrib.auth import get_user_model; "
                "User = get_user_model(); "
                f"User.objects.filter(username='{username}').delete()"
            ),
        ],
        cwd=_DOCKER_COMPOSE_DIR,
        capture_output=True,
    )


def login(page: Page) -> None:
    """Log in as the test user."""
    page.goto(f"{BASE_URL}/login/")
    page.fill("#username", TEST_USER)
    page.fill("#password", TEST_PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_url(f"{BASE_URL}/")


@pytest.fixture()
def auth_page(page: Page) -> Page:
    """Return a page that is already logged in."""
    login(page)
    return page
