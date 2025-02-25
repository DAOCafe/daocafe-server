from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework.test import APITestCase
from rest_framework import status

from django.core.files.uploadedfile import SimpleUploadedFile

from unittest.mock import patch

from core.helpers.create_user import create_user

from .dao_utils import DaoBaseMixin, DaoFactoryMixin, Dao
from logging_config import logger


class DaoAPITests(APITestCase):
    # *: test Suite for dao api operations. involves testing dao api, appropriate status codes and object ownership

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = create_user()
        cls.token = str(RefreshToken.for_user(cls.user).access_token)
        cls.HTTP_AUTHORIZATION = {f"HTTP_AUTHORIZATION": f"Bearer {cls.token}"}
        cls.url_prefix = "/api/v1/"

        dao_base = DaoBaseMixin()
        dao_factory = DaoFactoryMixin()

        # *: TEST OBJECTS
        cls.dao = dao_base.create_dao(owner=cls.user)
        cls.dao1 = dao_base.create_dao(owner=cls.user, slug="newslugish")

    def test_dao_list_successfull(self):
        response = self.client.get(f"{self.url_prefix}dao/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["data"]["results"]), 1)

    def test_dao_retrieval_successfull(self):
        response = self.client.get(f"{self.url_prefix}dao/slugish/info/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], "slugish")

    def test_dao_list_pagination(self):
        response = self.client.get(f"{self.url_prefix}dao/")
        pagination_keys = ["count", "next", "previous", "results"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for key in pagination_keys:
            self.assertIn(key, response.data["data"])

    def test_dao_list_retrieves_empty_list(self):
        self.dao.delete()
        self.dao1.delete()
        response = self.client.get(f"{self.url_prefix}dao/")
        self.assertEqual([], response.data["data"]["results"])

    def test_dao_retrieval_dao_does_not_exist(self):
        response = self.client.get(f"{self.url_prefix}dao/nonexistent/info/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        with self.assertRaises(Dao.DoesNotExist):
            self.dao.refresh_from_db()

    def test_dao_unallowed_methods(self):
        response = self.client.post(f"{self.url_prefix}dao/", **self.HTTP_AUTHORIZATION)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.put(
            f"{self.url_prefix}dao/slug/info/", **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.patch(
            f"{self.url_prefix}dao/slug/info/", **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.delete(
            f"{self.url_prefix}dao/slug/info/", **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # *NOTE: DAO ENDPOINTS INTERACTING WITH BLOCKCHAIN
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

        response = self.client.post(
            f"{self.url_prefix}dao-fetch/", payload, **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("services.blockchain.dao_service.DaoConfirmationService._get_initial_data")
    @patch("dao.packages.services.stake_service.StakeService.create_stake_instance")
    @patch("dao.packages.services.stake_service.StakeService.has_staked_amount")
    def test_dao_save_successful(
        self, mock_has_staked, mock_stake, mock_get_initial_data
    ):
        # Clear existing DAOs
        Dao.objects.all().delete()

        dao_address = "0x3CDCf8d0d3Ca5cDc423E4B5566554CC4a7Fc4830"

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

        # First create the DAO through fetch endpoint
        fetch_payload = {
            "dao_address": dao_address,
            "network": 11155111,
        }
        fetch_response = self.client.post(
            f"{self.url_prefix}dao-fetch/", fetch_payload, **self.HTTP_AUTHORIZATION
        )
        logger.critical(f"fetch response: {fetch_response.data}")
        self.assertEqual(fetch_response.status_code, status.HTTP_201_CREATED)

        # Get the created DAO
        created_dao = Dao.objects.get(dao_contracts__dao_address=dao_address)

        mock_has_staked.return_value = True
        mock_stake.return_value = {
            "amount": 1,
            "voting_power": 1000000,
            "user": self.user,
            "dao": created_dao.id,
        }

        with open("static/default-placeholder.jpg", "rb") as media_file:
            payload = {
                "id": created_dao.id,
                "dao_image": SimpleUploadedFile(
                    "media_file.jpg", media_file.read(), content_type="image/jpeg"
                ),
                "slug": "weirdo",
                "description": "brief",
            }

        response = self.client.patch(
            f"{self.url_prefix}dao-save/", payload, **self.HTTP_AUTHORIZATION
        )
        logger.critical(f"response: {response}\n{response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], payload["slug"])

    # *NOTE: STAKE ENDPOINTS TIGHTLY ASSOCIATED WITH DAO. INTERACTION WITH BLOCKCHAIN TAKES PLACE

    def test_refresh_stake_retrieval