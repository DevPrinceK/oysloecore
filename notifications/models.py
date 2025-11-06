from django.db import models
from django.contrib.auth import get_user_model
from oysloecore.sysutils.models import TimeStampedModel

class FCMDevice(TimeStampedModel):

    @property
    def user_model(self):
        return get_user_model()
    
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.user.name} - {self.token[:10]}"


class Alert(TimeStampedModel):
    """Simple user-targeted alerts for in-app notifications."""
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='alerts')
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    kind = models.CharField(max_length=50, blank=True, help_text='Type of alert, e.g., ACCOUNT_CREATED, ACCOUNT_APPROVED, PRODUCT_APPROVED')
    is_read = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['kind']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.title}"
