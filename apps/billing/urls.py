from django.urls import path

from apps.billing import views

app_name = "billing"

urlpatterns = [
    path("job-cards/<uuid:key>/bill/", views.bill, name="bill"),
    path("job-cards/<uuid:key>/bill/settle/<uuid:new_key>/", views.settle, name="settle"),
]
