'''
This module contains the models for the accounts application.
It includes the User, and OTP models.
These models are used to store information about the users 
and their otp information.

'''

from datetime import timedelta
from decimal import Decimal
import random
import string
from django.utils import timezone
from django.db import IntegrityError, transaction

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from oysloecore.sysutils.constants import Regions, UserLevelTrack
from oysloecore.sysutils.models import TimeStampedModel

from notifications.utils import send_mail, send_sms


# Referral code generator that does NOT touch the DB during import/app checks
def generate_unique_referral_code() -> str:
    """Generate a referral code (RF-XXXXXXXX) without querying the DB.
    Uniqueness is enforced with retries in User.save().
    """
    alphabet = string.ascii_uppercase + string.digits
    return 'RF-' + ''.join(random.choices(alphabet, k=8))

from .manager import AccountManager


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    '''Custom User model for the application'''
    email = models.EmailField(max_length=50, unique=True)
    phone = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=255)
    business_name = models.CharField(max_length=255, default='*** *** *** ***')
    id_number = models.CharField(max_length=50,  default='*** *** *** ***')
    second_number = models.CharField(max_length=15, default='')
    business_logo = models.ImageField(upload_to='business_logos/', blank=True, null=True)
    id_front_page = models.ImageField(upload_to='ids/', blank=True, null=True)
    id_back_page = models.ImageField(upload_to='ids/', blank=True, null=True)
    account_number = models.CharField(max_length=50, null=True)
    account_name = models.CharField(max_length=100, null=True)
    mobile_network = models.CharField(max_length=50, null=True)
    address = models.CharField(max_length=500, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    admin_verified = models.BooleanField(default=False)
    id_verified = models.BooleanField(default=False)

    deleted = models.BooleanField(default=False)  # Soft delete

    # Level and referral tracking
    level = models.CharField(
        max_length=10,
        choices=[(tag.value, tag.value) for tag in UserLevelTrack],
        default=UserLevelTrack.SILVER.value,
    )
    referral_points = models.IntegerField(default=0)
    referral_code = models.CharField(max_length=20, unique=True, default=generate_unique_referral_code)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    created_from_app = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)

    # preferences
    preferred_notification_email = models.EmailField(max_length=50, blank=True, null=True)
    preferred_notification_phone = models.CharField(max_length=15, blank=True, null=True)

    objects = AccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone', 'name']

    @property
    def active_ads(self) -> int:
        from django.db.models import Q
        from apiv1.models import Product
        return Product.objects.filter(
            Q(owner=self) & 
            Q(is_taken=False) & 
            (Q(status='VERIFIED') |
            Q(status='ACTIVE'))
            ).count()

    @property
    def taken_ads(self) -> int:
        from django.db.models import Q
        from apiv1.models import Product
        return Product.objects.filter(
            Q(owner=self) & 
            Q(is_taken=True) & 
            (Q(status='VERIFIED') |
            Q(status='ACTIVE'))
            ).count()

    def add_points(self, points: int) -> None:
        '''Add referral points and auto-update level.'''
        self.referral_points = (self.referral_points or 0) + int(points)
        self.update_level(commit=False)
        self.save(update_fields=["referral_points", "level", "updated_at"])

    def update_level(self, commit: bool = True) -> None:
        '''Update user level based on referral_points thresholds.'''
        pts = self.referral_points or 0
        # thresholds
        if pts >= 1_000_000:
            new_level = UserLevelTrack.DIAMOND.value
        elif pts >= 100_000:
            new_level = UserLevelTrack.GOLD.value
        else:
            new_level = UserLevelTrack.SILVER.value
        if new_level != self.level:
            self.level = new_level
            if commit:
                self.save(update_fields=["level", "updated_at"])

    def get_redeemable_points(self) -> int:
        '''Return the maximum redeemable points in blocks of 2,500.'''
        pts = self.referral_points or 0
        return (pts // 2500) * 2500

    def redeem_points(self) -> tuple[int, Decimal] | None:
        '''Redeem points in multiples of 2,500 -> GHs 500 per 2,500 points.
        Returns (redeemed_points, cash_amount) or None if nothing to redeem.
        '''
        redeemable = self.get_redeemable_points()
        if redeemable <= 0:
            return None
        # compute cash: 2500 pts => 500 GHS
        blocks = redeemable // 2500
        cash = Decimal('500.00') * blocks
        # deduct points
        self.referral_points = (self.referral_points or 0) - redeemable
        self.update_level(commit=False)
        self.save(update_fields=["referral_points", "level", "updated_at"])
        # credit wallet
        wallet, _ = Wallet.objects.get_or_create(user=self)
        wallet.deposit(cash)
        return redeemable, cash

    def __str__(self):
        return self.name

    # Ensure referral_code uniqueness with DB-level safeguard, without DB reads at import time
    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = generate_unique_referral_code()
        attempts = 0
        while True:
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError as e:
                if 'referral_code' in str(e).lower() and attempts < 5:
                    self.referral_code = generate_unique_referral_code()
                    attempts += 1
                    continue
                raise

class Referral(TimeStampedModel):
    '''Model to track user referrals'''
    def generate_ref_code():
        '''Generates a unique referral code'''
        return 'OYS-' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invitations')
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals')
    code = models.CharField(max_length=20, unique=True, default=generate_ref_code)
    used_referral_code = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.inviter.name} referred {self.invitee.name} with code {self.code}"
    
class Coupon(TimeStampedModel):
    '''Model to store coupon details'''
    code = models.CharField(max_length=20, unique=True)
    points = models.IntegerField(choices=[(5, '5'), (50, '50')], default=5)
    is_expired = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        creator = getattr(self.created_by, 'name', 'System') if self.created_by else 'System'
        return f"{creator} created Coupon: {self.code} with {self.points} points"

class Wallet(TimeStampedModel):
    '''Wallet model for storing user wallet information'''
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def deposit(self, amount) -> None:
        '''Deposit money into the wallet'''
        self.balance = (self.balance or Decimal('0.00')) + Decimal(str(amount))
        self.save()

    def withdraw(self, amount) -> None:
        '''Withdraw money from the wallet'''
        self.balance = (self.balance or Decimal('0.00')) - Decimal(str(amount))
        self.save()

    def __str__(self):
        return f"{self.user.name}'s Wallet"


class OTP(TimeStampedModel):
    '''One Time Password model'''
    phone = models.CharField(max_length=10)
    otp = models.CharField(max_length=6)

    def is_expired(self) -> bool:
        '''Returns True if the OTP is expired'''
        return (self.created_at + timedelta(minutes=30)) < timezone.now()
    
    def send_otp_to_user(self) -> None:
        '''Send the OTP to the user'''
        msg = f'Welcome to Oysloe Marketplace.\n\nYour OTP is {self.otp}\n\nRegards,\nOysloe Team'
        send_sms(message=msg, recipients=[self.phone])

    def __str__(self):
        return self.phone + ' - ' + self.otp

class Location(TimeStampedModel):
    '''Location model'''
    region = models.CharField(max_length=50, choices=[(t.value, t.value) for t in Regions], default=Regions.GREATER_ACCRA.value)
    name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.region}"