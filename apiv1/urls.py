from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .viewsets import (
    CategoryViewSet, SubCategoryViewSet, ProductViewSet, ProductImageViewSet,
    FeatureViewSet, ProductFeatureViewSet, ReviewViewSet,
    ChatRoomViewSet, MessageViewSet
)

urlpatterns = [
    path('', views.PingAPI.as_view(), name='ping'),
]

# accounts | authentications
urlpatterns += [
    path('login/', views.LoginAPI.as_view(), name='login'),
    path('otplogin/', views.OTPLoginAPI.as_view(), name='otp_login'),
    path('logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('verifyotp/', views.VerifyOTPAPI.as_view(), name='verifyotp'),
    path('register/', views.RegisterUserAPI.as_view(), name='register'),
    path('userprofile/', views.UserProfileAPIView.as_view(), name='userprofile'),
    path('changepassword/', views.ChangePasswordAPIView.as_view(), name='changepassword'),
    path('resetpassword/', views.ResetPasswordAPIView.as_view(), name='resetpassword'),
    path('userpreferences/', views.UserPreferenceAPIView.as_view(), name='userpreferences'),
    path('redeem-points/', views.RedeemReferralAPIView.as_view(), name='redeem_points'),
]

# chat related
urlpatterns += [
    # NOTE to get list of chatrooms, use websocket endpoint /ws/chats/
    path('chatroomid/', views.GetChatroomIdAPI.as_view(), name='get_chatroom_id'),
]

# OLD ENDPOINTS
# # products related
# urlpatterns += [
#     path('categories/', views.CategoriesAPIView.as_view(), name='categories'),
#     path('subcategories/', views.SubCategoriesAPIView.as_view(), name='subcategories'),
#     path('products/', views.ProductsAPI.as_view(), name='products'),
#     path('relatedproducts/', views.RelatedProductsAPI.as_view(), name='related_products'),
#     path('reviewproduct/', views.ReviewProductAPI.as_view(), name='review_product'),
# ]

# ViewSets via router
router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('subcategories', SubCategoryViewSet, basename='subcategory')
router.register('products', ProductViewSet, basename='product')
router.register('product-images', ProductImageViewSet, basename='productimage')
router.register('features', FeatureViewSet, basename='feature')
router.register('product-features', ProductFeatureViewSet, basename='productfeature')
router.register('reviews', ReviewViewSet, basename='review')
router.register('chatrooms', ChatRoomViewSet, basename='chatroom')
router.register('messages', MessageViewSet, basename='message')
from .viewsets import CouponViewSet
router.register('coupons', CouponViewSet, basename='coupon')

urlpatterns += [
    path('', include(router.urls)),
]