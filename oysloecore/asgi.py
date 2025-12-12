"""ASGI entrypoint for HTTP + WebSocket via Django Channels.

This wires standard Django views over HTTP and the chat-related
websocket routes defined in ``apiv1.routing.websocket_urlpatterns``.
"""

import os

# Configure Django settings **before** importing Django or app modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oysloecore.settings')

from django.core.asgi import get_asgi_application

# Initialize Django and populate the app registry *before* importing routing
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import apiv1.routing

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(apiv1.routing.websocket_urlpatterns)
        ),
    }
)
