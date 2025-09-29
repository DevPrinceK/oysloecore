from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Wallet, OTP


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
		('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
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
	list_display = ('id', 'email', 'otp', 'created_at')
	search_fields = ('email', 'otp')
	list_filter = ('created_at',)
	ordering = ('-created_at',)
