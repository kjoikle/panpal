from django.urls import path
from analytics import views

urlpatterns = [
    path('api/v1/assignments/get-or-create/', views.assignments_get_or_create, name='assignments_get_or_create'),
    path('api/v1/assignments/', views.assignments_list, name='assignments_list'),
    path('api/v1/impressions/bulk/', views.impressions_bulk, name='impressions_bulk'),
    path('api/v1/events/', views.events_create, name='events_create'),
    path('api/v1/health/', views.health_check, name='health_check'),
]
