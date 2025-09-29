import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom

logger = logging.getLogger(__name__)

class NewChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info(f"Attempting to connect: {self.scope}")
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        self.user = await self.get_user_from_token(self.scope['query_string'])

        if self.user:
            self.scope['user'] = self.user
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
            # Send chat history on connect
            await self.send_chat_history()
            # Mark all messages as read for the user
            await self.mark_all_messages_as_read()
            # Notify all members' unread count groups (including self) after marking as read
            await self.notify_unread_count_groups()
        else:
            await self.close()

    @database_sync_to_async
    def get_user_from_token(self, query_string):
        from urllib.parse import parse_qs
        from knox.auth import TokenAuthentication

        parsed = parse_qs(query_string.decode())
        token = parsed.get("token", [None])[0]

        if not token:
            return None

        try:
            user_auth_tuple = TokenAuthentication().authenticate_credentials(token.encode())
            return user_auth_tuple[0]  # the user object
        except Exception as e:
            logger.warning(f"Token auth failed: {e}")
            return None

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')
        message_type = data.get('type')  # Optional

        if message_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_notification',
                    'is_typing': True,
                    'username': self.user.email,
                }
            )
        elif message_type == 'stop_typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'stop_typing_notification',
                    'is_typing': False,
                    'username': self.user.email,
                }
            )
        elif message:  # Normal chat message
            recipient = data.get('recipient')
            # Save the message to the database
            await self.save_message(self.room_name, self.user, message)
            from datetime import datetime
            timestamp = datetime.utcnow().isoformat()
            if recipient:
                # Individual chat
                # send to the recipient's group
                recipient_group_name = f'user_{recipient}'
                await self.channel_layer.group_send(
                    recipient_group_name,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'username': self.user.email,
                        'email': self.user.email,
                        'timestamp': timestamp
                    }
                )
                # Do NOT send directly to sender's socket for individual chat (recipient_group_name is not sender)
            else:
                # Group chat
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'username': self.user.name,
                        'email': self.user.email,
                        'timestamp': timestamp
                    }
                )
               
            # Notify chatrooms_updates group to refresh chatrooms list
            await self.channel_layer.group_send(
                'chatrooms_updates',
                {
                    'type': 'chatrooms_update'
                }
            )
            # Notify all members' unread count groups
            await self.notify_unread_count_groups()

    @database_sync_to_async
    def get_member_ids(self):
        from .models import ChatRoom
        try:
            room = ChatRoom.objects.get(name=self.room_name)
            return list(room.members.values_list('id', flat=True))
        except ChatRoom.DoesNotExist:
            return []

    async def notify_unread_count_groups(self):
        member_ids = await self.get_member_ids()
        for user_id in member_ids:
            group_name = f'unread_count_{user_id}'
            await self.channel_layer.group_send(
                group_name,
                {'type': 'unread_count_update'}
            )

    @database_sync_to_async
    def save_message(self, room_name, sender, content):
        from .models import ChatRoom, Message
        try:
            room = ChatRoom.objects.get(name=room_name)
            Message.objects.create(room=room, sender=sender, content=content)
        except ChatRoom.DoesNotExist:
            pass

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'username': event['username'],
            'email': event.get('email', None),
            'message': event['message'],
            'timestamp': event.get('timestamp', None)
        }))

    async def typing_notification(self, event):
        await self.send(text_data=json.dumps({
            'typing': True,
            'username': event['username']
        }))

    async def stop_typing_notification(self, event):
        await self.send(text_data=json.dumps({
            'typing': False,
            'username': event['username']
        }))

    @database_sync_to_async
    def get_chat_history(self):
        from .models import ChatRoom, Message
        try:
            room = ChatRoom.objects.get(name=self.room_name)
            messages = Message.objects.filter(room=room).order_by('created_at')
            return [
                {
                    'id': msg.id,
                    'sender': msg.sender.name,
                    'email': msg.sender.email,
                    'content': msg.content,
                    'timestamp': msg.created_at.isoformat()
                }
                for msg in messages
            ]
        except ChatRoom.DoesNotExist:
            return []

    async def send_chat_history(self):
        history = await self.get_chat_history()
        await self.send(text_data=json.dumps({
            'type': 'chat_history',
            'messages': history
        }))

    @database_sync_to_async
    def mark_all_messages_as_read(self):
        from .models import ChatRoom
        try:
            room = ChatRoom.objects.get(name=self.room_name)
            room.read_all_messages(self.user)
        except ChatRoom.DoesNotExist:
            pass


