from unittest.mock import patch

from django.test import TestCase

from accounts.models import User
from apiv1.models import ChatRoom, Message


class ChatMessagePushSignalTests(TestCase):
	def setUp(self):
		self.sender = User.objects.create_user(
			email='sender@example.com',
			phone='0000000001',
			password='pass1234',
			name='Sender',
		)
		self.recipient = User.objects.create_user(
			email='recipient@example.com',
			phone='0000000002',
			password='pass1234',
			name='Recipient',
		)
		self.room = ChatRoom.objects.create(room_id='room_1', name='Room 1', is_group=False)
		self.room.members.add(self.sender, self.recipient)

	@patch('notifications.signals.send_push_notification')
	def test_push_sent_to_everyone_except_sender(self, mock_send_push):
		Message.objects.create(room=self.room, sender=self.sender, content='hello')

		self.assertEqual(mock_send_push.call_count, 1)
		args, kwargs = mock_send_push.call_args
		self.assertEqual(args[0], self.recipient)
