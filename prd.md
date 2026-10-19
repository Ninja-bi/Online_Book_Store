Here is a complete Product Requirements Document (PRD) for your Django Online Book Store project. It is structured so you can use it as a development blueprint or provide it to an AI coding tool to generate the application step by step.

# Product Requirements Document (PRD)

Project: Online Book Store API · Version 1.0 · October 2026

Backend: Django REST Framework

Authentication: JWT

Database: SQLite

## 1. Project overview

Product name: Online Book Store

The Online Book Store is a backend web application built using Django and Django REST Framework (DRF). It allows users to register, log in using their email and password, browse books, view individual book details, add books to a cart, and place orders.

The application will use JWT (JSON Web Token) authentication to secure protected API endpoints. SQLite will be the default database for storing users, books, carts, and orders. Django Admin will provide an interface for administrators to manage the store.

### Main objectives

- Implement secure user registration and email/password login.
- Generate JWT access and refresh tokens.
- Develop a separate Django app named `book`.
- Provide APIs to list all books and retrieve a book by ID.
- Implement a shopping cart and order management system.
- Provide an admin panel for managing books, users, and orders.
- Build a modular, maintainable REST API.

## 2. Technology stack

| Component            | Technology                         |
| -------------------- | ---------------------------------- |
| Programming language | Python                             |
| Backend framework    | Django                             |
| REST API             | Django REST Framework              |
| Authentication       | Simple JWT                         |
| Database             | SQLite                             |
| API documentation    | drf-spectacular / Swagger          |
| Admin panel          | Django Admin                       |
| Testing              | Django Test Framework / pytest     |
| API testing          | Postman                            |
| Image handling       | Pillow (optional, for book covers) |

Recommended packages:

```
pip install django djangorestframework djangorestframework-simplejwt pillow drf-spectacular
```

## 3. Application architecture

Client / Frontend

Browser, mobile app, or Postman

Django REST Framework

URL routing · Views · Serializers · Permissions

Accounts

Registration, JWT login, user profile

Book

Catalog, details, cart, orders

SQLite Database

Users · Books · Cart items · Orders · Order items

The Django Admin site will be a separate administrative interface connected to the same database.

## 4. User roles and permissions

Customer

- Register and log in with email and password.
- Browse available books and view details.
- Add books to the cart, change quantities, and remove items.
- Place orders and view personal order history.
- Access only their own cart and orders.

Administrator

- Log in through Django Admin.
- Create, update, and delete book listings.
- Manage inventory and book availability.
- View all customers and orders.
- Update order statuses.
- Access protected administrative operations.

## 5. Functional requirements

### FR-01: User registration and authentication

Users must be able to create an account using their name, email, and password.

Registration requirements

- Email must be unique.
- Password must meet Django's password validation rules.
- Passwords must be securely hashed, never stored as plain text.
- A successful registration creates a user account in SQLite.
- The application should use a custom Django user model with email as the login identifier.

Login requirements

- Users log in with email and password.
- Successful login returns a JWT access token and refresh token.
- Invalid credentials return an appropriate error.
- Protected APIs require a valid access token.
- Expired access tokens can be renewed using a valid refresh token.

### FR-02: Book catalog

The `book` app will provide book listing and detail APIs.

Each book should contain:

| Field         | Description              |
| ------------- | ------------------------ |
| `id`          | Unique primary key       |
| `title`       | Book title               |
| `author`      | Author name              |
| `description` | Book description         |
| `isbn`        | Unique ISBN, if provided |
| `price`       | Selling price            |
| `stock`       | Available inventory      |
| `cover_image` | Optional cover image     |
| `category`    | Book category            |
| `created_at`  | Creation timestamp       |
| `updated_at`  | Last update timestamp    |

Required functionality

- Fetch all active books.
- Fetch a single book by its ID.
- Return a 404 response for a nonexistent book.
- Hide unpublished books from public listings.
- Support optional pagination and search by title or author.
- Prevent negative prices and negative stock quantities.

### FR-03: Shopping cart

Users can add books to a cart before placing an order.

Required functionality

- Add a book to the cart.
- View the current user's cart.
- Update the quantity of a cart item.
- Remove a specific item.
- Clear the cart.
- Calculate the subtotal and total.
- Reject quantities below one or quantities exceeding available stock.

The cart must belong to the authenticated user. Two different users must never see or modify each other's cart.

Cart data example

```
{
  "items": [
    {
      "book_id": 1,
      "title": "Python Programming",
      "quantity": 2,
      "unit_price": "399.00",
      "subtotal": "798.00"
    }
  ],
  "total": "798.00"
}
```

