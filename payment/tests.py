import base64
import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from book.models import Book, Cart, CartItem
from order.models import Order, OrderItem, OrderStatus, PaymentMethod
from payment.models import Payment, PaymentStatus
from payment.cashfree_client import CashfreeConfigurationError, CashfreeApiError

User = get_user_model()


class CashfreePaymentIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="reader@example.com",
            name="Alice Reader",
            password="testpassword123",
        )
        self.other_user = User.objects.create_user(
            email="intruder@example.com",
            name="Bob Intruder",
            password="testpassword123",
        )

        self.book = Book.objects.create(
            title="Clean Architecture",
            author="Robert C. Martin",
            price=Decimal("450.00"),
            original_price=Decimal("599.00"),
            stock=10,
        )

        # Create cart for self.user
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(cart=self.cart, book=self.book, quantity=2)

    # ── 1. Successful payment initiation ─────────────────────────────────────
    @patch("payment.views.create_cashfree_order")
    def test_payment_initiation_success(self, mock_create_cf_order):
        self.client.force_login(self.user)

        mock_cf_data = MagicMock()
        mock_cf_data.order_id = "NB_1_1234567890"
        mock_cf_data.cf_order_id = "cf_ord_999888"
        mock_cf_data.payment_session_id = "session_mock_123"
        mock_create_cf_order.return_value = mock_cf_data

        payload = {
            "email": "reader@example.com",
            "first_name": "Alice",
            "last_name": "Reader",
            "phone": "9876543210",
            "street_address": "42 Galaxy Way",
            "landmark": "Near Book Tower",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pin_code": "560001",
            "payment_method": "upi",
        }

        response = self.client.post(reverse("payment-initiate"), payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["payment_session_id"], "session_mock_123")
        self.assertEqual(data["order_id"], "NB_1_1234567890")

        # Verify DB state
        payment = Payment.objects.filter(merchant_order_id="NB_1_1234567890").first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, PaymentStatus.PENDING)
        self.assertEqual(payment.amount, self.cart.total_payable)
        self.assertFalse(payment.order.is_paid)
        self.assertEqual(payment.order.status, OrderStatus.PENDING)

    # ── 2. Payment initiation with empty cart ────────────────────────────────
    def test_payment_initiation_empty_cart(self):
        self.client.force_login(self.user)
        self.cart.items.all().delete()

        payload = {
            "email": "reader@example.com",
            "first_name": "Alice",
            "last_name": "Reader",
            "street_address": "42 Galaxy Way",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pin_code": "560001",
        }
        response = self.client.post(reverse("payment-initiate"), payload)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    # ── 3. Payment initiation missing credentials ───────────────────────────
    @patch("payment.views.create_cashfree_order")
    def test_payment_initiation_missing_credentials(self, mock_create):
        self.client.force_login(self.user)
        mock_create.side_effect = CashfreeConfigurationError("Missing credentials")

        payload = {
            "email": "reader@example.com",
            "first_name": "Alice",
            "last_name": "Reader",
            "phone": "9876543210",
            "street_address": "42 Galaxy Way",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pin_code": "560001",
        }
        response = self.client.post(reverse("payment-initiate"), payload)
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["success"])

    # ── 4. Payment session creation failure (gateway error) ─────────────────
    @patch("payment.views.create_cashfree_order")
    def test_payment_session_creation_failure(self, mock_create):
        self.client.force_login(self.user)
        mock_create.side_effect = CashfreeApiError("Gateway timeout")

        payload = {
            "email": "reader@example.com",
            "first_name": "Alice",
            "last_name": "Reader",
            "street_address": "42 Galaxy Way",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pin_code": "560001",
        }
        response = self.client.post(reverse("payment-initiate"), payload)
        self.assertEqual(response.status_code, 502)
        self.assertFalse(response.json()["success"])

    # ── 5. Successful server-side payment verification ──────────────────────
    @patch("payment.views.fetch_cashfree_payments")
    @patch("payment.views.fetch_cashfree_order")
    def test_successful_server_side_verification(self, mock_fetch_order, mock_fetch_payments):
        self.client.force_login(self.user)

        order = Order.objects.create(
            user=self.user,
            email="reader@example.com",
            first_name="Alice",
            last_name="Reader",
            subtotal=Decimal("800.00"),
            total_payable=Decimal("800.00"),
            is_paid=False,
            status=OrderStatus.PENDING,
        )
        payment = Payment.objects.create(
            order=order,
            user=self.user,
            merchant_order_id="NB_ORD_TEST_01",
            amount=Decimal("800.00"),
            currency="INR",
            status=PaymentStatus.PENDING,
        )

        mock_cf_order = MagicMock()
        mock_cf_order.order_status = "PAID"
        mock_cf_order.order_amount = 800.0
        mock_cf_order.order_currency = "INR"
        mock_cf_order.cf_order_id = "cf_12345"
        mock_fetch_order.return_value = mock_cf_order

        mock_payment_entity = MagicMock()
        mock_payment_entity.payment_status = "SUCCESS"
        mock_payment_entity.cf_payment_id = 99887766
        mock_payment_entity.payment_group = "upi"
        mock_payment_entity.bank_reference = "UTR123456"
        mock_fetch_payments.return_value = [mock_payment_entity]

        response = self.client.get(reverse("payment-verify") + "?order_id=NB_ORD_TEST_01")
        self.assertRedirects(response, reverse("order-confirmation", kwargs={"order_id": order.id}))

        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertTrue(order.is_paid)
        self.assertEqual(order.status, OrderStatus.CONFIRMED)
        self.assertEqual(payment.status, PaymentStatus.PAID)
        self.assertEqual(payment.cf_payment_id, "99887766")

        # Confirm cart was cleared
        self.assertEqual(self.cart.items.count(), 0)

    # ── 6. Verification with invalid order ID ────────────────────────────────
    def test_verify_payment_invalid_order_id(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("payment-verify") + "?order_id=NON_EXISTENT")
        self.assertRedirects(response, reverse("checkout"))

    # ── 7. Unauthorized customer check ──────────────────────────────────────
    def test_unauthorized_customer_cannot_verify(self):
        # Order belongs to self.user
        order = Order.objects.create(
            user=self.user,
            email="reader@example.com",
            first_name="Alice",
            last_name="Reader",
            total_payable=Decimal("100.00"),
        )
        Payment.objects.create(
            order=order,
            user=self.user,
            merchant_order_id="NB_ORD_PRIVATE",
            amount=Decimal("100.00"),
        )

        # Log in as other_user
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("payment-verify") + "?order_id=NB_ORD_PRIVATE")
        self.assertEqual(response.status_code, 403)

    # ── 8. Payment amount mismatch rejection ─────────────────────────────────
    @patch("payment.views.fetch_cashfree_order")
    def test_payment_amount_mismatch_rejected(self, mock_fetch_order):
        self.client.force_login(self.user)
        order = Order.objects.create(
            user=self.user,
            email="reader@example.com",
            first_name="Alice",
            last_name="Reader",
            total_payable=Decimal("500.00"),
        )
        Payment.objects.create(
            order=order,
            user=self.user,
            merchant_order_id="NB_ORD_MISMATCH",
            amount=Decimal("500.00"),
        )

        mock_cf_order = MagicMock()
        mock_cf_order.order_status = "PAID"
        mock_cf_order.order_amount = 100.0  # Tampered amount
        mock_cf_order.order_currency = "INR"
        mock_fetch_order.return_value = mock_cf_order

        response = self.client.get(reverse("payment-verify") + "?order_id=NB_ORD_MISMATCH")
        self.assertRedirects(response, reverse("checkout"))

        order.refresh_from_db()
        self.assertFalse(order.is_paid)

    # ── 9. Verification when payment is still pending ────────────────────────
    @patch("payment.views.fetch_cashfree_order")
    def test_verify_payment_pending_state(self, mock_fetch_order):
        self.client.force_login(self.user)
        order = Order.objects.create(
            user=self.user,
            email="reader@example.com",
            first_name="Alice",
            last_name="Reader",
            total_payable=Decimal("200.00"),
        )
        Payment.objects.create(
            order=order,
            user=self.user,
            merchant_order_id="NB_ORD_PENDING",
            amount=Decimal("200.00"),
        )

        mock_cf_order = MagicMock()
        mock_cf_order.order_status = "ACTIVE"
        mock_cf_order.order_amount = 200.0
        mock_cf_order.order_currency = "INR"
        mock_fetch_order.return_value = mock_cf_order

        response = self.client.get(reverse("payment-verify") + "?order_id=NB_ORD_PENDING")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payment Processing")

        order.refresh_from_db()
        self.assertFalse(order.is_paid)
        # Cart must NOT be cleared when payment is pending
        self.assertTrue(self.cart.items.exists())

    # ── 10. Verification when payment fails ──────────────────────────────────
    @patch("payment.views.fetch_cashfree_order")
    def test_verify_payment_failed_state(self, mock_fetch_order):
        self.client.force_login(self.user)
        order = Order.objects.create(
            user=self.user,
            email="reader@example.com",
            first_name="Alice",
            last_name="Reader",
            total_payable=Decimal("200.00"),
        )
        payment = Payment.objects.create(
            order=order,
            user=self.user,
            merchant_order_id="NB_ORD_FAILED",
            amount=Decimal("200.00"),
        )

        mock_cf_order = MagicMock()
        mock_cf_order.order_status = "FAILED"
        mock_cf_order.order_amount = 200.0
        mock_cf_order.order_currency = "INR"
        mock_fetch_order.return_value = mock_cf_order

        response = self.client.get(reverse("payment-verify") + "?order_id=NB_ORD_FAILED")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payment Not Completed")

        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertFalse(order.is_paid)
        self.assertEqual(payment.status, PaymentStatus.FAILED)
        # Cart remains intact
        self.assertTrue(self.cart.items.exists())

    # ── 11. Repeated verification / page refresh idempotency ─────────────────
    def test_repeated_verification_idempotent(self):
        self.client.force_login(self.user)
        order = Order.objects.create(
            user=self.user,
            email="reader@example.com",
            first_name="Alice",
            last_name="Reader",
            total_payable=Decimal("300.00"),
            is_paid=True,
            status=OrderStatus.CONFIRMED,
        )
        Payment.objects.create(
            order=order,
            user=self.user,
            merchant_order_id="NB_ORD_ALREADY_PAID",
            amount=Decimal("300.00"),
            status=PaymentStatus.PAID,
        )

        response = self.client.get(reverse("payment-verify") + "?order_id=NB_ORD_ALREADY_PAID")
        self.assertRedirects(response, reverse("order-confirmation", kwargs={"order_id": order.id}))

    # ── 12. Webhook: valid signature & successful payment ───────────────────
    def test_webhook_valid_signature_payment_success(self):
        order = Order.objects.create(
            user=self.user,
            email="reader@example.com",
            first_name="Alice",
            last_name="Reader",
            total_payable=Decimal("450.00"),
            is_paid=False,
            status=OrderStatus.PENDING,
        )
        payment = Payment.objects.create(
            order=order,
            user=self.user,
            merchant_order_id="NB_ORD_WEBHOOK_01",
            amount=Decimal("450.00"),
            status=PaymentStatus.PENDING,
        )

        payload_dict = {
            "type": "PAYMENT_SUCCESS_WEBHOOK",
            "data": {
                "order": {"order_id": "NB_ORD_WEBHOOK_01", "order_amount": 450.0},
                "payment": {
                    "cf_payment_id": "99112233",
                    "payment_status": "SUCCESS",
                    "payment_group": "upi",
                    "bank_reference": "SBI_UTR_123",
                },
            },
        }
        raw_body = json.dumps(payload_dict)
        timestamp = "1792606000"

        # Generate HMAC-SHA256 signature using the configured secret
        secret = getattr(settings, "CASHFREE_WEBHOOK_SECRET", "")
        message = (timestamp + raw_body).encode("utf-8")
        computed_digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
        signature = base64.b64encode(computed_digest).decode("utf-8")

        response = self.client.post(
            reverse("payment-webhook"),
            data=raw_body,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE=signature,
            HTTP_X_WEBHOOK_TIMESTAMP=timestamp,
        )
        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertTrue(order.is_paid)
        self.assertEqual(order.status, OrderStatus.CONFIRMED)
        self.assertEqual(payment.status, PaymentStatus.PAID)
        self.assertEqual(payment.cf_payment_id, "99112233")

    # ── 13. Webhook: invalid signature rejection ────────────────────────────
    def test_webhook_invalid_signature_rejected(self):
        payload = json.dumps({"type": "PAYMENT_SUCCESS_WEBHOOK", "data": {}})
        response = self.client.post(
            reverse("payment-webhook"),
            data=payload,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE="tampered_invalid_signature",
            HTTP_X_WEBHOOK_TIMESTAMP="1792606000",
        )
        self.assertEqual(response.status_code, 400)

    # ── 14. Webhook: duplicate delivery idempotency ──────────────────────────
    def test_webhook_duplicate_delivery_idempotent(self):
        order = Order.objects.create(
            user=self.user,
            email="reader@example.com",
            first_name="Alice",
            last_name="Reader",
            total_payable=Decimal("150.00"),
            is_paid=True,
            status=OrderStatus.CONFIRMED,
        )
        payment = Payment.objects.create(
            order=order,
            user=self.user,
            merchant_order_id="NB_ORD_DUP",
            amount=Decimal("150.00"),
            status=PaymentStatus.PAID,
            cf_payment_id="11111",
        )

        payload_dict = {
            "type": "PAYMENT_SUCCESS_WEBHOOK",
            "data": {
                "order": {"order_id": "NB_ORD_DUP", "order_amount": 150.0},
                "payment": {"cf_payment_id": "11111", "payment_status": "SUCCESS"},
            },
        }
        raw_body = json.dumps(payload_dict)
        timestamp = "1792606000"
        secret = getattr(settings, "CASHFREE_WEBHOOK_SECRET", "")
        message = (timestamp + raw_body).encode("utf-8")
        computed_digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
        signature = base64.b64encode(computed_digest).decode("utf-8")

        response = self.client.post(
            reverse("payment-webhook"),
            data=raw_body,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE=signature,
            HTTP_X_WEBHOOK_TIMESTAMP=timestamp,
        )
        self.assertEqual(response.status_code, 200)
        # Verify no changes or errors
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PAID)
