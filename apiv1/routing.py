from django.urls import re_path

from apiv1.consumers import ChatRoomsConsumer, NewChatConsumer, UnreadCountConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>\w+)/$', NewChatConsumer.as_asgi()),
    re_path(r'ws/chatrooms/$', ChatRoomsConsumer.as_asgi()),
    re_path(r'ws/unread_count/$', UnreadCountConsumer.as_asgi()),
]