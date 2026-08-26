"""Placeholder views; the URL names are stable (see docs/ARCHITECTURE.md)."""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.urls import path

app_name = "ai"


@login_required
def placeholder(request, pk=None):
    return HttpResponse("AI import not built yet", content_type="text/plain")


@login_required
def translate_placeholder(request):
    return JsonResponse({"error": "AI translation not built yet"}, status=503)


urlpatterns = [
    path("r/<int:pk>/import/", placeholder, name="import"),
    path("r/<int:pk>/translate-missing/", placeholder, name="translate_missing"),
    path("ai/translate/", translate_placeholder, name="translate"),
]
