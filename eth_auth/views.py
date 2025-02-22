from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from drf_spectacular.utils import extend_schema
from django.contrib.auth import get_user_model

from .serializers import NonceSerializer, SignatureSerializer

from services.utils.exception_handler import ErrorHandlingMixin


class NonceManagerView(ErrorHandlingMixin, APIView):
    def handle_exception(self, ex):
        return super().handle_exception(ex)

    permission_classes = [AllowAny]
    serializer_class = NonceSerializer

    @extend_schema(
        request=NonceSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "nonce": {"type": "string"},
                    "timestamp": {"type": "integer"},
                },
            }
        },
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.create(serializer.validated_data)
        return Response(response)


class SignatureVerifierView(ErrorHandlingMixin, APIView):
    def handle_exception(self, ex):
        return super().handle_exception(ex)

    serializer_class = SignatureSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        request=SignatureSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "tokens": {
                        "type": "object",
                        "properties": {
                            "refresh": {"type": "string"},
                            "access": {"type": "string"},
                        },
                    },
                    "success": {"type": "boolean"},
                },
            }
        },
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        eth_address = serializer.validated_data["eth_address"]

        # try:
        User = get_user_model()
        user, _ = User.objects.get_or_create(eth_address=eth_address.lower())
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "is_success": True,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=200,
        )
        # except Exception as ex:
        #     return Response(
        #         {"error": str(ex)},
        #         status=status.HTTP_401_UNAUTHORIZED,
        #     )
