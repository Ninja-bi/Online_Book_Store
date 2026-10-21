# Online Book Store — NOOK Books

A modern, full-featured Online Bookstore built with Django, SQLite, and Cashfree Payment Gateway integration.

---

## Cashfree Payment Gateway Integration

The bookstore integrates Cashfree Payments using the official `cashfree-pg` (v6+) Python SDK on the backend and Cashfree Web Checkout JS SDK (v3) on the frontend.

### 1. Payment Flow Architecture

1. **Initiation (`/payment/initiate/`)**:
   - Customer submits shipping & contact information on the checkout page.
   - The backend validates stock and recalculates total pricing server-side from database records.
   - An unpaid, pending `Order` and associated `Payment` record are created.
   - The backend calls Cashfree's `PGCreateOrder` endpoint to generate a unique merchant order ID and returns a `payment_session_id`.
2. **Frontend Web Checkout**:
   - The checkout page receives `payment_session_id` and invokes Cashfree's Web Checkout JS SDK (`https://sdk.cashfree.com/js/v3/cashfree.js`).
   - The user completes payment using UPI, Credit/Debit Cards, Net Banking, or supported wallets.
3. **Server-Side Verification (`/payment/verify/`)**:
   - Upon completion, Cashfree redirects the customer back to the return URL: `/payment/verify/?order_id={order_id}`.
   - Django validates user authorization and queries Cashfree (`PGFetchOrder`) to verify that the order status is `PAID`, and that the amount and currency match.
   - Upon verification, the order is marked `CONFIRMED` (`is_paid = True`), transaction references are stored, and the cart is cleared.
4. **Asynchronous Webhook (`/payment/webhook/`)**:
   - Cashfree sends asynchronous webhook events (e.g. `PAYMENT_SUCCESS_WEBHOOK`, `ORDER_PAID_WEBHOOK`, `PAYMENT_FAILED_WEBHOOK`).
   - The webhook endpoint verifies HMAC-SHA256 signatures (`x-webhook-signature` and `x-webhook-timestamp`) against the raw request body.
   - Verified events update order and payment statuses idempotently.

---

## 2. Environment Configuration

Cashfree settings are loaded via `python-dotenv` from `.env`. Ensure `.env` is never committed (it is listed in `.gitignore`).

### Environment Variables

| Variable | Description | Example / Default |
|---|---|---|
| `CASHFREE_CLIENT_ID` | Cashfree App ID / Client ID | `TEST11306209...` |
| `CASHFREE_CLIENT_SECRET` | Cashfree Secret Key | `cfsk_ma_test_...` |
| `CASHFREE_ENV` | Environment (`sandbox` or `production`) | `sandbox` |
| `CASHFREE_API_VERSION` | API Version | `2023-08-01` |
| `CASHFREE_WEBHOOK_SECRET` | Webhook verification secret | (Client secret or dedicated webhook secret) |

Sample template is provided in [`.env.example`](file:///e:/Online%20Book%20Store/.env.example).

---

## 3. URLs and Endpoints

| URL Pattern | View Name | Purpose |
|---|---|---|
| `/payment/initiate/` | `payment-initiate` | POST: Server-side validation, Cashfree order creation & session generation |
| `/payment/verify/` | `payment-verify` | GET/POST: Server-side payment verification upon redirect from checkout |
| `/payment/webhook/` | `payment-webhook` | POST: Asynchronous Cashfree webhook listener with HMAC signature verification |
| `/payment/status/<order_id>/` | `payment-status-api` | GET: JSON status API endpoint for order & payment state |
| `/checkout/` | `checkout` | Checkout page with Cashfree payment options |
| `/confirmation/<order_id>/` | `order-confirmation` | Order confirmed receipt page |

---

## 4. Running Migrations & Tests

### Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Run Automated Tests
All Cashfree integration tests mock external API calls to avoid triggering real sandbox transactions during continuous integration:
```bash
python manage.py test payment
```

Run entire test suite:
```bash
python manage.py test
```

---

## 5. Security Measures

- **No Hardcoded Secrets**: Secrets are kept solely in `.env` and excluded via `.gitignore`.
- **Server-Side Pricing**: Prices and totals are computed strictly from database items, ignoring any frontend tampering.
- **Independent Verification**: Redirection alone never marks an order paid; Django independently verifies order status with Cashfree's backend.
- **CSRF Protection**: Web endpoints maintain CSRF security; the webhook listener is selectively exempt and guarded by HMAC-SHA256 signature verification.
- **Customer Isolation**: Users cannot verify or view orders that belong to other accounts.
- **Safe Cart Clearing**: Carts are cleared only after payment status is verified as `PAID`.