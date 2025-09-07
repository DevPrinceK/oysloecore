from django.db import models

from accounts.models import User


class ChatRoom(models.Model):
    '''The chatroom model for storing different chatrooms'''
    # user uuid for the room_id
    room_id = models.CharField(max_length=200, unique=True)
    name = models.CharField(max_length=100, unique=True)
    is_group = models.BooleanField(default=False)
    members = models.ManyToManyField(User, related_name='chatrooms')
    created_at = models.DateTimeField(auto_now_add=True)

    def get_total_unread_messages(self, user):
        '''Returns the total number of unread messages for a user in this chatroom'''
        return self.messages.filter(is_read=False, sender__is_active=True).exclude(sender=user).count()
    
    def read_all_messages(self, user):
        '''Marks all messages as read for a user in this chatroom'''
        self.messages.filter(is_read=False, sender__is_active=True).exclude(sender=user).update(is_read=True)

    def __str__(self):
        return self.name

class Message(models.Model):
    '''Messsage model for storing user messages'''
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.name}: {self.content[:20]}"
