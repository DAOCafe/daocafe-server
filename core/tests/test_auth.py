from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APITestCase
from rest_framework import status

from django.contrib.auth import get_user_model


from core.helpers.eth_address_generator import generate_test_eth_address
from logging_config import logger

User = get_user_model()


class AuthenticationTests(APITestCase):
    """
    test Suite for user API, checks jwt token

    Args:
        APITestCase (Class): django build in class
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create(
            eth_address=generate_test_eth_address(),
            nickname="user",
            email="johndoe@example.com",
        )
        cls.owner = User.objects.create(
            eth_address=generate_test_eth_address(), nickname="owner"
        )

        cls.user_token = str(RefreshToken.for_user(cls.user).access_token)
        cls.owner_token = str(RefreshToken.for_user(cls.owner).access_token)

        cls.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {cls.user}"}
        cls.owner_headers = {"HTTP_AUTHORIZATION": f"Bearer {cls.owner}"}

    def test_expired_token(self): ...
    def test_malformed_token(self): ...

    def test_login_with_no_jwt(self):
        response = self.client.post("/api/v1/user/profile/", user=self.user)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Authentication credentials were not provided", response.data)
