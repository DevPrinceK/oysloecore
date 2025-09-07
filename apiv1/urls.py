from django.urls import path
from . import views

urlpatterns = [
    path('', views.PingAPI.as_view(), name='ping'),
]

# accounts | authentications
urlpatterns += [
    path('login/', views.LoginAPI.as_view(), name='login'),
    path('logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('verifyotp/', views.VerifyOTPAPI.as_view(), name='verifyotp'),
    path('register/', views.RegisterUserAPI.as_view(), name='register'),
    path('userprofile/', views.UserProfileAPIView.as_view(), name='userprofile'),
    path('changepassword/', views.ChangePasswordAPIView.as_view(), name='changepassword'),
    path('resetpassword/', views.ResetPasswordAPIView.as_view(), name='resetpassword'),
    path('userpreferences/', views.UserPreferenceAPIView.as_view(), name='userpreferences'),
]

# chat related
urlpatterns += [
    # NOTE to get list of chatrooms, use websocket endpoint /ws/chats/
    path('chatroomid/', views.GetChatroomIdAPI.as_view(), name='get_chatroom_id'),
]

# products related
urlpatterns += [
    path('categories/', views.CategoriesAPIView.as_view(), name='categories'),
    path('subcategories/', views.SubCategoriesAPIView.as_view(), name='subcategories'),
    path('products/', views.ProductsAPI.as_view(), name='products'),
    path('relatedproducts/', views.RelatedProductsAPI.as_view(), name='related_products'),
]