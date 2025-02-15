from django.core.cache import cache
from web3 import Web3
from eth_account.messages import encode_defunct
import time
import secrets


class AuthenticationError(Exception): ...


class NonceManager:
    NONCE_TIMEOUT = 3600
    NONCE_PREFIX = "eth_nonce:"

    @classmethod
    def generate_nonce(cls, eth_address: str) -> str:
        """generates a new nonce for the given address"""
        nonce = secrets.token_hex(16)
        timestamp = int(time.time())
        cache_key = f"{cls.NONCE_PREFIX}{eth_address.lower()}"

        cache.set(cache_key, (nonce, timestamp), timeout=cls.NONCE_TIMEOUT)

        return nonce

    @classmethod
    def verify_nonce(cls, eth_address: str, nonce: str) -> bool:
        """verify nonce and delete it if valid"""
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
            cache_key = f"{NonceManager.NONCE_PREFIX}{eth_address.lower()}"
            stored_data = cache.get(cache_key)
            if not stored_data:
                return False

            stored_nonce, timestamp = stored_data

            if any(str(item) not in message for item in [stored_nonce, timestamp]):
                return False
            w3 = Web3()
            message_hash = encode_defunct(text=message)
            recovered_address = w3.eth.account.recover_message(
                message_hash, signature=signature
            )

            return recovered_address.lower() == eth_address.lower()
        except Exception as ex:
            return False
