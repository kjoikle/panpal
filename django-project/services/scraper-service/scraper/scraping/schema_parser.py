from __future__ import annotations

"""
Schema.org JSON-LD parser for recipe extraction.

Most modern recipe websites embed structured data as JSON-LD following the
schema.org/Recipe spec. This parser extracts it using the `extruct` library,
which handles JSON-LD, microdata, and RDFa in a single pass.

Field mapping from schema.org to our Recipe model:
  name               -> title
  description        -> description
  author.name        -> recipe_author
  image / image.url  -> image_url
  recipeIngredient   -> ingredients (joined with newlines)
  prepTime (ISO 8601)-> prep_time (int minutes)
  cookTime (ISO 8601)-> cook_time (int minutes)
  recipeInstructions -> steps (list of instruction strings)
  recipeCategory / keywords -> tags (list of strings)
"""
import re
import extruct


def parse(html: str, base_url: str) -> dict | None:
    """
    Try to extract recipe data from schema.org JSON-LD / microdata in html.

    Returns a normalized recipe dict on success, or None if no Recipe type found.
    """
    try:
        data = extruct.extract(html, base_url=base_url, syntaxes=['json-ld', 'microdata'])
    except Exception:
        return None

    recipe_node = _find_recipe_node(data)
    if recipe_node is None:
        return None

    return _normalize(recipe_node)


def _find_recipe_node(data: dict) -> dict | None:
    """Search extracted data for a node with @type == 'Recipe'."""
    candidates = data.get('json-ld', []) + data.get('microdata', [])
    for node in candidates:
        found = _search_node(node)
        if found:
            return found
    return None


def _search_node(node) -> dict | None:
    """Recursively search a node (or list of nodes) for @type == 'Recipe'."""
    if isinstance(node, list):
        for item in node:
            result = _search_node(item)
            if result:
                return result
        return None

    if not isinstance(node, dict):
        return None

    node_type = node.get('@type', '')
    if isinstance(node_type, list):
        node_type = ' '.join(node_type)
    if 'Recipe' in node_type:
        return node

    # Check @graph (common in JSON-LD documents)
    for value in node.values():
        if isinstance(value, (dict, list)):
            result = _search_node(value)
            if result:
                return result

    return None


def _normalize(node: dict) -> dict:
    """Map schema.org fields to our internal recipe dict."""
    return {
        'title': _str(node.get('name')),
        'description': _str(node.get('description')),
        'recipe_author': _extract_author(node.get('author')),
        'image_url': _extract_image(node.get('image')),
        'ingredients': _extract_ingredients(node.get('recipeIngredient')),
        'prep_time': _parse_duration(node.get('prepTime')),
        'cook_time': _parse_duration(node.get('cookTime')),
        'steps': _extract_steps(node.get('recipeInstructions')),
        'tags': _extract_tags(node.get('recipeCategory'), node.get('keywords')),
        'extraction_method': 'schema_org',
    }


def _str(value) -> str:
    if value is None:
        return ''
    if isinstance(value, list):
        return ' '.join(str(v) for v in value).strip()
    return str(value).strip()


def _extract_author(author) -> str:
    if not author:
        return ''
    if isinstance(author, str):
        return author.strip()
    if isinstance(author, dict):
        return author.get('name', '').strip()
    if isinstance(author, list) and author:
        return _extract_author(author[0])
    return ''


def _extract_image(image) -> str:
    if not image:
        return ''
    if isinstance(image, str):
        return image.strip()
    if isinstance(image, dict):
        return image.get('url', '').strip()
    if isinstance(image, list) and image:
        return _extract_image(image[0])
    return ''


def _extract_ingredients(ingredients) -> str:
    if not ingredients:
        return ''
    if isinstance(ingredients, list):
        return '\n'.join(str(i).strip() for i in ingredients if i)
    return str(ingredients).strip()


def _parse_duration(duration) -> int | None:
    """Parse ISO 8601 duration string (e.g. PT30M, PT1H15M) to total minutes."""
    if not duration:
        return None
    if isinstance(duration, (int, float)):
        return int(duration)

    duration = str(duration).upper()
    # Match PT[nH][nM][nS]
    match = re.match(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return None

    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)
    # seconds are ignored (not relevant for cooking times)

    total = days * 24 * 60 + hours * 60 + minutes
    return total if total > 0 else None


def _extract_steps(instructions) -> list[dict]:
    """
    Convert recipeInstructions to a list of {step_number, instruction_text} dicts.
    Handles plain strings, HowToStep objects, and HowToSection objects.
    """
    if not instructions:
        return []

    if isinstance(instructions, str):
        lines = [l.strip() for l in instructions.splitlines() if l.strip()]
        return [{'step_number': i, 'instruction_text': line} for i, line in enumerate(lines, 1)]

    flat = []
    _flatten_instructions(instructions, flat)

    return [{'step_number': i, 'instruction_text': text} for i, text in enumerate(flat, 1)]


def _flatten_instructions(instructions, out: list):
    if isinstance(instructions, str):
        text = instructions.strip()
        if text:
            out.append(text)
        return

    if isinstance(instructions, dict):
        node_type = instructions.get('@type', '')
        if 'HowToSection' in node_type:
            _flatten_instructions(instructions.get('itemListElement', []), out)
        else:
            text = instructions.get('text', '').strip()
            if text:
                out.append(text)
        return

    if isinstance(instructions, list):
        for item in instructions:
            _flatten_instructions(item, out)


def _extract_tags(category, keywords) -> list[str]:
    tags = []

    def _add(value):
        if not value:
            return
        if isinstance(value, str):
            for part in re.split(r'[,;]', value):
                part = part.strip()
                if part:
                    tags.append(part.lower())
        elif isinstance(value, list):
            for item in value:
                _add(item)

    _add(category)
    _add(keywords)
    return list(dict.fromkeys(tags))  # deduplicate, preserve order
