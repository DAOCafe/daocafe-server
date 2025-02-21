from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from django.conf import settings
from django.conf.urls.static import static
from forum.views import DipSyncronizationView, DipSingleSyncronizationView

from dao.views import StakeView
from forum.urls import vote_router

api_urlpatterns = [
    # authentication
    path("auth/", include("eth_auth.urls")),
    # user-related endpoints
    path("user/", include("user.urls")),
    # dao-related endpoints
    path("dao", include("dao.urls")),
    path("dao/", include("forum.urls")),
    path(
        "refresh/stake/",
        StakeView.as_view({"post": "create", "get": "list"}),
        name="refresh-stake",
    ),
    # dip-related endpoints
    path(
        "refresh/dao/<slug:slug>/dips/",
        DipSyncronizationView.as_view({"post": "create"}),
        name="refresh-dips",
    ),
    path("", include(vote_router.urls)),
    path(
        "refresh/dip/<int:pk>/status/",
        DipSingleSyncronizationView.as_view({"patch": "update"}),
        name="refresh-status",
    ),
]

urlpatterns = [
    path("api/v1/", include(api_urlpatterns)),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
