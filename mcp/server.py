"""
PanPal MCP Server
=================
Exposes PanPal's recipe API to AI applications via the Model Context Protocol.

Capabilities
------------
Resource : recipes://all
    Full catalogue of recipes in the PanPal database (first page, up to 18).

Tool     : search_recipes(query, cuisine_id, page)
    Search and filter recipes by free-text query and/or cuisine tag ID.

Tool     : scrape_recipe(url)
    Extract structured recipe data from any food blog URL.

Prompt   : cooking_assistant(recipe_title, question)
    Parameterized cooking Q&A prompt template.

Transport
---------
Runs over stdio by default (``python server.py``), making it compatible with
Claude Desktop, the MCP Inspector, and any client that spawns it as a subprocess.

Configuration
-------------
Set the following environment variables (or copy .env.example to .env):

    RECIPE_SERVICE_URL   — recipe service base URL  (default: http://localhost:8000)
    SCRAPER_SERVICE_URL  — scraper service base URL  (default: http://localhost:8002)
    INTERNAL_SERVICE_KEY — shared internal auth key  (default: dev-internal-key)
"""

import json
import os
import sys
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.prompts import Message

# Load .env from the same directory as this file, if present.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

RECIPE_SERVICE_URL = os.getenv("RECIPE_SERVICE_URL", "http://localhost:8000")
SCRAPER_SERVICE_URL = os.getenv("SCRAPER_SERVICE_URL", "http://localhost:8002")
INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "dev-internal-key")

mcp = FastMCP(
    name="PanPal Recipe Server",
    instructions=(
        "Provides access to the PanPal recipe database and scraping capabilities. "
        "Use search_recipes to find recipes by keyword or cuisine. "
        "Use scrape_recipe to import a new recipe from any food blog URL. "
        "Read recipes://all to browse the full catalogue."
    ),
)


# ---------------------------------------------------------------------------
# Resource
# ---------------------------------------------------------------------------


