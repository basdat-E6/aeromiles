from django.urls import path
from main.views import navbar, register, login

app_name = 'main'

urlpatterns = [
    path('', navbar, name='navbar'),
    path('register/', register, name='register'),
    path('login/', login, name='login'),
]