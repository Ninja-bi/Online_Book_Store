from django.db import models
from django.conf import settings
from book.models import Book


class OrderStatus(models.TextChoices):
    PENDING    = "pending",    "Pending"
    CONFIRMED  = "confirmed",  "Confirmed"
    SHIPPED    = "shipped",    "Shipped"
    DELIVERED  = "delivered",  "Delivered"
    CANCELLED  = "cancelled",  "Cancelled"


class PaymentMethod(models.TextChoices):
    UPI           = "upi",           "UPI / BHIM"
    CREDIT_CARD   = "credit_card",   "Credit / Debit Card"
    NET_BANKING   = "net_banking",   "Net Banking"
    COD           = "cod",           "Cash on Delivery"
    GPAY          = "gpay",          "Google Pay"
    PAYTM         = "paytm",         "Paytm / Wallets"


class Order(models.Model):
    """Represents a placed order by a user."""

    # ── Relationship ──────────────────────────────────────────────────────────
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    # ── Contact Information ───────────────────────────────────────────────────
    email          = models.EmailField(help_text="Email for confirmation & tracking")
    first_name     = models.CharField(max_length=100)
    last_name      = models.CharField(max_length=100)
    phone          = models.CharField(max_length=20, blank=True)

    # ── Shipping Address ──────────────────────────────────────────────────────
    street_address = models.CharField(max_length=255, help_text="Street address & house/flat no.")
    landmark       = models.CharField(max_length=255, blank=True, help_text="Landmark / delivery instructions")
    city           = models.CharField(max_length=100)
    state          = models.CharField(max_length=100)
    pin_code       = models.CharField(max_length=10)
    country        = models.CharField(max_length=100, default="India")

    # ── Payment ───────────────────────────────────────────────────────────────
    payment_method    = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
        default=PaymentMethod.UPI,
    )
    payment_reference = models.CharField(max_length=255, blank=True, help_text="UPI ID / transaction ref")
    is_paid           = models.BooleanField(default=False)

    # ── Pricing ───────────────────────────────────────────────────────────────
    subtotal          = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount          = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst               = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_payable     = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ── Status & Timestamps ───────────────────────────────────────────────────
    status     = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )
    notes      = models.TextField(blank=True, help_text="Internal notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Order"
        verbose_name_plural = "Orders"
        ordering            = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} — {self.first_name} {self.last_name} ({self.status})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def full_address(self):
        parts = [self.street_address, self.city, self.state, self.pin_code, self.country]
        return ", ".join(p for p in parts if p)

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    """A single book line-item within an order."""

    order    = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    book     = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True)

    # Snapshot fields — stored at time of purchase so price changes don't affect history
    title         = models.CharField(max_length=255)
    author        = models.CharField(max_length=255)
    cover_image   = models.ImageField(upload_to="covers/", null=True, blank=True)
    book_format   = models.CharField(max_length=50, default="Paperback")
    unit_price    = models.DecimalField(max_digits=10, decimal_places=2)
    original_price= models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantity      = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name        = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.quantity}× {self.title} (Order #{self.order_id})"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    @property
    def discount_percentage(self):
        if self.original_price and self.original_price > self.unit_price:
            ratio = (self.original_price - self.unit_price) / self.original_price
            return int(round(ratio * 100))
        return 0
