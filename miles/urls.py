from django.urls import path

from . import views

app_name = "miles"

urlpatterns = [
    path("claim/", views.claim_miles, name="claim_miles"),
]
