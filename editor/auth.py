"""Authentication helpers: staff-only decorator and a throttled login view."""

from functools import wraps

from django.contrib.auth.views import LoginView, redirect_to_login
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse

LOCK_AFTER = 10  # failed attempts per IP
LOCK_SECONDS = 15 * 60


def client_ip(request) -> str:
    """Caddy appends the real client address as the last X-Forwarded-For entry."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _fail_key(request) -> str:
    return f"editor:login-fail:{client_ip(request)}"


def is_locked(request) -> bool:
    return cache.get(_fail_key(request), 0) >= LOCK_AFTER


def record_failure(request) -> int:
    key = _fail_key(request)
    cache.add(key, 0, LOCK_SECONDS)
    try:
        count = cache.incr(key)
    except ValueError:
        count = 1
        cache.set(key, 1, LOCK_SECONDS)
    if count >= LOCK_AFTER:
        cache.set(key, count, LOCK_SECONDS)  # lock window starts at the last failure
    return count


def clear_failures(request) -> None:
    cache.delete(_fail_key(request))


def staff_required(view):
    """Login + staff. HTMX callers get 401 + HX-Redirect instead of a swapped login page."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not (user.is_authenticated and user.is_active):
            login_url = reverse("editor:login")
            if request.headers.get("HX-Request"):
                response = HttpResponse("Login required", status=401)
                response["HX-Redirect"] = login_url
                return response
            return redirect_to_login(request.get_full_path(), login_url)
        if not user.is_staff:
            return HttpResponseForbidden("Staff only")
        return view(request, *args, **kwargs)

    return wrapper


class ThrottledLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = False

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_staff and request.method == "GET":
            return redirect("editor:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if is_locked(request):
            form = self.get_form()
            form.full_clean()
            response = self.render_to_response(self.get_context_data(form=form, locked=True))
            response.status_code = 429
            return response
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        clear_failures(self.request)
        return super().form_valid(form)

    def form_invalid(self, form):
        count = record_failure(self.request)
        return self.render_to_response(self.get_context_data(form=form, locked=count >= LOCK_AFTER))
