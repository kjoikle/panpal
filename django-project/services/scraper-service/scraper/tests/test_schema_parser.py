"""
Tests for the schema.org JSON-LD parser.

Uses inline HTML fixtures so tests run offline with no external HTTP calls.
"""
from django.test import SimpleTestCase

from scraper.scraping import schema_parser


def _make_html(json_ld: str) -> str:
    return f"""
    <html><head>
    <script type="application/ld+json">{json_ld}</script>
    </head><body></body></html>
    """


FULL_RECIPE_JSON_LD = """
{
  "@context": "https://schema.org",
  "@type": "Recipe",
  "name": "Classic Chocolate Chip Cookies",
  "description": "Chewy, golden cookies loaded with chocolate chips.",
  "author": {"@type": "Person", "name": "Jane Baker"},
  "image": {"@type": "ImageObject", "url": "https://example.com/cookies.jpg"},
  "prepTime": "PT15M",
  "cookTime": "PT12M",
  "recipeIngredient": [
    "2 cups all-purpose flour",
    "1 tsp baking soda",
    "1 cup butter"
  ],
  "recipeInstructions": [
    {"@type": "HowToStep", "text": "Preheat oven to 375F."},
    {"@type": "HowToStep", "text": "Mix dry ingredients."},
    {"@type": "HowToStep", "text": "Bake for 12 minutes."}
  ],
  "recipeCategory": "Dessert",
  "keywords": "cookies, baking, chocolate"
}
"""


class SchemaParserTest(SimpleTestCase):

    def test_extracts_title(self):
        result = schema_parser.parse(_make_html(FULL_RECIPE_JSON_LD), base_url='https://example.com')
        self.assertEqual(result['title'], 'Classic Chocolate Chip Cookies')

    def test_extracts_description(self):
        result = schema_parser.parse(_make_html(FULL_RECIPE_JSON_LD), base_url='https://example.com')
        self.assertIn('chocolate chips', result['description'])

    def test_extracts_author(self):
        result = schema_parser.parse(_make_html(FULL_RECIPE_JSON_LD), base_url='https://example.com')
        self.assertEqual(result['recipe_author'], 'Jane Baker')

    def test_extracts_image_url(self):
        result = schema_parser.parse(_make_html(FULL_RECIPE_JSON_LD), base_url='https://example.com')
        self.assertEqual(result['image_url'], 'https://example.com/cookies.jpg')

    def test_extracts_ingredients_as_newline_joined_string(self):
        result = schema_parser.parse(_make_html(FULL_RECIPE_JSON_LD), base_url='https://example.com')
        lines = result['ingredients'].splitlines()
        self.assertEqual(len(lines), 3)
        self.assertIn('2 cups all-purpose flour', lines)

    def test_extracts_prep_time_in_minutes(self):
        result = schema_parser.parse(_make_html(FULL_RECIPE_JSON_LD), base_url='https://example.com')
        self.assertEqual(result['prep_time'], 15)

    def test_extracts_cook_time_in_minutes(self):
        result = schema_parser.parse(_make_html(FULL_RECIPE_JSON_LD), base_url='https://example.com')
        self.assertEqual(result['cook_time'], 12)

    def test_extracts_steps_as_list(self):
        result = schema_parser.parse(_make_html(FULL_RECIPE_JSON_LD), base_url='https://example.com')
        self.assertEqual(len(result['steps']), 3)
        self.assertEqual(result['steps'][0]['step_number'], 1)
        self.assertEqual(result['steps'][0]['instruction_text'], 'Preheat oven to 375F.')

    def test_extracts_tags(self):
        result = schema_parser.parse(_make_html(FULL_RECIPE_JSON_LD), base_url='https://example.com')
        self.assertIn('dessert', result['tags'])
        self.assertIn('cookies', result['tags'])

    def test_extraction_method_is_schema_org(self):
        result = schema_parser.parse(_make_html(FULL_RECIPE_JSON_LD), base_url='https://example.com')
        self.assertEqual(result['extraction_method'], 'schema_org')

    def test_returns_none_when_no_recipe_type(self):
        html = _make_html('{"@context": "https://schema.org", "@type": "Article", "name": "News"}')
        result = schema_parser.parse(html, base_url='https://example.com')
        self.assertIsNone(result)

    def test_returns_none_for_empty_html(self):
        result = schema_parser.parse('<html><body>No structured data here</body></html>', base_url='https://example.com')
        self.assertIsNone(result)

    def test_handles_string_image(self):
        json_ld = '{"@type": "Recipe", "name": "Test", "image": "https://example.com/img.jpg"}'
        result = schema_parser.parse(_make_html(json_ld), base_url='https://example.com')
        self.assertEqual(result['image_url'], 'https://example.com/img.jpg')

    def test_handles_hour_and_minute_duration(self):
        json_ld = '{"@type": "Recipe", "name": "Test", "prepTime": "PT1H30M"}'
        result = schema_parser.parse(_make_html(json_ld), base_url='https://example.com')
        self.assertEqual(result['prep_time'], 90)

    def test_handles_nested_graph(self):
        json_ld = """
        {
          "@context": "https://schema.org",
          "@graph": [
            {"@type": "WebPage", "name": "My Blog"},
            {"@type": "Recipe", "name": "Nested Recipe"}
          ]
        }
        """
        result = schema_parser.parse(_make_html(json_ld), base_url='https://example.com')
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'Nested Recipe')
