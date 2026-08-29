"""Printing routes (names are stable, see docs/ARCHITECTURE.md; mounted under /admin/)."""

from django.urls import path

from . import views

app_name = "printing"

urlpatterns = [
    path("r/<int:pk>/print/", views.print_page, name="print_page"),
    path("r/<int:pk>/qr.svg", views.qr_svg, name="qr_svg"),
    path("r/<int:pk>/qr.png", views.qr_png, name="qr_png"),
    path("r/<int:pk>/print/stickers.pdf", views.stickers_pdf, name="stickers_pdf"),
    path("r/<int:pk>/print/tent.pdf", views.tent_pdf, name="tent_pdf"),
]
