"""
Top-level recipe extraction pipeline.

Runs the three parser layers in sequence, falling back to the next layer
when the current one fails or produces an insufficient result.

    schema_parser  →  llm_parser  →  html_parser
"""
from __future__ import annotations

import logging

from . import html_parser, llm_parser, schema_parser

logger = logging.getLogger(__name__)


def parse(html: str, url: str) -> dict | None:
    """
    Extract a recipe from raw HTML, trying each layer in order.

    Returns a normalized recipe dict on success, or None if all layers fail.
    """
    result = schema_parser.parse(html, base_url=url)

    if not llm_parser.is_result_sufficient(result):
        logger.debug('schema_parser insufficient, trying llm_parser')
        result = llm_parser.parse(html)

    if not llm_parser.is_result_sufficient(result):
        logger.debug('llm_parser insufficient, trying html_parser')
        result = html_parser.parse(html)

    return result
