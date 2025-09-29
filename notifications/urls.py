from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SaveFCMTokenView, FCMDeviceViewSet

router = DefaultRouter()
router.register('devices', FCMDeviceViewSet, basename='fcmdevice')

urlpatterns = [
    path('save-fcm-token/', SaveFCMTokenView.as_view()),  # legacy
    path('', include(router.urls)),
]
