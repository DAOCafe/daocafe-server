from rest_framework import serializers
from eth_utils import is_checksum_address

# CUSTOM MODULES
from core.validators.eth_network_validator import validate_network
from .models import Dao, Contract, Stake
from .packages.services.dao_service import DaoService
from .packages.services.stake_service import StakeService
from services.blockchain.dao_service import DaoConfirmationService
from django.forms.models import model_to_dict
from django.db.models import Sum
from logging_config import logger

# DAO/DAO DEPLOYMENT SERIALIZERS


class DaoInitialSerializer(serializers.ModelSerializer):
    """first stage of creating dao with dao address passed fetches associated with dao addresses for rest of the contracts"""

    network = serializers.IntegerField(validators=[validate_network])
    initial_data = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dao_service = DaoService()

    class Meta:
        model = Contract
        fields = [
            "dao_address",
            "token_address",
            "treasury_address",
            "staking_address",
            "network",
            "initial_data",
        ]
        read_only_fields = [
            "token_address",
            "treasury_address",
            "staking_address",
            "initial_data",
        ]

    def get_initial_data(self, obj):
        return {
            "dao_id": obj.dao.id,
            "dao_name": obj.dao.dao_name,
            "token_name": obj.dao.token_name,
            "symbol": obj.dao.symbol,
            "version": obj.dao.version,
        }

    def create(self, validated_data):
        blockchain_service = DaoConfirmationService(
            dao_address=validated_data["dao_address"], network=validated_data["network"]
        )

        data_from_chain = blockchain_service._get_initial_data()
        data_from_chain["network"] = validated_data["network"]
        logger.info(f"user {self.context['request'].user.eth_address}")
        logger.info(f"data from chain: {data_from_chain['sender']}")
        contracts = self.dao_service.instanciate_dao_and_contracts(
            user=self.context["request"].user,
            chain_data=data_from_chain,
        )

        return contracts


class StakeSerializer(serializers.ModelSerializer):
    dao_slug = serializers.CharField(max_length=10, required=False)
    id = serializers.IntegerField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stake_service = StakeService()

    class Meta:
        model = Stake
        fields = [
            "id",
            "dao_slug",
            "amount",
            "user",
            "dao",
        ]
        read_only_fields = ["amount", "user", "dao"]

    def validate_amount(self, value):
        if isinstance(value, int):
            value = float(value)
        return value

    def create(self, validated_data):
        dao_id = self.context.get("dao_id")
        slug = self.context.get("slug")

        if not dao_id and not slug:
            raise serializers.ValidationError("either dao_id or slug must be provided")

        stake = self.stake_service.create_stake_instance(
            dao_id=dao_id if dao_id else None,
            slug=slug if slug else None,
            user=self.context.get("user"),
        )
        return stake

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.pop("dao", None)
        user = instance.user
        representation["user"] = user.nickname
        representation["eth_address"] = user.eth_address
        representation["image"] = user.image.url if user.image else None
        return representation


class DaoCompleteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = Dao
        fields = [
            "id",
            "dao_image",
            "cover_image",
            "slug",
            "socials",
            "description",
            "is_active",
        ]
        read_only_fields = ["is_active"]

    def validate_slug(self, value):
        import re

        if self.instance and value in [None, ""]:
            raise serializers.ValidationError("slug is required when updating")
        if value:
            value = value.lower()
            if not re.match(r"^[a-z0-9-]+$", value):
                raise serializers.ValidationError(
                    "slug can only contain lowercase letters, numbers and hyphens"
                )
        return value

    def validate_socials(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError(
                "Socials must be a valid JSON object (dict)."
            )
        return data

    def update(self, instance, validated_data):
        stake_service = StakeService()
        if not stake_service.has_staked_amount(
            user=self.context["request"].user, dao=instance
        ):
            raise serializers.ValidationError(
                "user must have staked amount greater than 0"
            )

        instance.is_active = True

        for attr, value in validated_data.items():
            if attr == "slug":
                if instance.slug not in [None, ""]:
                    logger.critical("written slug is immutable ")
                    raise ValueError("written slug is immutable")
            setattr(instance, attr, value)

        instance.save()

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        for key in [
            "is_active",
            "cover_image",
            "dao_image",
            "socials",
            "description",
        ]:
            representation.pop(key, None)

        return representation


class DaoActiveSerializer(serializers.ModelSerializer):
    contracts = serializers.SerializerMethodField()
    stake = serializers.SerializerMethodField()
    user_stake = serializers.SerializerMethodField()

    class Meta:
        model = Dao
        fields = [
            "dao_name",
            "owner",
            "slug",
            "description",
            "dao_image",
            "cover_image",
            "socials",
            "created_at",
            "updated_at",
            "dip_count",
            "token_name",
            "network",
            "symbol",
            "total_supply",
            "version",
            "contracts",
            "stake",
            "user_stake",
        ]
        read_only_fields = fields

    def get_contracts(self, obj):
        return [
            {
                "dao_address": contract.dao_address,
                "token_address": contract.token_address,
                "treasury_address": contract.treasury_address,
                "staking_address": contract.staking_address,
            }
            for contract in obj.contracts
        ]

    def get_stake(self, obj):
        return {
            "staker_count": str(obj.staker_count),
            "total_staked": str(obj.total_staked)
        }

    def get_user_stake(self, obj):
        request = self.context["request"]
        if request and request.user.is_authenticated:
            stake = obj.dao_stakers.filter(user=request.user).first()
            if stake:
                return {
                    "has_staked": str(stake.amount),
                    "voting_power": str(stake.voting_power)
                }
        return {
            "has_staked": "0",
            "voting_power": "0"
        }

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        view = self.context.get("view")
        if view and view.action == "list":
            [
                representation.pop(key)
                for key in [
                    "contracts",
                    "description",
                    "created_at",
                    "updated_at",
                    "total_supply",
                    "version",
                    "token_name",
                    "owner",
                    "socials",
                    "cover_image",
                ]
            ]

        # Ensure total_supply is a string
        if "total_supply" in representation:
            representation["total_supply"] = str(representation["total_supply"])

        return representation
