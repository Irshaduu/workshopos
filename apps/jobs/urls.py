from django.urls import path

from apps.jobs import views

app_name = "jobs"

urlpatterns = [
    path("", views.live_board, name="live_board"),
    path("job-cards/new/", views.job_card_new, name="new"),
    path("job-cards/new/<uuid:key>/", views.job_card_create, name="create"),
    path("job-cards/<uuid:key>/", views.job_card_edit, name="edit"),
    path("job-cards/<uuid:key>/cancel/", views.job_card_cancel, name="cancel"),
]
