from datetime import timedelta
from unittest.mock import patch

from rest_framework_simplejwt.tokens import RefreshToken, AccessToken, TokenError
from rest_framework import status

from django.test import TestCase, Client
from django.utils.timezone import now

from core.helpers.create_user import create_user
from dao.models import Dao
from logging_config import logger


class AuthenticationTests(TestCase):
    """
    test Suite for jwt token logic (expiration, validation, etc.)

    Args:
        APITestCase (Class): django build in class
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client()
        cls.user = create_user()
        # cls.owner = User.objects.create(
        #     eth_address=generate_test_eth_address(), nickname="owner"
        # )

        cls.user_token = str(RefreshToken.for_user(cls.user).access_token)
        # cls.owner_token = str(RefreshToken.for_user(cls.owner).access_token)

        cls.HTTP_AUTHORIZATION = {"HTTP_AUTHORIZATION": f"Bearer {cls.user}"}
        # cls.owner_headers = {"HTTP_AUTHORIZATION": f"Bearer {cls.owner}"}

        cls.url_prefix = "/api/v1/"

    def test_expired_token(self):
        token = AccessToken(self.user_token)

        try:
            token.verify()
            is_valid = True
        except TokenError:
            is_valid = False

        self.assertTrue(is_valid)

        past_timestamp = int((now() - timedelta(days=1)).timestamp())
        token.payload["exp"] = past_timestamp

        with self.assertRaises(TokenError):
            token.verify()

    def test_malformed_token(self):
        malformed_token_str = str(self.user_token) + "123123"

        with self.assertRaises(TokenError):
            AccessToken(malformed_token_str).verify()

    # TODO: EXPAND TOKENS AND AUTH TEST POOL FURTHER

    # *NOTE: STARTING POINT FOR AUTHENTICATION TESTS ONE TEST PER API, EXTENSIVE TEST COVERAGE TAKES PLACE IN DEDICATED APP-TEST SUITES

    def test_login_with_no_jwt(self):
        response = self.client.post(f"{self.url_prefix}user/profile/", user=self.user)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn(
            "Authentication credentials were not provided", response.data["error"]
        )

    @patch("services.blockchain.dao_service.DaoConfirmationService._get_initial_data")
    def test_dao_base_initialization(self, mock_get_initial_data):
        Dao.objects.all().delete()

        dao_address = "0x3CDCf8d0d3Ca5cDc423E4B5566554CC4a7Fc4830"
        # Mock the blockchain response
        mock_get_initial_data.return_value = {
            "sender": self.user.eth_address,
            "dao_address": dao_address,
            "token_address": "0x4CDCf8d0d3Ca5cDc423E4B5566554CC4a7Fc4831",
            "treasury_address": "0x5CDCf8d0d3Ca5cDc423E4B5566554CC4a7Fc4832",
            "staking_address": "0x6CDCf8d0d3Ca5cDc423E4B5566554CC4a7Fc4833",
            "dao_name": "Test DAO",
            "token_name": "Test Token",
            "version": "1.0.0",
            "symbol": "TEST",
            "total_supply": "1000000000000000000000000",
        }

        payload = {
            "dao_address": dao_address,
            "network": 11155111,
        }

        response = self.client.post(f"{self.url_prefix}dao-fetch/", payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
