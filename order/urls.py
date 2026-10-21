from django.urls import path
from . import views

urlpatterns = [
    path("checkout/",              views.checkout,           name="checkout"),
    path("checkout/place/",        views.place_order,        name="place-order"),
    path("confirmation/<int:order_id>/", views.order_confirmation, name="order-confirmation"),
    path("orders/",                views.order_history,      name="order-history"),
]
