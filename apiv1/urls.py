from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .viewsets import (
    CategoryViewSet, SubCategoryViewSet, ProductViewSet, ProductImageViewSet,
    FeatureViewSet, ProductFeatureViewSet, PosibleFeatureValueViewSet, ReviewViewSet,
    ChatRoomViewSet, MessageViewSet, FeedbackViewSet,
    SubscriptionViewSet, UserSubscriptionViewSet, PaymentViewSet,
    PaystackPaymentViewSet, AccountDeleteRequestViewSet,
    PrivacyPolicyViewSet, TermsAndConditionsViewSet,
)

urlpatterns = [
    path('', views.PingAPI.as_view(), name='ping'),
]

# accounts | authentications
urlpatterns += [
    path('login/', views.LoginAPI.as_view(), name='login'),
    path('adminlogin/', views.AdminLoginAPI.as_view(), name='admin_login'),
    path('otplogin/', views.OTPLoginAPI.as_view(), name='otp_login'),
    path('logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('verifyotp/', views.VerifyOTPAPI.as_view(), name='verifyotp'),
    path('register/', views.RegisterUserAPI.as_view(), name='register'),
    path('userprofile/', views.UserProfileAPIView.as_view(), name='userprofile'),
    path('changepassword/', views.ChangePasswordAPIView.as_view(), name='changepassword'),
    path('resetpassword/', views.ResetPasswordAPIView.as_view(), name='resetpassword'),
    path('userpreferences/', views.UserPreferenceAPIView.as_view(), name='userpreferences'),
    path('redeem-points/', views.RedeemReferralAPIView.as_view(), name='redeem_points'),
    path('admin/verifyuser/', views.AdminVerifyUserAPIView.as_view(), name='admin_verify_user'),
    path('admin/verify-user-id/', views.AdminVerifyUserIdAPIView.as_view(), name='admin_verify_user_id'),
    path('admin/users/', views.AdminListUsersAPIView.as_view(), name='admin_users'),
    path('admin/categories/', views.AdminListCategoriesAPIView.as_view(), name='admin_categories'),
]

# chat related
urlpatterns += [
    # NOTE to get list of chatrooms, use websocket endpoint /ws/chats/
    path('chatroomid/', views.GetChatroomIdAPI.as_view(), name='get_chatroom_id'),
]


# ViewSets via router
router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('subcategories', SubCategoryViewSet, basename='subcategory')
router.register('products', ProductViewSet, basename='product')
router.register('product-images', ProductImageViewSet, basename='productimage')
router.register('features', FeatureViewSet, basename='feature')
router.register('product-features', ProductFeatureViewSet, basename='productfeature')
router.register('possible-feature-values', PosibleFeatureValueViewSet, basename='possiblefeaturevalue')
router.register('reviews', ReviewViewSet, basename='review')
router.register('chatrooms', ChatRoomViewSet, basename='chatroom')
router.register('messages', MessageViewSet, basename='message')
from .viewsets import CouponViewSet
router.register('coupons', CouponViewSet, basename='coupon')
from .viewsets import LocationViewSet
router.register('locations', LocationViewSet, basename='location')
from .viewsets import AlertViewSet
router.register('alerts', AlertViewSet, basename='alert')
from .viewsets import ProductReportViewSet
router.register('product-reports', ProductReportViewSet, basename='product-report')
router.register('feedback', FeedbackViewSet, basename='feedback')
router.register('subscriptions', SubscriptionViewSet, basename='subscription')
router.register('user-subscriptions', UserSubscriptionViewSet, basename='user-subscription')
router.register('payments', PaymentViewSet, basename='payment')
router.register('paystack', PaystackPaymentViewSet, basename='paystack')
router.register('account-delete-requests', AccountDeleteRequestViewSet, basename='account-delete-request')
router.register('privacy-policies', PrivacyPolicyViewSet, basename='privacy-policy')
router.register('terms-and-conditions', TermsAndConditionsViewSet, basename='terms-and-conditions')

urlpatterns += [
    path('', include(router.urls)),
]