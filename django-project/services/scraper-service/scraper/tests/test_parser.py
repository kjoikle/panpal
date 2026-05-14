"""Unit tests for the top-level recipe extraction pipeline (parser.py)."""
from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from scraper.scraping import parser as recipe_parser

_SUFFICIENT = {
    'title': 'Pasta',
    'description': '',
    'recipe_author': '',
    'image_url': '',
    'ingredients': '200g pasta\nsalt',
    'prep_time': None,
    'cook_time': None,
    'steps': [],
    'tags': [],
    'extraction_method': 'schema_org',
}

_INSUFFICIENT = {
    'title': '',
    'description': '',
    'recipe_author': '',
    'image_url': '',
    'ingredients': '',
    'prep_time': None,
    'cook_time': None,
    'steps': [],
    'tags': [],
    'extraction_method': 'html_fallback',
}

_SAMPLE_HTML = '<html><body><p>Some page</p></body></html>'
_SAMPLE_URL = 'https://example.com/recipe'


class ParserPipelineTests(SimpleTestCase):
    @patch('scraper.scraping.parser.llm_parser.parse')
    @patch('scraper.scraping.parser.html_parser.parse')
    @patch('scraper.scraping.parser.schema_parser.parse')
    def test_uses_schema_result_when_sufficient(self, mock_schema, mock_html, mock_llm):
        mock_schema.return_value = _SUFFICIENT
        result = recipe_parser.parse(_SAMPLE_HTML, url=_SAMPLE_URL)
        self.assertEqual(result, _SUFFICIENT)
        mock_llm.assert_not_called()
        mock_html.assert_not_called()

    @patch('scraper.scraping.parser.llm_parser.parse')
    @patch('scraper.scraping.parser.html_parser.parse')
    @patch('scraper.scraping.parser.schema_parser.parse')
    def test_falls_back_to_llm_when_schema_insufficient(self, mock_schema, mock_html, mock_llm):
        mock_schema.return_value = None
        llm_result = {**_SUFFICIENT, 'extraction_method': 'llm_fallback'}
        mock_llm.return_value = llm_result
        result = recipe_parser.parse(_SAMPLE_HTML, url=_SAMPLE_URL)
        self.assertEqual(result, llm_result)
        mock_html.assert_not_called()

    @patch('scraper.scraping.parser.llm_parser.parse')
    @patch('scraper.scraping.parser.html_parser.parse')
    @patch('scraper.scraping.parser.schema_parser.parse')
    def test_falls_back_to_html_when_llm_insufficient(self, mock_schema, mock_html, mock_llm):
        mock_schema.return_value = None
        mock_llm.return_value = None
        html_result = {**_SUFFICIENT, 'extraction_method': 'html_fallback'}
        mock_html.return_value = html_result
        result = recipe_parser.parse(_SAMPLE_HTML, url=_SAMPLE_URL)
        self.assertEqual(result, html_result)
        mock_html.assert_called_once_with(_SAMPLE_HTML)

    @patch('scraper.scraping.parser.llm_parser.parse')
    @patch('scraper.scraping.parser.html_parser.parse')
    @patch('scraper.scraping.parser.schema_parser.parse')
    def test_returns_none_when_all_fail(self, mock_schema, mock_html, mock_llm):
        mock_schema.return_value = None
        mock_llm.return_value = None
        mock_html.return_value = None
        result = recipe_parser.parse(_SAMPLE_HTML, url=_SAMPLE_URL)
        self.assertIsNone(result)
