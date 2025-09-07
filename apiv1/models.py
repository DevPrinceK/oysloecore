from django.db import models
import random, string
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


class Product(models.Model):
    '''Product model for storing product details'''
    def generate_pid(self):
        '''Generates a unique product ID'''
        return 'pid_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=15))

    pid = models.CharField(max_length=20, unique=True, default=generate_pid)
    name = models.CharField(max_length=100)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)  
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Category(models.Model):
    '''Category model for storing product categories'''
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class SubCategory(models.Model):
    '''SubCategory model for storing product sub-categories'''
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.category.name} - {self.name}"

class Feature(models.Model):
    '''Feature model for storing product features for certain sub-categories'''
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='features')
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return f"{self.subcategory.name} - {self.name}"
    
class ProductFeature(models.Model):
    '''Intermediate model to link products with their features and values'''
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_features')
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)
    value = models.CharField(max_length=255)

    class Meta:
        unique_together = ('product', 'feature')

    def __str__(self):
        return f"{self.product.name} - {self.feature.name}: {self.value}"

