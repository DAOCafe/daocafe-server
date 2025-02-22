from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .__init__ import generate_test_eth_address
from logging_config import logger

User = get_user_model()


class AuthenticationTests(APITestCase):
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

    def test_login_successfull(self):
        response = self.client.get(
            "/api/v1/user/profile/", HTTP_AUTHORIZATION=f"Bearer {self.user_token}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("eth_address", response.data)

        self.assertEqual(
            response.wsgi_request.META["HTTP_AUTHORIZATION"],
            f"Bearer {self.user_token}",
        )

    def test_login_with_no_jwt(self):
        response = self.client.post("/api/v1/user/profile/", user=self.user)
        logger.debug(f"response: {response}\data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Authentication credentials were not provided", response.data)

    def
