from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from services.blockchain.dip_sync_service import (
    DipSyncronizationService,
)
from .models import Dip, Thread, Reply, Like, Vote
from dao.models import Dao, Contract
from .abstract.abstract_models import DipStatus
from user.serializers import UserSerializer
from django.shortcuts import get_object_or_404
from logging_config import logger
from .services.vote_service import VoteService
from .abstract.abstract_models import ProposalType


class LexicalContentValidator:
    def __call__(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Content must be a JSON object")
        if "root" not in value:
            raise serializers.ValidationError("Content must have a root node")
        if "children" not in value["root"]:
            raise serializers.ValidationError("Root must have children")
        # Basic structure validation - can be expanded based on needs
        if not isinstance(value["root"]["children"], list):
            raise serializers.ValidationError("Children must be an array")


class BaseForumSerializer(serializers.ModelSerializer):
    """base serializer for thread dip fields"""

    author = UserSerializer(read_only=True)
    replies_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    content = serializers.JSONField(validators=[LexicalContentValidator()])

    class Meta:
        abstract = True
        fields = [
            "id",
            "title",
            "content",
            "created_at",
            "updated_at",
            "views_count",
            "replies_count",
            "likes_count",
            "is_liked",
            "author",
            "dao",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "views_count",
            "author",
            "dao",
            "replies_count",
        ]

    def get_replies_count(self, obj) -> int:
        return obj.replies.count()

    def get_likes_count(self, obj) -> int:
        return obj.likes.count()

    def get_is_liked(self, obj) -> bool:
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def validate(self, attrs):
        dao = Dao.objects.filter(slug=self.context.get("slug")).first()
        if not dao:
            raise serializers.ValidationError("dao not found")
        if not dao.is_active:
            raise serializers.ValidationError("dao is not active")
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        dao = Dao.objects.get(slug=self.context["slug"])
        if dao.is_active and request.user.is_authenticated:
            return self.Meta.model.objects.create(
                author=request.user, dao=dao, **validated_data
            )
        return False

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        view = self.context.get("view")
        if view and view.action == "list":
            representation.pop("content")
        return representation


class ReplySerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    content = serializers.JSONField(validators=[LexicalContentValidator()])

    class Meta:
        model = Reply
        fields = ["id", "content", "author", "created_at", "likes_count", "is_liked"]
        read_only_fields = ["id", "author", "created_at"]

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def _get_parent_object(self):
        """helper method to get parent Thread or Dip object"""
        thread_id = self.context.get("thread_id")
        dip_id = self.context.get("dip_id")
        if thread_id:
            return Thread.objects.get(id=thread_id)
        if dip_id:
            return Dip.objects.get(id=dip_id)
        raise serializers.ValidationError("either thead_id or dip_id is required")

    def create(self, validated_data):
        try:
            with transaction.atomic():
                parent_obj = self._get_parent_object()
                content_type = ContentType.objects.get_for_model(parent_obj)

                reply = Reply.objects.create(
                    content_type=content_type,
                    object_id=parent_obj.id,
                    author=self.context["request"].user,
                    **validated_data,
                )
                return reply
        except Exception as ex:
            raise serializers.ValidationError(str(ex))


class ThreadSerializer(BaseForumSerializer):
    class Meta(BaseForumSerializer.Meta):
        model = Thread


class ThreadDetailSerializer(ThreadSerializer):
    replies = ReplySerializer(many=True, read_only=True)

    class Meta(ThreadSerializer.Meta):
        fields = ThreadSerializer.Meta.fields + ["replies"]


class DipSerializer(BaseForumSerializer):
    proposal_data = serializers.JSONField(required=True)
    proposal_type = serializers.CharField()
    total_votes = serializers.IntegerField(source="total_voting_power", read_only=True)

    class Meta(BaseForumSerializer.Meta):
        model = Dip
        fields = [
            "id",
            "status",
            "proposal_type",
            "end_time",
            "proposal_id",
            "proposal_data",
            "content",
            "title",
            "author",
            "created_at",
            "updated_at",
            "views_count",
            "replies_count",
            "likes_count",
            "is_liked",
            "dao",
            "total_votes",
        ]
        read_only_fields = [
            "id",
            "status",
            "proposal_id",
            "end_time",
            "created_at",
            "updated_at",
            "views_count",
            "author",
            "dao",
            "replies_count",
            "likes_count",
            "is_liked",
        ]

    def validate_proposal_type(self, value):
        if value == "Transfer":
            value = "0"
        return value

    def validate(self, data):
        logger.debug(f"data from validate in serializer: {data}")

        amount = data.get("proposal_data", {}).get("amount")
        amount = int(amount) * 10**18

        if amount is not None:
            data["proposal_data"]["amount"] = amount
        if "proposal_type" in data and data["proposal_type"] == "Transfer":
            data["proposal_type"] = "0"

        return data

    def to_representation(self, instance):

        representation = super().to_representation(instance)
        representation["proposal_type"] = ProposalType(instance.proposal_type).label
        if representation.get("status") == DipStatus.DRAFT:
            representation.pop("status", None)
        if not isinstance(representation.get("proposal_id"), int):
            representation.pop("proposal_id", None)
        representation.pop("dao")

        proposal_data = representation["proposal_data"]
        proposal_data["for_votes"] = getattr(instance, "for_votes", 0)
        proposal_data["against_votes"] = getattr(instance, "against_votes", 0)
        representation["proposal_data"] = proposal_data
        return representation


class DipRefreshSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dip
        fields = [
            "status",
            "proposal_id",
            "proposal_data",
            "end_time",
            "proposal_type",
            "dao",
        ]
        read_only_fields = [
            "status",
            "proposal_id",
            "proposal_data",
            "proposal_type",
            "end_time",
            "dao",
        ]

    def validate(self, data):
        slug = self.context.get("slug")
        try:
            dao = Dao.objects.get(slug=slug)
            dao_contract = Contract.objects.filter(dao=dao).first()
            data["dao"] = dao
            data["contract"] = dao_contract
            return data
        except Dao.DoesNotExist:
            raise serializers.ValidationError("dao with the given slug does not exist")

    def create(self, validated_data):

        sync_service = DipSyncronizationService(validated_data["contract"])
        try:
            result = sync_service.start_blockchain_sync(validated_data["dao"])
            return result

        except Exception as ex:
            logger.info(f"error: {str(ex)}")
            raise serializers.ValidationError(
                f"failed to synchronize blockchain data with database records: {str(ex)}"
            )


class DipDetailSerializer(DipSerializer):
    replies = ReplySerializer(many=True, read_only=True)

    class Meta(DipSerializer.Meta):
        fields = DipSerializer.Meta.fields + ["replies"]


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ["id", "user", "content_type", "object_id"]
        read_only_fields = ["id", "user", "content_type", "object_id"]


class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ["id", "support", "dip", "user"]
        read_only_fields = ["id", "support", "dip", "user"]

    def validate(self, data):
        dip = get_object_or_404(Dip, id=self.context["id"])
        logger.info(f"dip: {dip}")
        if not dip or not dip.status == DipStatus.ACTIVE:
            raise serializers.ValidationError("dip cannot be casted vote on")
        data["dip"] = dip
        return data

    def validate_support(self, value):
        if not value:
            raise serializers.ValidationError("no vote provided")
        if not isinstance(value, bool):
            raise serializers.ValidationError("vote must be of bool type")
        return value

    def create(self, validated_data):
        logger.critical("reached create")
        votes = VoteService().create_vote_instance(dip=validated_data["dip"])
        logger.debug(f"votes: {votes}")

        return votes


class VotingHistorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Vote
        fields = "__all__"
        read_only_fields = fields
