from django.db import models
import random, string
from accounts.models import User
from oysloecore.sysutils.models import TimeStampedModel
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.db import transaction


class ChatRoom(TimeStampedModel):
    '''The chatroom model for storing different chatrooms'''
    # user uuid for the room_id
    room_id = models.CharField(max_length=200, unique=True)
    name = models.CharField(max_length=100, unique=True)
    is_group = models.BooleanField(default=False)
    members = models.ManyToManyField(User, related_name='chatrooms')

    def get_total_unread_messages(self, user):
        '''Returns the total number of unread messages for a user in this chatroom'''
        return self.messages.filter(is_read=False, sender__is_active=True).exclude(sender=user).count()
    
    def read_all_messages(self, user):
        '''Marks all messages as read for a user in this chatroom'''
        self.messages.filter(is_read=False, sender__is_active=True).exclude(sender=user).update(is_read=True)

    def __str__(self):
        return self.name

class Message(TimeStampedModel):
    '''Messsage model for storing user messages'''
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.name}: {self.content[:20]}"


class Product(TimeStampedModel):
    '''Product model for storing product details'''
    def generate_pid(self):
        '''Generates a unique product ID'''
        return 'pid_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=15))

    pid = models.CharField(max_length=20, unique=True, default=generate_pid)
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)  
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def all_images(self):
        images = ProductImage.objects.filter(product__pid=self.pid)
        return [img.image.url for img in images]

    def __str__(self):
        return self.name

class ProductImage(TimeStampedModel):
    '''Model to store multiple images for a product'''
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')

    def __str__(self):
        return f"{self.product.name} Image"


class Category(TimeStampedModel):
    '''Category model for storing product categories'''
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class SubCategory(TimeStampedModel):
    '''SubCategory model for storing product sub-categories'''
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.category.name} - {self.name}"

class Feature(TimeStampedModel):
    '''Feature model for storing product features for certain sub-categories'''
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='features')
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return f"{self.subcategory.name} - {self.name}"
    
class ProductFeature(TimeStampedModel):
    '''Intermediate model to link products with their features and values'''
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_features')
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)
    value = models.CharField(max_length=255)

    class Meta:
        unique_together = ('product', 'feature')

    def __str__(self):
        return f"{self.product.name} - {self.feature.name}: {self.value}"

class Review(TimeStampedModel):
    '''Review model for storing product reviews'''
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('product', 'user')

    def __str__(self):
        return f"{self.user.name} - {self.product.name} Review"


class Coupon(TimeStampedModel):
    """Coupon model supporting percent or fixed discounts with limits and validity windows."""
    DISCOUNT_PERCENT = 'percent'
    DISCOUNT_FIXED = 'fixed'
    DISCOUNT_TYPE_CHOICES = [
        (DISCOUNT_PERCENT, 'Percent'),
        (DISCOUNT_FIXED, 'Fixed'),
    ]

    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    max_uses = models.PositiveIntegerField(blank=True, null=True, help_text='Total times this coupon can be used across all users')
    uses = models.PositiveIntegerField(default=0)
    per_user_limit = models.PositiveIntegerField(blank=True, null=True, help_text='Max uses allowed per user')
    valid_from = models.DateTimeField(blank=True, null=True)
    valid_until = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code

    def is_within_validity(self) -> bool:
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def remaining_uses(self) -> int | None:
        if self.max_uses is None:
            return None
        return max(self.max_uses - self.uses, 0)


class CouponRedemption(TimeStampedModel):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='redemptions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coupon_redemptions')

    def __str__(self):
        return f"{self.user.email} -> {self.coupon.code}"