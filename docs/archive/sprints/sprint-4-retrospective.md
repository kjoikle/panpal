# Sprint 4 Retrospective

## What Went Well
- Image functionality was stabilized across the platform, with broken rendering fixed and fallback logic implemented.
- The Manual food blog input was completed and successfully imported recipes (titles, ingredients, instructions) from multiple blog formats.
- Image extraction within the recipe input was added, enabling automatic capture and validation of recipe images.
- The analytics page received its first major iteration, including ingredient frequency insights and a cleaner UI.
- Overall UI polish improved the product’s usability and reduced visual inconsistencies.

## What Could Be Improved
- We had to reprioritize our backlog to focus on key bug fixes, which reduced the time available for some planned enhancements.
- Scraper reliability varies by blog structure; more generalized parsing logic is still needed.
- Some analytics metrics depend on larger or cleaner datasets and will require further refinement.
- Image handling revealed edge cases (large files, unsupported formats) that may need future improvements.

## Key Learnings
- Prioritizing critical bugs early helps maintain stability and reduces technical debt down the line.
- Building modular scraping logic makes it easier to support additional sites later.
- Standardizing media storage and validation simplifies downstream development.
- Incremental analytics improvements clarify data requirements and gaps.
