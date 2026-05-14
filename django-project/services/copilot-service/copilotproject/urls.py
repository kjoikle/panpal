from django.urls import path
from copilot import views

urlpatterns = [
    path('health/', views.health_check, name='health'),
]
