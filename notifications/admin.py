from django.contrib import admin
from .models import FCMDevice, Alert


@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'token', 'created_at')
	search_fields = ('user__email', 'user__name', 'token')
	list_filter = ('created_at',)
	ordering = ('-created_at',)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'title', 'kind', 'is_read', 'created_at')
	search_fields = (
		'user__email', 'user__name', 'title', 'body'
	)
	list_filter = ('is_read', 'kind', 'created_at')
	ordering = ('-created_at',)
