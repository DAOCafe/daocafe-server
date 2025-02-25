# from rest_framework.response import Response
# from rest_framework import status
from drf_spectacular.utils import extend_schema

# CUSTOM MODULES
from .models import Dao, Stake
from .serializers import (
    DaoInitialSerializer,
    StakeSerializer,
    DaoCompleteSerializer,
    DaoActiveSerializer,
)
from .packages.abstract.abstract_views import (
    BaseDaoView,
    PublicBaseDaoView,
)
from django.db.models import When, Case, Sum, Count, F
from logging_config import logger
from drf_spectacular.utils import extend_schema, OpenApiParameter

######################## VIEWS ########################


# DAO CREATION/DEPLOYMENT


@extend_schema(tags=["dao"])
class DaoInitialView(BaseDaoView):
    """view for managing user's DAOs
    supports: list, retrieve, create for authenticated users
    """

    serializer_class = DaoInitialSerializer

    def get_queryset(self):
        return Dao.objects.filter(owner=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        context["network"] = self.request.data.get("network")
        return context


@extend_schema(tags=["refresh"])
class StakeView(BaseDaoView):
    serializer_class = StakeSerializer

    def paginate_queryset(self, queryset):
        dao_id = self.request.GET.get("id")
        slug = self.request.GET.get("slug")

        if dao_id or slug:
            return None
        return super().paginate_queryset(queryset)

    def get_queryset(self):
        dao_id = self.request.GET.get("id")
        slug = self.request.GET.get("slug")

        logger.debug(f"dao_id: {dao_id}\ndao_slug: {slug}")

        queryset = Stake.objects.all()
        if dao_id:
            queryset = queryset.filter(dao__id=dao_id)
        elif slug:
            queryset = queryset.filter(dao__slug=slug)
        return queryset.order_by("-amount")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method == "POST":
            # For POST: Get params from request body
            context["dao_id"] = self.request.data.get("id")
            context["slug"] = self.request.data.get("dao_slug")
        else:
            # For GET: Get params from query string
            context["dao_id"] = self.request.GET.get("id")
            context["slug"] = self.request.GET.get("slug")
        context["user"] = self.request.user
        return context

    @extend_schema(
        parameters=[
            OpenApiParameter(name="id", type=int, description="filter by id"),
            OpenApiParameter(name="slug", type=str, description="filter by slug"),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@extend_schema(tags=["dao"])
class DaoCompleteView(BaseDaoView):
    serializer_class = DaoCompleteSerializer
    queryset = Dao.objects.all()

    def get_object(self):
        dao_id = self.request.data.get("id")
        return Dao.objects.get(id=dao_id)


# RETRIEVE ACTIVE DAOS REQUIRES NO AUTH
@extend_schema(tags=["dao"])
class ActiveDaosView(PublicBaseDaoView):
    """
    view for public access to active DAOs
    supports: list, retrieve for all users
    """

    serializer_class = DaoActiveSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Dao.objects.filter(is_active=True).annotate(
            staker_count=Count("dao_stakers"),
            total_staked=Sum("dao_stakers__amount"),
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
