import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Alert
from .utils import send_push_notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Alert)
def send_alert_push_notification(sender, instance: Alert, created: bool, **kwargs):
    if not created:
        return

    try:
        # Keep payload small and string-only for FCM data payload compatibility.
        data_payload = {
            'kind': (instance.kind or ''),
            'alert_id': str(instance.id),
        }
        send_push_notification(
            instance.user,
            instance.title,
            instance.body or '',
            data_payload=data_payload,
        )
    except Exception:
        # Never fail alert creation due to push issues.
        logger.exception('Failed to send push notification for Alert')
