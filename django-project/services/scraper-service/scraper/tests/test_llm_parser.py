"""Unit tests for the LLM fallback recipe parser."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from scraper.scraping import llm_parser


_VALID_LLM_RESPONSE = {
    'title': 'Chocolate Cake',
    'description': 'A rich chocolate cake.',
    'recipe_author': 'Jane Smith',
    'image_url': 'https://example.com/cake.jpg',
    'ingredients': '2 cups flour\n1 cup sugar\n3 eggs',
    'prep_time': 20,
    'cook_time': 45,
    'steps': [
        {'step_number': 1, 'instruction_text': 'Preheat oven to 350F.'},
        {'step_number': 2, 'instruction_text': 'Mix dry ingredients.'},
    ],
    'tags': ['dessert', 'chocolate'],
}

_SAMPLE_HTML = """
<html>
<head><title>Chocolate Cake Recipe</title></head>
<body>
<script>var x = 1;</script>
<style>body { color: red; }</style>
<h1>Chocolate Cake</h1>
<p>A rich chocolate cake recipe.</p>
<ul><li>2 cups flour</li><li>1 cup sugar</li></ul>
</body>
</html>
"""


class IsResultSufficientTests(SimpleTestCase):
    def test_sufficient_result(self):
        result = {'title': 'Pasta', 'ingredients': '200g pasta\nsalt'}
        self.assertTrue(llm_parser.is_result_sufficient(result))

    def test_missing_title(self):
        result = {'title': '', 'ingredients': '200g pasta'}
        self.assertFalse(llm_parser.is_result_sufficient(result))

    def test_missing_ingredients(self):
        result = {'title': 'Pasta', 'ingredients': ''}
        self.assertFalse(llm_parser.is_result_sufficient(result))

    def test_none_result(self):
        self.assertFalse(llm_parser.is_result_sufficient(None))

    def test_both_missing(self):
        result = {'title': '', 'ingredients': ''}
        self.assertFalse(llm_parser.is_result_sufficient(result))


class ExtractVisibleTextTests(SimpleTestCase):
    def test_strips_script_and_style(self):
        text = llm_parser._extract_visible_text(_SAMPLE_HTML)
        self.assertNotIn('var x = 1', text)
        self.assertNotIn('color: red', text)

    def test_preserves_visible_text(self):
        text = llm_parser._extract_visible_text(_SAMPLE_HTML)
        self.assertIn('Chocolate Cake', text)
        self.assertIn('A rich chocolate cake recipe', text)
        self.assertIn('2 cups flour', text)

    def test_no_empty_lines(self):
        text = llm_parser._extract_visible_text(_SAMPLE_HTML)
        for line in text.splitlines():
            self.assertTrue(line.strip(), f'Empty line found in output: {repr(line)}')


def _make_llm_response(content: str) -> MagicMock:
    """Build a mock LangChain AIMessage-like response."""
    mock = MagicMock()
    mock.content = content
    return mock


@override_settings(
    LLM_PROVIDER='claude',
    LLM_MODEL='claude-haiku-4-5-20251001',
    ANTHROPIC_API_KEY='test-key',
)
class ParseClaudeTests(SimpleTestCase):
    @patch('scraper.scraping.llm_parser._get_llm')
    def test_parse_success(self, mock_get_llm):
        mock_get_llm.return_value.invoke.return_value = _make_llm_response(
            json.dumps(_VALID_LLM_RESPONSE)
        )
        result = llm_parser.parse(_SAMPLE_HTML)
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'Chocolate Cake')
        self.assertEqual(result['ingredients'], '2 cups flour\n1 cup sugar\n3 eggs')
        self.assertEqual(result['prep_time'], 20)
        self.assertEqual(result['cook_time'], 45)
        self.assertEqual(len(result['steps']), 2)
        self.assertEqual(result['tags'], ['dessert', 'chocolate'])
        self.assertEqual(result['extraction_method'], 'llm_fallback')

    @patch('scraper.scraping.llm_parser._get_llm')
    def test_parse_invalid_json_returns_none(self, mock_get_llm):
        mock_get_llm.return_value.invoke.return_value = _make_llm_response(
            'Sorry, I could not extract the recipe.'
        )
        result = llm_parser.parse(_SAMPLE_HTML)
        self.assertIsNone(result)

    @patch('scraper.scraping.llm_parser._get_llm')
    def test_parse_not_recipe_returns_none(self, mock_get_llm):
        mock_get_llm.return_value.invoke.return_value = _make_llm_response(
            json.dumps({'error': 'not a recipe'})
        )
        result = llm_parser.parse(_SAMPLE_HTML)
        self.assertIsNone(result)

    @patch('scraper.scraping.llm_parser._get_llm')
    def test_parse_api_exception_returns_none(self, mock_get_llm):
        mock_get_llm.return_value.invoke.side_effect = Exception('API error')
        result = llm_parser.parse(_SAMPLE_HTML)
        self.assertIsNone(result)


@override_settings(
    LLM_PROVIDER='openai',
    LLM_MODEL='gpt-4o-mini',
    OPENAI_API_KEY='test-key',
)
class ParseOpenAITests(SimpleTestCase):
    @patch('scraper.scraping.llm_parser._get_llm')
    def test_parse_success(self, mock_get_llm):
        mock_get_llm.return_value.invoke.return_value = _make_llm_response(
            json.dumps(_VALID_LLM_RESPONSE)
        )
        result = llm_parser.parse(_SAMPLE_HTML)
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'Chocolate Cake')
        self.assertEqual(result['extraction_method'], 'llm_fallback')

    @patch('scraper.scraping.llm_parser._get_llm')
    def test_parse_invalid_json_returns_none(self, mock_get_llm):
        mock_get_llm.return_value.invoke.return_value = _make_llm_response(
            'Not valid JSON.'
        )
        result = llm_parser.parse(_SAMPLE_HTML)
        self.assertIsNone(result)

    @patch('scraper.scraping.llm_parser._get_llm')
    def test_parse_not_recipe_returns_none(self, mock_get_llm):
        mock_get_llm.return_value.invoke.return_value = _make_llm_response(
            json.dumps({'error': 'not a recipe'})
        )
        result = llm_parser.parse(_SAMPLE_HTML)
        self.assertIsNone(result)
