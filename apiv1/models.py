from django.db import models
import random, string
from accounts.models import User
from oysloecore.sysutils.constants import ProductStatus, ProductStatus, ProductType, Regions
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
    def generate_pid():
        '''Generates a unique product ID'''
        return 'pid_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=15))

    pid = models.CharField(max_length=20, unique=True, default=generate_pid)
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)  
    location = models.ForeignKey('Location', on_delete=models.SET_NULL, null=True, blank=True)
    type = models.CharField(max_length=100, choices=[(tag.value, tag.value) for tag in ProductType], default=ProductType.SALE.value)
    status = models.CharField(max_length=20, choices=[(tag.value, tag.value) for tag in ProductStatus], default=ProductStatus.PENDING.value)
    is_taken = models.BooleanField(default=False)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=100, default='One Time Payment')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products', null=True)
    suspension_note = models.TextField(blank=True, null=True, help_text='Reason provided when this product is suspended by an admin.')
    
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
    

class PosibleFeatureValue(TimeStampedModel):
    '''Model to store possible values for a feature'''
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, related_name='values')
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.feature.name} - {self.value}"

    
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

    # Users who liked this review
    likes = models.ManyToManyField(User, related_name='liked_reviews', blank=True)

    class Meta:
        unique_together = ('product', 'user')

    def __str__(self):
        return f"{self.user.name} - {self.product.name} Review"
    
class Feedback(TimeStampedModel):
    '''Feedback model for storing user feedback of the app'''
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()
    message = models.TextField()

    def __str__(self):
        return f"{self.user.name} - {self.rating} Feedback"


class Favourite(TimeStampedModel):
    """Tracks products favourited by users."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favourites')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='favourited_by')

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.email} ❤ {self.product.pid}"


class ProductLike(TimeStampedModel):
    """Tracks likes on products by users."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_likes')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='liked_by')

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.email} 👍 {self.product.pid}"


class ProductReport(TimeStampedModel):
    """Reports submitted by users against products/ads."""
    REASON_SPAM = 'SPAM'
    REASON_INAPPROPRIATE = 'INAPPROPRIATE'
    REASON_SCAM = 'SCAM'
    REASON_OTHER = 'OTHER'
    REASON_CHOICES = [
        (REASON_SPAM, 'Spam or misleading'),
        (REASON_INAPPROPRIATE, 'Inappropriate content'),
        (REASON_SCAM, 'Scam or fraud'),
        (REASON_OTHER, 'Other'),
    ]

    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='reports')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_reports')
    reason = models.CharField(max_length=30, choices=REASON_CHOICES, default=REASON_OTHER)
    message = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('product', 'user')

    def __str__(self):
        return f"Report on {self.product.pid} by {self.user.email}"


class Location(TimeStampedModel):
    """Location model for admin-managed locations."""
    name = models.CharField(max_length=150, unique=True)
    region = models.CharField(max_length=50, choices=[(t.value, t.value) for t in Regions], default=Regions.GREATER_ACCRA.value)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


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


class Subscription(TimeStampedModel):
    """Subscription/package model for different plans users can buy."""
    name = models.CharField(max_length=100, unique=True)
    tier = models.CharField(max_length=50,)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.0, help_text='Just a tag to be used for differentiating plans')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text='Percentage discount on the original price if any')
    features = models.TextField(help_text='Comma-separated list of features included in this subscription')
    duration_days = models.PositiveIntegerField(help_text='Duration of the subscription in days')
    max_products = models.PositiveIntegerField(help_text='Maximum number of products allowed under this subscription. Use 0 for unlimited.')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def get_effective_price(self):
        """Return the price after applying discount percentage if original_price and discount_percentage are set.
        Falls back to `price` when discount data is incomplete."""
        try:
            if self.original_price and self.discount_percentage:
                # discount_percentage assumed to be e.g. 10 for 10%
                discount_fraction = (self.discount_percentage or 0) / 100
                discounted = self.original_price * (1 - discount_fraction)
                # Ensure not negative
                if discounted < 0:
                    return self.price
                return discounted
        except Exception:
            return self.price
        return self.price

    def get_features_list(self):
        """Return features as a list split on commas, trimming whitespace."""
        if not self.features:
            return []
        return [f.strip() for f in self.features.split(',') if f.strip()]


class UserSubscription(TimeStampedModel):
    """Tracks which subscription a user has and until when it is valid."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='user_subscriptions')
    payment = models.OneToOneField(
        'Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_subscription',
        help_text='Payment record that funded this subscription (if any).',
    )

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} -> {self.subscription.name} ({self.start_date} - {self.end_date})"


class Payment(TimeStampedModel):
    """Payment records for subscriptions and other billable actions.

    Initially focused on subscription purchases via Paystack.
    """

    STATUS_PENDING = 'PENDING'
    STATUS_SUCCESS = 'SUCCESS'
    STATUS_FAILED = 'FAILED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        help_text='Subscription this payment is intended for (if applicable).',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='GHS')
    provider = models.CharField(max_length=30, default='paystack')
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    channel = models.CharField(max_length=50, blank=True, null=True)
    raw_response = models.JSONField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.provider.upper()} {self.reference} ({self.status})"


class AccountDeleteRequest(TimeStampedModel):
    """Stores user account deletion requests with reasons and approval status."""

    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='delete_requests')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    admin_comment = models.TextField(blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Delete request for {self.user.email} - {self.status}"
    

class PrivacyPolicy(TimeStampedModel):
    '''Model to store privacy policy content'''
    title = models.CharField(max_length=200, default='Privacy Policy')
    date = models.DateField()
    body = models.TextField()

    def __str__(self):
        return f"Privacy Policy updated on {self.updated_at.strftime('%Y-%m-%d %H:%M:%S')}"
    

class TermsAndConditions(TimeStampedModel):
    '''Model to store terms and conditions content'''
    title = models.CharField(max_length=200, default='Terms and Conditions')
    date = models.DateField()
    body = models.TextField()

    def __str__(self):
        return f"Terms and Conditions updated on {self.updated_at.strftime('%Y-%m-%d %H:%M:%S')}"
    

class JobApplication(TimeStampedModel):
    '''Model to store job application details'''

    def generate_application_id():
        """Generates a short unique application ID.

        Uses a callable so a new value is generated per instance.
        """
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

    application_id = models.CharField(max_length=20, unique=True, default=generate_application_id)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    location = models.CharField(max_length=100)
    gender = models.CharField(max_length=20)
    dob = models.DateField()
    resume = models.FileField(upload_to='job_applications/resumes/')
    cover_letter = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Job Application from {self.name} ({self.email})"