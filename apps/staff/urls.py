from django.urls import path

from apps.staff import views

app_name = "staff"

urlpatterns = [
    path("", views.staff_list, name="list"),
    path("new/<uuid:key>/", views.staff_new, name="new"),
    path("<uuid:key>/edit/", views.staff_edit, name="edit"),
    path("<uuid:key>/turn-off/", views.staff_turn_off, name="turn_off"),
    path("<uuid:key>/turn-on/", views.staff_turn_on, name="turn_on"),
]
