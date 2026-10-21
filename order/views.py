from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from book.models import Cart, CartItem
from .models import Order, OrderItem, OrderStatus, PaymentMethod


def _get_cart(request):
    """Helper to retrieve the current authenticated user's cart."""
    if request.user.is_authenticated:
        return Cart.objects.filter(user=request.user).order_by("-updated_at").first()
    return None


@login_required(login_url="user-login")
def checkout(request):
    """Render the checkout page (contact info + shipping address + payment). Requires authentication."""
    cart = _get_cart(request)

    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("cart")

    # Pre-fill name/email for authenticated user
    user = request.user
    name_parts = user.name.split(" ", 1)
    prefill = {
        "first_name": name_parts[0],
        "last_name":  name_parts[1] if len(name_parts) > 1 else "",
        "email":      user.email,
    }

    context = {
        "cart":    cart,
        "prefill": prefill,
        "page":    "checkout",
    }
    return render(request, "order/checkout.html", context)


@login_required(login_url="user-login")
def place_order(request):
    """Handle POST from checkout form — create Order & OrderItems. Requires authentication."""
    if request.method != "POST":
        return redirect("checkout")

    cart = _get_cart(request)
    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("cart")

    payment_method = request.POST.get("payment_method", "cod").strip()
    if payment_method != "cod":
        messages.warning(request, "Online payments must be processed securely through Cashfree.")
        return redirect("checkout")

    # Validate required shipping and contact details
    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    email = request.POST.get("email", "").strip() or request.user.email
    phone = request.POST.get("phone", "").strip()
    street_address = request.POST.get("street_address", "").strip()
    landmark = request.POST.get("landmark", "").strip()
    city = request.POST.get("city", "").strip()
    state = request.POST.get("state", "").strip()
    pin_code = request.POST.get("pin_code", "").strip()

    if not all([first_name, last_name, street_address, city, state, pin_code]):
        messages.error(request, "Please fill in all required shipping address fields.")
        return redirect("checkout")

    # Create COD order securely linked to request.user
    order = Order.objects.create(
        user           = request.user,
        email          = email,
        first_name     = first_name,
        last_name      = last_name,
        phone          = phone,
        street_address = street_address,
        landmark       = landmark,
        city           = city,
        state          = state,
        pin_code       = pin_code,
        payment_method = PaymentMethod.COD,
        payment_reference = "COD",
        is_paid        = False,
        status         = OrderStatus.PENDING,
        subtotal       = cart.subtotal,
        discount       = cart.discount,
        delivery_fee   = cart.delivery_fee,
        gst            = round(cart.total_payable * 5 / 100, 2),
        total_payable  = cart.total_payable,
    )

    # Create order items from cart
    for item in cart.items.all():
        OrderItem.objects.create(
            order          = order,
            book           = item.book,
            title          = item.book.title,
            author         = item.book.author,
            cover_image    = item.book.cover_image,
            book_format    = item.book.format,
            unit_price     = item.book.price,
            original_price = item.book.original_price,
            quantity       = item.quantity,
        )

    # Clear the cart
    cart.items.all().delete()

    messages.success(request, f"Order #{order.id} placed successfully!")
    return redirect("order-confirmation", order_id=order.id)


@login_required(login_url="user-login")
def order_confirmation(request, order_id):
    """Show the order confirmation & receipt page with strict ownership check."""
    order = get_object_or_404(Order.objects.prefetch_related("items", "items__book", "payment"), id=order_id)
    if order.user != request.user and not request.user.is_staff:
        messages.error(request, "You are not authorized to view this order receipt.")
        return redirect("order-history")
    return render(request, "order/confirmation.html", {"order": order})


def order_history(request):
    """Show a user's past orders and ordered items."""
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to view your order history.")
        return redirect("user-login")
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items", "items__book", "payment")
        .order_by("-created_at")
    )
    return render(request, "order/history.html", {"orders": orders})
