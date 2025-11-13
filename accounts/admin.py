from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Wallet, OTP, Referral, Coupon, Location


@admin.register(User)
class UserAdmin(BaseUserAdmin):
	model = User
	list_display = (
		'id', 'email', 'phone', 'name', 'is_active', 'is_staff', 'created_at', 'updated_at'
	)
	list_filter = ('is_active', 'is_staff', 'is_superuser', 'deleted', 'created_at')
	search_fields = ('email', 'phone', 'name')
	ordering = ('-created_at',)

	fieldsets = (
		(None, {'fields': ('email', 'phone', 'password')}),
		('Personal info', {'fields': ('name', 'address', 'avatar')}),
		('Preferences', {'fields': ('preferred_notification_email', 'preferred_notification_phone')}),
		('Status', {'fields': ('deleted', 'is_active', 'phone_verified', 'email_verified', 'created_from_app')}),
		('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
	)
	add_fieldsets = (
		(None, {
			'classes': ('wide',),
			'fields': ('email', 'phone', 'name', 'password1', 'password2'),
		}),
	)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'balance', 'created_at', 'updated_at')
	search_fields = ('user__email', 'user__name', 'user__phone')
	list_filter = ('created_at',)
	ordering = ('-created_at',)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
	list_display = ('id', 'phone', 'otp', 'created_at')
	search_fields = ('phone', 'otp')
	list_filter = ('created_at',)
	ordering = ('-created_at',)


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
	list_display = ('id', 'inviter', 'invitee', 'code', 'used_referral_code', 'created_at')
	search_fields = ('inviter__email', 'inviter__name', 'invitee__email', 'invitee__name', 'code', 'used_referral_code')
	list_filter = ('created_at',)
	ordering = ('-created_at',)


@admin.register(Coupon)
class AccountsCouponAdmin(admin.ModelAdmin):
	list_display = ('id', 'code', 'points', 'is_expired', 'created_by', 'created_at')
	search_fields = ('code', 'created_by__email', 'created_by__name')
	list_filter = ('is_expired', 'created_at')
	ordering = ('-created_at',)


@admin.register(Location)
class AccountsLocationAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'region', 'created_at', 'updated_at')
	search_fields = ('name',)
	list_filter = ('region', 'created_at')
	ordering = ('name',)
