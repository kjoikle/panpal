# paste into a file like test_parse.py and run: python test_parse.py

import requests
import sys
sys.path.insert(0, '.')

from scraper.scraping import schema_parser, html_parser

URL = "https://smittenkitchen.com/2026/02/miso-chicken-and-rice/"

html = requests.get(
    URL,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=10
).text

# Try schema.org first
result = schema_parser.parse(html, base_url=URL)
if result:
    print("Method: schema_org")
else:
    result = html_parser.parse(html)
    print("Method: html_fallback")

import json
print(json.dumps(result, indent=2))
