from rest_framework import serializers
from .models import Book, Category


class BookListSerializer(serializers.ModelSerializer):
    """Lightweight serializer used for list views."""

    in_stock = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model  = Book
        fields = [
            "id", "title", "author", "price", "original_price",
            "discount_percentage", "stock", "in_stock", "rating",
            "rating_count", "category", "category_display", "cover_image",
            "is_bestseller", "is_active", "created_at",
        ]


class BookDetailSerializer(serializers.ModelSerializer):
    """Full serializer used for retrieve / create / update views."""

    in_stock = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model  = Book
        fields = [
            "id", "title", "author", "description",
            "isbn", "price", "original_price", "discount_percentage",
            "stock", "in_stock", "rating", "rating_count",
            "format", "pages", "language", "publisher", "is_bestseller",
            "cover_image", "category", "category_display",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "discount_percentage", "created_at", "updated_at"]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock cannot be negative.")
        return value


class CategorySerializer(serializers.Serializer):
    """Returns the list of available categories."""

    value = serializers.CharField()
    label = serializers.CharField()
