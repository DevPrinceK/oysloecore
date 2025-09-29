'''
This module contains the models for the accounts application.
It includes the User, and OTP models.
These models are used to store information about the users 
and their otp information.

'''

from datetime import timedelta
import random
import string
from django.utils import timezone

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from oysloecore.sysutils.constants import UserLevelTrack
from oysloecore.sysutils.models import TimeStampedModel

from notifications.utils import send_mail

from .manager import AccountManager


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    '''Custom User model for the application'''
    email = models.EmailField(max_length=50, unique=True)
    phone = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=500, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    deleted = models.BooleanField(default=False)  # Soft delete

    # Use primitive strings for choices to avoid exposing Enum instances to DRF/JSON encoders
    level = models.CharField(
        max_length=10,
        choices=[(tag.value, tag.value) for tag in UserLevelTrack],
        default=UserLevelTrack.SILVER.value,
    )
    referral_points = models.IntegerField(default=0)
    
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

    def redeem_points(self) -> bool:
        '''Redeem referral points'''
        # check if user can redeem. User can only redeem in multiples of 2,500 points. 
        # eg. if user has 3000 points, they can only redeem 2500 points whiles 500 points remains in their account
        pass

    def __str__(self):
        return self.name


class Referral(TimeStampedModel):
    '''Model to track user referrals'''
    def generate_ref_code():
        '''Generates a unique referral code'''
        return 'OYS-' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invitations')
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals')
    code = models.CharField(max_length=20, unique=True, default=generate_ref_code)

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

    def deposit(self, amount: float) -> None:
        '''Deposit money into the wallet'''
        self.balance += amount
        self.save()

    def withdraw(self, amount: float) -> None:
        '''Withdraw money from the wallet'''
        self.balance -= amount
        self.save()

    def __str__(self):
        return f"{self.user.name}'s Wallet"


class OTP(TimeStampedModel):
    '''One Time Password model'''
    email = models.CharField(max_length=100)
    otp = models.CharField(max_length=6)

    def is_expired(self) -> bool:
        '''Returns True if the OTP is expired'''
        return (self.created_at + timedelta(minutes=30)) < timezone.now()
    
    def send_otp_to_user(self) -> None:
        '''Send the OTP to the user'''
        msg = f'Welcome to Oysloe Market Place.\n\nYour OTP is {self.otp}\n\nRegards,\nOysloe Team'
        send_mail([self.email], 'OTP', msg)

    def __str__(self):
        return self.email + ' - ' + self.otp