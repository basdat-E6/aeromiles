from django.urls import path
from main.views import landing, dashboard, profil_view

app_name = "main"

urlpatterns = [
    path("", landing, name="landing"),
    path("dashboard/", dashboard, name="dashboard"),
    path("pengaturan-profil/", profil_view, name="profil"),
]
