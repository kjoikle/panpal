"""
PanPal MCP Demo Client
======================
Connects to the PanPal MCP server via stdio (spawning it as a subprocess),
automatically discovers all available capabilities, and prints them out.
Then demonstrates invoking one tool end-to-end.

Usage
-----
Default demo — invokes search_recipes(query="pasta"):

    python client.py

Scrape-recipe demo — invokes scrape_recipe(url=<URL>):

    python client.py --url "https://example.com/some-recipe/"

Configuration
-------------
The client forwards the following environment variables (or .env values) to
the server subprocess:

    RECIPE_SERVICE_URL   — recipe service base URL  (default: http://localhost:8000)
    SCRAPER_SERVICE_URL  — scraper service base URL  (default: http://localhost:8002)
    INTERNAL_SERVICE_KEY — shared internal auth key  (default: dev-internal-key)
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# Load .env from the same directory as this file, if present.
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# Path to server.py, resolved relative to this file so the client works
# regardless of the working directory it is invoked from.
_SERVER_PATH = str(Path(__file__).parent / "server.py")

# Spawn the server with the same Python interpreter as the client and forward
# the relevant environment variables explicitly — the stdio subprocess does NOT
# automatically inherit the parent's loaded dotenv values on all platforms.
SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=[_SERVER_PATH],
    env={
        "PATH": os.environ.get("PATH", ""),
        "RECIPE_SERVICE_URL": os.environ.get(
            "RECIPE_SERVICE_URL", "http://localhost:8000"
        ),
        "SCRAPER_SERVICE_URL": os.environ.get(
            "SCRAPER_SERVICE_URL", "http://localhost:8002"
        ),
        "INTERNAL_SERVICE_KEY": os.environ.get(
            "INTERNAL_SERVICE_KEY", "dev-internal-key"
        ),
    },
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _header(title: str) -> None:
    bar = "=" * 60
    print(f"\n{bar}")
    print(f"  {title}")
    print(bar)


def _print_tools(tools: list) -> None:
    _header("TOOLS")
    if not tools:
        print("  (none)")
        return
    for tool in tools:
        print(f"\nTool : {tool.name}")
        print(f"  Description : {tool.description}")
        schema = tool.inputSchema or {}
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        if props:
            print("  Parameters  :")
            for name, info in props.items():
                req_label = " (required)" if name in required else " (optional)"
                ptype = info.get("type", "any")
                desc = info.get("description", "")
                print(f"    - {name}: {ptype}{req_label}")
                if desc:
                    print(f"        {desc}")
        else:
            print("  Parameters  : none")


def _print_resources(resources: list) -> None:
    _header("RESOURCES")
    if not resources:
        print("  (none)")
        return
    for resource in resources:
        print(f"\nResource : {resource.name}")
        print(f"  URI         : {resource.uri}")
        print(f"  Description : {resource.description}")


def _print_prompts(prompts: list) -> None:
    _header("PROMPTS")
    if not prompts:
        print("  (none)")
        return
    for prompt in prompts:
        print(f"\nPrompt : {prompt.name}")
        print(f"  Description : {prompt.description}")
        if prompt.arguments:
            print("  Arguments   :")
            for arg in prompt.arguments:
                req_label = " (required)" if arg.required else " (optional)"
                print(f"    - {arg.name}{req_label}: {arg.description or ''}")
        else:
            print("  Arguments   : none")


# ---------------------------------------------------------------------------
# Main coroutine
# ---------------------------------------------------------------------------


async def run(demo_scrape_url: str | None = None) -> None:
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            # MCP handshake — must be the first call inside the session.
            await session.initialize()

            # ── Capability discovery ────────────────────────────────────

            tools_result = await session.list_tools()
            resources_result = await session.list_resources()
            prompts_result = await session.list_prompts()

            _print_tools(tools_result.tools)
            _print_resources(resources_result.resources)
            _print_prompts(prompts_result.prompts)

            # ── Tool demonstration ──────────────────────────────────────

            if demo_scrape_url:
                tool_name = "scrape_recipe"
                arguments = {"url": demo_scrape_url}
            else:
                tool_name = "search_recipes"
                arguments = {"query": "pasta", "page": 1}

            _header(f"TOOL DEMONSTRATION — {tool_name}")
            print(f"\nArguments sent:\n  {arguments}\n")

            result = await session.call_tool(tool_name, arguments=arguments)

            print("Response received:")
            for block in result.content:
                if isinstance(block, types.TextContent):
                    print(block.text)
                else:
                    print(f"[Non-text content: {type(block).__name__}]")

            if result.isError:
                print("\n[The tool reported an error (isError=True)]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    demo_url: str | None = None

    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "--url":
        demo_url = args[1]
    elif len(args) != 0:
        print("Usage: python client.py [--url <recipe-page-url>]")
        sys.exit(1)

    try:
        asyncio.run(run(demo_scrape_url=demo_url))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
