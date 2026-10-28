from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("", views.home, name="home"),
    path("sign-in/", views.sign_in, name="sign_in"),
    path("sign-in/code/", views.sign_in_code, name="sign_in_code"),
    path("sign-in/password/", views.sign_in_password, name="sign_in_password"),
]
