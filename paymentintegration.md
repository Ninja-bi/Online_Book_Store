# Task: Integrate Cashfree Payment Gateway into My Existing Django Online Bookstore

## 1. Project Context

I have an existing Online Bookstore application built using Django and Python. I want to integrate the Cashfree Payment Gateway so customers can securely purchase books using online payments.

I will provide my existing `.env` file containing my Cashfree configuration and other project environment variables.

**Your primary objective is to modify my existing project, not create a new Django project.**

Before making changes, inspect the entire relevant project structure, existing models, views, URL configurations, templates, authentication system, cart functionality, and environment configuration.

Preserve all existing working functionality.

## 2. Technology Stack

- Backend: Python and Django
- Database: Existing SQLite database
- Payment gateway: Cashfree Payments
- Python integration: Official `cashfree-pg` SDK
- Frontend: Existing HTML, CSS, JavaScript, and Django templates
- Authentication: Existing authentication system, including JWT if already implemented
- Configuration: Existing `.env` file
- Currency: INR
- Initial testing environment: Cashfree Sandbox

Do not replace my existing technology stack or migrate to another framework.

## 3. Environment Configuration

I will provide my existing `.env` file.

First, inspect its variable names and reuse the existing configuration wherever possible.

Expected Cashfree configuration may resemble:

```env
CASHFREE_CLIENT_ID=your_client_id
CASHFREE_CLIENT_SECRET=your_client_secret
CASHFREE_ENV=sandbox
```

These are examples only. Use the actual variable names already present in my supplied `.env` file when they are appropriate.

Requirements:

1. Load environment variables securely through the project's existing configuration method.
2. If the project does not already load `.env`, implement an appropriate solution without disrupting the current settings.
3. Never hardcode API credentials in Python, JavaScript, HTML, templates, or source control.
4. Never expose the Client Secret or other private credentials through API responses, browser JavaScript, HTML source, logs, or error messages.
5. Keep `.env` in `.gitignore`.
6. Do not overwrite, delete, or unnecessarily modify unrelated environment variables.
7. Do not print secret values in terminal output or reports.
8. Validate that required variables exist at startup or when initializing the payment integration.
9. If the credentials are missing or invalid, return a safe, actionable error.
10. Do not change the application to production mode automatically. Keep Sandbox mode enabled during development.

If the provided credentials are live production credentials, do not use them for test transactions. Use appropriate sandbox credentials for testing.

## 4. Inspect the Existing Project First

Before writing code, identify:

- Django project name and settings module.
- Existing Django applications.
- User authentication implementation.
- Book model and book pricing fields.
- Shopping cart implementation.
- Existing order and order-item models.
- Existing checkout workflow.
- Existing payment-related code.
- Current URL naming conventions.
- Existing frontend checkout template.
- How environment variables are loaded.
- Whether order totals are calculated on the server or client.

Create a short implementation plan based on the existing architecture.

Do not ask me to recreate files or models that already exist. Reuse and extend existing implementations wherever possible.

If an essential detail is genuinely missing, identify it before making a potentially destructive change.

## 5. Install and Configure Cashfree Python SDK

Use the official Cashfree Python SDK:

```bash
pip install cashfree-pg
```

Inspect the installed SDK version and its actual API signatures before writing the integration.

Use the official SDK documentation:

https://www.cashfree.com/docs/api-reference/payments/sdk

Python SDK repository:

https://github.com/cashfree/cashfree-pg-sdk-python

Implement the SDK initialization according to the installed version. Do not blindly copy initialization code from an older SDK version.

Use the official Cashfree Sandbox environment for development.

Keep the integration organized in an appropriate existing Django application. Avoid unnecessary duplicate configuration files.

## 6. Create a Payment Order

Integrate payment initiation with the existing checkout and order workflow.

When an authenticated customer clicks the Pay Now button:

