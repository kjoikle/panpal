import time

from locust import HttpUser, task, between
from bs4 import BeautifulSoup

class RecipeUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.recipe_ids = []
        self.login()

    def get_csrf_token(self, url):
        """Fetch CSRF token from cookie or HTML input"""
        response = self.client.get(url, name=f"GET {url}")
        # Try cookie first
        csrf_token = self.client.cookies.get("csrftoken")
        if csrf_token:
            return csrf_token
        # Fallback: parse HTML input
        soup = BeautifulSoup(response.text, "html.parser")
        csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
        if csrf_input:
            return csrf_input["value"]
        raise Exception(f"CSRF token not found at {url}")

    def login(self):
        """Perform login"""
        csrf_token = self.get_csrf_token("/login/")
        with self.client.post(
            "/login/",
            {
                "username": "testuser",
                "password": "123456",
                "csrfmiddlewaretoken": csrf_token
            },
            headers={"Referer": "/login/"},
            allow_redirects=False,
            catch_response=True,
            name="/login/"
        ) as response:
            if response.status_code != 302:
                response.failure(f"Login failed with status {response.status_code}")

    @task
    def create_recipe(self):
        """Create a new recipe (no updated_at needed)"""
        csrf_token = self.get_csrf_token("/create/")
        response = self.client.get(f"/create/")
        soup = BeautifulSoup(response.text, "html.parser")
        updated_at = soup.find("input", {"name": "updated_at"})['value']
        payload = {
            "title": "Load Test Recipe",
            "description": "Testing Locust",
            "source_url": "https://example.com/recipe",
            "image_url": "https://example.com/image.jpg",
            "ingredients": "1 cup flour\n1 egg",
            "prep_time": 5,
            "cook_time": 10,
            "tags_csv": "test,locust",
            "steps_text": "Mix ingredients\nBake at 350F",
            "csrfmiddlewaretoken": csrf_token,
            "updated_at": updated_at,
        }

        with self.client.post(
            "/create/",
            payload,
            headers={"Referer": "/create/", "Accept": "application/json"},
            name="POST /create/",
            catch_response=True
        ) as response:
            if response.status_code == 201:
                recipe_id = response.json().get("id")
                if recipe_id:
                    self.recipe_ids.append(recipe_id)
            else:
                response.failure(f"Create failed with status {response.status_code}")

    @task
    def edit_recipe(self):
        """Edit the last created recipe using updated_at for concurrency"""
        if not self.recipe_ids:
            return

        recipe_id = self.recipe_ids[-1]

        response = self.client.get(f"/recipe/{recipe_id}/edit/")
        soup = BeautifulSoup(response.text, "html.parser")

        csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
        updated_input = soup.find("input", {"name": "updated_at"})

        if not csrf_input or not updated_input:
            return  # Could not get form; skip

        csrf_token = csrf_input["value"]
        updated_at = updated_input["value"]

        payload = {
            "title": "Edited Recipe",
            "description": "Edited description",
            "recipe_author": "testuser",
            "source_url": "https://example.com/recipe",
            "image_url": "https://example.com/image.jpg",
            "ingredients": "1 cup flour\n1 egg",
            "prep_time": 5,
            "cook_time": 10,
            "tags_csv": "test,locust",
            "steps_text": "Mix ingredients\nBake at 350F",
            "csrfmiddlewaretoken": csrf_token,
            "updated_at": updated_at,  # REQUIRED for edit
        }

        with self.client.post(
                f"/recipe/{recipe_id}/edit/",
                payload,
                headers={"Referer": f"/recipe/{recipe_id}/edit/"},
                catch_response=True,
                allow_redirects=False,
                name="/edit/",
        ) as response:
            if response.status_code == 302:
                return
            if response.status_code == 409:
                response.failure("Conflict: concurrent edit detected")
            elif response.status_code == 403:
                response.failure("Forbidden: not the author")
            else:
                response.failure(f"Unexpected status {response.status_code}")

    @task
    def delete_recipe(self):
        """Delete the oldest recipe"""
        if not self.recipe_ids:
            return

        recipe_id = self.recipe_ids.pop(0)
        csrf_token = self.get_csrf_token(f"/recipe/{recipe_id}/edit/")

        with self.client.post(
            f"/recipe/{recipe_id}/delete/",
            {"csrfmiddlewaretoken": csrf_token},
            headers={"Referer": f"/recipe/{recipe_id}/delete/"},
            catch_response=True,
            allow_redirects=False,
            name="/delete/",
        ) as response:
            if response.status_code != 302:
                response.failure(f"Delete failed with status {response.status_code}")

    @task
    def conflicting_edit(self):
        """Simulate a concurrency conflict by using a stale updated_at timestamp"""
        if not self.recipe_ids:
            return  # no recipe to edit

        recipe_id = self.recipe_ids[-1]

        # Step 1: Fetch current form
        page = self.client.get(f"/recipe/{recipe_id}/edit/")
        soup = BeautifulSoup(page.text, "html.parser")

        # csrf = soup.find("input", {"name": "csrfmiddlewaretoken"})["value"]
        csrf_token = self.get_csrf_token(f"/recipe/{recipe_id}/edit/")
        ts = soup.find("input", {"name": "updated_at"})["value"]

        # Step 2: First edit (simulating User A)
        self.client.post(
            f"/recipe/{recipe_id}/edit/",
            {
                "title": "User A edit",
                "description": "Edited by User A",
                "recipe_author": "testuser",
                "source_url": "https://example.com/recipe",
                "image_url": "https://example.com/image.jpg",
                "ingredients": "1 cup flour\n1 egg",
                "prep_time": 5,
                "cook_time": 10,
                "tags_csv": "test,locust",
                "steps_text": "Mix ingredients\nBake at 350F",
                "csrfmiddlewaretoken": csrf_token,
                "updated_at": ts,
            },
            catch_response=True,
            allow_redirects=False,
        )

        # Optional: simulate real-world delay
        time.sleep(0.5)

        # Step 3: Second edit with stale timestamp (User B)
        with self.client.post(
                f"/recipe/{recipe_id}/edit/",
                {
                    "title": "User B edit",
                    "description": "Edited by User B",
                    "recipe_author": "testuser",
                    "source_url": "https://example.com/recipe",
                    "image_url": "https://example.com/image.jpg",
                    "ingredients": "1 cup flour\n1 egg",
                    "prep_time": 5,
                    "cook_time": 10,
                    "tags_csv": "test,locust",
                    "steps_text": "Mix ingredients\nBake at 350F",
                    "csrfmiddlewaretoken": csrf_token,
                    "updated_at": ts,  # stale timestamp
                },
                catch_response=True,
                allow_redirects=False,
                name="/edit-conflict/",
        ) as response:
            if response.status_code != 409:
                response.failure(
                    f"Expected 409 Conflict due to concurrency, got {response.status_code}"
                )
            else:
                response.success()