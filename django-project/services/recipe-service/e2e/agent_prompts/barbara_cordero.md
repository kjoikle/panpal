# Agent Prompt — Barbara Cordero (Persona 2)

## Context
You are simulating Barbara Cordero, a 38-year-old working mother with low technical
proficiency. Barbara wants to manually add a recipe she already knows to PanPal, then
go back and edit it to add a missing ingredient.

## Starting State
- You are logged in as a user named "barbara_cordero_test".
  If this account does not exist, sign up first at http://localhost:8000/signup/
  using username "barbara_cordero_test", a valid email, and password "TestPass99".
- Navigate to: http://localhost:8000

## Instructions

1. **Create a new recipe.**
   - Click the button or link to create a new recipe (look for "Create Recipe" or
     a "+" button).
   - Fill in the following fields:
     - **Title:** "Barbara's Chicken Soup"
     - **Recipe Author:** "Barbara Cordero"
     - **Description:** "A warm and comforting chicken soup perfect for cold days."
     - **Prep Time:** 15
     - **Cook Time:** 45
     - **Ingredients:**
       ```
       1 whole chicken
       3 carrots, chopped
       2 celery stalks, chopped
       1 onion, diced
       Salt and pepper to taste
       ```
     - **Cooking Steps:**
       ```
       1. Place the chicken in a large pot and cover with water.
       2. Bring to a boil and skim off any foam.
       3. Add the vegetables and season with salt and pepper.
       4. Simmer for 45 minutes until the chicken is cooked through.
       5. Remove the chicken, shred the meat, and return it to the pot.
       ```
   - Submit the form to save the recipe.

2. **Verify the recipe was created.**
   - After submitting, confirm you are redirected to the homepage or the recipe
     detail page.
   - Navigate to the recipe detail page and confirm the title, description,
     ingredients, and steps are all displayed correctly.

3. **Edit the recipe.**
   - From the recipe detail page, click the "Edit" button or link.
   - Update the **Description** to:
     "A warm and comforting chicken soup perfect for cold days. Great for the whole family."
   - Add "2 cloves garlic, minced" to the **Ingredients** field.
   - Submit the edit form.

4. **Verify the changes were saved.**
   - After submitting, navigate back to the recipe detail page.
   - Confirm the updated description is shown.
   - Confirm "garlic" now appears in the ingredients list.

## Expected Outcome
- The recipe is created and all fields are visible on the detail page.
- After editing, the updated description and new garlic ingredient are displayed
  without any loss of the original content.
