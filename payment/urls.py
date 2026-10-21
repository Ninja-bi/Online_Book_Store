from django.urls import path
from . import views

urlpatterns = [
    # Initiate Cashfree payment session
    path("initiate/", views.initiate_payment, name="payment-initiate"),

    # Server-side return & verification after Cashfree checkout redirect
    path("verify/", views.verify_payment, name="payment-verify"),

    # Cashfree asynchronous webhook listener
    path("webhook/", views.cashfree_webhook, name="payment-webhook"),

    # JSON status endpoint
    path("status/<str:order_id>/", views.payment_status_api, name="payment-status-api"),
]
