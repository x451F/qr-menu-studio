"""Placeholder views; the URL names are stable (see docs/ARCHITECTURE.md)."""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.urls import path

app_name = "printing"


@login_required
def placeholder(request, pk):
    return HttpResponse("Printing not built yet", content_type="text/plain")


urlpatterns = [
    path("r/<int:pk>/print/", placeholder, name="print_page"),
    path("r/<int:pk>/qr.svg", placeholder, name="qr_svg"),
    path("r/<int:pk>/qr.png", placeholder, name="qr_png"),
    path("r/<int:pk>/print/stickers.pdf", placeholder, name="stickers_pdf"),
    path("r/<int:pk>/print/tent.pdf", placeholder, name="tent_pdf"),
]
