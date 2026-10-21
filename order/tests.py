from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from book.models import Book
from order.models import Order, OrderItem, OrderStatus, PaymentMethod

User = get_user_model()


class OrderDisplayTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="booklover@example.com",
            name="Book Lover",
            password="securepassword123",
        )
        self.other_user = User.objects.create_user(
            email="stranger@example.com",
            name="Stranger",
            password="securepassword123",
        )

        self.book1 = Book.objects.create(
            title="Design Patterns",
            author="Erich Gamma et al.",
            price=Decimal("650.00"),
            original_price=Decimal("800.00"),
            stock=15,
            format="Paperback",
        )
        self.book2 = Book.objects.create(
            title="The Pragmatic Programmer",
            author="David Thomas, Andrew Hunt",
            price=Decimal("720.00"),
            original_price=Decimal("950.00"),
            stock=20,
            format="Hardcover",
        )

    def test_order_confirmation_displays_all_ordered_items(self):
        """Make sure user can see all ordered items on order confirmation / receipt page."""
        order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            first_name="Book",
            last_name="Lover",
            phone="9876543210",
            street_address="100 Tech Park",
            city="Bengaluru",
            state="Karnataka",
            pin_code="560100",
            subtotal=Decimal("1370.00"),
            total_payable=Decimal("1270.00"),
            is_paid=True,
            status=OrderStatus.CONFIRMED,
        )

        item1 = OrderItem.objects.create(
            order=order,
            book=self.book1,
            title=self.book1.title,
            author=self.book1.author,
            book_format="Paperback",
            unit_price=self.book1.price,
            original_price=self.book1.original_price,
            quantity=1,
        )
        item2 = OrderItem.objects.create(
            order=order,
            book=self.book2,
            title=self.book2.title,
            author=self.book2.author,
            book_format="Hardcover",
            unit_price=self.book2.price,
            original_price=self.book2.original_price,
            quantity=2,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse("order-confirmation", kwargs={"order_id": order.id}))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")
        # Check both ordered items appear
        self.assertIn("Design Patterns", content)
        self.assertIn("Erich Gamma et al.", content)
        self.assertIn("The Pragmatic Programmer", content)
        self.assertIn("David Thomas, Andrew Hunt", content)
        self.assertIn("Hardcover", content)
        self.assertIn("Paperback", content)
        self.assertIn("₹650.00", content)
        self.assertIn("₹1440.00", content)  # 2 x 720
        self.assertIn("Ordered Items", content)
        self.assertIn("100 Tech Park", content)
        self.assertIn("₹1270.00", content)

    def test_order_history_requires_login(self):
        """Unauthenticated access to order history redirects to login."""
        response = self.client.get(reverse("order-history"))
        self.assertRedirects(response, reverse("user-login"))

    def test_order_history_displays_user_orders_and_all_items(self):
        """Make sure user can see all their past orders and all ordered items within them."""
        self.client.force_login(self.user)

        # Create order for user
        order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            first_name="Book",
            last_name="Lover",
            street_address="42 Readers Way",
            city="Pune",
            state="Maharashtra",
            pin_code="411001",
            total_payable=Decimal("650.00"),
            is_paid=True,
            status=OrderStatus.CONFIRMED,
        )
        OrderItem.objects.create(
            order=order,
            book=self.book1,
            title="Design Patterns",
            author="Erich Gamma et al.",
            book_format="Paperback",
            unit_price=Decimal("650.00"),
            quantity=1,
        )

        # Create order for stranger
        other_order = Order.objects.create(
            user=self.other_user,
            email=self.other_user.email,
            first_name="Secret",
            last_name="Stranger",
            street_address="99 Hidden Street",
            total_payable=Decimal("999.00"),
        )
        OrderItem.objects.create(
            order=other_order,
            book=self.book2,
            title="Secret Stranger Book Title 12345",
            author="Incognito",
            unit_price=Decimal("999.00"),
            quantity=1,
        )

        response = self.client.get(reverse("order-history"))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")
        # User's ordered book must be visible
        self.assertIn("Design Patterns", content)
        self.assertIn("Erich Gamma et al.", content)
        self.assertIn(f"Order #{order.id}", content)

        # Other user's order items must NOT be visible
        self.assertNotIn("Secret Stranger Book Title 12345", content)

    def test_order_history_empty_state(self):
        """Empty state is shown when user has not placed any orders yet."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("order-history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Orders Placed Yet")
        self.assertContains(response, "Explore Books Catalog")

    def test_checkout_requires_authentication(self):
        """Unauthenticated user trying to access /checkout/ must be redirected to sign in."""
        response = self.client.get(reverse("checkout"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("user-login"), response.url)

    def test_place_order_requires_authentication(self):
        """Unauthenticated user trying to place an order must be redirected to sign in."""
        response = self.client.post(reverse("place-order"), {"payment_method": "cod"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("user-login"), response.url)

    def test_order_confirmation_rejects_unauthenticated_or_other_user(self):
        """Order confirmation cannot be accessed without login or by other users."""
        order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            first_name="Book",
            last_name="Lover",
            street_address="100 Tech Park",
            city="Bengaluru",
            state="Karnataka",
            pin_code="560100",
            total_payable=Decimal("500.00"),
        )
        # Unauthenticated
        res_anon = self.client.get(reverse("order-confirmation", kwargs={"order_id": order.id}))
        self.assertEqual(res_anon.status_code, 302)
        self.assertIn(reverse("user-login"), res_anon.url)

        # Other user
        self.client.force_login(self.other_user)
        res_other = self.client.get(reverse("order-confirmation", kwargs={"order_id": order.id}))
        self.assertEqual(res_other.status_code, 302)
        self.assertRedirects(res_other, reverse("order-history"))

