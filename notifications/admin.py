from django.contrib import admin
from .models import FCMDevice


@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'token', 'created_at')
	search_fields = ('user__email', 'user__name', 'token')
	list_filter = ('created_at',)
	ordering = ('-created_at',)
