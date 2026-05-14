# Sprint 1 Summary 
## Executive Summary 

Our team is building a recipe aggregation webpage that allows users to 
create curated lists of recipes searched from their favorite sources. 
Users will be able to form personalized accounts that have options for 
further curation, recipe consolidations, filtered searches, and 
easy-to-read and access recipes. In later stages, this could be a more 
community-driven recipe sharing and consolidation tool to access recipes 
and try new cuisine.  

When we think of the journey from deciding what to cook to the process of 
choosing a recipe, there are many obstacles that can make this process 
time-consuming and inefficient. First, a user could be dealing with a 
multitude of options on Google where they must comb through where there 
are hundreds or thousands of pages and links just to get to a recipe. Then 
a user could be faced with ads blocking the view of the recipes or making 
it hard to find. Or even worse, they are faced with an Odyssey-level story 
of some woman’s grandmother’s backstory that they simply don’t care about. 
Imagine a seamless app that provides just the information that is needed 
in a recipe, with search functionality to speed up the process of turning 
ideas into full blown meals.  

## User Research & Problem Definition 
### User Journeys (All Users) 
1. User navigates to site, clicks the create account button, creates 
a user profile with demographic information (Age, Cooking Level, 
Allergies, etc.) 
2. Given no account:  
	a. User visits website --> given a simple search interface --> The 
user searches for a recipe and is presented with a list view of recipes 
options with a simple image of the recipe and a name aggregated from 
various food blogs.  
4. User can input blogs or sites with specific names to prime the 
search functionality to only return options from those sources to create 
more specific and curated options that are not as cumbersome to look 
through 
5. Users click into the search button, have searched return, and can 
filter the options based on criteria (Time to make, ingredients available, 
cuisine type) 
6. When a user finally finds a recipe in the list view they find 
appealing, they are brought to a recipe detail page with image, 
ingredients, and instructions 
7. User can click into a recipe and is presented with a ingredient 
list and recipe instructions (rather than the standard long blog post 
telling you about the author etc).   
8. Users with accounts save a recipe to their own page, which is then 
searchable by them and can have notes added to it by the user (e.g. “I 
prefer to replace the cilantro with parsley in this recipe”.) 
9. Users find a new recipe and create a manual recipe entry. This can 
be saved in standalone Recipes or in the Lists tab 
 
### User Personas 
#### Persona 1 — The Busy Pragmatist Cook 
**Name**: Maya, 31  
**Life Context**: Works full-time in consulting, lives with partner, cooks 
dinner 3–4 nights per week  
**Pain Today**: Hates scrolling through “my mother-in-law’s Tuscan summer 
memories…” blog posts just to get to ingredients  
**Primary Goals**:   
- Quick search → clean, concise recipe → cook immediately 
- Wants to save go-to recipes in one place instead of bookmarking 
random URLs 
- Wants to annotate (e.g. “less chili for Ben”)
  
**Value of Product to Her**: 
- Time savings + mental clarity 
- One library across blogs without all the fluff 
- Notes as personal memory over time 
 
#### Persona 2 — The New Home Cook in Learning Mode 
**Name**: Jordan, 24   
**Life Context**: Just graduated, first apartment, learning to cook  
**Pain Today**: Gets overwhelmed by choice and recipe tone; too much  
storytelling and pop-ups, hard to know what’s “standard format”  
**Primary Goals**:  
- Clear, standardized instructions 
- Save beginner-friendly dishes and make slight tweaks as skills 
grow 
- Wants to search through a curated list of trusted blogs, not the 
whole internet

**Value of Product to Them**:    
- Feels “guided” without gatekeeping 
- Library gives them confidence + trackable progress 
- Notes and re-searchability help build routine 
 
#### Persona 3 — The Hobby Food Nerd / Tinkerer 
**Name**: Celeste, 38  
**Life Context**: Loves cooking, sends recipes to friends, hosts dinner 
parties  
**Pain Today**: Has 200 screenshots + Notes app chaos + random saved 
TikToks / 
blogs; unstructured mess   
**Primary Goals**:  
- Aggregate from chosen sources 
- Store and categorize her edits (“my version”) 
- Eventually share best recipes with friends or online

