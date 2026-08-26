"""Editor URL names (dashboard, restaurant_new, restaurant_edit, restaurant_settings, login, logout
are stable, see docs/ARCHITECTURE.md; the rest are HTMX endpoints private to this app)."""

from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views_menu as m
from . import views_restaurant as r
from .auth import ThrottledLoginView, staff_required

app_name = "editor"

urlpatterns = [
    path("login/", ThrottledLoginView.as_view(), name="login"),
    path("logout/", staff_required(LogoutView.as_view()), name="logout"),
    path("", r.dashboard, name="dashboard"),
    path("r/new/", r.restaurant_new, name="restaurant_new"),
    path("r/<int:pk>/", m.restaurant_edit, name="restaurant_edit"),
    path("r/<int:pk>/settings/", r.restaurant_settings, name="restaurant_settings"),
    path("r/<int:pk>/publish/", r.restaurant_publish, name="restaurant_publish"),
    path("r/<int:pk>/logo/", r.restaurant_logo, name="restaurant_logo"),
    # categories
    path("r/<int:pk>/categories/add/", m.category_add, name="category_add"),
    path("categories/<int:pk>/", m.category_update, name="category_update"),
    path("categories/<int:pk>/toggle/", m.category_toggle, name="category_toggle"),
    path("categories/<int:pk>/delete/", m.category_delete, name="category_delete"),
    path("categories/<int:pk>/items/add/", m.item_add, name="item_add"),
    # items
    path("items/<int:pk>/", m.item_update, name="item_update"),
    path("items/<int:pk>/toggle/<str:field>/", m.item_toggle, name="item_toggle"),
    path("items/<int:pk>/duplicate/", m.item_duplicate, name="item_duplicate"),
    path("items/<int:pk>/delete/", m.item_delete, name="item_delete"),
    path("items/<int:pk>/photo/", m.item_photo, name="item_photo"),
    path("r/<int:pk>/items/undo/", m.item_undo, name="item_undo"),
    # specials
    path("r/<int:pk>/specials/add/<str:kind>/", m.special_add, name="special_add"),
    path("specials/<int:pk>/", m.special_update, name="special_update"),
    path("specials/<int:pk>/toggle/", m.special_toggle, name="special_toggle"),
    path("specials/<int:pk>/delete/", m.special_delete, name="special_delete"),
    # ordering
    path("r/<int:pk>/reorder/categories/", m.reorder_categories, name="reorder_categories"),
    path("r/<int:pk>/reorder/items/", m.reorder_items, name="reorder_items"),
    path("r/<int:pk>/reorder/specials/", m.reorder_specials, name="reorder_specials"),
]
