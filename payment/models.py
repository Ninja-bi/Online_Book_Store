from django.db import models
from django.conf import settings


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PAID = "PAID", "Paid"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
    USER_DROPPED = "USER_DROPPED", "User Dropped"


class Payment(models.Model):
    """
    Tracks payment sessions and transactions initiated through Cashfree Payment Gateway.
    """
    order = models.OneToOneField(
        "order.Order",
        on_delete=models.CASCADE,
        related_name="payment",
        help_text="The local order associated with this payment",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    merchant_order_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Merchant order ID sent to Cashfree (unique per payment attempt)",
    )
    cf_order_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Cashfree internal order ID",
    )
    payment_session_id = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Payment session ID used by Cashfree Web Checkout SDK",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount in INR (calculated on backend)",
    )
    currency = models.CharField(
        max_length=10,
        default="INR",
        help_text="Currency code (INR)",
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    cf_payment_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Cashfree transaction reference ID",
    )
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Payment method used (e.g. card, upi, netbanking, app)",
    )
    bank_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Bank UTR or authorization code",
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Safe error or failure reason from Cashfree",
    )
    raw_response = models.JSONField(
        blank=True,
        null=True,
        help_text="Sanitized Cashfree response payload for audit/debugging",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.merchant_order_id} — Order #{self.order.id} ({self.status}) ₹{self.amount}"

    @property
    def is_successful(self):
        return self.status == PaymentStatus.PAID
