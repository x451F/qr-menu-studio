import os

# Tests run with dev settings (insecure local secret key); see README.md.
os.environ.setdefault("DJANGO_DEBUG", "1")
