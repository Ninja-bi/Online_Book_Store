import json
import logging
from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from book.models import Cart, CartItem
from order.models import Order, OrderItem, OrderStatus, PaymentMethod
from .models import Payment, PaymentStatus
from .cashfree_client import (
    create_cashfree_order,
    fetch_cashfree_order,
    fetch_cashfree_payments,
    verify_webhook_signature,
    CashfreeConfigurationError,
    CashfreeApiError,
)

logger = logging.getLogger(__name__)


def _get_cart(request):
    """Helper to retrieve the current authenticated user's cart."""
    if request.user.is_authenticated:
        return Cart.objects.filter(user=request.user).order_by("-updated_at").first()
    return None


@require_POST
def initiate_payment(request):
    """
    Step 1 of Cashfree Payment Flow:
    - Enforces user authentication
    - Validates cart and customer details
    - Recalculates total payable on server from DB prices
    - Creates or updates local pending Order & Payment records
    - Calls Cashfree SDK to create order and obtain payment_session_id
    - Returns JSON to frontend for Cashfree Web Checkout JS SDK
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {"success": False, "error": "Please sign in to complete your checkout and place an order.", "require_login": True},
            status=401,
        )

    cart = _get_cart(request)
    if not cart or not cart.items.exists():
        return JsonResponse(
            {"success": False, "error": "Your cart is empty. Please add books before checkout."},
            status=400,
        )

    # Validate stock / active availability
    for item in cart.items.select_related("book").all():
        if not item.book:
            return JsonResponse(
                {"success": False, "error": "One of the items in your cart is no longer available."},
                status=400,
            )

    # Extract & validate customer contact & shipping details
    email = request.POST.get("email", "").strip()
    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    phone = request.POST.get("phone", "").strip()
    street_address = request.POST.get("street_address", "").strip()
    landmark = request.POST.get("landmark", "").strip()
    city = request.POST.get("city", "").strip()
    state = request.POST.get("state", "").strip()
    pin_code = request.POST.get("pin_code", "").strip()
    payment_method = request.POST.get("payment_method", "upi").strip()

    if not all([email, first_name, last_name, street_address, city, state, pin_code]):
        return JsonResponse(
            {"success": False, "error": "Please provide all required shipping and contact details."},
            status=400,
        )

    # Server-side calculation of pricing (never trust frontend numbers)
    subtotal = cart.subtotal
    discount = cart.discount
    delivery_fee = cart.delivery_fee
    total_payable = cart.total_payable

    if total_payable <= 0:
        return JsonResponse(
            {"success": False, "error": "Order payable amount must be greater than zero."},
            status=400,
        )

    gst = round(Decimal(str(total_payable)) * Decimal("0.05"), 2)

    try:
        with transaction.atomic():
            # Create a local pending Order strictly associated with authenticated user
            order = Order.objects.create(
                user=request.user,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                street_address=street_address,
                landmark=landmark,
                city=city,
                state=state,
                pin_code=pin_code,
                payment_method=payment_method,
                subtotal=subtotal,
                discount=discount,
                delivery_fee=delivery_fee,
                gst=gst,
                total_payable=total_payable,
                status=OrderStatus.PENDING,
                is_paid=False,
            )

            # Create OrderItem records from cart items
            for item in cart.items.select_related("book").all():
                OrderItem.objects.create(
                    order=order,
                    book=item.book,
                    title=item.book.title,
                    author=item.book.author,
                    cover_image=item.book.cover_image,
                    book_format=item.book.format,
                    unit_price=item.book.price,
                    original_price=item.book.original_price,
                    quantity=item.quantity,
                )

            # Cashfree return URL with placeholder for order_id
            return_url = request.build_absolute_uri(
                reverse("payment-verify")
            ) + "?order_id={order_id}"

            # Webhook notification URL
            notify_url = request.build_absolute_uri(reverse("payment-webhook"))

            # Call Cashfree SDK to create the payment order
            cf_order = create_cashfree_order(
                order=order,
                return_url=return_url,
                customer_phone=phone,
                customer_email=email,
                customer_name=f"{first_name} {last_name}".strip(),
                notify_url=notify_url,
            )

            # Persist Payment record linked strictly to request.user
            payment, _ = Payment.objects.update_or_create(
                order=order,
                defaults={
                    "user": request.user,
                    "merchant_order_id": cf_order.order_id,
                    "cf_order_id": getattr(cf_order, "cf_order_id", ""),
                    "payment_session_id": cf_order.payment_session_id,
                    "amount": order.total_payable,
                    "currency": "INR",
                    "status": PaymentStatus.PENDING,
                },
            )

        return JsonResponse({
            "success": True,
            "payment_session_id": cf_order.payment_session_id,
            "order_id": cf_order.order_id,
            "cf_order_id": getattr(cf_order, "cf_order_id", ""),
            "environment": getattr(settings, "CASHFREE_ENV", "sandbox"),
        })

    except CashfreeConfigurationError as e:
        logger.error("Cashfree configuration error: %s", str(e))
        return JsonResponse(
            {"success": False, "error": "Payment service configuration error. Please contact support."},
            status=503,
        )
    except CashfreeApiError as e:
        logger.error("Cashfree API error: %s", str(e))
        return JsonResponse(
            {"success": False, "error": "Unable to initiate payment with payment gateway. Please try again."},
            status=502,
        )
    except Exception as e:
        logger.exception("Unexpected error in initiate_payment: %s", str(e))
        return JsonResponse(
            {"success": False, "error": "An unexpected error occurred while initiating payment. Please try again."},
            status=500,
        )


@require_http_methods(["GET", "POST"])
def verify_payment(request):
    """
    Step 2 of Cashfree Payment Flow:
    - Customer returns to this URL from Cashfree Checkout: /payment/verify/?order_id=...
    - Independently contacts Cashfree API server-side to verify payment status
    - Validates order amount, currency, and customer ownership
    - Atomically updates Payment and Order models upon confirmed payment
    - Clears customer's cart only upon verified payment
    """
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to verify and complete your order.")
        return redirect("user-login")

    order_id = request.GET.get("order_id") or request.POST.get("order_id")
    if not order_id:
        messages.error(request, "Invalid payment verification request: missing order identifier.")
        return redirect("checkout")

    # Securely retrieve local payment and order
    payment = Payment.objects.filter(merchant_order_id=order_id).select_related("order", "order__user").first()
    if not payment:
        logger.warning("Verification attempted for non-existent order_id: %s", order_id)
        messages.error(request, "Order record not found. Please contact support if your payment was deducted.")
        return redirect("checkout")

    order = payment.order

    # Ownership check: authenticated user must match order owner
    if order.user and order.user != request.user and not request.user.is_staff:
        logger.warning("User %s attempted to access order %s owned by %s", request.user, order.id, order.user)
        return HttpResponseForbidden("You are not authorized to view or verify this order.")

    # Idempotent: If already marked PAID, redirect to confirmation immediately
    if payment.status == PaymentStatus.PAID and order.is_paid:
        messages.info(request, "Your payment has already been verified.")
        return redirect("order-confirmation", order_id=order.id)

    # Independently verify status with Cashfree API
    try:
        cf_order = fetch_cashfree_order(order_id)
    except Exception as e:
        logger.error("Failed to fetch order %s from Cashfree during verification: %s", order_id, str(e))
        return render(request, "payment/status.html", {
            "status": "ERROR",
            "order": order,
            "payment": payment,
            "title": "Verification Pending",
            "message": "We could not reach the payment gateway to verify your transaction. Please do not re-pay. We will update the status automatically via webhook.",
        })

    cf_status = getattr(cf_order, "order_status", "").upper()
    cf_amount = getattr(cf_order, "order_amount", 0)
    cf_currency = getattr(cf_order, "order_currency", "INR")

    # Amount & currency integrity checks
    if cf_currency != "INR":
        logger.error("Currency mismatch for order %s: expected INR, got %s", order_id, cf_currency)
        messages.error(request, "Payment verification failed due to currency mismatch.")
        return redirect("checkout")

    if abs(Decimal(str(cf_amount)) - payment.amount) > Decimal("0.01"):
        logger.error("Amount mismatch for order %s: expected %s, got %s", order_id, payment.amount, cf_amount)
        messages.error(request, "Payment verification failed due to amount mismatch.")
        return redirect("checkout")

    # Handle statuses
    if cf_status == "PAID":
        # Fetch payment transaction details (UTR, method, etc.)
        cf_payments = fetch_cashfree_payments(order_id)
        cf_payment_id = ""
        payment_method = payment.order.payment_method
        bank_reference = ""

        if cf_payments:
            for p in cf_payments:
                p_status = getattr(p, "payment_status", "").upper()
                if p_status == "SUCCESS":
                    cf_payment_id = str(getattr(p, "cf_payment_id", ""))
                    payment_method = str(getattr(p, "payment_group", payment_method))
                    bank_reference = str(getattr(p, "bank_reference", ""))
                    break

        with transaction.atomic():
            payment.status = PaymentStatus.PAID
            if cf_payment_id:
                payment.cf_payment_id = cf_payment_id
            if payment_method:
                payment.payment_method = payment_method
            if bank_reference:
                payment.bank_reference = bank_reference
            payment.raw_response = {
                "cf_order_id": getattr(cf_order, "cf_order_id", ""),
                "order_status": cf_status,
                "order_amount": cf_amount,
            }
            payment.save()

            order.is_paid = True
            order.status = OrderStatus.CONFIRMED
            order.payment_reference = cf_payment_id or order_id
            order.save()

            # Clear cart only after verified payment
            cart = _get_cart(request)
            if cart:
                cart.items.all().delete()

            # Clean pending session ID
            if "pending_order_id" in request.session:
                del request.session["pending_order_id"]

        messages.success(request, f"Payment successful! Order #{order.id} has been confirmed.")
        return redirect("order-confirmation", order_id=order.id)

    elif cf_status in ["ACTIVE", "PENDING"]:
        payment.status = PaymentStatus.PENDING
        payment.save()
        return render(request, "payment/status.html", {
            "status": "PENDING",
            "order": order,
            "payment": payment,
            "title": "Payment Processing",
            "message": "Your payment is currently being processed by Cashfree. You will receive an email once confirmed.",
        })

    else:
        # FAILED, CANCELLED, USER_DROPPED, EXPIRED
        status_choice = PaymentStatus.USER_DROPPED if cf_status == "USER_DROPPED" else PaymentStatus.FAILED
        payment.status = status_choice
        payment.error_message = f"Payment status from Cashfree: {cf_status}"
        payment.save()

        # Do NOT clear cart so user can retry
        return render(request, "payment/status.html", {
            "status": "FAILED",
            "order": order,
            "payment": payment,
            "title": "Payment Not Completed",
            "message": "Your payment was not completed or was cancelled. Your cart items have been preserved so you can try again.",
        })


@csrf_exempt
@require_POST
def cashfree_webhook(request):
    """
    Step 3 of Cashfree Payment Flow: Asynchronous Webhook Receiver
    - Accepts Cashfree webhook notifications
    - Verifies cryptographic signature using HMAC-SHA256
    - Processes payment events idempotently
    - Updates local order/payment and clears cart safely
    """
    raw_body = request.body.decode("utf-8")
    signature = request.headers.get("x-webhook-signature") or request.META.get("HTTP_X_WEBHOOK_SIGNATURE")
    timestamp = request.headers.get("x-webhook-timestamp") or request.META.get("HTTP_X_WEBHOOK_TIMESTAMP")

    if not signature or not timestamp:
        logger.warning("Cashfree webhook received without signature or timestamp.")
        return HttpResponseBadRequest("Missing signature or timestamp headers.")

    if not verify_webhook_signature(signature, raw_body, timestamp):
        logger.warning("Cashfree webhook signature verification failed.")
        return HttpResponseBadRequest("Invalid webhook signature.")

    try:
        payload = json.loads(raw_body)
    except Exception as exc:
        logger.error("Invalid JSON received in webhook body: %s", str(exc))
        return HttpResponseBadRequest("Malformed JSON.")

    event_type = payload.get("type", "")
    data = payload.get("data", {})
    order_data = data.get("order", {})
    order_id = order_data.get("order_id")

    logger.info("Cashfree webhook event received: %s for order %s", event_type, order_id)

    if not order_id:
        return JsonResponse({"status": "ignored", "reason": "No order_id in webhook data"})

    payment = Payment.objects.filter(merchant_order_id=order_id).select_related("order", "order__user").first()
    if not payment:
        logger.warning("Webhook received for unknown order_id: %s", order_id)
        return JsonResponse({"status": "ignored", "reason": "Order not found"})

    order = payment.order

    if event_type in ["PAYMENT_SUCCESS_WEBHOOK", "ORDER_PAID_WEBHOOK"]:
        if not payment.is_successful:
            with transaction.atomic():
                payment_data = data.get("payment", {})
                cf_payment_id = str(payment_data.get("cf_payment_id", ""))
                payment_method = str(payment_data.get("payment_group", payment.payment_method or ""))
                bank_reference = str(payment_data.get("bank_reference", ""))

                payment.status = PaymentStatus.PAID
                if cf_payment_id:
                    payment.cf_payment_id = cf_payment_id
                if payment_method:
                    payment.payment_method = payment_method
                if bank_reference:
                    payment.bank_reference = bank_reference
                payment.raw_response = data
                payment.save()

                order.is_paid = True
                order.status = OrderStatus.CONFIRMED
                if cf_payment_id:
                    order.payment_reference = cf_payment_id
                order.save()

                # Clear user's cart if exists
                if order.user:
                    Cart.objects.filter(user=order.user).delete()

            logger.info("Order #%s marked PAID via webhook.", order.id)

    elif event_type in ["PAYMENT_FAILED_WEBHOOK", "PAYMENT_USER_DROPPED_WEBHOOK"]:
        if not payment.is_successful:
            payment.status = (
                PaymentStatus.USER_DROPPED if "DROPPED" in event_type else PaymentStatus.FAILED
            )
            payment.error_message = f"Webhook event: {event_type}"
            payment.save()
            logger.info("Order #%s marked %s via webhook.", order.id, payment.status)

    return JsonResponse({"status": "success", "event": event_type})


def payment_status_api(request, order_id):
    """
    Lightweight API endpoint for client-side polling / modal checkout verification.
    Requires authentication and order ownership.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    payment = get_object_or_404(Payment, merchant_order_id=order_id)
    if payment.order.user and payment.order.user != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Not authorized")

    return JsonResponse({
        "order_id": payment.merchant_order_id,
        "status": payment.status,
        "is_paid": payment.is_successful,
        "amount": str(payment.amount),
        "local_order_id": payment.order.id,
    })

