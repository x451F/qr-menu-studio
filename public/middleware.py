"""Security headers.

Add to ``MIDDLEWARE`` right after ``django.middleware.security.SecurityMiddleware``:

    "public.middleware.SecurityHeadersMiddleware",

* ``/m/...`` (public menus): Content-Security-Policy compatible with the inline CSS/JS the page
  ships, Permissions-Policy, nosniff. ``frame-ancestors 'self'`` still lets the editor embed the
  page in its live-preview iframe.
* ``/admin/...`` and ``/dj/...``: ``X-Robots-Tag: noindex``.
* Preview requests (``?preview=1``) are never indexed either.
"""

CSP = (
    "default-src 'self'; "
    "img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self' 'unsafe-inline'; "
    "font-src 'self'; "
    "frame-ancestors 'self'; "
    "base-uri 'none'; "
    "form-action 'self'"
)
PERMISSIONS_POLICY = (
    "camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
    "accelerometer=(), gyroscope=(), magnetometer=(), interest-cohort=()"
)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        path = request.path
        if path.startswith("/m/"):
            response.setdefault("Content-Security-Policy", CSP)
            response.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
            response.setdefault("X-Content-Type-Options", "nosniff")
            if request.GET.get("preview") == "1":
                response.setdefault("X-Robots-Tag", "noindex, nofollow")
        elif path.startswith(("/admin/", "/dj/")) or path in ("/admin", "/dj"):
            response.setdefault("X-Robots-Tag", "noindex, nofollow")
            response.setdefault("X-Content-Type-Options", "nosniff")
        return response
