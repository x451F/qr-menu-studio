# Security

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's **private vulnerability reporting**
(Security tab → "Report a vulnerability") and include steps to reproduce. You will get an answer
within a few days.

## What the application does

**Secrets and configuration**
- All secrets come from environment variables (`.env`, never committed). `.env.example` contains
  placeholders only.
- With `DEBUG` off an empty `DJANGO_SECRET_KEY` is a fatal error, and the container refuses to
  start an `https://` deployment that still uses the local demo or placeholder secret key or
  admin password.
- The Anthropic API key is read from the environment only and never logged.

**Admin**
- Single staff account; every admin view requires a logged-in staff user.
- Login is throttled per client IP (10 failures lock the IP for 15 minutes).
- Django password validators, CSRF protection on every form and HTMX request, `HttpOnly` and
  `SameSite=Lax` session cookies, `Secure` cookies behind HTTPS.
- `X-Robots-Tag: noindex` on all admin pages.

**Public menu**
- Content-Security-Policy (`default-src 'self'`, `frame-ancestors 'self'`, `base-uri 'none'`,
  `form-action 'self'`), Permissions-Policy, `nosniff`, `Referrer-Policy`.
- No cookies except an optional language preference; no third-party requests or trackers.
- Unpublished restaurants return 404 to everyone except the admin.

**Uploads**
- Images are decoded and re-encoded with Pillow (EXIF rotation, metadata stripped), with size and
  pixel-count limits and decompression bombs treated as errors. Only the re-encoded files are
  stored and served.

**Transport and hosting**
- Caddy obtains HTTPS certificates automatically and sends HSTS on HTTPS requests.
- Caddy mounts the data volume read-only and serves uploaded media as
  static files.

## Supported versions

Only the latest `main` branch receives fixes.