1. Verify that the customer is authorized to purchase the selected order.
2. Retrieve the relevant cart and book information from the database.
3. Validate book availability and quantities.
4. Calculate the total amount on the Django backend using trusted database prices.
5. Never trust an amount, discount, or total supplied directly by the frontend.
6. Create or reuse a local pending order according to the existing order workflow.
7. Generate a unique Cashfree-compatible order ID.
8. Create the corresponding payment order using the Cashfree Python SDK.
9. Specify the currency as INR.
10. Provide the required customer details.
11. Configure an appropriate return URL using Django URL configuration.
12. Save the Cashfree order ID and relevant payment references in the local database.
13. Return only the information required by the frontend, including the payment session ID.
14. Handle network errors, API errors, and invalid responses safely.

Do not create duplicate local orders or duplicate payment sessions unnecessarily when the customer double-clicks the payment button or retries after a network failure.

Follow the existing order model and business logic. Add fields only when necessary.

## 7. Integrate Cashfree Checkout into the Existing UI

Use Cashfree's official Web Checkout JavaScript SDK:

https://sdk.cashfree.com/js/v3/cashfree.js

Integrate the checkout flow into my existing checkout page.

Requirements:

- Preserve the existing website design and layout.
- Reuse the current cart, order summary, book details, and checkout components.
- Add or update the Pay Now button.
- Request a payment session from the Django backend.
- Open Cashfree Checkout using the returned payment session ID.
- Use Sandbox mode during development.
- Display a loading indicator while payment initiation is in progress.
- Prevent accidental duplicate submissions.
- Display useful error messages if payment initiation fails.
- Handle canceled payments, failed payments, and interrupted checkout sessions.
- Keep the payment flow compatible with the existing authentication and CSRF configuration.
- Do not expose Cashfree's Client Secret to the browser.
- Do not trust frontend redirects or frontend payment status.

If the project uses a JWT-authenticated API instead of Django session authentication, follow the existing JWT authentication pattern and use the appropriate authorization headers. Do not assume session authentication is in use without inspecting the project.

## 8. Implement Payment Verification

Implement a secure server-side payment verification endpoint.

After checkout, the frontend may display a processing or result page, but Django must independently verify the actual payment status with Cashfree.

The verification workflow must:

1. Identify the local order securely.
2. Retrieve its associated Cashfree order ID from the database.
3. Fetch the order status from Cashfree using the official Python SDK.
4. Confirm that the Cashfree order ID matches the local order.
5. Confirm that the order status is `PAID` before marking the local order as paid.
6. Where supported by the SDK response, validate the amount and currency against the local order.
7. Ensure the local order belongs to the authenticated customer, or otherwise validate access through a secure server-side mechanism.
8. Update payment status atomically.
9. Prevent duplicate verification requests from causing duplicate business operations.
10. Preserve pending status when payment is still processing.
11. Handle failed, canceled, expired, and unknown payment states safely.
12. Return a clear status response without exposing private credentials or internal exceptions.

A customer visiting a success URL must never be sufficient to mark an order as paid.

Do not clear the cart, confirm fulfillment, or grant access to purchased products until the required payment confirmation has been established.

## 9. Implement Cashfree Webhooks

Configure a webhook endpoint for reliable asynchronous payment updates.

Use the official Cashfree webhook documentation to implement signature verification.

Requirements:

- Accept the webhook request in the format expected by Cashfree.
- Read the original raw request body before parsing or modifying it.
- Verify the signature using Cashfree's documented algorithm, timestamp, and webhook secret requirements.
- Handle timestamp validation and replay protection according to the official guidance.
- Never trust a webhook without successful verification.
- Match the Cashfree order and payment references to existing local records.
- Update the local order safely and idempotently.
- Prevent duplicate webhook events from repeating fulfillment or other business operations.
- Handle out-of-order notifications and multiple payment attempts carefully.
- Return the appropriate HTTP response codes.
- Log useful diagnostic information without recording credentials, sensitive customer information, or payment secrets.