class TemChatConsumer(AsyncWebsocketConsumer):
    """Temporary chat consumer to chat with any user by passing their email in the query string.
    Flow:
    - client connects with token and other user's email (param 'email' or 'other_email')
    - server finds existing private ChatRoom for the two users or creates one
    - continues same chat flow as NewChatConsumer for that room
    """
    async def connect(self):
        self.query = self.scope.get('query_string', b'')
        self.user = await self.get_user_from_token(self.query)

        if not self.user:
            await self.close()
            return

        self.scope['user'] = self.user

        # get/create private room for (self.user, other_user_email)
        self.room = await self.get_or_create_private_room(self.query, self.user)
        if not self.room:
            await self.close()
            return

        self.room_name = self.room.name
        self.room_group_name = f'chat_{self.room_name}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.send_chat_history()
        await self.mark_all_messages_as_read()
        await self.notify_unread_count_groups()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')
        message_type = data.get('type')

        if message_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_notification',
                    'is_typing': True,
                    'username': self.user.email,
                }
            )
            return
        if message_type == 'stop_typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'stop_typing_notification',
                    'is_typing': False,
                    'username': self.user.email,
                }
            )
            return

        if message:
            # save and broadcast to room
            await self.save_message(self.room_name, self.user, message)
            from datetime import datetime
            timestamp = datetime.utcnow().isoformat()

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': self.user.name,
                    'email': self.user.email,
                    'timestamp': timestamp,
                }
            )

            # notify viewers of chatrooms list and unread counts
            await self.channel_layer.group_send(
                'chatrooms_updates',
                {'type': 'chatrooms_update'}
            )
            await self.notify_unread_count_groups()

    @database_sync_to_async
    def get_user_from_token(self, query_string):
        from urllib.parse import parse_qs
        from knox.auth import TokenAuthentication

        parsed = parse_qs(query_string.decode())
        token = parsed.get("token", [None])[0]

        if not token:
            return None

        try:
            user_auth_tuple = TokenAuthentication().authenticate_credentials(token.encode())
            return user_auth_tuple[0]
        except Exception as e:
            logger.warning(f"Token auth failed: {e}")
            return None

    @database_sync_to_async
    def get_or_create_private_room(self, query_string, current_user):
        from urllib.parse import parse_qs
        from .models import ChatRoom
        from accounts.models import User as AccountUser
        from django.db import IntegrityError
        import random, string

        parsed = parse_qs(query_string.decode())
        other_email = parsed.get('email', parsed.get('other_email', [None]))[0]
        if not other_email:
            return None

        try:
            other = AccountUser.objects.filter(email=other_email).first()
        except Exception:
            return None

        if not other:
            return None

        # don't allow chatting with self
        if other.id == current_user.id:
            return None

        # try to find an existing private chatroom containing both users
        room = ChatRoom.objects.filter(is_group=False, members=current_user).filter(members=other).first()
        if room:
            return room

        # create a new private chatroom
        # make a compact unique name
        min_id = min(current_user.id, other.id)
        max_id = max(current_user.id, other.id)
        rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        name = f'private_{min_id}_{max_id}_{rand}'
        try:
            room = ChatRoom.objects.create(room_id=name, name=name, is_group=False)
            room.members.add(current_user, other)
            return room
        except IntegrityError:
            # fallback: try again with a different suffix
            rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            name = f'private_{min_id}_{max_id}_{rand}'
            try:
                room = ChatRoom.objects.create(room_id=name, name=name, is_group=False)
                room.members.add(current_user, other)
                return room
            except Exception:
                return None

    @database_sync_to_async
    def save_message(self, room_name, sender, content):
        from .models import ChatRoom, Message
        try:
            room = ChatRoom.objects.get(name=room_name)
            Message.objects.create(room=room, sender=sender, content=content)
        except ChatRoom.DoesNotExist:
            pass

    @database_sync_to_async
    def get_chat_history(self):
        from .models import ChatRoom, Message
        try:
            room = ChatRoom.objects.get(name=self.room_name)
            messages = Message.objects.filter(room=room).order_by('created_at')
            return [
                {
                    'id': msg.id,
                    'sender': msg.sender.name,
                    'email': msg.sender.email,
                    'content': msg.content,
                    'timestamp': msg.created_at.isoformat()
                }
                for msg in messages
            ]
        except ChatRoom.DoesNotExist:
            return []

    async def send_chat_history(self):
        history = await self.get_chat_history()
        await self.send(text_data=json.dumps({
            'type': 'chat_history',
            'messages': history
        }))

    @database_sync_to_async
    def get_member_ids(self):
        from .models import ChatRoom
        try:
            room = ChatRoom.objects.get(name=self.room_name)
            return list(room.members.values_list('id', flat=True))
        except ChatRoom.DoesNotExist:
            return []

    async def notify_unread_count_groups(self):
        member_ids = await self.get_member_ids()
        for user_id in member_ids:
            group_name = f'unread_count_{user_id}'
            await self.channel_layer.group_send(
                group_name,
                {'type': 'unread_count_update'}
            )

    @database_sync_to_async
    def mark_all_messages_as_read(self):
        from .models import ChatRoom
        try:
            room = ChatRoom.objects.get(name=self.room_name)
            room.read_all_messages(self.user)
        except ChatRoom.DoesNotExist:
            pass


class ChatRoomsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'chatrooms_updates'
        self.user = await self.get_user_from_token(self.scope['query_string'])
        if self.user:
            self.scope['user'] = self.user
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            await self.send_chatrooms_list()
        else:
            await self.close()

    @database_sync_to_async
    def get_user_from_token(self, query_string):
        from urllib.parse import parse_qs
        from knox.auth import TokenAuthentication
        parsed = parse_qs(query_string.decode())
        token = parsed.get("token", [None])[0]
        if not token:
            return None
        try:
            user_auth_tuple = TokenAuthentication().authenticate_credentials(token.encode())
            return user_auth_tuple[0]  # the user object
        except Exception as e:
            logger.warning(f"Token auth failed: {e}")
            return None

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Optionally handle client messages
        pass

    async def chatrooms_update(self, event):
        await self.send_chatrooms_list()

    @database_sync_to_async
    def get_chatrooms(self):
        """
        Return chatrooms where the user is a member,
        include `other_user` (if private) and the last message.
        """
        from .models import Message

        chatrooms = ChatRoom.objects.filter(members=self.user)

        result = []
        for room in chatrooms:
            data = {
                'id': room.id,
                'name': room.name,
                'is_group': room.is_group,
                'unread': room.get_total_unread_messages(self.user),
                'created_at': room.created_at.isoformat(),
            }

            # Add other user for private chats
            if not room.is_group:
                other_members = room.members.exclude(id=self.user.id)
                if other_members.exists():
                    data['other_user'] = other_members.first().name
                    # avatar
                    data['other_user_avatar'] = other_members.first().avatar.url if other_members.first().avatar else ''
                else:
                    data['other_user'] = None
                    data['other_user_avatar'] = ''

            # Fetch last message
            last_message = (
                Message.objects.filter(room=room)
                .order_by('-created_at')
                .first()
            )

            if last_message:
                data['last_message'] = {
                    'text': last_message.content,
                    'created_at': last_message.created_at.isoformat(),
                    'sender': last_message.sender.name,
                }
            else:
                data['last_message'] = None

            result.append(data)

        return result


    async def send_chatrooms_list(self):
        chatrooms = await self.get_chatrooms()
        await self.send(text_data=json.dumps({
            'type': 'chatrooms_list',
            'chatrooms': chatrooms
        }, default=str))


class UnreadCountConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = await self.get_user_from_token(self.scope['query_string'])
        if self.user:
            self.group_name = f'unread_count_{self.user.id}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            await self.send_unread_count()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    @database_sync_to_async
    def get_user_from_token(self, query_string):
        from urllib.parse import parse_qs
        from knox.auth import TokenAuthentication
        parsed = parse_qs(query_string.decode())
        token = parsed.get("token", [None])[0]
        if not token:
            return None
        try:
            user_auth_tuple = TokenAuthentication().authenticate_credentials(token.encode())
            return user_auth_tuple[0]  # the user object
        except Exception as e:
            logger.warning(f"Token auth failed: {e}")
            return None

    @database_sync_to_async
    def get_total_unread_count(self):
        from .models import ChatRoom
        chatrooms = ChatRoom.objects.filter(members=self.user)
        total = 0
        for room in chatrooms:
            total += room.get_total_unread_messages(self.user)
        return total

    async def send_unread_count(self):
        count = await self.get_total_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': count
        }))

    async def receive(self, text_data):
        # Optionally allow client to request refresh
        await self.send_unread_count()

    async def unread_count_update(self, event):
        await self.send_unread_count()