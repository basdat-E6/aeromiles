from django.urls import path

from . import views

app_name = "miles"

urlpatterns = [
    path("claim/", views.claim_miles, name="claim_miles"),
    path("edit-claim/", views.edit_claim, name="edit_claim"),
    path("delete-claim/", views.delete_claim, name="delete_claim"),
    path("approve-claim/<int:claim_id>/", views.approve_claim, name="approve_claim"),
    path("reject-claim/<int:claim_id>/", views.reject_claim, name="reject_claim"),
]
