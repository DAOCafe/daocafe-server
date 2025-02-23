from django.core.cache import cache
from web3 import Web3
from eth_account.messages import encode_defunct
import time
import secrets
from logging_config import logger


class AuthenticationError(Exception): ...


class NonceManager:
    NONCE_TIMEOUT = 3600
    NONCE_PREFIX = "eth_nonce:"

    @classmethod
    def generate_nonce(cls, eth_address: str) -> str:
        """generates a new nonce for the given address and sets in cache

        Args:
            eth_address (str): eth address

        Returns:
            str: set in cache nonce
        """

        nonce = secrets.token_hex(16)
        timestamp = int(time.time())
        cache_key = f"{cls.NONCE_PREFIX}{eth_address.lower()}"

        cache.set(cache_key, (nonce, timestamp), timeout=cls.NONCE_TIMEOUT)

        return nonce

    @classmethod
    def verify_nonce(cls, eth_address: str, nonce: str) -> bool:
        """verifies nonce with the bound eth_address to cache key

        Args:
            eth_address (str): users eth_address
            nonce (str):

        Returns:
            bool: whether the nonce is valid and present in cache
        """
        cache_key = f"{cls.NONCE_PREFIX}{eth_address.lower()}"
        stored_data = cache.get(cache_key)

        try:
            if not stored_data:
                return False

            stored_nonce, timestamp = stored_data
            current_time = int(time.time())

            if current_time - timestamp > cls.NONCE_TIMEOUT:
                # cache.delete(cache_key)
                return False

            if stored_nonce != nonce:
                return False
            # FIXME: UNCOMMENT IN PRODUCTION
            # cache.delete(cache_key)
            return True
        except Exception as ex:
            return False


class SignatureVerifier:
    @staticmethod
    def verify_ethereum_signature(
        message: str, signature: str, eth_address: str
    ) -> bool:
        """verify that the signature was signed by the address owner"""
        try:
            print(f"Starting signature verification for address: {eth_address}")
            print(f"Message to verify: {message}")

            cache_key = f"{NonceManager.NONCE_PREFIX}{eth_address.lower()}"
            stored_data = cache.get(cache_key)
            if not stored_data:
                print("Verification failed: No stored nonce data found in cache")
                return False

            stored_nonce, timestamp = stored_data

            if any(str(item) not in message for item in [stored_nonce, timestamp]):
                return False

            print("Attempting to recover address from signature...")
            w3 = Web3()
            message_hash = encode_defunct(text=message)
            recovered_address = w3.eth.account.recover_message(
                message_hash, signature=signature
            )
            print(f"Recovered address: {recovered_address}")
            print(f"Expected address: {eth_address}")

            result = recovered_address.lower() == eth_address.lower()
            if not result:
                print(
                    "Verification failed: Recovered address does not match expected address"
                )
            else:
                print("Signature verification successful!")
            return result
        except Exception as ex:
            print(f"Verification failed with exception: {str(ex)}")
            return False
