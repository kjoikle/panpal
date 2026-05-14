from __future__ import annotations

"""
HTML fallback parser for recipe extraction.

Used when no schema.org structured data is found on the page.
Uses BeautifulSoup to heuristically locate recipe content via common
CSS class names and HTML patterns used by popular recipe blogs.
"""
import re
from bs4 import BeautifulSoup


# Common CSS class/id patterns used by recipe blogs
_INGREDIENT_PATTERNS = [
    'wprm-recipe-ingredient',
    'tasty-recipe-ingredients',
    'recipe-ingredient',
    'ingredient',
    'ingredients',
]

_INSTRUCTION_PATTERNS = [
    'wprm-recipe-instruction',
    'tasty-recipe-instructions',
    'recipe-instruction',
    'instruction',
    'instructions',
    'directions',
    'direction',
    'steps',
    'step',
    'method',
]

_TITLE_PATTERNS = [
    'wprm-recipe-name',
    'tasty-recipes-title',
    'recipe-title',
    'recipe-name',
    'recipe_title',
]

_TIME_PATTERNS = {
    'prep': ['wprm-recipe-prep_time', 'prep-time', 'preptime', 'prep_time'],
    'cook': ['wprm-recipe-cook_time', 'cook-time', 'cooktime', 'cook_time'],
}


def parse(html: str) -> dict | None:
    """
    Try to extract recipe fields from raw HTML using heuristics.

    Returns a normalized recipe dict, or None if no meaningful content found.
    """
    soup = BeautifulSoup(html, 'html.parser')

    title = _find_title(soup)
    ingredients = _find_ingredients(soup)
    steps = _find_steps(soup)

    # Require at least a title or some ingredients to consider this a valid parse
    if not title and not ingredients:
        return None

    return {
        'title': title,
        'description': _find_description(soup),
        'recipe_author': _find_author(soup),
        'image_url': _find_image(soup),
        'ingredients': ingredients,
        'prep_time': _find_time(soup, 'prep'),
        'cook_time': _find_time(soup, 'cook'),
        'steps': steps,
        'tags': [],
        'extraction_method': 'html_fallback',
    }


def _find_by_class_patterns(soup: BeautifulSoup, patterns: list[str], tag=None):
    """Return first element matching any class pattern (substring match)."""
    for pattern in patterns:
        kwargs = {'class_': re.compile(pattern, re.IGNORECASE)}
        el = soup.find(tag, **kwargs) if tag else soup.find(**kwargs)
        if el:
            return el
    return None


def _find_all_by_class_patterns(soup: BeautifulSoup, patterns: list[str], tag=None):
    """Return all elements matching any class pattern."""
    for pattern in patterns:
        kwargs = {'class_': re.compile(pattern, re.IGNORECASE)}
        results = soup.find_all(tag, **kwargs) if tag else soup.find_all(**kwargs)
        if results:
            return results
    return []


def _find_title(soup: BeautifulSoup) -> str:
    # Try recipe-specific class names first
    el = _find_by_class_patterns(soup, _TITLE_PATTERNS)
    if el:
        return el.get_text(strip=True)

    # Fall back to first <h1>
    h1 = soup.find('h1')
    if h1:
        return h1.get_text(strip=True)

    return ''


def _find_description(soup: BeautifulSoup) -> str:
    for pattern in ['wprm-recipe-summary', 'tasty-recipes-description', 'recipe-description', 'recipe-summary']:
        el = soup.find(class_=re.compile(pattern, re.IGNORECASE))
        if el:
            return el.get_text(separator=' ', strip=True)

    # Try og:description meta tag
    meta = soup.find('meta', attrs={'property': 'og:description'})
    if meta:
        return meta.get('content', '').strip()

    return ''


def _find_author(soup: BeautifulSoup) -> str:
    for pattern in ['wprm-recipe-author', 'recipe-author', 'author']:
        el = soup.find(class_=re.compile(pattern, re.IGNORECASE))
        if el:
            text = el.get_text(strip=True)
            if text:
                return text

    # Try author meta tag
    meta = soup.find('meta', attrs={'name': 'author'})
    if meta:
        return meta.get('content', '').strip()

    return ''


def _find_image(soup: BeautifulSoup) -> str:
    # og:image is the most reliable
    meta = soup.find('meta', attrs={'property': 'og:image'})
    if meta:
        return meta.get('content', '').strip()

    # Recipe-specific image classes
    for pattern in ['wprm-recipe-image', 'recipe-image', 'recipe-photo']:
        el = soup.find(class_=re.compile(pattern, re.IGNORECASE))
        if el:
            img = el.find('img')
            if img:
                return img.get('src', '').strip()

    return ''


def _find_ingredients(soup: BeautifulSoup) -> str:
    items = _find_all_by_class_patterns(soup, _INGREDIENT_PATTERNS, tag='li')
    if not items:
        # Try a container div/ul then grab li children
        container = _find_by_class_patterns(soup, _INGREDIENT_PATTERNS)
        if container:
            items = container.find_all('li')

    if items:
        return '\n'.join(li.get_text(separator=' ', strip=True) for li in items if li.get_text(strip=True))

    return ''


def _find_steps(soup: BeautifulSoup) -> list[dict]:
    items = _find_all_by_class_patterns(soup, _INSTRUCTION_PATTERNS, tag='li')
    if not items:
        container = _find_by_class_patterns(soup, _INSTRUCTION_PATTERNS)
        if container:
            items = container.find_all('li')

    if not items:
        # Try an ordered list that looks like instructions
        for ol in soup.find_all('ol'):
            lis = ol.find_all('li')
            if len(lis) >= 2:
                items = lis
                break

    steps = []
    for i, li in enumerate(items, 1):
        text = li.get_text(separator=' ', strip=True)
        if text:
            steps.append({'step_number': i, 'instruction_text': text})

    return steps


def _find_time(soup: BeautifulSoup, kind: str) -> int | None:
    patterns = _TIME_PATTERNS.get(kind, [])
    for pattern in patterns:
        el = soup.find(class_=re.compile(pattern, re.IGNORECASE))
        if el:
            text = el.get_text(strip=True)
            minutes = _parse_time_text(text)
            if minutes:
                return minutes

    # Try <time> elements with datetime attribute (ISO 8601)
    for time_el in soup.find_all('time'):
        dt = time_el.get('datetime', '')
        if dt.startswith('PT'):
            from .schema_parser import _parse_duration
            parsed = _parse_duration(dt)
            if parsed:
                return parsed

    return None


def _parse_time_text(text: str) -> int | None:
    """Parse human-readable time strings like '30 mins', '1 hr 15 min' to minutes."""
    text = text.lower()
    total = 0

    hour_match = re.search(r'(\d+)\s*h(?:r|our)?s?', text)
    if hour_match:
        total += int(hour_match.group(1)) * 60

    min_match = re.search(r'(\d+)\s*m(?:in|inute)?s?', text)
    if min_match:
        total += int(min_match.group(1))

    if total == 0:
        # Maybe it's just a plain number
        plain = re.match(r'^\s*(\d+)\s*$', text)
        if plain:
            return int(plain.group(1))

    return total if total > 0 else None