@mcp.resource(
    uri="recipes://all",
    name="All Recipes",
    description=(
        "Full catalogue of recipes in the PanPal database. "
        "Returns the first page (up to 18 recipes) with pagination metadata."
    ),
    mime_type="application/json",
)
async def all_recipes() -> str:
    """Fetch the first page of all recipes from the PanPal recipe service."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{RECIPE_SERVICE_URL}/api/recipes/",
                params={"page": 1, "page_size": 18},
            )
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
        except httpx.HTTPStatusError as exc:
            return json.dumps(
                {"error": f"Recipe service returned HTTP {exc.response.status_code}"}
            )
        except httpx.RequestError as exc:
            return json.dumps(
                {"error": f"Could not reach recipe service: {exc}"}
            )


# ---------------------------------------------------------------------------
# Tool 1 — search_recipes
# ---------------------------------------------------------------------------


@mcp.tool
async def search_recipes(
    query: Optional[str] = None,
    cuisine_id: Optional[int] = None,
    page: int = 1,
) -> str:
    """Search the PanPal recipe database.

    Args:
        query:      Free-text search term matched against recipe titles,
                    descriptions, tags, and step instructions.
        cuisine_id: Filter by cuisine Tag ID (integer). Tag IDs can be found
                    in the ``cuisine_tag`` field of recipe objects returned by
                    this tool. Pass the numeric ID, not the cuisine name.
        page:       Page number for paginated results (default: 1, page size: 18).

    Returns:
        A human-readable summary of matching recipes with pagination info,
        or an error message if the service is unavailable.
    """
    params: dict = {"page": page, "page_size": 18}
    if query:
        params["q"] = query
    if cuisine_id is not None:
        params["cuisine"] = cuisine_id

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{RECIPE_SERVICE_URL}/api/recipes/",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            return f"Error: recipe service returned HTTP {exc.response.status_code}"
        except httpx.RequestError as exc:
            return f"Error: could not reach recipe service — {exc}"

    recipes = data.get("recipes", [])
    pagination = data.get("pagination", {})
    total = pagination.get("total_count", len(recipes))
    current_page = pagination.get("page", page)
    total_pages = pagination.get("total_pages", 1)

    if not recipes:
        return "No recipes found matching the given criteria."

    lines = [
        f"Found {total} recipe(s)  (page {current_page} of {total_pages}):\n"
    ]
    for recipe in recipes:
        time_parts = []
        if recipe.get("prep_time"):
            time_parts.append(f"prep {recipe['prep_time']} min")
        if recipe.get("cook_time"):
            time_parts.append(f"cook {recipe['cook_time']} min")
        time_str = ", ".join(time_parts) if time_parts else "time not listed"
        cuisine_str = recipe.get("cuisine_tag") or "unspecified cuisine"
        description = (recipe.get("description") or "")[:120]

        lines.append(
            f"[{recipe['id']}] {recipe['title']}\n"
            f"    Cuisine: {cuisine_str}  |  {time_str}\n"
            f"    {description}"
        )

    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 2 — scrape_recipe
# ---------------------------------------------------------------------------


@mcp.tool
async def scrape_recipe(url: str) -> str:
    """Extract structured recipe data from any food blog URL.

    Sends the URL to PanPal's scraper service, which attempts extraction via
    JSON-LD / Schema.org structured data first, then falls back to an LLM-based
    parser if needed.

    Args:
        url: Full URL of the recipe page (must start with http:// or https://).

    Returns:
        A JSON string with structured recipe data including title, description,
        ingredients, steps, prep/cook times, image URL, and the extraction method
        used (``schema_org``, ``llm``, or ``html``).
        Returns an error message string if scraping fails.
    """
    if not url.startswith(("http://", "https://")):
        return "Error: url must start with http:// or https://"

    headers = {"X-Internal-Service-Key": INTERNAL_SERVICE_KEY}

    # 90-second timeout mirrors scraper_client.py:SCRAPER_TIMEOUT — the LLM
    # fallback path can be slow for complex pages.
    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                f"{SCRAPER_SERVICE_URL}/api/v1/scrape/",
                json={"url": url},
                headers=headers,
            )
        except httpx.RequestError as exc:
            return f"Error: could not reach scraper service — {exc}"

    if response.status_code == 400:
        body = response.json()
        return f"Scraping failed: {body.get('error', 'unknown error')}"
    if response.status_code == 403:
        return (
            "Error: scraper service rejected the internal service key. "
            "Check that INTERNAL_SERVICE_KEY matches the value in docker-compose.yml."
        )
    if response.status_code == 504:
        return "Error: target URL timed out during fetch."

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return f"Error: scraper service returned HTTP {exc.response.status_code}"

    return json.dumps(response.json(), indent=2)


# ---------------------------------------------------------------------------
# Prompt (optional)
# ---------------------------------------------------------------------------


@mcp.prompt
def cooking_assistant(recipe_title: str, question: str) -> list[Message]:
    """Generate a cooking assistant prompt for a specific recipe question.

    Args:
        recipe_title: The name of the recipe being discussed.
        question:     A cooking question about the recipe (e.g. substitutions,
                      technique, timing, scaling).

    Returns:
        A list containing a single user-role message ready to send to an LLM.
    """
    return [
        Message(
            role="user",
            content=(
                f"You are a friendly and knowledgeable cooking assistant "
                f"helping with the recipe '{recipe_title}'.\n\n"
                f"Question: {question}\n\n"
                f"Please provide a clear, practical answer. "
                f"Where relevant, suggest ingredient substitutions, "
                f"technique tips, or timing adjustments."
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Emit a startup notice to stderr so it does not pollute the stdio JSON-RPC
    # stream that the MCP client reads from stdout.
    print("PanPal MCP Server starting (stdio transport)...", file=sys.stderr)
    mcp.run()
