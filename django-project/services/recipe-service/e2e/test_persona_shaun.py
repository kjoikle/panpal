"""
Persona 3 — Shaun
Busy consultant, high technical proficiency, uses the recipe import feature
and Kitchen Copilot (verifies both OpenAI LLM and ElevenLabs TTS integrations).

Prerequisites:
  - recipe-service running at http://localhost:8000
  - copilot-service running and reachable via WebSocket
  - OPENAI_API_KEY and ELEVENLABS_API_KEY set in the copilot service environment

Run: pytest e2e/test_persona_shaun.py -v
"""

import re
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from playwright.sync_api import Page, expect
from conftest import delete_test_user

BASE_URL = "http://localhost:8000"

COPILOT_TIMEOUT = 20_000   # ms — LLM responses can take a few seconds
TTS_TIMEOUT     = 15_000   # ms — ElevenLabs audio may take a moment to arrive

# Minimal recipe page with schema.org JSON-LD — served locally so the
# scraper never needs to hit an external site.
_RECIPE_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Shaun's Test Mushroom Pasta</title>
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Recipe",
    "name": "Shaun's Test Mushroom Pasta",
    "author": {"@type": "Person", "name": "Shaun"},
    "description": "A quick and creamy mushroom pasta perfect for weeknights.",
    "prepTime": "PT10M",
    "cookTime": "PT20M",
    "recipeIngredient": [
      "200g spaghetti",
      "250g mushrooms, sliced",
      "2 cloves garlic",
      "150ml double cream",
      "Salt and pepper to taste"
    ],
    "recipeInstructions": [
      {"@type": "HowToStep", "text": "Cook spaghetti in salted boiling water until al dente."},
      {"@type": "HowToStep", "text": "Fry garlic and mushrooms in butter until golden."},
      {"@type": "HowToStep", "text": "Add cream, season, and toss with drained pasta."}
    ]
  }
  </script>
