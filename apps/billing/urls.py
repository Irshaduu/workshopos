from django.urls import path

from apps.billing import views

app_name = "billing"

urlpatterns = [
    path("paid-bills/", views.paid_bills, name="paid_bills"),
    path("job-cards/<uuid:key>/bill/", views.bill, name="bill"),
    path("job-cards/<uuid:key>/bill/settle/<uuid:new_key>/", views.settle, name="settle"),
    path(
        "job-cards/<uuid:key>/bill/payments/<uuid:change_key>/",
        views.change_payments,
        name="change_payments",
    ),
]
