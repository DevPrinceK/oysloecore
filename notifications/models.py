from django.db import models
from django.contrib.auth import get_user_model

class FCMDevice(models.Model):
    @property
    def user_model(self):
        return get_user_model()
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} - {self.token[:10]}"
