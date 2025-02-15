from rest_framework.response import Response
from rest_framework import status
from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from django.db import transaction
import logging
from drf_spectacular.utils import extend_schema
from django.db.models import Count, When, Case, IntegerField, Sum


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# CUSTOM CLASSES
from .abstract.abstract_view import (
    BaseForumView,
    BaseReplyView,
    BaseLikeView,
    BaseTransactionDip,
)
from .serializers import (
    ThreadSerializer,
    ThreadDetailSerializer,
    DipSerializer,
    DipRefreshSerializer,
    DipDetailSerializer,
    ReplySerializer,
    LikeSerializer,
    VoteSerializer,
    serializers,
)
from .models import Thread, Dip, DipStatus, Reply, Like, View, Vote


class BaseContentView(BaseForumView):

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        print(f"instance: {instance}")
        print(f"instance id: {instance.id}")
        print(f"user: {request.user}")
        content_type = ContentType.objects.get_for_model(instance)
        with transaction.atomic():
            # Only track views for authenticated users
            if request.user.is_authenticated:
                view, created = View.objects.get_or_create(
                    content_type=content_type,
                    object_id=instance.id,
                    user=request.user,
                )
                if created:
                    instance.views_count = F("views_count") + 1
                    instance.save()
                    instance.refresh_from_db()
            else:
                # For anonymous users, just increment the view count
                print(f"view not counted for anonymous user")
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        dao_slug = self.kwargs.get("slug")
        if not dao_slug:
            raise serializers.ValidationError("slug is required")

        serializer = self.get_serializer(
            data=request.data, context={"request": request, "slug": dao_slug}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["thread"])
class ThreadView(BaseContentView):
    """
    thread view includes operations: list, retrieve, create for dip model
    """

    def get_serializer_class(self):
        return ThreadDetailSerializer if self.action == "retrieve" else ThreadSerializer

    def get_queryset(self):
        dao_slug = self.kwargs.get("slug")
        print(f"dao slug: {dao_slug}")

        thread = Thread.objects.filter(dao__slug=dao_slug)
        return thread


@extend_schema(tags=["dip"])
class DipView(BaseContentView):
    """
    dip view includes operations: list, retrieve, create for dip model
    """

    def get_serializer_class(self):
        return DipDetailSerializer if self.action == "retrieve" else DipSerializer

    def get_queryset(self):
        dao_slug = self.kwargs.get("slug")

        return (
            Dip.objects.filter(dao__slug=dao_slug, status=DipStatus.ACTIVE)
            .annotate(
                for_votes=Count(
                    Case(
                        When(votes__support=True, then=1), output_field=IntegerField()
                    ),
                ),
                against_votes=Count(
                    Case(
                        When(votes__support=False, then=1), output_field=IntegerField()
                    )
                ),
            )
            .annotate(total_voting_power=Sum("votes__voting_power"))
            .order_by("-proposal_id")
        )


@extend_schema(tags=["refresh"])
class DipSyncronizationView(BaseTransactionDip):
    """dip view for refreshing and synchronizing database records and on-chain proposals"""

    serializer_class = DipRefreshSerializer
    queryset = Dip.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["slug"] = self.kwargs.get("slug")
        return context

    def create(self, request, *args, **kwargs):

        serializer = self.serializer_class(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(
            {"message": "sync started"},
            status=status.HTTP_200_OK,
        )


class BaseReplyContentView(BaseReplyView):
    """base view for replies to either Thread or Dip"""

    serializer_class = ReplySerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context_key = "thread_id" if self.model == Thread else "dip_id"
        context[context_key] = self.kwargs.get("id")
        return context

    def get_queryset(self):
        object_id = self.kwargs.get("id")
        return Reply.objects.filter(
            content_type=ContentType.objects.get_for_model(self.model),
            object_id=object_id,
        )

    def create(self, request, *args, **kwargs):
        object_id = self.kwargs.get("id")
        dao_slug = self.kwargs.get("slug")
        parent_obj = self.model.objects.get(id=object_id)
        if parent_obj.dao.slug != dao_slug:
            raise serializers.ValidationError("invalid dao slug for this content")
        serializer = self.get_serializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["thread"])
class ThreadReplyView(BaseReplyContentView):
    model = Thread


@extend_schema(tags=["dip"])
class DipReplyView(BaseReplyContentView):
    model = Dip


class BaseLikeContentView(BaseLikeView):
    """base view for likes on any content type"""

    serializer_class = LikeSerializer
    model = None

    def get_content_type(self):
        return ContentType.objects.get_for_model(self.model)

    def get_object_id(self):
        object_id = self.kwargs.get("id")
        obj = self.model.objects.filter(id=object_id).first()

        if hasattr(obj, "dao") and obj.dao.slug != self.kwargs.get("slug"):
            raise serializers.ValidationError("slugs do not match")
        return object_id

    def create(self, request, *args, **kwargs):
        content_type = self.get_content_type()
        object_id = self.get_object_id()
        like = Like.objects.filter(
            user=request.user,
            content_type=content_type,
            object_id=object_id,
        ).first()
        if like:
            like.delete()
            return Response(
                {
                    "status": "unliked",
                    "msg": f"removed like from: {self.model.__name__} {object_id}",
                },
                status=status.HTTP_200_OK,
            )
        else:
            like = Like.objects.create(
                user=request.user,
                content_type=content_type,
                object_id=object_id,
            )
            print(f"created new like {like}")
            serializer = self.get_serializer(like)
            # QUESTION
            # serializer.is_valid(raise_exception=True)
            return Response({"status": "liked"}, status=status.HTTP_201_CREATED)


@extend_schema(tags=["thread"])
class ThreadLikeView(BaseLikeContentView):
    model = Thread


@extend_schema(tags=["dip"])
class DipLikeView(BaseLikeContentView):
    model = Dip


@extend_schema(tags=["dynamic"])
class ReplyLikeView(BaseLikeContentView):
    model = Reply

    def get_object_id(self):
        reply_id = self.kwargs.get("reply_id")
        parent_id = self.kwargs.get("id")
        reply = Reply.objects.filter(id=reply_id).first()
        if reply.object_id != int(parent_id):
            raise serializers.ValidationError("ids do not match")
        return reply_id


@extend_schema(tags=["refresh"])
class VoteSynchronizationView(BaseTransactionDip):
    serializer_class = VoteSerializer
    queryset = Vote.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["id"] = self.kwargs.get("id")
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data,
            context=self.get_serializer_context(),
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"msg": "started sync process"}, status=status.HTTP_200_OK)
