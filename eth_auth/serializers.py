"""serializers for user api"""

from rest_framework import serializers
from eth_utils import is_checksum_address
import time
from django.core.cache import cache
from .eth_authentication import NonceManager, SignatureVerifier


def validate_eth_address(eth_address: str) -> str:
    """helper method: validates eth address for API view"""

    if not is_checksum_address(eth_address):
        raise serializers.ValidationError("invalid eth address")

    return eth_address.lower()


class NonceSerializer(serializers.Serializer):
    eth_address = serializers.CharField(max_length=42)

    def create(self, validated_data) -> dict:
        eth_address = validate_eth_address(validated_data["eth_address"])
        nonce = NonceManager.generate_nonce(eth_address)
        timestamp = int(time.time())
        response = {"nonce": nonce, "timestamp": timestamp}
        return response


class SignatureSerializer(serializers.Serializer):
    eth_address = serializers.CharField(max_length=42)
    signature = serializers.CharField()
    message = serializers.CharField()

    def validate(self, attrs):
        eth_address = attrs["eth_address"]
        message = attrs["message"]
        signature = attrs["signature"]

        # First validate the checksum format
        validate_eth_address(eth_address)

        # Then convert to lowercase for storage/comparison
        eth_address = eth_address.lower()

        cache_key = f"{NonceManager.NONCE_PREFIX}{eth_address}"
        stored_data = cache.get(cache_key)
        if not stored_data:
            raise serializers.ValidationError("nonce not found or expired")

        stored_nonce, stored_timestamp = stored_data
        try:
            if not NonceManager.verify_nonce(eth_address, stored_nonce):
                raise serializers.ValidationError("failed to verify nonce")

            if not SignatureVerifier.verify_ethereum_signature(
                message=message, signature=signature, eth_address=eth_address
            ):
                raise serializers.ValidationError("invalid signature")

            attrs["eth_address"] = eth_address
            return attrs
        except Exception as ex:
            raise serializers.ValidationError(str(ex))