The prices above are illustrative. The server must calculate totals using database values rather than trusting prices supplied by the client.

### FR-04: Order management

Customers can convert their cart into an order.

Order workflow

Add books to cart

Validate stock and prices

Create order and order items

Reduce stock and clear cart

Return order confirmation

Required functionality

- Place an order using the authenticated user's cart.
- Validate that all requested books are available.
- Calculate the final amount on the server.
- Save the order and its items in a database transaction.
- Store the purchase price of each book at the time of ordering.
- Reduce inventory only when the order is successfully created.
- Clear the cart after successful checkout.
- Allow customers to view their own orders and order details.
- Allow administrators to update order statuses.

Recommended order statuses:

- `PENDING`
- `CONFIRMED`
- `SHIPPED`
- `DELIVERED`
- `CANCELLED`

For the initial version, checkout can be cash on delivery or a simulated payment flow. Real payment gateway integration is outside the MVP unless added later.

## 6. API endpoint specification

Use `/api/v1/` as the base URL.

### Authentication APIs

| Method | Endpoint                      | Purpose                    | Access                    |
| ------ | ----------------------------- | -------------------------- | ------------------------- |
| POST   | `/api/v1/auth/register/`      | Register a user            | Public                    |
| POST   | `/api/v1/auth/login/`         | Obtain JWT tokens          | Public                    |
| POST   | `/api/v1/auth/token/refresh/` | Refresh access token       | Public with refresh token |
| GET    | `/api/v1/auth/me/`            | Get current user's profile | Authenticated             |

### Book APIs

| Method    | Endpoint              | Purpose               | Access |
| --------- | --------------------- | --------------------- | ------ |
| GET       | `/api/v1/books/`      | List books            | Public |
| GET       | `/api/v1/books/<id>/` | Retrieve a book by ID | Public |
| POST      | `/api/v1/books/`      | Create a book         | Admin  |
| PUT/PATCH | `/api/v1/books/<id>/` | Update a book         | Admin  |
| DELETE    | `/api/v1/books/<id>/` | Delete a book         | Admin  |

Public catalog endpoints are read-only for ordinary users. Book-management operations must be restricted to administrators.

### Cart APIs

| Method | Endpoint                   | Purpose                  |
| ------ | -------------------------- | ------------------------ |
| GET    | `/api/v1/cart/`            | View current user's cart |
| POST   | `/api/v1/cart/items/`      | Add a book to cart       |
| PATCH  | `/api/v1/cart/items/<id>/` | Update quantity          |
| DELETE | `/api/v1/cart/items/<id>/` | Remove an item           |
| DELETE | `/api/v1/cart/clear/`      | Clear the cart           |

All cart APIs require JWT authentication.

Example request for adding a book:

```
{
  "book_id": 1,
  "quantity": 2
}
```

### Order APIs

| Method | Endpoint                      | Purpose                      | Access               |
| ------ | ----------------------------- | ---------------------------- | -------------------- |
| POST   | `/api/v1/orders/checkout/`    | Place an order from the cart | Customer             |
| GET    | `/api/v1/orders/`             | List current user's orders   | Customer             |
| GET    | `/api/v1/orders/<id>/`        | View order details           | Order owner or admin |
| PATCH  | `/api/v1/orders/<id>/status/` | Update order status          | Admin                |

The API must not allow customers to submit arbitrary totals, change another user's order, or mark their own orders as delivered.

## 7. Database design

The project should use Django ORM and SQLite by default.

User

`id` · `name` · `email` · `password` · `is_staff` · `is_active`

One user has one cart and can place many orders

Cart

`id` · `user_id` · `created_at`

Order

`id` · `user_id` · `total_amount` · `status` · `created_at`

CartItem

`cart_id` · `book_id` · `quantity`

OrderItem

`order_id` · `book_id` · `quantity` · `unit_price`

Book

`id` · `title` · `author` · `price` · `stock` · `category` · `is_active`

### Database rules

- A user has one cart, with multiple cart items.
- Each cart item references one book.
- A user can place multiple orders.
- Each order contains one or more order items.
- `OrderItem.unit_price` stores the price at purchase time.
- Use `DecimalField` for money, not floating-point fields.
- Use foreign keys and suitable uniqueness constraints to preserve data integrity.
- Use transactions for checkout to prevent partial orders and incorrect inventory updates.

## 8. Django project structure

Recommended structure:

```
online_bookstore/
│
├── manage.py
├── requirements.txt
├── db.sqlite3
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── accounts/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── permissions.py
│   └── tests.py
│
└── book/
    ├── models.py
    ├── serializers.py
    ├── views.py
    ├── urls.py
    ├── permissions.py
    ├── admin.py
    ├── services.py
    └── tests.py
```

The `accounts` app handles the custom user model and authentication. The `book` app handles the book catalog, cart, and order functionality.

Important implementation detail: Create and configure the custom user model before running the first database migrations. Changing the user model after tables have been created can require complex migration work.

## 9. Django Admin panel

The admin panel will be available at:

`http://127.0.0.1:8000/admin/`

Administrators should be able to:

- Add and edit books.
- Search books by title, author, and ISBN.
- Filter books by category and availability.
- Inspect stock levels.
- View customer accounts.
- View orders and order items.
- Filter orders by status and date.
- Update permitted order statuses.
- Inspect order totals and purchase-time prices.

Create an administrator account using:

```
python manage.py createsuperuser
```

Use Django's built-in staff and superuser permissions. Do not expose the admin interface as a regular customer endpoint.

## 10. Non-functional requirements

Security

- Use JWT authentication and appropriate DRF permission classes.
- Hash passwords with Django's built-in password hashers.
- Keep secret keys and production credentials out of source control.
- Validate all request data on the server.
- Restrict cart and order queries to the authenticated owner.
- Use HTTPS in production.
- Configure CORS and token lifetimes appropriately if a separate frontend is introduced.

Performance

- Paginate the book listing.
- Use efficient ORM queries and indexes where appropriate.
- Avoid unnecessary database queries when loading order items.
- Keep the initial version suitable for local development and a small demonstration deployment.

Reliability

- Use database transactions for checkout.
- Validate stock before confirming an order.
- Write automated tests for authentication, permissions, cart operations, and checkout.
- Provide consistent JSON error responses.

Maintainability

- Separate serializers, views, permissions, and business logic.
- Use versioned API routes.
- Document endpoints with Swagger/OpenAPI.
- Store dependencies in `requirements.txt`.

## 11. MVP acceptance criteria

The project is considered complete when all of the following work:

## Definition of done

0 of 12

Users can register with an email and password.

Users can log in and receive valid JWT access and refresh tokens.

Protected endpoints reject missing, invalid, or expired access tokens.

Anyone can list active books and fetch an individual book by ID.

Only administrators can create, update, or delete books.

Authenticated users can add, update, view, and remove their own cart items.

Users cannot access another customer's cart or orders.

Checkout validates stock and calculates totals on the server.

Successful checkout creates an order, saves item prices, updates stock, and clears the cart atomically.

Customers can view their own order history and order details.

Administrators can manage books and orders through Django Admin.

SQLite migrations, API documentation, and automated tests are included.

## 12. Development phases

1. Phase 1 — Project setup: Create the Django project, install dependencies, configure SQLite, and set up the custom user model.
2. Phase 2 — Authentication: Implement registration, email/password login, JWT issuance, refresh, and profile endpoints.
3. Phase 3 — Book catalog: Build the book model, serializers, read APIs, admin registration, search, and pagination.
4. Phase 4 — Shopping cart: Implement cart models, item operations, quantity validation, and totals.
5. Phase 5 — Orders and checkout: Add order models, transaction-safe checkout, inventory handling, and order history.
6. Phase 6 — Testing and documentation: Test authentication, access control, edge cases, and checkout; generate Swagger documentation.

## 13. Out of scope for version 1.0

To keep the first version achievable, defer the following features:

- Online payment gateway integration.
- Delivery tracking and courier integration.
- Reviews, ratings, and wishlists.
- Discount codes and loyalty points.
- Email verification and password-reset email workflows.
- Recommendation algorithms.
- A full frontend storefront (the initial deliverable is a REST API).

These can be added in later versions.

## 14. Definition of the final deliverable

The completed application should include:

- A runnable Django project with `accounts` and `book` apps.
- A working SQLite database and migrations.
- JWT-based email/password authentication.
- Book catalog, shopping cart, and checkout APIs.
- Customer order history and administrator order management.
- A configured Django Admin panel.
- Swagger API documentation.
- A `requirements.txt`, setup instructions, and automated tests.
- Sample book data for testing the application.

Recommended implementation order: Start with the custom user model and JWT authentication, then build the book catalog, followed by the cart and checkout workflow. This order avoids having to redesign authentication or database relationships later.