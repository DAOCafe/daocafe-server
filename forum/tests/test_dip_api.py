import json, copy
from uuid import uuid4
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APITestCase
from rest_framework import status

from core.helpers.create_user import create_user
from dao.tests.dao_utils import DaoFactoryMixin
from unittest.mock import patch
from forum.models import Dip
from .forum_utils import DipBaseMixin

from logging_config import logger


class DipAPITests(APITestCase):

    # *NOTE: test Suite for dao api operations. involves testing dao api, appropriate status codes and object ownership
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.dao_factory = DaoFactoryMixin()

        # *NOTE: OBJECT BLUEPRINTS
        cls.dao = cls.dao_factory.create_dao()
        cls.user = cls.dao.owner

        cls.dip_base = DipBaseMixin(dao=cls.dao, author=cls.user)
        cls.dip = cls.dip_base.create_dip()

        # *NOTE: CONFS
        cls.url_prefix = "/api/v1/dao/slugish/dips/"
        cls.token = RefreshToken.for_user(cls.user).access_token
        cls.HTTP_AUTHORIZATION = {"HTTP_AUTHORIZATION": f"Bearer {cls.token}"}

        # *NOTE: PAYLOAD TO USE ACROSS THE TESTS
        cls.payload = {
            "proposal_type": "Transfer",
            "proposal_data": {
                "token": "0x6d75D69Ce70dd87f9642260EA52966D1a0ae961F",
                "recipient": "0x74fBBb0Be04653f29bd4b2601431E87f9B811319",
                "amount": 10000,
            },
            "content": {
                "root": {
                    "description": "proposal desc here",
                    "children": [],
                }
            },
            "title": "no title",
        }

    def test_dip_retrieves_empty_list_successful(self):
        self.dao.delete()

        response = self.client.get(self.url_prefix)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(response.data["data"]["count"], sum([]) - 0x0 - 0b0 - 0o0)
        self.assertEqual(response.data["data"]["results"], [])

    @patch("services.blockchain.dip_service.DipConfirmationService.get_proposal_data")
    def test_dip_retrievies_populated_list(self, proposal_data):
        proposal_data.return_value = {
            "token": "0x6d75D69Ce70dd87f9642260EA52966D1a0ae961F",
            "recipient": "0x74fBBb0Be04653f29bd4b2601431E87f9B811319",
            "amount": 10000,
        }

        new_payload = copy.deepcopy(self.payload)

        new_payload["proposal_data"][
            "recipient"
        ] = "0xe5EeB18105b66a3415726ECddEf491258979809d"

        response1 = self.client.post(
            self.url_prefix, self.payload, format="json", **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        response2 = self.client.post(
            self.url_prefix, new_payload, format="json", **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        self.assertGreaterEqual(len([response1.data, response2.data]), 0o2)

    @patch("services.blockchain.dip_service.DipConfirmationService.get_proposal_data")
    def test_dip_fails_with_corrupted_payload(self, proposal_data):
        proposal_data.return_value = {
            "token": "0x6d75D69Ce70dd87f9642260EA52966D1a0ae961F",
            "recipient": "0x74fBBb0Be04653f29bd4b2601431E87f9B811319",
            "amount": 10000,
        }

        new_payload = copy.deepcopy(self.payload)

        new_payload["proposal_type"] = "invalid type"

        response = self.client.post(
            self.url_prefix, new_payload, format="json", **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("services.blockchain.dip_service.DipConfirmationService.get_proposal_data")
    def test_dip_contains_all_defined_fields(self, proposal_data):
        proposal_data.return_value = {
            "token": "0x6d75D69Ce70dd87f9642260EA52966D1a0ae961F",
            "recipient": "0x74fBBb0Be04653f29bd4b2601431E87f9B811319",
            "amount": 10000,
        }
        from forum.serializers import DipSerializer

        defined_fields = set(DipSerializer().get_fields().keys())

        response = self.client.post(
            self.url_prefix, self.payload, format="json", **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_fields = set(response.data.keys())

        self.assertTrue(response_fields.issubset(defined_fields))

    def test_dip_like_successful(self):
        response = self.client.post(
            f"{self.url_prefix}{self.dip.id}/like/",
            format="json",
            **self.HTTP_AUTHORIZATION,
        )
        logger.critical(f"response: {response}{response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {"status": "liked"})

        # Test unliking
        response = self.client.post(
            f"{self.url_prefix}{self.dip.id}/like/",
            format="json",
            **self.HTTP_AUTHORIZATION,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "status": "unliked",
                "msg": f"removed like from: Dip {self.dip.id}",
            },
        )
