from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.generic import RedirectView


def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("", RedirectView.as_view(url="/admin/", permanent=False)),
    path("healthz", healthz, name="healthz"),
    path("m/", include("public.urls")),
    path("admin/", include("printing.urls")),
    path("admin/", include("ai.urls")),
    path("admin/", include("editor.urls")),
    path("dj/", admin.site.urls),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
