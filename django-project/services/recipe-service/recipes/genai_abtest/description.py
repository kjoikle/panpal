"""
Recipe description generator with 3 LangChain-powered approaches.

Approaches:
  - casual:       friendly, conversational home-cook tone
  - professional: technique-forward culinary vocabulary
  - poetic:       sensory-rich food-magazine style
"""

import random
from typing import Optional
from django.conf import settings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

APPROACHES = ["casual", "professional", "poetic"]

SYSTEM_PROMPTS = {
    "casual": (
        "You are a friendly home cook who loves sharing recipes with family and friends. "
        "Write a short, warm, conversational description (1 sentence) for the recipe below. "
        "Your description should be clear so that the user can identify the dish and its appeal. "
        "Use approachable language that makes the dish sound achievable for anyone. "
        "Do not include a title — just the description. "
        "Do not summarize the recipe; instead, highlight what makes it special or delicious."
        "e.g. 'This hearty stew is packed with tender beef and veggies, perfect for cozy weeknights!'"
    ),
    "professional": (
        "You are an experienced chef writing for a culinary publication. "
        "Write a precise, technique-forward description (1 sentence) for the recipe below. "
        "Use culinary vocabulary and highlight key techniques or flavor profiles. "
        "Do not include a title — just the description."
        "Do not summarize the recipe; instead, highlight what makes it special or delicious."
        "e.g. 'A classic coq au vin, featuring braised chicken thighs in a rich red wine sauce, finished with pearl onions and mushrooms.'"
    ),
    "poetic": (
        "You are a food writer crafting copy for a high-end food magazine. "
        "Write an evocative, sensory-rich description (1 sentence) for the recipe below. "
        "Your description should be clear so that the user can identify the dish and its appeal. "
        "Appeal to sight, smell, taste, and texture. Make the reader crave it. "
        "Do not include a title — just the description."
        "Do not summarize the recipe; instead, highlight what makes it special or delicious."
        "e.g. 'This vibrant salad combines crisp vegetables with a tangy vinaigrette, creating a refreshing centerpiece for any meal.'"
    ),
}


def _build_chain(approach: str):
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=settings.OPENAI_API_KEY,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPTS[approach]),
        ("human", "{recipe_context}"),
    ])
    return prompt | llm | StrOutputParser()


def _build_input(recipe) -> dict:
    steps = recipe.steps.all()
    steps_text = "\n".join(
        f"{s.step_number}. {s.instruction_text}" for s in steps
    ) or "No steps provided."

    tags = ", ".join(t.name for t in recipe.tags.all()) or "None"

    parts = [f"Title: {recipe.title}"]
    if recipe.description:
        parts.append(f"Existing description: {recipe.description}")
    parts.append(f"Ingredients:\n{recipe.ingredients or 'Not specified'}")
    parts.append(f"Steps:\n{steps_text}")
    parts.append(f"Tags: {tags}")
    if recipe.prep_time:
        parts.append(f"Prep time: {recipe.prep_time} minutes")
    if recipe.cook_time:
        parts.append(f"Cook time: {recipe.cook_time} minutes")

    return {"recipe_context": "\n\n".join(parts)}


def generate(recipe, approach: Optional[str] = None) -> dict:
    """Generate a description for one approach (randomly chosen if not specified)."""
    if approach not in APPROACHES:
        approach = random.choice(APPROACHES)
    content = _build_chain(approach).invoke(_build_input(recipe))
    return {"approach": approach, "content": content}


def compare(recipe) -> dict:
    """Generate descriptions for two randomly chosen different approaches."""
    two = random.sample(APPROACHES, 2)
    return {"descriptions": [generate(recipe, a) for a in two]}