</head>
<body><h1>Shaun's Test Mushroom Pasta</h1></body>
</html>"""


@pytest.fixture(scope="session")
def local_recipe_server():
    """Spin up a tiny HTTP server that serves a single recipe page."""
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = _RECIPE_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass  # suppress request logs during tests

    server = HTTPServer(("0.0.0.0", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://host.docker.internal:{port}/recipe"
    server.shutdown()


@pytest.fixture()
def shaun(page: Page):
    """Sign up and log in as a fresh Shaun account, then delete it after the test."""
    uid = uuid.uuid4().hex[:8]
    username = f"shaun_{uid}"
    password = "Shaunpass99"

    page.goto(f"{BASE_URL}/signup/")
    page.fill("#username", username)
    page.fill("#email", f"{username}@example.com")
    page.fill("#password1", password)
    page.fill("#password2", password)
    page.click("button[type='submit']")
    page.wait_for_url(f"{BASE_URL}/")

    yield page

    delete_test_user(username)


class TestShaun:

    def test_import_page_loads(self, shaun: Page):
        """Shaun can navigate to the import recipe page."""
        shaun.goto(f"{BASE_URL}/import/")
        expect(shaun.locator("#url")).to_be_visible()

    def test_import_recipe_populates_form(self, shaun: Page, local_recipe_server: str):
        """Submitting a locally-served recipe URL pre-fills the review form."""
        shaun.goto(f"{BASE_URL}/import/")
        shaun.fill("#url", local_recipe_server)
        shaun.click("button[type='submit']")

        shaun.wait_for_selector("#id_title", timeout=30_000)

        title_value = shaun.input_value("#id_title")
        assert title_value.strip() != "", (
            "Expected the scraper to populate the recipe title, but #id_title was empty."
        )

    def test_import_recipe_saves_successfully(self, shaun: Page, local_recipe_server: str):
        """Shaun reviews and saves the imported recipe."""
        shaun.goto(f"{BASE_URL}/import/")
        shaun.fill("#url", local_recipe_server)
        shaun.click("button[type='submit']")
        shaun.wait_for_selector("#id_title", timeout=30_000)

        shaun.click("button[type='submit']")
        shaun.wait_for_url(f"{BASE_URL}/", timeout=15_000)

    def test_recipe_detail_loads_after_import(self, shaun: Page, local_recipe_server: str):
        """After import the detail page shows the recipe title."""
        shaun.goto(f"{BASE_URL}/import/")
        shaun.fill("#url", local_recipe_server)
        shaun.click("button[type='submit']")
        shaun.wait_for_selector("#id_title", timeout=30_000)

        title = shaun.input_value("#id_title")
        shaun.click("button[type='submit']")
        shaun.wait_for_url(f"{BASE_URL}/", timeout=15_000)

        shaun.get_by_text(title).first.click()
        shaun.wait_for_url(re.compile(r"/recipe/\d+/"))
        expect(shaun.get_by_text(title).first).to_be_visible()

    def _import_and_navigate(self, shaun: Page, local_recipe_server: str) -> None:
        """Helper: import the local recipe and navigate to its detail page."""
        shaun.goto(f"{BASE_URL}/import/")
        shaun.fill("#url", local_recipe_server)
        shaun.click("button[type='submit']")
        shaun.wait_for_selector("#id_title", timeout=30_000)
        title = shaun.input_value("#id_title")
        shaun.click("button[type='submit']")
        shaun.wait_for_url(f"{BASE_URL}/", timeout=15_000)
        shaun.get_by_text(title).first.click()
        shaun.wait_for_url(re.compile(r"/recipe/\d+/"))

    def test_kitchen_copilot_panel_opens(self, shaun: Page, local_recipe_server: str):
        """Shaun clicks Start Kitchen Copilot and the panel becomes visible."""
        self._import_and_navigate(shaun, local_recipe_server)

        # Launch the copilot
        shaun.click("#copilot-start-btn")

        # The copilot panel and banner should become visible
        expect(shaun.locator("#copilot-panel")).to_be_visible(timeout=COPILOT_TIMEOUT)
        expect(shaun.locator("#copilot-banner")).to_be_visible(timeout=COPILOT_TIMEOUT)

    def test_kitchen_copilot_llm_responds(self, shaun: Page, local_recipe_server: str):
        """Shaun sends a message and the Copilot replies — confirming the LLM API works."""
        self._import_and_navigate(shaun, local_recipe_server)

        shaun.click("#copilot-start-btn")
        expect(shaun.locator("#copilot-panel")).to_be_visible(timeout=COPILOT_TIMEOUT)

        shaun.fill("#copilot-text-input", "What do I need to prepare before I start cooking?")
        shaun.click("button[onclick='sendCopilotQuestion()']")

        # Wait for at least two <p> elements in transcript (user message + assistant reply)
        shaun.wait_for_function(
            "document.querySelectorAll('#copilot-transcript p').length >= 2",
            timeout=COPILOT_TIMEOUT,
        )

        transcript = shaun.inner_text("#copilot-transcript")
        assert len(transcript.strip()) > 0, "Copilot transcript is empty — LLM may not have responded"

    def test_kitchen_copilot_tts_audio_triggered(self, shaun: Page, local_recipe_server: str):
        """After the LLM responds, the TTS handler sets aiSpeaking=true — confirming ElevenLabs TTS works."""
        self._import_and_navigate(shaun, local_recipe_server)

        shaun.click("#copilot-start-btn")
        expect(shaun.locator("#copilot-panel")).to_be_visible(timeout=COPILOT_TIMEOUT)

        # Send a message to trigger a TTS response
        shaun.fill("#copilot-text-input", "I'm ready, let's start!")
        shaun.click("button[onclick='sendCopilotQuestion()']")

        # Wait for aiSpeaking to become true (set by playAudioChunks when ElevenLabs audio arrives)
        # or for more than 2 transcript messages (text_transcript is also sent alongside audio)
        shaun.wait_for_function(
            "window.aiSpeaking === true || document.querySelectorAll('#copilot-transcript p').length >= 3",
            timeout=TTS_TIMEOUT,
        )

        tts_fired = shaun.evaluate(
            "window.aiSpeaking === true || document.querySelectorAll('#copilot-transcript p').length >= 3"
        )
        assert tts_fired, (
            "aiSpeaking never became true and transcript did not grow — "
            "ElevenLabs TTS may not have responded"
        )
