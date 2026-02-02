import logging
import os
from collections.abc import Sequence

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


def send_sms(
    *args,
    message: str | None = None,
    recipients: Sequence[str] | None = None,
    sender: str | None = None,
):
    """Send an SMS via Arkesel.

    Supports both call styles used in this repo:
    - Legacy: send_sms(<recipient_phone>, <message>)
    - Preferred: send_sms(message=<message>, recipients=[<recipient_phone>, ...])
    """
    # Backward-compatible positional form: (recipient, message)
    if args:
        if len(args) == 2 and message is None and recipients is None:
            recipient_phone, legacy_message = args
            recipients = [str(recipient_phone)]
            message = str(legacy_message)
        else:
            raise TypeError('send_sms expects (recipient, message) or keyword args message=..., recipients=[...]')

    msg = (message or '').strip()
    if not msg:
        return False

    recips = [str(r).strip() for r in (recipients or []) if str(r).strip()]
    if not recips:
        return False

    api_key = getattr(dj_settings, 'ARKESEL_API_KEY', '')
    if not api_key:
        logger.warning('ARKESEL_API_KEY not configured; skipping SMS send')
        return False

    sender = sender or getattr(dj_settings, 'SENDER_ID', None)
    header = {
        'api-key': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    send_sms_url = "https://sms.arkesel.com/api/v2/sms/send"
    payload = {
        'sender': sender,
        'message': msg,
        'recipients': recips,
    }

    try:
        response = requests.post(send_sms_url, headers=header, json=payload, timeout=10)
        try:
            return response.json()
        except Exception:
            return {'ok': response.ok, 'status_code': response.status_code, 'text': response.text}
    except Exception:
        logger.exception('SMS send failed')
        return False