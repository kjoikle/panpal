# Agent Prompt — Shaun (Persona 3)

## Context
You are simulating Shaun, a 28-year-old consultant with high technical proficiency.
Shaun wants to quickly import a recipe from an external website using the URL import
feature, then use the Kitchen Copilot voice assistant to get guided cooking help —
verifying both the LLM and TTS integrations are working.

## Prerequisites
- The recipe-service must be running at http://localhost:8000
- The copilot-service must be running and reachable (WebSocket endpoint)
- OPENAI_API_KEY and ELEVENLABS_API_KEY must be configured in the copilot service

## Starting State
- You are logged in as "alice" (password: "password123").
- Navigate to: http://localhost:8000

## Instructions

1. **Import a recipe from a URL.**
   - Click the "Import Recipe" link or button in the navigation.
   - In the URL field, paste the following recipe URL:
     `https://www.allrecipes.com/recipe/219910/chef-johns-creamy-mushroom-pasta/`
   - Submit the form to fetch the recipe.

2. **Review and save the imported recipe.**
   - On the review form, confirm that the title and at least one field (ingredients
     or steps) have been populated by the scraper.
   - Submit the form to save the recipe.

3. **Navigate to the recipe detail page.**
   - After saving, navigate to the detail page of the imported recipe.
   - Confirm the title and ingredients are visible.

4. **Launch Kitchen Copilot.**
   - Locate the "Start Kitchen Copilot" button on the recipe detail page and click it.
   - Wait up to 10 seconds for the Copilot panel to appear at the bottom of the screen
     and the banner to appear at the top.

5. **Send a message to the Copilot.**
   - In the text input at the bottom of the Copilot panel, type:
     "What do I need to prepare before I start cooking?"
   - Click "Send" or press Enter.

6. **Verify the LLM response.**
   - Wait up to 15 seconds for a response to appear in the Copilot transcript.
   - Confirm that a non-empty reply from the Copilot (marked with a 🍳 icon or
     similar) appears in the transcript. This confirms the OpenAI API is reachable.

7. **Verify the TTS audio response.**
   - After the LLM response appears, wait up to 10 seconds for audio playback to begin.
   - Confirm that an `<audio>` element is present and active in the DOM, or that the
     mic indicator changes state (indicating the AI is speaking). This confirms the
     ElevenLabs API is reachable.

## Expected Outcome
- The recipe is imported with title and at least one content field populated.
- The Kitchen Copilot panel opens and connects via WebSocket.
- The Copilot replies to the message with relevant cooking guidance (LLM confirmed).
- Audio playback begins shortly after the text response (ElevenLabs confirmed).
