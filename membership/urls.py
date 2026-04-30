from django.urls import path

from .views import kelola_member, identitas

app_name = "membership"

urlpatterns = [
    path("kelola-member/", kelola_member, name="kelola_member"),
    path("identitas/", identitas, name="identitas"),
]
