"""Quick diagnostic: checks if startKitchenCopilot is defined and logs JS errors on the recipe detail page."""
import re
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8000"

RECIPE_HTML = """\
<!DOCTYPE html>
<html>
<head>
  <title>Shaun's Test Mushroom Pasta</title>
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Recipe",
    "name": "Shaun's Test Mushroom Pasta",
    "author": {"@type": "Person", "name": "Shaun"},
    "description": "A quick and creamy mushroom pasta.",
    "prepTime": "PT10M",
    "cookTime": "PT20M",
    "recipeIngredient": ["200g spaghetti", "250g mushrooms"],
    "recipeInstructions": [
      {"@type": "HowToStep", "text": "Cook spaghetti."},
      {"@type": "HowToStep", "text": "Fry mushrooms."}
    ]
  }
  </script>
</head>
<body><h1>Shaun's Test Mushroom Pasta</h1></body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = RECIPE_HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


server = HTTPServer(("0.0.0.0", 0), Handler)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()
recipe_url = f"http://host.docker.internal:{port}/recipe"

uid = uuid.uuid4().hex[:8]
username = f"shaun_diag_{uid}"
password = "Shaunpass99"

errors = []
console_msgs = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("pageerror", lambda e: errors.append(f"PAGEERROR [{page.url}]: {e}"))
    page.on("console", lambda m: console_msgs.append(f"[{m.type}] {m.text}"))

    # Sign up
    page.goto(f"{BASE_URL}/signup/")
    page.fill("#username", username)
    page.fill("#email", f"{username}@example.com")
    page.fill("#password1", password)
    page.fill("#password2", password)
    page.click("button[type='submit']")
    page.wait_for_url(f"{BASE_URL}/")

    # Import
    page.goto(f"{BASE_URL}/import/")
    page.fill("#url", recipe_url)
    page.click("button[type='submit']")
    page.wait_for_selector("#id_title", timeout=30_000)
    title = page.input_value("#id_title")
    page.click("button[type='submit']")
    page.wait_for_url(f"{BASE_URL}/")
    page.get_by_text(title).first.click()
    page.wait_for_url(re.compile(r"/recipe/\d+/"))

    ws_events = []
    page.on("websocket", lambda ws: ws_events.append(f"WS created: {ws.url}"))

    page.wait_for_load_state("networkidle")
    print(f"URL: {page.url}")
    # Write what Playwright sees to a file for inspection
    with open("/tmp/playwright_page.html", "w") as f:
        f.write(page.content())
    print("Page HTML written to /tmp/playwright_page.html")
    fn_type = page.evaluate("typeof startKitchenCopilot")
    print(f"startKitchenCopilot type : {fn_type}")

    # Click the button and wait a moment
    page.click("#copilot-start-btn")
    page.wait_for_timeout(5000)

    print(f"WS events after click    : {ws_events or 'none'}")

    # Try calling it directly
    try:
        result = page.evaluate("startKitchenCopilot(); 'called'")
        print(f"Direct evaluate call     : {result}")
    except Exception as e:
        print(f"Direct evaluate error    : {e}")

    page.wait_for_timeout(3000)
    print(f"WS events after evaluate : {ws_events or 'none'}")

    if errors:
        print("\n--- JS errors ---")
        for e in errors:
            print(e)
    else:
        print("\nNo JS errors.")

    if console_msgs:
        print("\n--- Console ---")
        for m in console_msgs:
            print(m)

    browser.close()

server.shutdown()