Do not assume the webhook secret is identical to the API Client Secret. Use the appropriate documented secret and configuration.

If webhook support requires a new environment variable, add the variable name to `.env.example` or document it without including a real secret.

## 10. Database and Order Status Management

Reuse the existing order model whenever possible.

If the current implementation does not support payment tracking, introduce an appropriate structure with fields equivalent to:

- Local order reference
- Customer reference
- Total amount
- Currency
- Order status
- Payment status
- Cashfree order ID
- Payment reference, when available
- Creation timestamp
- Last update timestamp

Choose field names that fit the existing codebase.

Use clear and consistent order states, such as:

- PENDING
- PAID
- FAILED
- CANCELLED

Adapt these states to the existing application instead of creating conflicting status systems.

Important rules:

- A payment failure must not be recorded as a successful purchase.
- A pending payment must not trigger order fulfillment.
- A verified successful payment must not be processed twice.
- Do not delete or overwrite historical payment references unnecessarily.
- Use database transactions for critical order and payment updates.
- Do not modify the existing SQLite database manually.
- Create appropriate Django migrations for any schema changes.
- Preserve existing customer orders and cart data.

## 11. URL Configuration

Add the necessary routes using the existing project's URL conventions.

Required functionality may include:

- Create or initiate payment
- Return from Cashfree Checkout
- Verify payment status
- Receive Cashfree webhook events
- Display payment success, pending, and failure results

Use appropriate HTTP methods and authentication requirements.

Do not expose administrative payment operations to ordinary users.

Ensure route names and URL parameters are consistent with the existing templates and views.

## 12. Security Requirements

Treat payment security as a critical requirement.

Implement the following:

- Server-side amount calculation.
- Authentication and authorization checks.
- Django CSRF protection wherever applicable.
- Secure credential handling.
- Cashfree server-side order verification.
- Verified webhook signatures.
- Idempotent payment updates.
- Safe exception handling.
- Input validation.
- Protection against users accessing another customer's orders.
- No trusting client-side payment status.
- No marking orders paid based solely on a redirect.
- No logging API secrets or sensitive payment information.

Do not disable CSRF protection globally to make the payment integration work.

If a webhook endpoint needs an exemption from Django CSRF middleware, apply it only to the dedicated webhook view and compensate with proper Cashfree signature verification.

## 13. Error Handling and User Experience

Handle the following cases:

- Missing Cashfree credentials.
- Incorrect SDK configuration.
- Cashfree API unavailable.
- Payment order creation failure.
- Invalid payment session.
- Payment canceled by the customer.
- Payment pending or delayed.
- Payment failure.
- Successful payment.
- Duplicate checkout submission.
- Duplicate webhook delivery.
- Customer refreshes the success page.
- Customer opens an order they do not own.
- Webhook arrives before the customer returns to the website.
- Customer closes the browser before the return redirect.
- Database update failure.

Show clear, user-friendly messages on the website while keeping technical diagnostics in secure server logs.

Do not display stack traces or raw API error responses to customers.

## 14. Testing Requirements

Use Cashfree Sandbox credentials and test transactions.

Create or update Django tests for:

- Successful payment initiation.
- Invalid order ID.
- Unauthorized customer.
- Invalid order amount.
- Payment session creation failure.
- Successful server-side verification.
- Pending payment.
- Failed payment.
- Payment amount mismatch.
- Invalid webhook signature.
- Duplicate webhook delivery.
- Repeated verification request.
- Payment success page refresh.
- Order status remains unpaid when verification fails.

Mock Cashfree SDK responses in automated tests. Do not require real payment transactions to run the test suite.

Run:

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py test
```

Only create migrations if model changes are actually required. Inspect generated migrations before applying them.

Do not delete the existing database or reset existing data.

Report any tests that could not be completed and explain why.

## 15. Documentation

Create or update a `README.md` section explaining