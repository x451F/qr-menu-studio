"""Placeholder views. URL names here are stable (see docs/ARCHITECTURE.md)."""

from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.urls import path

app_name = "editor"


@login_required
def placeholder(request, pk=None):
    return HttpResponse("Editor not built yet", content_type="text/plain")


urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", placeholder, name="dashboard"),
    path("r/new/", placeholder, name="restaurant_new"),
    path("r/<int:pk>/", placeholder, name="restaurant_edit"),
    path("r/<int:pk>/settings/", placeholder, name="restaurant_settings"),
]
