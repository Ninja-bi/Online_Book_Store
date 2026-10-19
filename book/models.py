from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class Category(models.TextChoices):
    FICTION     = "fiction",     "Fiction"
    NON_FICTION = "non_fiction", "Non-Fiction"
    SCIENCE     = "science",     "Science"
    TECHNOLOGY  = "technology",  "Technology"
    HISTORY     = "history",     "History"
    BIOGRAPHY   = "biography",   "Biography"
    SELF_HELP   = "self_help",   "Self-Help"
    CHILDREN    = "children",    "Children"
    MYSTERY     = "mystery",     "Mystery"
    FANTASY     = "fantasy",     "Fantasy"
    ROMANCE     = "romance",     "Romance"
    OTHER       = "other",       "Other"


class Book(models.Model):
    """Represents a book available in the store."""

    title          = models.CharField(max_length=255)
    author         = models.CharField(max_length=255)
    description    = models.TextField(blank=True)
    isbn           = models.CharField(max_length=13, unique=True, null=True, blank=True)
    price          = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    stock          = models.PositiveIntegerField(default=0)
    cover_image    = models.ImageField(upload_to="covers/", null=True, blank=True)
    category       = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.OTHER,
    )
    rating         = models.DecimalField(max_digits=3, decimal_places=1, default=4.5)
    rating_count   = models.CharField(max_length=30, default="10k")
    format         = models.CharField(max_length=50, default="Paperback")
    pages          = models.PositiveIntegerField(default=320)
    language       = models.CharField(max_length=50, default="English")
    publisher      = models.CharField(max_length=150, default="NOOK Books")
    tag            = models.CharField(max_length=50, blank=True, default="")
    is_bestseller  = models.BooleanField(default=False)
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Book"
        verbose_name_plural = "Books"
        ordering            = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.author}"

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def discount_percentage(self):
        if self.original_price and self.original_price > self.price:
            ratio = (self.original_price - self.price) / self.original_price
            return int(round(ratio * 100))
        return 0

    @property
    def display_tag(self):
        if self.tag:
            return self.tag
        if self.is_bestseller:
            return "BESTSELLER"
        return ""


class Cart(models.Model):
    """Shopping cart model for guest or authenticated user."""

    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carts",
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Cart"
        verbose_name_plural = "Carts"
        ordering            = ["-updated_at"]

    def __str__(self):
        return f"Cart #{self.id} ({self.user or self.session_key})"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def original_total(self):
        total = 0
        for item in self.items.all():
            orig = item.book.original_price or item.book.price
            total += orig * item.quantity
        return total

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def discount(self):
        # Reader discount: Rs. 100 on orders >= Rs. 500
        if self.subtotal >= 500:
            return 100
        return 0

    @property
    def delivery_fee(self):
        return 0  # Free Delivery

    @property
    def total_payable(self):
        return max(0, self.subtotal - self.discount + self.delivery_fee)

    @property
    def total_savings(self):
        return max(0, self.original_total - self.total_payable)

    @property
    def savings_percentage(self):
        if self.original_total > 0:
            return int(round((self.total_savings / self.original_total) * 100))
        return 0


class CartItem(models.Model):
    """Individual item in a shopping cart."""

    cart       = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    book       = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity   = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Cart Item"
        verbose_name_plural = "Cart Items"
        unique_together     = ("cart", "book")
        ordering            = ["id"]

    def __str__(self):
        return f"{self.quantity}x {self.book.title} (Cart #{self.cart_id})"

    @property
    def unit_price(self):
        return self.book.price

    @property
    def subtotal(self):
        return self.book.price * self.quantity
