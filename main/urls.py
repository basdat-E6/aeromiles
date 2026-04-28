from django.urls import path
from main.views import navbar

app_name = "main"

urlpatterns = [
    path("", navbar, name="navbar"),
]