**Value of Product to Her**:   
- Finally gives structure to hobby 
- Allows sharing and personalization 
- Becomes a culinary archive of “her takes” 
### Succes Metrics   
| **Acquisition** | **Activation** | **Retention** |
|------------------|----------------|----------------|
| Site Visits | Accounts Created | Repeat Visitor |
| Doesn’t Abandon Rate (Stays for 10+ seconds, 2+ clicks) | 1st Recipe Accessed After Account Creation Rate | Recipes Saves/Opened |
|  |  | Average Session Length |
|  |  | Recipe Searches |
|  |  | Average Time Spent on Search Page |
 
### Key Features 
#### Core Features (For MVP) 
- Search which aggregates recipes from a predefined list of blogs 
and extracts a photo and title   
- Browse a list of recipes (scrolling) --> Will be hardcoded at 
first 
- Recipe Details Page: Image, the ingredient list and instructions 
to prepare the meal in a standard format.   
 
#### Core Features (Future Sprint) 
- Account Creation  
- Account Login  
- Manual Entry of New Recipe 
- Saved Lists 
- Ability to save recipes to own page (will require login and create 
account pages, as well as a data table connecting users with all saved 
recipes)   
- Share recipes with friends  
- Allow the user to add their own custom blog list to do the 
search   
- Filtering:  
	- Cuisines type  
	- Time to Make  
	- Author   
	- Ingredients  
	- Food Category (drink, dessert, entree)  
	- Dietary Restrictions / Allergies 
- Recommendation Search (Input ingredients you have and it outputs 
recipes) 
 
## Product Backlog with INVEST User Stories 
Stories in GitHub Project: 
https://github.com/users/luciavinapatino/projects/1/views/1 

## Story Point Estimates and Prioritization 
Story Estimates in GitHub Project: 
https://github.com/users/luciavinapatino/projects/1/views/1 

## Wireframes/Mockups
Link to Figma: https://prong-race-07856116.figma.site  
 
## Technical Architecture Plan 
### Backend framework 
- We’ll use Django. 
- It gives us built-in tools for user accounts, database management, 
and an admin dashboard, so we can focus on building recipe features like 
saving favorites and searching recipes. 

### Database and structure 
- We’ll use PostgreSQL for both development and production. 
- It’s reliable, secure, and supports features like full-text 
search (for finding recipes by keywords) and strong data consistency. 
- Main tables: 
	- Users – people who create accounts. 
	- Recipes – includes the title, description, author, and date 
created. 
	- Steps – numbered instructions linked to each recipe. 
	- Tags – labels like “vegan” or “dessert.” 
	- Favorites – connects users to the recipes they’ve favorited. 
- (Each recipe can have many tags, and each user can favorite many 
recipes.) 

### Deployment (where it runs online) 
- We’ll host everything on Render or Railway, since both can run 
Django apps and include managed PostgreSQL databases with simple setup. 
-  If we need more flexibility later, Fly.io or Heroku are easy to 
move to. 

### Third-party services 
- Login: Django’s built-in authentication system. 
- Email: Use Postmark or SendGrid for password resets and 
notifications. 
- File uploads (optional): Use Cloudflare R2 or Amazon S3 if users 
can upload images. 
- Error tracking (optional): Add Sentry to catch and report bugs 
automatically. 

### Development workflow 
- Each developer works on a separate Git branch for their feature 
(like “add-favorites”). 
- When done, open a pull request so someone else can review before 
merging. 
- Keep changes small and test locally first. 
- Use GitHub Actions (or similar) to automatically run tests and 
check for code errors. 
- Store secret keys and database passwords in a local .env file 
(never commit it to GitHub). 

## GitHub Project Setup 
Link to project: 
https://github.com/users/luciavinapatino/projects/1/views/1

## Sprint Planning for Sprint 2 & 3 
Link to Sprint Board: https://github.com/users/luciavinapatino/projects/1  
Link to Sprint 2 Planning Doc: 
https://github.com/luciavinapatino/rough-frost/blob/main/docs/sprints/sprint-2-planning.md 

## Team Documentation 
Link to Team Charter, Definition of Done, and Definition of Ready: 
https://github.com/luciavinapatino/rough-frost/tree/main/docs 

