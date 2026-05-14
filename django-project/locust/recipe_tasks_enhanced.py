import time
import json
from datetime import datetime
from locust import HttpUser, task, between, events
from bs4 import BeautifulSoup

# Global metrics storage
metrics = {
    "errors": {
        "timeouts": 0,
        "500_errors": 0,
        "409_conflicts": 0,
        "other_errors": 0
    },
    "data_inconsistencies": [],
    "slow_requests": [],
    "response_times": [],
    "start_time": None,
    "end_time": None
}


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize metrics when test starts"""
    metrics["start_time"] = datetime.now()
    print("=" * 60)
    print("LOAD TEST STARTED")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate comprehensive report when test stops"""
    metrics["end_time"] = datetime.now()
    duration = (metrics["end_time"] - metrics["start_time"]).total_seconds()

    print("\n" + "=" * 60)
    print("LOAD TEST COMPLETED - MILESTONE 2 METRICS REPORT")
    print("=" * 60)

    # Error rates
    print("\n--- ERROR RATES ---")
    print(f"Timeouts: {metrics['errors']['timeouts']}")
    print(f"500 Errors: {metrics['errors']['500_errors']}")
    print(f"409 Conflicts (expected): {metrics['errors']['409_conflicts']}")
    print(f"Other Errors: {metrics['errors']['other_errors']}")

    total_errors = sum(metrics['errors'].values())
    stats = environment.stats
    total_requests = stats.total.num_requests
    if total_requests > 0:
        error_rate = (total_errors / total_requests) * 100
        print(f"Total Error Rate: {error_rate:.2f}%")

    # Performance metrics
    print("\n--- PERFORMANCE METRICS ---")
    print(f"Test Duration: {duration:.2f} seconds")
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Failed Requests: {stats.total.num_failures}")
    print(f"Requests per Second: {stats.total.total_rps:.2f}")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"Median Response Time: {stats.total.median_response_time:.2f}ms")
    print(f"95th Percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99th Percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")

    # Slow requests
    print("\n--- SLOW REQUESTS (>2000ms) ---")
    if metrics['slow_requests']:
        print(f"Count: {len(metrics['slow_requests'])}")
        for req in metrics['slow_requests'][:10]:  # Show first 10
            print(f"  {req['endpoint']}: {req['time']:.2f}ms")
    else:
        print("No slow requests detected")

    # Data inconsistencies
    print("\n--- DATA INCONSISTENCIES ---")
    if metrics['data_inconsistencies']:
        print(f"Count: {len(metrics['data_inconsistencies'])}")
        for issue in metrics['data_inconsistencies'][:5]:  # Show first 5
            print(f"  Recipe {issue['recipe_id']}: {issue['issue']}")
    else:
        print("No data inconsistencies detected")

    # Save detailed report to file
    save_detailed_report(environment)


def save_detailed_report(environment):
    """Save detailed metrics to JSON file"""
    report = {
        "test_info": {
            "start_time": metrics["start_time"].isoformat(),
            "end_time": metrics["end_time"].isoformat(),
            "duration_seconds": (metrics["end_time"] - metrics["start_time"]).total_seconds()
        },
        "errors": metrics["errors"],
        "data_inconsistencies": metrics["data_inconsistencies"],
        "slow_requests": metrics["slow_requests"],
        "performance": {
            "total_requests": environment.stats.total.num_requests,
            "failed_requests": environment.stats.total.num_failures,
            "requests_per_second": environment.stats.total.total_rps,
            "avg_response_time": environment.stats.total.avg_response_time,
            "median_response_time": environment.stats.total.median_response_time,
            "95th_percentile": environment.stats.total.get_response_time_percentile(0.95),
            "99th_percentile": environment.stats.total.get_response_time_percentile(0.99)
        }
    }

    with open("milestone2_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\n--- Detailed report saved to: milestone2_report.json ---")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, exception, **kwargs):
    """Track detailed metrics for each request"""

    # Track slow requests (>2 seconds)
    if response_time > 2000:
        metrics['slow_requests'].append({
            "endpoint": name,
            "time": response_time,
            "timestamp": datetime.now().isoformat()
        })

    # Track specific error types
    if exception:
        if "timeout" in str(exception).lower():
            metrics['errors']['timeouts'] += 1
        else:
            metrics['errors']['other_errors'] += 1
    elif response:
        if response.status_code == 500:
            metrics['errors']['500_errors'] += 1
        elif response.status_code == 409:
            metrics['errors']['409_conflicts'] += 1


class RecipeUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.recipe_ids = []
        self.created_recipes = {}  # Track expected data for consistency checks
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

    def on_stop(self):
        """Clean up all created recipes before exiting"""
        print(f"\n[Cleanup] User stopping. Cleaning up {len(self.recipe_ids)} remaining recipes...")

        cleanup_count = 0
        failed_cleanup = 0

        # Delete all remaining recipes
        while self.recipe_ids:
            recipe_id = self.recipe_ids.pop(0)
            try:
                csrf_token = self.get_csrf_token(f"/recipe/{recipe_id}/edit/")
                response = self.client.post(
                    f"/recipe/{recipe_id}/delete/",
                    {"csrfmiddlewaretoken": csrf_token},
                    headers={"Referer": f"/recipe/{recipe_id}/delete/"},
                    allow_redirects=False,
                )

                if response.status_code == 302:
                    cleanup_count += 1
                    if recipe_id in self.created_recipes:
                        del self.created_recipes[recipe_id]
                else:
                    failed_cleanup += 1

            except Exception as e:
                failed_cleanup += 1
                print(f"[Cleanup] Failed to delete recipe {recipe_id}: {e}")

        print(f"[Cleanup] Successfully deleted {cleanup_count} recipes")
        if failed_cleanup > 0:
            print(f"[Cleanup] Failed to delete {failed_cleanup} recipes")

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
                name="POST /login/"
        ) as response:
            if response.status_code != 302:
                response.failure(f"Login failed with status {response.status_code}")

    @task(3)
    def create_recipe(self):
        """Create a new recipe and track expected data"""
        csrf_token = self.get_csrf_token("/create/")
        response = self.client.get(f"/create/")
        soup = BeautifulSoup(response.text, "html.parser")
        updated_at = soup.find("input", {"name": "updated_at"})['value']
        # Use unique title with timestamp for tracking
        timestamp = int(time.time() * 1000)
        title = f"Load Test Recipe {timestamp}"

        payload = {
            "title": title,
            "description": "Testing Locust for Milestone 2",
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
                    # Track expected data for consistency checks
                    self.created_recipes[recipe_id] = {
                        "title": title,
                        "description": payload["description"],
                        "prep_time": payload["prep_time"],
                        "cook_time": payload["cook_time"]
                    }
                    response.success()
            else:
                response.failure(f"Create failed with status {response.status_code}")

    @task(5)
    def view_recipe(self):
        """View a recipe - most common operation (read-heavy workload)"""
        if not self.recipe_ids:
            return

        recipe_id = self.recipe_ids[-1]
        with self.client.get(
                f"/recipe/{recipe_id}/",
                name="/view/",
                catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"View failed with status {response.status_code}")

    @task(2)
    def verify_recipe_consistency(self):
        """Verify recipe data hasn't been corrupted by concurrent operations"""
        if not self.recipe_ids or not self.created_recipes:
            return

        recipe_id = self.recipe_ids[-1]

        # Skip if we haven't created this recipe
        if recipe_id not in self.created_recipes:
            return

        expected = self.created_recipes[recipe_id]

        with self.client.get(
                f"/recipe/{recipe_id}/",
                name="/verify-consistency/",
                catch_response=True
        ) as response:
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")

                # Check if expected fields are present and valid
                inconsistencies = []

                # Example checks - adjust based on your HTML structure
                title_elem = soup.find("h1") or soup.find("title")
                if title_elem and expected["title"] not in title_elem.get_text():
                    inconsistencies.append("Title mismatch")

                # Check for required fields existence
                if not soup.find(text=lambda t: "ingredients" in str(t).lower()):
                    inconsistencies.append("Missing ingredients section")

                if not soup.find(text=lambda t: "steps" in str(t).lower() or "instructions" in str(t).lower()):
                    inconsistencies.append("Missing steps/instructions section")

                if inconsistencies:
                    for issue in inconsistencies:
                        metrics['data_inconsistencies'].append({
                            "recipe_id": recipe_id,
                            "issue": issue,
                            "timestamp": datetime.now().isoformat()
                        })
                    response.failure(f"Data inconsistency: {', '.join(inconsistencies)}")
                else:
                    response.success()
            else:
                response.failure(f"Consistency check failed with status {response.status_code}")

    @task(2)
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

        new_title = f"Edited Recipe {int(time.time() * 1000)}"

        payload = {
            "title": new_title,
            "description": "Edited description - Milestone 2",
            "recipe_author": "testuser",
            "source_url": "https://example.com/recipe",
            "image_url": "https://example.com/image.jpg",
            "ingredients": "2 cups flour\n2 eggs",
            "prep_time": 10,
            "cook_time": 15,
            "tags_csv": "test,locust,edited",
            "steps_text": "Mix ingredients\nBake at 375F",
            "csrfmiddlewaretoken": csrf_token,
            "updated_at": updated_at,
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
                # Update tracked data
                if recipe_id in self.created_recipes:
                    self.created_recipes[recipe_id]["title"] = new_title
                    self.created_recipes[recipe_id]["description"] = payload["description"]
                response.success()
            elif response.status_code == 409:
                response.failure("Conflict: concurrent edit detected")
            elif response.status_code == 403:
                response.failure("Forbidden: not the author")
            else:
                response.failure(f"Unexpected status {response.status_code}")

    @task(1)
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
            if response.status_code == 302:
                # Remove from tracking
                if recipe_id in self.created_recipes:
                    del self.created_recipes[recipe_id]
                response.success()
            else:
                response.failure(f"Delete failed with status {response.status_code}")

    @task(1)
    def conflicting_edit(self):
        """Simulate a concurrency conflict by using a stale updated_at timestamp"""
        if not self.recipe_ids:
            return

        recipe_id = self.recipe_ids[-1]

        # Step 1: Fetch current form
        page = self.client.get(f"/recipe/{recipe_id}/edit/")
        soup = BeautifulSoup(page.text, "html.parser")

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

        # Simulate real-world delay
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
            if response.status_code == 409:
                response.success()  # This is the expected behavior
            else:
                response.failure(
                    f"Expected 409 Conflict due to concurrency, got {response.status_code}"
                )