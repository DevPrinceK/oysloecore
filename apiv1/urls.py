from django.urls import path
from . import views

urlpatterns = [
    path('', views.PingAPI.as_view(), name='ping'),
]
