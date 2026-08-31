"""AI routes. URL names ``import``, ``translate`` and ``translate_missing`` are stable (docs/ARCHITECTURE.md)."""

from django.urls import path

from . import views

app_name = "ai"

urlpatterns = [
    path("r/<int:pk>/import/", views.import_upload, name="import"),
    path("r/<int:pk>/import/<int:draft_id>/", views.import_review, name="import_review"),
    path("r/<int:pk>/import/<int:draft_id>/discard/", views.import_discard, name="import_discard"),
    path("r/<int:pk>/translate-missing/", views.translate_missing, name="translate_missing"),
    path("ai/translate/", views.translate, name="translate"),
]
