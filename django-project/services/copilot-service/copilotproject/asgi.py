import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'copilotproject.settings')
django.setup()

from copilot.consumers import CopilotConsumer

websocket_urlpatterns = [
    path('ws/copilot/<int:recipe_id>/', CopilotConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AllowedHostsOriginValidator(
        URLRouter(websocket_urlpatterns)
    ),
})
