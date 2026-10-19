"""HTML template views for the Book application."""

import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Book, Category, Cart, CartItem
from .cart_service import (
    get_or_create_cart,
    add_to_cart as service_add_to_cart,
    update_cart_quantity as service_update_qty,
    remove_from_cart as service_remove_from_cart,
)


def home_view(request):
    """
    Renders the modern NOOK home page matching Image 1:
    - Hero section with title and search bar
    - Bestsellers section loaded directly from the database
    - Category exploration and additional curated books
    """
    bestsellers = Book.objects.filter(is_active=True, is_bestseller=True)[:6]
    other_books = Book.objects.filter(is_active=True, is_bestseller=False)[:6]

    if not bestsellers.exists():
        bestsellers = Book.objects.filter(is_active=True)[:6]

    context = {
        "bestsellers": bestsellers,
        "other_books": other_books,
        "categories": Category.choices,
    }
    return render(request, "book/home.html", context)


def book_list_view(request):
    """
    Renders the book catalog/shop page with search and category filters.
    """
    qs = Book.objects.filter(is_active=True)

    search_query = request.GET.get("search", "").strip()
    if search_query:
        qs = qs.filter(title__icontains=search_query) | qs.filter(author__icontains=search_query)

    selected_category = request.GET.get("category", "").strip()
    category_label = ""
    if selected_category:
        qs = qs.filter(category=selected_category)
        for val, label in Category.choices:
            if val == selected_category:
                category_label = label
                break

    show_bestsellers = request.GET.get("bestseller") == "1"
    if show_bestsellers:
        qs = qs.filter(is_bestseller=True)

    context = {
        "books": qs,
        "search_query": search_query,
        "selected_category": selected_category,
        "category_label": category_label,
        "show_bestsellers": show_bestsellers,
        "categories": Category.choices,
    }
    return render(request, "book/book_list.html", context)


def book_detail_view(request, pk):
    """
    Renders the book detail page matching Image 2:
    - 3D book showcase with thumbnail strip and navigation arrows
    - Bestseller tag, title, author, rating, pricing, description
    - 2x2 metadata specs grid
    - 'You May Also Like' recommendations from the database
    """
    book = get_object_or_404(Book, pk=pk, is_active=True)

    # Find related books in same category
    related_qs = Book.objects.filter(is_active=True).exclude(pk=book.pk)
    related_books = list(related_qs.filter(category=book.category)[:4])

    # If fewer than 4 related by category, fill from other active books
    if len(related_books) < 4:
        needed = 4 - len(related_books)
        existing_ids = [b.id for b in related_books] + [book.id]
        fillers = list(related_qs.exclude(id__in=existing_ids)[:needed])
        related_books.extend(fillers)

    context = {
        "book": book,
        "related_books": related_books,
    }
    return render(request, "book/book_detail.html", context)


# ── Shopping Cart Views ────────────────────────────────────────────────────────

def _serialize_cart(cart):
    """Helper to return cart summary dict for JSON responses."""
    return {
        "total_items": cart.total_items,
        "original_total": float(cart.original_total),
        "subtotal": float(cart.subtotal),
        "discount": float(cart.discount),
        "delivery_fee": float(cart.delivery_fee),
        "total_payable": float(cart.total_payable),
        "total_savings": float(cart.total_savings),
        "savings_percentage": cart.savings_percentage,
    }


def cart_view(request):
    """
    Renders the shopping cart page:
    - Stepper: 01 Cart / 02 Shipping / 03 Payment / 04 Review
    - Cart items list with cover, format, price, qty controls, wishlist & remove
    - Order Summary sticky card with subtotal, discount, delivery, total, savings
    - Frequently Added Together 3-card recommendation grid
    """
    cart = get_or_create_cart(request)

    # Books for "Frequently Added Together" excluding current cart items
    in_cart_ids = list(cart.items.values_list("book_id", flat=True))
    preferred_ids = [6, 7, 9]  # The God of the Woods, Normal People, The Nightingale
    frequently_added = list(Book.objects.filter(id__in=preferred_ids).exclude(id__in=in_cart_ids))

    if len(frequently_added) < 3:
        needed = 3 - len(frequently_added)
        more = list(Book.objects.filter(is_active=True).exclude(id__in=in_cart_ids + [b.id for b in frequently_added])[:needed])
        frequently_added.extend(more)

    context = {
        "cart": cart,
        "frequently_added": frequently_added,
    }
    return render(request, "book/cart.html", context)


@require_POST
def cart_update_qty_view(request):
    """AJAX endpoint to update quantity of a book in cart."""
    cart = get_or_create_cart(request)
    try:
        data = json.loads(request.body)
        book_id = int(data.get("book_id"))
        quantity = int(data.get("quantity", 1))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"success": False, "error": "Invalid payload."}, status=400)

    item, error = service_update_qty(cart, book_id, quantity)
    return JsonResponse({
        "success": True,
        "item_quantity": item.quantity if item else 0,
        "cart": _serialize_cart(cart),
    })


@require_POST
def cart_remove_item_view(request):
    """AJAX endpoint to remove an item from cart."""
    cart = get_or_create_cart(request)
    try:
        data = json.loads(request.body)
        book_id = int(data.get("book_id"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"success": False, "error": "Invalid payload."}, status=400)

    service_remove_from_cart(cart, book_id)
    return JsonResponse({
        "success": True,
        "cart": _serialize_cart(cart),
    })


@require_POST
def cart_add_item_view(request):
    """AJAX endpoint to add an item to cart."""
    cart = get_or_create_cart(request)
    try:
        data = json.loads(request.body)
        book_id = int(data.get("book_id"))
        quantity = int(data.get("quantity", 1))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"success": False, "error": "Invalid payload."}, status=400)

    item, error = service_add_to_cart(cart, book_id, quantity)
    if error:
        return JsonResponse({"success": False, "error": error}, status=400)

    return JsonResponse({
        "success": True,
        "cart": _serialize_cart(cart),
    })
