from django.urls import path

from .views import kelola_member

app_name = "membership"

urlpatterns = [
    path("kelola-member/", kelola_member, name="kelola_member"),
]
