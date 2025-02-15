"""url mappings for the user API"""

from django.urls import path
from .views import NonceManagerView, SignatureVerifierView

app_name = "eth_auth"

urlpatterns = [
    path("nonce/", NonceManagerView.as_view(), name="nonce"),
    path("verify/", SignatureVerifierView.as_view(), name="signature"),
]
