from django.urls import path
from .views import BookListCreateView, BookDetailView, BookByCategoryView, CategoryListView

urlpatterns = [
    # GET  /api/v1/books/                    — list all books  (+ search & category filter)
    # POST /api/v1/books/                    — create a book   (admin only)
    path("", BookListCreateView.as_view(), name="book-list-create"),

    # GET /api/v1/books/categories/          — list all category options
    path("categories/", CategoryListView.as_view(), name="book-categories"),

    # GET /api/v1/books/category/<slug>/     — books filtered by category
    path("category/<str:category>/", BookByCategoryView.as_view(), name="book-by-category"),

    # GET    /api/v1/books/<id>/             — retrieve a book
    # PUT    /api/v1/books/<id>/             — full update     (admin only)
    # PATCH  /api/v1/books/<id>/             — partial update  (admin only)
    # DELETE /api/v1/books/<id>/             — delete          (admin only)
    path("<int:pk>/", BookDetailView.as_view(), name="book-detail"),
]
