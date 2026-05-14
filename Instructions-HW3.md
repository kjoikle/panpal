# Instructions — HW3: MCP Server and Client

## Overview

This document describes the Model Context Protocol (MCP) server and client
implemented for PanPal as part of Homework Assignment 3.

### What was built

An MCP server (`mcp/server.py`) that exposes three PanPal backend API
capabilities to AI applications, and a demo client (`mcp/client.py`) that
connects to it, discovers all capabilities, and invokes one tool end-to-end.

### Where it lives in the repository

```
mcp/
├── server.py           # FastMCP server
├── client.py           # Demo client (uses the low-level mcp SDK)
├── requirements.txt    # Python dependencies
└── .env.example        # Environment variable template
Instructions-HW3.md     # This file (also at project root)
```

The MCP layer is fully independent of the Django services — it makes outbound
HTTP calls to the already-running recipe and scraper services.

---

## Capabilities exposed

### Resource — `recipes://all`
A URI-addressable snapshot of the PanPal recipe catalogue (first page, up to
18 recipes). Returns JSON from `GET /api/recipes/` on the recipe service.

### Tool — `search_recipes`
Search and filter the recipe database.

| Parameter   | Type    | Required | Description |
|-------------|---------|----------|-------------|
| `query`     | string  | no       | Free-text search (title, description, tags, steps) |
| `cuisine_id`| integer | no       | Filter by cuisine Tag ID (numeric, not name) |
| `page`      | integer | no       | Page number (default: 1) |

Returns a formatted summary of matching recipes with pagination info.

### Tool — `scrape_recipe`
Extract structured recipe data from any food blog URL.

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| `url`     | string | yes      | Full URL starting with `http://` or `https://` |

Calls `POST /api/v1/scrape/` on the scraper service. Uses a 90-second timeout
to accommodate the LLM fallback parser. Returns JSON with title, ingredients,
steps, prep/cook times, and `extraction_method` (`schema_org`, `llm`, or `html`).

### Prompt — `cooking_assistant` (optional)
A parameterized cooking Q&A prompt template.

| Argument       | Required | Description |
|----------------|----------|-------------|
| `recipe_title` | yes      | Name of the recipe |
| `question`     | yes      | Cooking question (substitutions, technique, timing, etc.) |

---

## Prerequisites

- Python 3.11 or 3.12
- The PanPal Django services must be running on their default ports:
  - Recipe service: `http://localhost:8000`
  - Scraper service: `http://localhost:8002`

The easiest way to start all services is Docker Compose:

```bash
cd django-project
docker compose up -d
```

Alternatively, run each service manually with `python manage.py runserver`.

---

## Installation

```bash
# From the project root
cd mcp
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Configuration

```bash
cp mcp/.env.example mcp/.env
```

Edit `mcp/.env` if your services run on non-default ports or if you changed
`INTERNAL_SERVICE_KEY` from the default `dev-internal-key`.

```
RECIPE_SERVICE_URL=http://localhost:8000
SCRAPER_SERVICE_URL=http://localhost:8002
INTERNAL_SERVICE_KEY=dev-internal-key
```

> The `INTERNAL_SERVICE_KEY` must match the value set in `docker-compose.yml`
> (default: `dev-internal-key`).

---

## Running the demo client

```bash
# Activate the venv first (if not already active)
source mcp/.venv/bin/activate

# Default demo — discovers all capabilities, then invokes search_recipes(query="pasta")
python mcp/client.py

# Scrape-recipe demo — discovers all capabilities, then invokes scrape_recipe(url=...)
python mcp/client.py --url "https://www.allrecipes.com/recipe/20144/banana-banana-bread/"
```

### Expected output structure

```
============================================================
  TOOLS
============================================================

Tool : search_recipes
  Description : Search the PanPal recipe database.
  Parameters  :
    - query: string (optional)
        Free-text search term ...
    - cuisine_id: integer (optional)
        Filter by cuisine Tag ID ...
    - page: integer (optional)
        Page number ...

Tool : scrape_recipe
  ...

============================================================
  RESOURCES
============================================================

Resource : All Recipes
  URI         : recipes://all
  Description : Full catalogue of recipes ...

============================================================
  PROMPTS
============================================================

Prompt : cooking_assistant
  Description : Generate a cooking assistant prompt ...
  Arguments   :
    - recipe_title (required): ...
    - question (required): ...

============================================================
  TOOL DEMONSTRATION — search_recipes
============================================================

Arguments sent:
  {'query': 'pasta', 'page': 1}

Response received:
Found N recipe(s)  (page 1 of M):

[42] Spaghetti Carbonara
    Cuisine: italian  |  prep 10 min, cook 20 min
    A classic Roman pasta dish ...
...
```

---

## Running the server standalone

For use with the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector)
or Claude Desktop, run the server directly:

```bash
source mcp/.venv/bin/activate
python mcp/server.py
```

The server will wait for JSON-RPC messages on stdin. Press `Ctrl+C` to stop it.

### Claude Desktop configuration

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "panpal": {
      "command": "/absolute/path/to/mcp/.venv/bin/python",
      "args": ["/absolute/path/to/mcp/server.py"],
      "env": {
        "RECIPE_SERVICE_URL": "http://localhost:8000",
        "SCRAPER_SERVICE_URL": "http://localhost:8002",
        "INTERNAL_SERVICE_KEY": "dev-internal-key"
      }
    }
  }
}
```

---

## Troubleshooting

**"Could not reach recipe service"**
Make sure the recipe service is running on port 8000. Run
`docker compose up -d` in `django-project/` or start it manually.

**"Could not reach scraper service"**
Make sure the scraper service is running on port 8002.

**"scraper service rejected the internal service key"**
The `INTERNAL_SERVICE_KEY` in `mcp/.env` must match the value used by the
Django services (default: `dev-internal-key`). Check `docker-compose.yml`.

**`ModuleNotFoundError: No module named 'fastmcp'`**
Activate the virtual environment: `source mcp/.venv/bin/activate`

**`ModuleNotFoundError: No module named 'mcp'`**
Run `pip install -r mcp/requirements.txt` inside the activated venv.

**`scrape_recipe` times out**
The LLM-fallback parser can take up to 90 seconds on complex pages. This is
normal. Make sure `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is set in the
scraper service's environment if the LLM fallback is needed.
