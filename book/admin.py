from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Book, Cart, CartItem


@admin.register(Book)
class BookAdmin(ModelAdmin):
    """Modern Unfold Admin configuration for the Book model."""

    list_display  = [
        "title", "author", "category", "price", "original_price",
        "stock", "rating", "tag", "is_bestseller", "is_active", "created_at"
    ]
    list_filter   = ["category", "is_bestseller", "is_active"]
    search_fields = ["title", "author", "isbn", "publisher"]
    list_editable = ["price", "original_price", "stock", "tag", "is_bestseller", "is_active"]
    ordering      = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Book Info", {
            "fields": ("title", "author", "description", "isbn", "cover_image", "format"),
        }),
        ("Pricing & Inventory", {
            "fields": ("price", "original_price", "stock"),
        }),
        ("Classification & Highlights", {
            "fields": ("category", "tag", "is_bestseller", "is_active"),
        }),
        ("Details & Ratings", {
            "fields": ("rating", "rating_count", "pages", "language", "publisher"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


class CartItemInline(TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ["book"]


@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ["id", "user", "session_key", "total_items", "subtotal", "updated_at"]
    inlines = [CartItemInline]
    readonly_fields = ["created_at", "updated_at"]

