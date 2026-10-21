from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Order, OrderItem


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("book", "title", "author", "book_format", "unit_price", "original_price", "quantity", "subtotal")
    fields = ("title", "author", "book_format", "unit_price", "quantity", "subtotal")

    def subtotal(self, obj):
        return f"₹{obj.subtotal}"
    subtotal.short_description = "Subtotal"


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display   = ("id", "full_name", "email", "status", "payment_method", "total_payable", "created_at")
    list_filter    = ("status", "payment_method", "is_paid", "created_at")
    search_fields  = ("email", "first_name", "last_name", "phone")
    readonly_fields = ("subtotal", "discount", "delivery_fee", "gst", "total_payable", "created_at", "updated_at")
    inlines        = [OrderItemInline]

    fieldsets = (
        ("Contact & Customer", {"fields": ("user", "email", "first_name", "last_name", "phone")}),
        ("Shipping Address", {"fields": ("street_address", "landmark", "city", "state", "pin_code", "country")}),
        ("Payment Details", {"fields": ("payment_method", "payment_reference", "is_paid")}),
        ("Pricing Breakdown", {"fields": ("subtotal", "discount", "delivery_fee", "gst", "total_payable")}),
        ("Status & Logistics", {"fields": ("status", "notes", "created_at", "updated_at")}),
    )


@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display  = ("order", "title", "author", "book_format", "unit_price", "quantity")
    list_filter   = ("book_format",)
    search_fields = ("title", "author")

