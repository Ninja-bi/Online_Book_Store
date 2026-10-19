"""HTML page routes for the Book app."""

from django.urls import path
from .page_views import (
    home_view,
    book_list_view,
    book_detail_view,
    cart_view,
    cart_update_qty_view,
    cart_remove_item_view,
    cart_add_item_view,
)

urlpatterns = [
    # Book browsing pages
    path("", home_view, name="home"),
    path("books/", book_list_view, name="book-catalog"),
    path("books/<int:pk>/", book_detail_view, name="book-detail-page"),

    # Shopping cart page and actions
    path("cart/", cart_view, name="cart"),
    path("cart/update/", cart_update_qty_view, name="cart-update-qty"),
    path("cart/remove/", cart_remove_item_view, name="cart-remove-item"),
    path("cart/add/", cart_add_item_view, name="cart-add-item"),
]
