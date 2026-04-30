from django.urls import path
from main.views import navbar, dashboard

app_name = "main"

urlpatterns = [
    path("", navbar, name="navbar"),
    path("dashboard/", dashboard, name="dashboard"),
]
