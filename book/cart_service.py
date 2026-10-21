"""Cart business logic and helpers for session and authenticated carts."""

from .models import Book, Cart, CartItem


def get_or_create_cart(request):
    """
    Retrieves or creates a database-backed Cart for the authenticated user
    or current session.
    """
    cart = None

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key)

    return cart


def add_to_cart(cart, book_id, quantity=1):
    """Adds a book to the cart or increments its quantity."""
    try:
        book = Book.objects.get(id=book_id, is_active=True)
    except Book.DoesNotExist:
        return None, "Book not found."

    if book.stock < quantity:
        return None, "Requested quantity exceeds available stock."

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        book=book,
        defaults={"quantity": quantity},
    )

    if not created:
        item.quantity += quantity
        if item.quantity > book.stock:
            item.quantity = book.stock
        item.save()

    return item, None


def update_cart_quantity(cart, book_id, quantity):
    """Updates the quantity of a specific book in the cart."""
    try:
        item = CartItem.objects.get(cart=cart, book_id=book_id)
    except CartItem.DoesNotExist:
        return None, "Item not in cart."

    if quantity <= 0:
        item.delete()
        return None, "Item removed."

    if quantity > item.book.stock:
        quantity = item.book.stock

    item.quantity = quantity
    item.save()
    return item, None


def remove_from_cart(cart, book_id):
    """Removes an item from the cart."""
    CartItem.objects.filter(cart=cart, book_id=book_id).delete()


def merge_session_cart_to_user(session_key, user):
    """
    Merges items from an anonymous session cart into the authenticated user's cart.
    Prevents loss of cart items when a guest user is redirected to sign in to place an order.
    """
    if not session_key or not user or not user.is_authenticated:
        return

    session_cart = Cart.objects.filter(session_key=session_key).first()
    if not session_cart or not session_cart.items.exists():
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)

    for s_item in session_cart.items.all():
        u_item, created = CartItem.objects.get_or_create(
            cart=user_cart,
            book=s_item.book,
            defaults={"quantity": s_item.quantity},
        )
        if not created:
            new_qty = u_item.quantity + s_item.quantity
            if s_item.book.stock and new_qty > s_item.book.stock:
                new_qty = s_item.book.stock
            u_item.quantity = new_qty
            u_item.save()

    # Clean up the session cart
    session_cart.delete()

