"""HTML page routes for the user app (template views)."""

from django.shortcuts import render
from django.urls import path


def login_page(request):
    return render(request, "user/login.html")


def register_page(request):
    return render(request, "user/register.html")


urlpatterns = [
    path("login/",    login_page,    name="user-login"),
    path("register/", register_page, name="user-register"),
]
