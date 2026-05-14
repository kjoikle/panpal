"""
Tests for the HTML fallback parser.
"""
from django.test import SimpleTestCase

from scraper.scraping import html_parser


WPRM_HTML = """
<html>
<head>
  <meta property="og:image" content="https://example.com/pasta.jpg">
  <meta property="og:description" content="A quick and easy pasta recipe.">
</head>
<body>
  <h1 class="wprm-recipe-name">Simple Pasta</h1>
  <span class="wprm-recipe-author">Chef Mario</span>
  <ul>
    <li class="wprm-recipe-ingredient">200g spaghetti</li>
    <li class="wprm-recipe-ingredient">2 cloves garlic</li>
    <li class="wprm-recipe-ingredient">Olive oil</li>
  </ul>
  <ol>
    <li class="wprm-recipe-instruction">Boil water and cook pasta.</li>
    <li class="wprm-recipe-instruction">Fry garlic in olive oil.</li>
    <li class="wprm-recipe-instruction">Combine and serve.</li>
  </ol>
</body>
</html>
"""

PLAIN_HTML = """
<html>
<body>
  <h1>Grandma's Apple Pie</h1>
  <ul class="ingredients">
    <li>3 apples</li>
    <li>1 cup sugar</li>
    <li>Pie crust</li>
  </ul>
  <ol class="instructions">
    <li>Peel and slice apples.</li>
    <li>Mix with sugar.</li>
    <li>Pour into crust and bake.</li>
  </ol>
</body>
</html>
"""


class HtmlParserTest(SimpleTestCase):

    def test_extracts_title_from_wprm_class(self):
        result = html_parser.parse(WPRM_HTML)
        self.assertEqual(result['title'], 'Simple Pasta')

    def test_extracts_title_from_h1_fallback(self):
        result = html_parser.parse(PLAIN_HTML)
        self.assertEqual(result['title'], "Grandma's Apple Pie")

    def test_extracts_author(self):
        result = html_parser.parse(WPRM_HTML)
        self.assertEqual(result['recipe_author'], 'Chef Mario')

    def test_extracts_image_from_og_tag(self):
        result = html_parser.parse(WPRM_HTML)
        self.assertEqual(result['image_url'], 'https://example.com/pasta.jpg')

    def test_extracts_description_from_og_tag(self):
        result = html_parser.parse(WPRM_HTML)
        self.assertIn('pasta', result['description'])

    def test_extracts_ingredients_as_newline_string(self):
        result = html_parser.parse(WPRM_HTML)
        lines = result['ingredients'].splitlines()
        self.assertEqual(len(lines), 3)
        self.assertIn('200g spaghetti', lines)

    def test_extracts_steps_as_list(self):
        result = html_parser.parse(WPRM_HTML)
        self.assertEqual(len(result['steps']), 3)
        self.assertEqual(result['steps'][0]['step_number'], 1)
        self.assertIn('Boil water', result['steps'][0]['instruction_text'])

    def test_extracts_from_plain_ingredient_class(self):
        result = html_parser.parse(PLAIN_HTML)
        lines = result['ingredients'].splitlines()
        self.assertIn('3 apples', lines)

    def test_extracts_from_plain_instruction_class(self):
        result = html_parser.parse(PLAIN_HTML)
        self.assertEqual(len(result['steps']), 3)

    def test_extraction_method_is_html_fallback(self):
        result = html_parser.parse(WPRM_HTML)
        self.assertEqual(result['extraction_method'], 'html_fallback')

    def test_returns_none_for_page_with_no_content(self):
        result = html_parser.parse('<html><body><p>This is not a recipe.</p></body></html>')
        self.assertIsNone(result)
