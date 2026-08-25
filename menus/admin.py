from django.contrib import admin

from .models import Category, DailySpecial, Item, Restaurant


class CategoryInline(admin.TabularInline):
    model = Category
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "theme", "is_published", "updated_at")
    inlines = [CategoryInline]


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("__str__", "category", "is_sold_out", "is_visible")
    list_filter = ("category__restaurant",)


admin.site.register(Category)
admin.site.register(DailySpecial)
