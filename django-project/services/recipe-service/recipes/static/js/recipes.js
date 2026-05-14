// Sample recipe data
const recipes = [
    {
        id: 1,
        title: 'Classic Spaghetti Carbonara',
        cuisine: 'Italian',
        source: 'Serious Eats',
        time: '20 min',
        servings: '4 servings',
        image: 'https://placehold.co/400x300/FFD700/333333?text=Spaghetti+Carbonara'
    },
    {
        id: 2,
        title: 'Creamy Chicken Curry',
        cuisine: 'Indian',
        source: 'Bon Appetit',
        time: '35 min',
        servings: '6 servings',
        image: 'https://placehold.co/400x300/FF8C00/333333?text=Chicken+Curry'
    },
    {
        id: 3,
        title: 'Perfect Chocolate Chip Cookies',
        cuisine: 'American',
        source: "Sally's Baking Addiction",
        time: '25 min',
        servings: '24 servings',
        image: 'https://placehold.co/400x300/8B4513/FFFFFF?text=Chocolate+Cookies'
    },
    {
        id: 4,
        title: 'Fresh Greek Salad',
        cuisine: 'Greek',
        source: 'The Mediterranean Dish',
        time: '15 min',
        servings: '4 servings',
        image: 'https://placehold.co/400x300/32CD32/333333?text=Greek+Salad'
    },
    {
        id: 5,
        title: 'Street-Style Chicken Tacos',
        cuisine: 'Mexican',
        source: 'Minimalist Baker',
        time: '30 min',
        servings: '6 servings',
        image: 'https://placehold.co/400x300/FF6347/FFFFFF?text=Chicken+Tacos'
    },
    {
        id: 6,
        title: 'Asian Beef Stir-Fry',
        cuisine: 'Asian',
        source: 'The Woks of Life',
        time: '25 min',
        servings: '4 servings',
        image: 'https://placehold.co/400x300/8B0000/FFFFFF?text=Beef+Stir-Fry'
    },
    {
        id: 7,
        title: 'Grilled Lemon Herb Salmon',
        cuisine: 'Mediterranean',
        source: 'Downshiftology',
        time: '20 min',
        servings: '4 servings',
        image: 'https://placehold.co/400x300/FF69B4/FFFFFF?text=Grilled+Salmon'
    },
    {
        id: 8,
        title: 'Colorful Buddha Bowl',
        cuisine: 'Vegetarian',
        source: 'Cookie and Kate',
        time: '30 min',
        servings: '4 servings',
        image: 'https://placehold.co/400x300/9370DB/FFFFFF?text=Buddha+Bowl'
    }
];

// Render recipe cards
function renderRecipes(recipesToRender) {
    const grid = document.getElementById('recipesGrid');

    if (!grid) return;

    grid.innerHTML = '';

    recipesToRender.forEach(recipe => {
        const card = document.createElement('a');
        card.href = 'recipe-detail.html';
        card.className = 'recipe-card';

        card.innerHTML = `
            <img src="${recipe.image}" alt="${recipe.title}" class="recipe-card-image">
            <div class="recipe-card-content">
                <div class="recipe-card-header">
                    <h3 class="recipe-card-title">${recipe.title}</h3>
                    <span class="cuisine-tag">${recipe.cuisine}</span>
                </div>
                <p class="recipe-card-source">From ${recipe.source}</p>
                <div class="recipe-card-meta">
                    <div class="meta-item">
                        <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                            <circle cx="10" cy="10" r="8" stroke="currentColor" stroke-width="2" fill="none"/>
                            <path d="M10 5V10L14 12" stroke="currentColor" stroke-width="2"/>
                        </svg>
                        <span>${recipe.time}</span>
                    </div>
                    <div class="meta-item">
                        <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                            <path d="M10 3C7 3 5 5 5 7C5 7 4 7 4 8C4 9 5 9 5 9V13C5 14.5 7 16 10 16C13 16 15 14.5 15 13V9C15 9 16 9 16 8C16 7 15 7 15 7C15 5 13 3 10 3Z" fill="currentColor"/>
                        </svg>
                        <span>${recipe.servings}</span>
                    </div>
                </div>
            </div>
        `;

        grid.appendChild(card);
    });

    // Update results count
    const resultsCount = document.querySelector('.results-count');
    if (resultsCount) {
        resultsCount.textContent = `Showing all ${recipesToRender.length} recipes`;
    }
}

// Filter recipes
function filterRecipes() {
    const cuisineFilter = document.querySelector('.filter-select:nth-of-type(1)');
    const categoryFilter = document.querySelector('.filter-select:nth-of-type(2)');
    const timeFilter = document.querySelector('.filter-select:nth-of-type(3)');
    const authorFilter = document.querySelector('.filter-select:nth-of-type(4)');

    let filtered = [...recipes];

    // Apply cuisine filter
    if (cuisineFilter && cuisineFilter.value !== 'All Cuisines') {
        filtered = filtered.filter(recipe => recipe.cuisine === cuisineFilter.value);
    }

    // Apply author filter
    if (authorFilter && authorFilter.value !== 'All Authors') {
        filtered = filtered.filter(recipe => recipe.source === authorFilter.value);
    }

    renderRecipes(filtered);
}

// Search functionality
function searchRecipes(searchTerm) {
    const filtered = recipes.filter(recipe =>
        recipe.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        recipe.cuisine.toLowerCase().includes(searchTerm.toLowerCase()) ||
        recipe.source.toLowerCase().includes(searchTerm.toLowerCase())
    );

    renderRecipes(filtered);
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Render all recipes initially
    renderRecipes(recipes);

    // Add filter event listeners
    const filterSelects = document.querySelectorAll('.filter-select');
    filterSelects.forEach(select => {
        select.addEventListener('change', filterRecipes);
    });

    // Add search event listener
    const searchInput = document.querySelector('.search-bar input');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            searchRecipes(e.target.value);
        });
    }
});
