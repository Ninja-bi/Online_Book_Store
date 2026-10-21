"""HTML page routes for the user app (template views)."""

from django.contrib import messages
from django.contrib.auth import logout as django_logout
from django.shortcuts import render, redirect
from django.urls import path


def login_page(request):
    return render(request, "user/login.html")


def register_page(request):
    return render(request, "user/register.html")


def logout_page(request):
    django_logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("home")


def profile_page(request):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to view your profile.")
        return redirect("user-login")
    orders_count = request.user.orders.count() if hasattr(request.user, "orders") else 0
    return render(request, "user/profile.html", {
        "user": request.user,
        "orders_count": orders_count,
    })


urlpatterns = [
    path("login/",    login_page,    name="user-login"),
    path("register/", register_page, name="user-register"),
    path("logout/",   logout_page,   name="user-logout"),
    path("profile/",  profile_page,  name="user-profile"),
]
