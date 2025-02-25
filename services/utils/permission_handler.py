from rest_framework.exceptions import (
    AuthenticationFailed,
)
from rest_framework.permissions import (
    BasePermission,
    SAFE_METHODS,
)
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.urls import resolve
from logging_config import logger


class CustomPermissionHandler(BasePermission):
    # """
    # Unified permission handler for DAO and Forum operations:
    # - Public GET access for viewing DAOs and forum content
    # - JWT required for forum actions (posts, replies, likes)
    # - JWT + ownership required for DAO manipulations
    # """

    OWNER_REQUIRED_ENDPOINTS = [
        "dao-fetch",
        "dao-save",
    ]  # Removed refresh-status since it operates on Dip objects which use author instead of owner
    AUTH_REQUIRED_ENDPOINTS = [
        "thread-create",
        "dip-create",
        "thread-like",
        "dip-like",
        "thread-reply",
        "dip-reply",
        "reply-like",
        "refresh-status",  # Added here since it only needs authentication, not ownership check
    ]

    def authenticate(self, request):
        """Attempt authentication for all requests"""
        logger.debug("attempting authentication..")
        jwt_auth = JWTAuthentication()
        try:
            result = jwt_auth.authenticate(request)
            return result
        except Exception:
            raise

    def resolve_url(self, request):
        resolved = resolve(request.path_info)
        logger.debug(f"url path: {resolved.url_name}")
        return resolved.url_name

    def has_permission(self, request, view):
        """Check permissions based on endpoint requirements"""
        logger.debug("checking has_permission")
        url_path = self.resolve_url(request)
        if url_path == "refresh-stake":
            return True

        # If endpoint requires authentication
        if url_path in self.AUTH_REQUIRED_ENDPOINTS + self.OWNER_REQUIRED_ENDPOINTS:
            auth_result = self.authenticate(request)
            if not auth_result:
                return False
            user, token = auth_result
            request.user = user
            return True

        # For non-auth endpoints, allow safe methods
        if request.method in SAFE_METHODS:
            auth_result = self.authenticate(request)

            logger.debug(f"request: {request}\nauth result: {auth_result}")
            return True

        # For other methods on non-auth endpoints, require authentication
        auth_result = self.authenticate(request)
        if not auth_result:
            raise AuthenticationFailed(
                {
                    "error": "authentication credentials were not provided",
                }
            )
        user, token = auth_result
        request.user = user
        return True

    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        logger.debug("checking object permission")
        url_path = self.resolve_url(request)
        if url_path == "refresh-stake":
            return True

        # Owner required endpoints need ownership check
        if url_path in self.OWNER_REQUIRED_ENDPOINTS:
            return bool(request and request.user == obj.owner)

        # Auth required endpoints need authentication check
        if url_path in self.AUTH_REQUIRED_ENDPOINTS:
            return bool(request.user and request.user.is_authenticated)

        # For other endpoints, allow safe methods
        if request.method in SAFE_METHODS:
            auth_result = self.authenticate(request)
            logger.debug(f"request: {request}\nauth result: {auth_result}")
            return True

        # For non-safe methods, require authentication
        return bool(request.user and request.user.is_authenticated)

    def authenticate_header(self, request):
        """Return Bearer auth header for all requests to ensure Swagger includes auth"""
        return 'Bearer realm="api"'
