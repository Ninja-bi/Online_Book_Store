from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from .models import Book, Category
from .serializers import BookDetailSerializer, BookListSerializer, CategorySerializer


# ── Pagination ────────────────────────────────────────────────────────────────

class BookPagination(PageNumberPagination):
    page_size            = 12
    page_size_query_param = "page_size"
    max_page_size        = 100


# ── Helper ────────────────────────────────────────────────────────────────────

def active_books():
    """Return only published / active books."""
    return Book.objects.filter(is_active=True)


# ── Book List & Create ────────────────────────────────────────────────────────

class BookListCreateView(APIView):
    """
    GET  /api/v1/books/  — List all active books (public).
    POST /api/v1/books/  — Create a new book (admin only).

    Query params:
      ?search=<str>       — filter by title or author (case-insensitive)
      ?category=<slug>    — filter by category slug
      ?page=<n>           — pagination
      ?page_size=<n>      — results per page (max 100)
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return [AllowAny()]

    @extend_schema(
        parameters=[
            OpenApiParameter("search",   str, description="Search by title or author"),
            OpenApiParameter("category", str, description="Filter by category slug (e.g. fiction, science)"),
            OpenApiParameter("page",     int, description="Page number"),
            OpenApiParameter("page_size",int, description="Results per page (max 100)"),
        ],
        responses={200: BookListSerializer(many=True)},
        summary="List all active books",
        description="Returns a paginated list of active books. Supports search and category filtering.",
    )
    def get(self, request):
        qs = active_books()

        # Search by title or author
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(title__icontains=search) | qs.filter(author__icontains=search)

        # Filter by category
        category = request.query_params.get("category", "").strip()
        if category:
            qs = qs.filter(category=category)

        # Paginate
        paginator   = BookPagination()
        page        = paginator.paginate_queryset(qs, request)
        serializer  = BookListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=BookDetailSerializer,
        responses={
            201: BookDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            403: OpenApiResponse(description="Admin access required"),
        },
        summary="Create a book (admin only)",
    )
    def post(self, request):
        serializer = BookDetailSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            book = serializer.save()
            return Response(BookDetailSerializer(book, context={"request": request}).data,
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── Book Detail, Update & Delete ──────────────────────────────────────────────

class BookDetailView(APIView):
    """
    GET    /api/v1/books/<id>/  — Retrieve a book by ID (public).
    PUT    /api/v1/books/<id>/  — Full update (admin only).
    PATCH  /api/v1/books/<id>/  — Partial update (admin only).
    DELETE /api/v1/books/<id>/  — Delete a book (admin only).
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_object(self, pk):
        try:
            return Book.objects.get(pk=pk, is_active=True)
        except Book.DoesNotExist:
            return None

    @extend_schema(
        responses={
            200: BookDetailSerializer,
            404: OpenApiResponse(description="Book not found"),
        },
        summary="Retrieve a book by ID",
    )
    def get(self, request, pk):
        book = self.get_object(pk)
        if not book:
            return Response({"detail": "Book not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BookDetailSerializer(book, context={"request": request}).data)

    @extend_schema(
        request=BookDetailSerializer,
        responses={200: BookDetailSerializer, 404: OpenApiResponse(description="Book not found")},
        summary="Update a book (admin only)",
    )
    def put(self, request, pk):
        book = self.get_object(pk)
        if not book:
            return Response({"detail": "Book not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = BookDetailSerializer(book, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=BookDetailSerializer,
        responses={200: BookDetailSerializer, 404: OpenApiResponse(description="Book not found")},
        summary="Partially update a book (admin only)",
    )
    def patch(self, request, pk):
        book = self.get_object(pk)
        if not book:
            return Response({"detail": "Book not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = BookDetailSerializer(book, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        responses={
            204: OpenApiResponse(description="Book deleted"),
            404: OpenApiResponse(description="Book not found"),
        },
        summary="Delete a book (admin only)",
    )
    def delete(self, request, pk):
        book = self.get_object(pk)
        if not book:
            return Response({"detail": "Book not found."}, status=status.HTTP_404_NOT_FOUND)
        book.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Books by Category ─────────────────────────────────────────────────────────

class BookByCategoryView(APIView):
    """
    GET /api/v1/books/category/<slug>/
    Returns all active books in the given category.
    Supports ?search= and pagination.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter("search",    str, description="Filter results by title or author"),
            OpenApiParameter("page",      int, description="Page number"),
            OpenApiParameter("page_size", int, description="Results per page (max 100)"),
        ],
        responses={
            200: BookListSerializer(many=True),
            400: OpenApiResponse(description="Invalid category"),
        },
        summary="List books by category",
        description=(
            "Returns all active books in the specified category. "
            "Valid slugs: " + ", ".join(c[0] for c in Category.choices)
        ),
    )
    def get(self, request, category):
        # Validate category slug
        valid = [c[0] for c in Category.choices]
        if category not in valid:
            return Response(
                {
                    "detail": f"'{category}' is not a valid category.",
                    "valid_categories": valid,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = active_books().filter(category=category)

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(title__icontains=search) | qs.filter(author__icontains=search)

        paginator  = BookPagination()
        page       = paginator.paginate_queryset(qs, request)
        serializer = BookListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


# ── Category List ─────────────────────────────────────────────────────────────

class CategoryListView(APIView):
    """
    GET /api/v1/books/categories/
    Returns all available category slugs and their display labels.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: CategorySerializer(many=True)},
        summary="List all book categories",
    )
    def get(self, request):
        data = [{"value": v, "label": l} for v, l in Category.choices]
        return Response(data)
