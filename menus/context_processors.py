from django.conf import settings


def app_flags(request):
    return {"AI_ENABLED": settings.AI_ENABLED, "PUBLIC_BASE_URL": settings.PUBLIC_BASE_URL}
