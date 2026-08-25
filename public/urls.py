from django.urls import path

from . import views

app_name = "public"

urlpatterns = [
    path("<slug:slug>/", views.menu, name="menu"),
]
