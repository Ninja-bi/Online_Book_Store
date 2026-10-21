"""
URL configuration for Book_Store project.
"""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    # HTML Book Pages  →  / (Home), /books/ (Catalog), /books/<id>/ (Detail)
    path("", include("book.page_urls")),

    # Admin panel
    path("admin/", admin.site.urls),

    # HTML pages  →  /user/login/  and  /user/register/
    path("user/", include("user.page_urls")),

    # REST API  →  /api/v1/auth/register/  /api/v1/auth/login/  etc.
    path("api/v1/auth/", include("user.urls")),

    # Order pages  →  /checkout/  /orders/  etc.
    path("", include("order.urls")),

    # Payment pages & webhooks  →  /payment/initiate/  /payment/verify/  etc.
    path("payment/", include("payment.urls")),

    # Book API  →  /api/v1/books/
    path("api/v1/books/", include("book.urls")),

    # Swagger / OpenAPI docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/",   SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/",  SpectacularRedocView.as_view(url_name="schema"),   name="redoc"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
