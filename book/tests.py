from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Book, Category

User = get_user_model()


class BookAPITests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com", name="Admin User", password="adminpassword123"
        )
        self.normal_user = User.objects.create_user(
            email="user@example.com", name="Normal User", password="userpassword123"
        )

        self.book1 = Book.objects.create(
            title="Dune",
            author="Frank Herbert",
            description="Epic sci-fi novel",
            isbn="9780441172719",
            price="19.99",
            stock=10,
            category=Category.SCIENCE,
            is_active=True,
        )
        self.book2 = Book.objects.create(
            title="The Hobbit",
            author="J.R.R. Tolkien",
            description="Fantasy classic",
            isbn="9780547928227",
            price="14.50",
            stock=5,
            category=Category.FANTASY,
            is_active=True,
        )
        self.inactive_book = Book.objects.create(
            title="Secret Draft",
            author="Unknown",
            description="Draft",
            isbn="9780000000000",
            price="9.99",
            stock=0,
            category=Category.FICTION,
            is_active=False,
        )

    def test_list_books(self):
        """Test listing all active books."""
        url = reverse("book-list-create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        titles = [b["title"] for b in response.data["results"]]
        self.assertIn("Dune", titles)
        self.assertIn("The Hobbit", titles)
        self.assertNotIn("Secret Draft", titles)

    def test_get_book_by_id(self):
        """Test retrieving a single book by ID."""
        url = reverse("book-detail", kwargs={"pk": self.book1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Dune")
        self.assertEqual(response.data["author"], "Frank Herbert")
        self.assertEqual(response.data["category"], Category.SCIENCE)

    def test_get_book_by_id_not_found(self):
        """Test 404 for invalid book ID or inactive book."""
        url = reverse("book-detail", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Inactive book should also return 404
        url_inactive = reverse("book-detail", kwargs={"pk": self.inactive_book.id})
        res_inactive = self.client.get(url_inactive)
        self.assertEqual(res_inactive.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_books_by_category_endpoint(self):
        """Test filtering books by category via category URL endpoint."""
        url = reverse("book-by-category", kwargs={"category": Category.SCIENCE})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Dune")

    def test_get_books_by_category_query_param(self):
        """Test filtering books by category via ?category= query param."""
        url = reverse("book-list-create") + f"?category={Category.FANTASY}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "The Hobbit")

    def test_get_books_by_invalid_category(self):
        """Test 400 when an invalid category slug is passed to category endpoint."""
        url = reverse("book-by-category", kwargs={"category": "non_existent_category"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("valid_categories", response.data)

    def test_categories_list(self):
        """Test listing all category options."""
        url = reverse("book-categories")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)
        slugs = [c["value"] for c in response.data]
        self.assertIn("science", slugs)
        self.assertIn("fantasy", slugs)

    def test_admin_can_create_book(self):
        """Test that an admin user can create a book."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("book-list-create")
        payload = {
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "description": "A Handbook of Agile Software Craftsmanship",
            "isbn": "9780132350884",
            "price": "29.99",
            "stock": 15,
            "category": "technology",
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Clean Code")
        self.assertTrue(Book.objects.filter(isbn="9780132350884").exists())

    def test_public_user_cannot_create_book(self):
        """Test that unauthenticated or non-admin users cannot create a book."""
        url = reverse("book-list-create")
        payload = {
            "title": "Unauthorized Book",
            "author": "Anonymous",
            "price": "10.00",
            "stock": 5,
        }
        # Unauthenticated
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated non-admin
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
