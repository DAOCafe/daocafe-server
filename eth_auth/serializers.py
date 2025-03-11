"""serializers for user api"""

from rest_framework import serializers
from eth_utils import is_checksum_address
import time
import traceback
from django.core.cache import cache
from logging_config import logger
from .eth_authentication import NonceManager, SignatureVerifier


def validate_eth_address(eth_address: str) -> str:
    """helper method: validates eth address for API view"""
    logger.info(f"Validating Ethereum address: {eth_address}")
    
    if not is_checksum_address(eth_address):
        logger.error(f"Invalid Ethereum address format: {eth_address}")
        raise serializers.ValidationError("invalid eth address")

    normalized = eth_address.lower()
    logger.info(f"Address validated and normalized: {normalized}")
    return normalized


class NonceSerializer(serializers.Serializer):
    eth_address = serializers.CharField(max_length=42)

    def create(self, validated_data) -> dict:
        try:
            logger.info(f"Creating nonce for request data: {validated_data}")
            eth_address = validate_eth_address(validated_data["eth_address"])
            
            # Generate nonce using the NonceManager
            nonce = NonceManager.generate_nonce(eth_address)
            timestamp = int(time.time())
            
            # Prepare response
            response = {"nonce": nonce, "timestamp": timestamp}
            logger.info(f"Nonce created successfully: {response}")
            
            return response
        except Exception as ex:
            logger.error(f"Error creating nonce: {str(ex)}")
            logger.error(traceback.format_exc())
            raise serializers.ValidationError(f"Failed to create nonce: {str(ex)}")


class SignatureSerializer(serializers.Serializer):
    eth_address = serializers.CharField(max_length=42)
    signature = serializers.CharField()
    message = serializers.CharField()

    def validate(self, attrs):
        try:
            logger.info(f"Validating signature request: {attrs}")
            eth_address = attrs["eth_address"]
            message = attrs["message"]
            signature = attrs["signature"]

            # First validate the checksum format
            validate_eth_address(eth_address)

            # Then convert to lowercase for storage/comparison
            eth_address = eth_address.lower()
            logger.info(f"Normalized address: {eth_address}")

            # Check cache for stored nonce
            cache_key = f"{NonceManager.NONCE_PREFIX}{eth_address}"
            logger.info(f"Looking up cache key: {cache_key}")
            
            stored_data = cache.get(cache_key)
            logger.info(f"Retrieved from cache: {stored_data}")
            
            if not stored_data:
                logger.error(f"No nonce found in cache for address: {eth_address}")
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
                
                raise serializers.ValidationError("nonce not found or expired")

            if not isinstance(stored_data, tuple) or len(stored_data) != 2:
                logger.error(f"Invalid stored data format: {stored_data}")
                raise serializers.ValidationError("invalid nonce data format")
                
            stored_nonce, stored_timestamp = stored_data
            logger.info(f"Stored nonce: {stored_nonce}, timestamp: {stored_timestamp}")
            
            # Verify nonce
            if not NonceManager.verify_nonce(eth_address, stored_nonce):
                logger.error(f"Failed to verify nonce for address: {eth_address}")
                raise serializers.ValidationError("failed to verify nonce")

            # Verify signature
            if not SignatureVerifier.verify_ethereum_signature(
                message=message, signature=signature, eth_address=eth_address
            ):
                logger.error(f"Invalid signature for address: {eth_address}")
                raise serializers.ValidationError("invalid signature")

            logger.info(f"Signature validation successful for address: {eth_address}")
            attrs["eth_address"] = eth_address
            return attrs
        except serializers.ValidationError:
            # Re-raise validation errors
            raise
        except Exception as ex:
            logger.error(f"Unexpected error during signature validation: {str(ex)}")
            logger.error(traceback.format_exc())
            raise serializers.ValidationError(f"Signature validation error: {str(ex)}")
