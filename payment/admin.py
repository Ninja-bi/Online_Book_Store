from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = (
        "merchant_order_id",
        "order",
        "amount",
        "currency",
        "status",
        "cf_payment_id",
        "payment_method",
        "created_at",
    )
    list_filter = ("status", "currency", "payment_method", "created_at")
    search_fields = ("merchant_order_id", "cf_order_id", "cf_payment_id", "order__id", "order__email")
    readonly_fields = (
        "merchant_order_id",
        "cf_order_id",
        "payment_session_id",
        "cf_payment_id",
        "amount",
        "currency",
        "created_at",
        "updated_at",
        "raw_response",
    )

    fieldsets = (
        ("Order & Identity", {"fields": ("user", "order", "merchant_order_id", "cf_order_id")}),
        ("Transaction Details", {"fields": ("amount", "currency", "status", "payment_method")}),
        ("Cashfree Gateway Identifiers", {"fields": ("payment_session_id", "cf_payment_id", "bank_reference")}),
        ("Gateway Logs & Timing", {"fields": ("error_message", "created_at", "updated_at", "raw_response"), "classes": ("collapse",)}),
    )

