"""Image processing for uploaded photos and logos."""

from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

PHOTO_MAX = 1600
LOGO_MAX = 512


def process_photo(file, name: str = "photo.jpg") -> ContentFile:
    img = Image.open(file)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    img.thumbnail((PHOTO_MAX, PHOTO_MAX), Image.Resampling.LANCZOS)
    out = BytesIO()
    img.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    stem = name.rsplit(".", 1)[0][:40] or "photo"
    return ContentFile(out.getvalue(), name=f"{stem}.jpg")


def process_logo(file, name: str = "logo.png") -> ContentFile:
    img = Image.open(file)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGBA")
    img.thumbnail((LOGO_MAX, LOGO_MAX), Image.Resampling.LANCZOS)
    out = BytesIO()
    img.save(out, "PNG", optimize=True)
    stem = name.rsplit(".", 1)[0][:40] or "logo"
    return ContentFile(out.getvalue(), name=f"{stem}.png")


def photo_view(field_file) -> dict | None:
    """Return {"src", "srcset", "width", "height"} for templates, or None."""
    if not field_file:
        return None
    try:
        return {"src": field_file.url, "srcset": "", "width": field_file.width, "height": field_file.height}
    except (OSError, ValueError):
        return None
