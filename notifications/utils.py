import array
import logging
import os

from django.conf import settings as dj_settings
from pyfcm import FCMNotification

from .models import FCMDevice

logger = logging.getLogger(__name__)

_push_service = None


def _get_push_service() -> FCMNotification | None:
    global _push_service
    if _push_service is not None:
        return _push_service

    # Preferred: keep the whole service-account JSON in an env var.
    # This avoids storing key files on disk/repo. We materialize it to a runtime-only path.
    service_account_json = os.getenv('FCM_SERVICE_ACCOUNT_JSON')

    service_account_file = os.getenv('FCM_SERVICE_ACCOUNT_FILE')
    if service_account_json:
        try:
            decoded = service_account_json.strip()
        except Exception:
            logger.exception('Invalid FCM_SERVICE_ACCOUNT_JSON')
            return None

        runtime_dir = dj_settings.BASE_DIR / '.runtime'
        runtime_dir.mkdir(parents=True, exist_ok=True)
        service_account_file = str(runtime_dir / 'fcm-service-account.json')
        try:
            # Only write if missing or changed.
            if not os.path.exists(service_account_file) or open(service_account_file, 'r', encoding='utf-8').read() != decoded:
                with open(service_account_file, 'w', encoding='utf-8') as f:
                    f.write(decoded)
        except Exception:
            logger.exception('Failed to write runtime FCM service account file')
            return None

    if not service_account_file:
        # Legacy fallback (discouraged): repo-relative key file.
        # Only allow this in development to reduce the chance of leaking keys in prod.
        if (os.getenv('ENVIRONMENT') or '').lower() == 'development':
            service_account_file = str(dj_settings.BASE_DIR / 'notifications' / 'oysloemobile.json')
        else:
            logger.warning('FCM not configured: set FCM_SERVICE_ACCOUNT_JSON or FCM_SERVICE_ACCOUNT_FILE')
            return None

    project_id = os.getenv('FCM_PROJECT_ID') or 'oysloemobile'

    if not os.path.exists(service_account_file):
        logger.warning(f"FCM service account file not found: {service_account_file}")
        return None

    _push_service = FCMNotification(
        service_account_file=service_account_file,
        project_id=project_id,
    )
    return _push_service


def send_push_notification(user, title, message, *, data_payload=None):
    push_service = _get_push_service()
    if not push_service:
        return "FCM not configured"

    devices = FCMDevice.objects.filter(user=user)
    registration_ids = [device.token for device in devices]

    if not registration_ids:
        return "No devices"

    params_list = [
        {
            "fcm_token": token,
            "notification_title": title,
            "notification_body": message,
            "data_payload": data_payload or {},
        }
        for token in registration_ids
    ]

    try:
        result = push_service.async_notify_multiple_devices(
            params_list=params_list,
        )
    except Exception:
        logger.exception("FCM push send failed")
        return "FCM send failed"

    logger.info(f"Push notification sent to {len(registration_ids)} devices")
    return result


def send_mail(receipient: list, subject: str, message: str) -> None:
    """
    Send an email
    """
    from django.core.mail import send_mail
    from django.conf import settings

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        receipient,
        fail_silently=False,
    )


import requests


def send_sms(message: str, recipients: array.array, sender: str | None = None):
    '''Sends an SMS to the specified recipients'''
    sender = sender or getattr(dj_settings, 'SENDER_ID', None)
    header = {"api-key": getattr(dj_settings, 'ARKESEL_API_KEY', ''), 'Content-Type': 'application/json',
              'Accept': 'application/json'}
    SEND_SMS_URL = "https://sms.arkesel.com/api/v2/sms/send"
    payload = {
        "sender": sender,
        "message": message,
        "recipients": recipients
    } 
    try:
        response = requests.post(SEND_SMS_URL, headers=header, json=payload)
    except Exception as e:
        print(f"Error: {e}")
        return False
    else:
        print(response.json())
        return response.json()