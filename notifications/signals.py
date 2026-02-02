import logging
import threading

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from apiv1.models import Message

from .models import Alert
from .utils import send_push_notification, send_sms

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

        # Fire-and-forget an SMS notification as well (best-effort).
        try:
            phone = getattr(instance.user, 'preferred_notification_phone', None) or getattr(instance.user, 'phone', None)
            phone = (str(phone).strip() if phone else '')
            if phone and getattr(settings, 'ARKESEL_API_KEY', ''):
                sms_text = f"{(instance.title or '').strip()} {(instance.body or '').strip()}".strip()
                sms_text = ' '.join(sms_text.split())  # collapse whitespace/newlines
                if instance.kind == 'ACCOUNT_CREATED':
                    sms_text += "\nLogin to your account to get started. https://www.oysloe.com"
                if sms_text:
                    def _sms_send(recipient: str, message: str):
                        try:
                            send_sms(message=message, recipients=[recipient])
                        except Exception:
                            logger.exception('Failed to send SMS notification for Alert')

                    threading.Thread(target=_sms_send, args=(phone, sms_text), daemon=True).start()
        except Exception:
            logger.exception('Failed to queue SMS notification for Alert')

    except Exception:
        # Never fail alert creation due to push issues.
        logger.exception('Failed to send push notification for Alert')


@receiver(post_save, sender=Message)
def send_chat_message_push_notification(sender, instance: Message, created: bool, **kwargs):
    if not created:
        return

    try:
        room = instance.room
        sender_user = instance.sender

        recipients = room.members.filter(is_active=True).exclude(id=sender_user.id)
        if not recipients.exists():
            return

        title = f"New message from {getattr(sender_user, 'name', '') or 'Someone'}"
        if getattr(instance, 'is_media', False):
            body = "Sent an attachment"
        else:
            body = (instance.content or '').strip()

        # Keep payload small and string-only for FCM data payload compatibility.
        data_payload = {
            'kind': 'chat_message',
            'room_id': str(getattr(room, 'room_id', '') or ''),
            'chatroom_id': str(getattr(room, 'id', '') or ''),
            'message_id': str(getattr(instance, 'id', '') or ''),
            'sender_id': str(getattr(sender_user, 'id', '') or ''),
        }

        for user in recipients:
            try:
                send_push_notification(
                    user,
                    title,
                    body,
                    data_payload=data_payload,
                )
            except Exception:
                logger.exception('Failed to send push notification for chat message')
    except Exception:
        # Never fail message creation due to push issues.
        logger.exception('Failed to process chat message push notifications')
