from django.urls import path
from . import views

urlpatterns = [
    path('', views.PingAPI.as_view(), name='ping'),
]

# accounts
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