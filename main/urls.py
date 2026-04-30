from django.urls import path
from main.views import navbar, dashboard, profil_view

app_name = "main"

urlpatterns = [
    path("", navbar, name="navbar"),
    path("dashboard/", dashboard, name="dashboard"),
    path('pengaturan-profil/', profil_view, name='profil'),
]
