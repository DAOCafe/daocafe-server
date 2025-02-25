from django.urls import path

from .views import DaoInitialView, DaoCompleteView, ActiveDaosView

app_name = "dao"

urlpatterns = [
    path("/", ActiveDaosView.as_view({"get": "list"}), name="daos-list"),
    path("-fetch/", DaoInitialView.as_view({"post": "create"}), name="dao-fetch"),
    path("-save/", DaoCompleteView.as_view({"patch": "update"}), name="dao-save"),
    path(
        "/<slug:slug>/info/",
        ActiveDaosView.as_view({"get": "retrieve"}),
        name="daos-retrieve",
    ),
]
