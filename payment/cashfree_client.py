import base64
import hashlib
import hmac
import logging
import time
from decimal import Decimal
from django.conf import settings
from cashfree_pg.api_client import Cashfree
from cashfree_pg.models.create_order_request import CreateOrderRequest
from cashfree_pg.models.customer_details import CustomerDetails
from cashfree_pg.models.order_meta import OrderMeta

logger = logging.getLogger(__name__)


class CashfreeConfigurationError(Exception):
    """Raised when Cashfree credentials or settings are missing."""
    pass


class CashfreeApiError(Exception):
    """Raised when Cashfree API returns an error or fails."""
    pass


def get_cashfree_client() -> Cashfree:
    """
    Initializes and returns the official Cashfree Python SDK client
    using credentials loaded from settings (.env).
    """
    client_id = getattr(settings, "CASHFREE_CLIENT_ID", "").strip()
    client_secret = getattr(settings, "CASHFREE_CLIENT_SECRET", "").strip()
    env_str = getattr(settings, "CASHFREE_ENV", "sandbox").strip().lower()

    if not client_id or not client_secret:
        logger.error("Cashfree credentials missing: CASHFREE_CLIENT_ID or CASHFREE_CLIENT_SECRET is empty.")
        raise CashfreeConfigurationError(
            "Cashfree Payment Gateway is not configured. Please set CASHFREE_CLIENT_ID and CASHFREE_CLIENT_SECRET in .env."
        )

    env = Cashfree.SANDBOX if env_str == "sandbox" else Cashfree.PRODUCTION
    
    # Configure API version
    api_version = getattr(settings, "CASHFREE_API_VERSION", "2023-08-01").strip()
    Cashfree.XApiVersion = api_version

    return Cashfree(env, client_id, client_secret)


def create_cashfree_order(
    order,
    return_url: str,
    customer_phone: str = "",
    customer_email: str = "",
    customer_name: str = "",
    notify_url: str = None,
):
    """
    Creates a payment order with Cashfree using official cashfree-pg SDK.
    Generates a unique merchant order ID and returns the order response
    containing payment_session_id.
    """
    cf = get_cashfree_client()

    # Cashfree order ID format: alphanumeric with hyphen or underscore, max 50 chars
    unique_order_id = f"NB_{order.id}_{int(time.time())}"[:45]

    # Clean phone: Cashfree expects 10 digits for Indian numbers
    cleaned_phone = "".join(filter(str.isdigit, customer_phone or getattr(order, "phone", "") or ""))
    if len(cleaned_phone) < 10:
        cleaned_phone = "9999999999"  # Fallback for sandbox
    elif len(cleaned_phone) > 10:
        cleaned_phone = cleaned_phone[-10:]

    customer_id = (
        f"usr_{order.user.id}"
        if order.user
        else f"gst_{order.id}_{int(time.time()) % 10000}"
    )[:40]

    email = (
        customer_email
        or getattr(order, "email", "")
        or (order.user.email if order.user else "customer@example.com")
    ).strip()
    if not email:
        email = "customer@example.com"

    name = (
        customer_name
        or getattr(order, "full_name", "")
        or (order.user.name if order.user and hasattr(order.user, "name") else "Customer")
    ).strip()
    if not name:
        name = "Customer"

    customer = CustomerDetails(
        customer_id=customer_id,
        customer_phone=cleaned_phone,
        customer_email=email,
        customer_name=name,
    )

    meta_kwargs = {"return_url": return_url}
    if notify_url:
        meta_kwargs["notify_url"] = notify_url
    meta = OrderMeta(**meta_kwargs)

    amount = float(order.total_payable)
    if amount <= 0:
        raise ValueError("Order payable amount must be greater than zero.")

    req = CreateOrderRequest(
        order_id=unique_order_id,
        order_amount=amount,
        order_currency="INR",
        customer_details=customer,
        order_meta=meta,
        order_note=f"Order #{order.id} at NOOK Books",
    )

    try:
        response = cf.PGCreateOrder(create_order_request=req)
        logger.info("Cashfree order created successfully. Order ID: %s", unique_order_id)
        return response.data
    except Exception as exc:
        logger.error("Error creating Cashfree order for Order #%s: %s", order.id, str(exc))
        raise CashfreeApiError(f"Payment gateway error: {str(exc)}") from exc


def fetch_cashfree_order(order_id: str):
    """
    Fetches the latest order state from Cashfree using PGFetchOrder.
    """
    cf = get_cashfree_client()
    try:
        response = cf.PGFetchOrder(order_id=order_id)
        return response.data
    except Exception as exc:
        logger.error("Error fetching Cashfree order %s: %s", order_id, str(exc))
        raise CashfreeApiError(f"Failed to fetch order status from payment gateway: {str(exc)}") from exc


def fetch_cashfree_payments(order_id: str):
    """
    Fetches the list of payments made for a given Cashfree order.
    """
    cf = get_cashfree_client()
    try:
        response = cf.PGOrderFetchPayments(order_id=order_id)
        return response.data
    except Exception as exc:
        logger.warning("Could not fetch payment entities for order %s: %s", order_id, str(exc))
        return []


def verify_webhook_signature(signature: str, raw_body_str: str, timestamp: str) -> bool:
    """
    Verifies Cashfree webhook signature using HMAC-SHA256 as documented by Cashfree.
    Data format: timestamp + raw_body
    """
    if not signature or not timestamp or not raw_body_str:
        return False

    webhook_secret = getattr(settings, "CASHFREE_WEBHOOK_SECRET", "") or getattr(
        settings, "CASHFREE_CLIENT_SECRET", ""
    )
    if not webhook_secret:
        logger.error("No Cashfree webhook secret or client secret configured.")
        return False

    try:
        message = (timestamp + raw_body_str).encode("utf-8")
        secret_bytes = webhook_secret.encode("utf-8")
        computed_digest = hmac.new(secret_bytes, message, hashlib.sha256).digest()
        computed_sig = base64.b64encode(computed_digest).decode("utf-8")
        return hmac.compare_digest(computed_sig, signature)
    except Exception as exc:
        logger.error("Error during webhook signature verification: %s", str(exc))
        return False
