from pyfcm import FCMNotification
from .models import FCMDevice

# push_service = FCMNotification(api_key="YOUR_SERVER_KEY")
push_service = FCMNotification(
    service_account_file="notifications/dxpmobile.json",
    project_id="dxpmobile"
)

def send_push_notification(user, title, message):
    devices = FCMDevice.objects.filter(user=user)
    registration_ids = [device.token for device in devices]

    if not registration_ids:
        print("No devices found for user.")
        return "No devices"
    
    params_list = [
        {
            "fcm_token": token,
            "notification_title": title,
            "notification_body": message,
        }
        for token in registration_ids
    ]
    result = push_service.async_notify_multiple_devices(
        params_list=params_list,
    )

    print(f"Push notification sent to {len(registration_ids)} devices: {result}")

    return result
