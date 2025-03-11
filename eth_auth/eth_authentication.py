from django.core.cache import cache
from web3 import Web3
from eth_account.messages import encode_defunct
import time
import secrets
import os
import traceback
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
        # Normalize address to lowercase
        eth_address = eth_address.lower()
        logger.info(f"Generating nonce for address: {eth_address}")
        
        nonce = secrets.token_hex(16)
        timestamp = int(time.time())
        cache_key = f"{cls.NONCE_PREFIX}{eth_address}"
        
        logger.info(f"Cache key: {cache_key}, nonce: {nonce}, timestamp: {timestamp}")
        
        # Store the data
        success = cache.set(cache_key, (nonce, timestamp), timeout=cls.NONCE_TIMEOUT)
        
        # Verify it was stored
        stored_data = cache.get(cache_key)
        if stored_data:
            logger.info(f"Successfully stored nonce in cache: {stored_data}")
        else:
            logger.error(f"Failed to store nonce in cache for {eth_address}")
        
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
        # Normalize address to lowercase
        eth_address = eth_address.lower()
        logger.info(f"Verifying nonce for address: {eth_address}, nonce: {nonce}")
        
        cache_key = f"{cls.NONCE_PREFIX}{eth_address}"
        logger.info(f"Looking up cache key: {cache_key}")
        
        stored_data = cache.get(cache_key)
        logger.info(f"Retrieved from cache: {stored_data}")
        
        try:
            if not stored_data:
                logger.error(f"No stored nonce found for {eth_address} with key {cache_key}")
                return False
            
            if not isinstance(stored_data, tuple) or len(stored_data) != 2:
                logger.error(f"Invalid stored data format: {stored_data}")
                return False
            
            stored_nonce, timestamp = stored_data
            current_time = int(time.time())
            
            if current_time - timestamp > cls.NONCE_TIMEOUT:
                logger.error(f"Nonce expired for {eth_address}: {current_time - timestamp}s > {cls.NONCE_TIMEOUT}s")
                return False
            
            if stored_nonce != nonce:
                logger.error(f"Nonce mismatch for {eth_address}: expected {stored_nonce}, got {nonce}")
                return False
                
            # Delete nonce in production to prevent replay attacks
            # In development, we might keep it for debugging purposes
            if not os.environ.get('DEBUG', 'False').lower() == 'true':
                cache.delete(cache_key)
                logger.info(f"Deleted used nonce for {eth_address}")
            
            logger.info(f"Nonce verification successful for {eth_address}")
            return True
        except Exception as ex:
            logger.error(f"Error verifying nonce: {str(ex)}")
            logger.error(traceback.format_exc())
            return False


class SignatureVerifier:
    @staticmethod
    def verify_ethereum_signature(
        message: str, signature: str, eth_address: str
    ) -> bool:
        """verify that the signature was signed by the address owner"""
        try:
            # Normalize address to lowercase
            eth_address = eth_address.lower()
            logger.info(f"Verifying signature for address: {eth_address}")
            logger.info(f"Message: {message}")
            logger.info(f"Signature: {signature}")

            cache_key = f"{NonceManager.NONCE_PREFIX}{eth_address}"
            logger.info(f"Looking up cache key: {cache_key}")
            
            stored_data = cache.get(cache_key)
            logger.info(f"Retrieved from cache: {stored_data}")
            
            if not stored_data:
                logger.error("Verification failed: No stored nonce data found in cache")
                # Try to check if there are any keys with similar prefix
                all_keys = []
                for db in range(3):  # Check first 3 databases
                    try:
                        from django.core.cache.backends.redis import RedisCache
                        if isinstance(cache, RedisCache):
                            client = cache.client.get_client()
                            client.select(db)
                            keys = client.keys(f"{NonceManager.NONCE_PREFIX}*")
                            if keys:
                                all_keys.extend([f"DB{db}:{k.decode()}" for k in keys])
                    except Exception as e:
                        logger.error(f"Error checking Redis DB{db}: {str(e)}")
                
                if all_keys:
                    logger.info(f"Found similar keys in Redis: {all_keys}")
                else:
                    logger.info("No similar keys found in Redis")
                    
                return False

            if not isinstance(stored_data, tuple) or len(stored_data) != 2:
                logger.error(f"Invalid stored data format: {stored_data}")
                return False
                
            stored_nonce, timestamp = stored_data

            if any(str(item) not in message for item in [stored_nonce, timestamp]):
                logger.error(f"Message does not contain nonce or timestamp: {message}")
                return False

            logger.info("Attempting to recover address from signature...")
            w3 = Web3()
            message_hash = encode_defunct(text=message)
            recovered_address = w3.eth.account.recover_message(
                message_hash, signature=signature
            )
            logger.info(f"Recovered address: {recovered_address}")
            logger.info(f"Expected address: {eth_address}")

            result = recovered_address.lower() == eth_address.lower()
            if not result:
                logger.error(
                    "Verification failed: Recovered address does not match expected address"
                )
            else:
                logger.info("Signature verification successful!")
            return result
        except Exception as ex:
            logger.error(f"Verification failed with exception: {str(ex)}")
            logger.error(traceback.format_exc())
            return False
