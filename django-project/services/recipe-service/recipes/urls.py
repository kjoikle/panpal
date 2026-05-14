from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('create/', views.create_recipe, name='create_recipe'),
    path('import/', views.import_recipe, name='import_recipe'),
    path('recipe/<int:pk>/', views.recipe_detail, name='recipe_detail'),
    path('recipe/<int:pk>/edit/', views.edit_recipe, name='edit_recipe'),
    path('recipe/<int:pk>/delete/', views.delete_recipe, name='delete_recipe'),
    path('recipes/<int:pk>/save/', views.save_recipe, name='save_recipe'),

    # API endpoints
    path('api/recipes/', views.recipes_api, name='recipes_api'),
    path('api/recipes/describe/rankings/', views.describe_rankings, name='describe_rankings'),
    path('api/recipes/<int:recipe_id>/describe/', views.describe_recipe, name='describe_recipe'),
    path('recipes/<int:recipe_id>/description-test/', views.description_test_page, name='description_test'),
    path('api/ab-test/event/', views.ab_test_event, name='ab_test_event'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),

    path('autologin/<str:token>/', views.autologin, name='autologin'),

    # Staff admin
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/delete-user/<int:user_id>/', views.admin_delete_user, name='admin_delete_user'),
]
