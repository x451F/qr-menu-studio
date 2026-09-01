"""Image pipeline: upload normalisation, WebP variants, cleanup.

Public contract (used by the editor and the seed command):
    process_photo(file, name)  -> ContentFile   JPEG, <= 1600 px, EXIF-rotated, metadata stripped
    process_logo(file, name)   -> ContentFile   PNG with alpha, <= 512 px
    photo_view(field_file)     -> dict | None   {"src", "srcset", "width", "height"}
    ensure_variants(field_file)                 create the WebP variants next to the stored file
    delete_with_variants(storage, name)         remove a stored photo and its variants

Variants live next to the original: ``photos/3/abc.jpg`` -> ``photos/3/abc.480.webp``,
``photos/3/abc.960.webp``. They are created on Item save (see signals.py) and lazily by
``photo_view`` when missing. Variants are never upscaled.
"""

import logging
import warnings
from io import BytesIO

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageFile, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

PHOTO_MAX = 1600
LOGO_MAX = 512
VARIANT_WIDTHS = (480, 960)
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_PIXELS = 60_000_000  # ~ 7750 x 7750; anything bigger is refused (decompression bombs)
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF", "MPO", "BMP", "TIFF"}

_DIMS_TTL = 60 * 60 * 24


# ---------------------------------------------------------------------------------------
# Upload validation / normalisation
# ---------------------------------------------------------------------------------------
def _upload_size(file) -> int | None:
    size = getattr(file, "size", None)
    if size is not None:
        return size
    try:
        pos = file.tell()
        file.seek(0, 2)
        size = file.tell()
        file.seek(pos)
        return size
    except (AttributeError, OSError, ValueError):
        return None


def _open_image(file) -> Image.Image:
    """Open and fully decode an upload, raising ValidationError with a friendly message."""
    size = _upload_size(file)
    if size is not None and size > MAX_UPLOAD_BYTES:
        raise ValidationError(
            f"This image is too large ({size / 1024 / 1024:.0f} MB). The maximum is "
            f"{MAX_UPLOAD_BYTES // 1024 // 1024} MB."
        )
    if hasattr(file, "seek"):
        file.seek(0)
    # WeasyPrint sets the global ImageFile.LOAD_TRUNCATED_IMAGES = True on import; uploads must
    # still be fully decodable, so force strict loading here (sync gunicorn workers: no races).
    previous_truncated = ImageFile.LOAD_TRUNCATED_IMAGES
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(file)
            if img.format not in ALLOWED_FORMATS:
                raise ValidationError("Unsupported image type. Please upload a JPEG, PNG or WebP file.")
            if img.width * img.height > MAX_PIXELS:
                raise ValidationError("This image has too many pixels. Please upload a smaller picture.")
            img.load()
    except ValidationError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError("This image has too many pixels. Please upload a smaller picture.") from None
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, EOFError):
        raise ValidationError("This file is not a valid image. Please upload a JPEG, PNG or WebP file.") from None
    finally:
        ImageFile.LOAD_TRUNCATED_IMAGES = previous_truncated
    return img


def _flatten_to_rgb(img: Image.Image) -> Image.Image:
    """Convert to RGB; transparent areas become white (JPEG has no alpha)."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(background, rgba).convert("RGB")
    if img.mode in ("I;16", "I;16L", "I;16B", "I"):
        img = img.point(lambda v: v / 256).convert("L")
    return img.convert("RGB")


def _stem(name: str, default: str) -> str:
    base = name.rsplit("/", 1)[-1]
    stem = base.rsplit(".", 1)[0] if "." in base else base
    return stem[:40] or default


def process_photo(file, name: str = "photo.jpg") -> ContentFile:
    img = _open_image(file)
    img = ImageOps.exif_transpose(img)
    img = _flatten_to_rgb(img)
    img.thumbnail((PHOTO_MAX, PHOTO_MAX), Image.Resampling.LANCZOS)
    out = BytesIO()
    # No exif/icc passed -> metadata (incl. GPS) is stripped.
    img.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    return ContentFile(out.getvalue(), name=f"{_stem(name, 'photo')}.jpg")


def process_logo(file, name: str = "logo.png") -> ContentFile:
    img = _open_image(file)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGBA")
    img.thumbnail((LOGO_MAX, LOGO_MAX), Image.Resampling.LANCZOS)
    out = BytesIO()
    img.save(out, "PNG", optimize=True)
    return ContentFile(out.getvalue(), name=f"{_stem(name, 'logo')}.png")


# ---------------------------------------------------------------------------------------
# WebP variants
# ---------------------------------------------------------------------------------------
def variant_name(name: str, width: int) -> str:
    """photos/3/abc.jpg -> photos/3/abc.480.webp"""
    base = name.rsplit(".", 1)[0] if "." in name.rsplit("/", 1)[-1] else name
    return f"{base}.{width}.webp"


def _variant_names(name: str) -> list[str]:
    return [variant_name(name, w) for w in VARIANT_WIDTHS]


def ensure_variants(field_file, *, force: bool = False) -> bool:
    """Create missing WebP variants for a stored photo. Returns True when all exist afterwards."""
    if not field_file:
        return False
    storage = field_file.storage
    name = field_file.name
    missing = [
        (w, variant_name(name, w))
        for w in VARIANT_WIDTHS
        if force or not storage.exists(variant_name(name, w))
    ]
    if not missing:
        return True
    try:
        with storage.open(name, "rb") as fh:
            img = Image.open(fh)
            img.load()
        img = ImageOps.exif_transpose(img)
        img = _flatten_to_rgb(img)
        for width, vname in missing:
            copy = img.copy()
            if copy.width > width:  # never upscale
                copy.thumbnail((width, 10_000), Image.Resampling.LANCZOS)
            out = BytesIO()
            copy.save(out, "WEBP", quality=78, method=4)
            if storage.exists(vname):
                storage.delete(vname)
            storage.save(vname, ContentFile(out.getvalue()))
    except Exception:  # never break a save/render because of a variant
        logger.exception("Could not create WebP variants for %s", name)
        return False
    return True


def delete_with_variants(storage, name: str, *, variants: bool = True) -> None:
    """Delete a stored file and (optionally) its WebP variants; missing files are ignored."""
    if not name:
        return
    names = [name] + (_variant_names(name) if variants else [])
    for n in names:
        try:
            storage.delete(n)
        except OSError:
            logger.warning("Could not delete %s", n, exc_info=True)
    cache.delete_many([f"imgdims:{name}", f"imgvar:{name}"])


def _dimensions(field_file) -> tuple[int, int] | None:
    key = f"imgdims:{field_file.name}"
    dims = cache.get(key)
    if dims is None:
        try:
            with field_file.storage.open(field_file.name, "rb") as fh:
                with Image.open(fh) as img:
                    dims = img.size
        except (OSError, ValueError, UnidentifiedImageError):
            return None
        cache.set(key, dims, _DIMS_TTL)
    return dims


def photo_view(field_file) -> dict | None:
    """Return {"src", "srcset", "width", "height"} for templates, or None.

    src is the largest WebP variant; srcset lists both variants with width descriptors.
    Falls back to the original file (empty srcset) if variants cannot be produced.
    """
    if not field_file:
        return None
    name = field_file.name
    dims = _dimensions(field_file)
    if dims is None:
        return None
    orig_w, orig_h = dims
    try:
        if not cache.get(f"imgvar:{name}"):
            if not ensure_variants(field_file):
                return {"src": field_file.url, "srcset": "", "width": orig_w, "height": orig_h}
            cache.set(f"imgvar:{name}", 1, _DIMS_TTL)
        storage = field_file.storage
        entries, seen = [], set()
        for w in VARIANT_WIDTHS:
            actual = min(w, orig_w)
            if actual in seen:
                continue
            seen.add(actual)
            entries.append(f"{storage.url(variant_name(name, w))} {actual}w")
        largest = min(VARIANT_WIDTHS[-1], orig_w)
        return {
            "src": storage.url(variant_name(name, VARIANT_WIDTHS[-1])),
            "srcset": ", ".join(entries),
            "width": largest,
            "height": max(1, round(orig_h * largest / orig_w)),
        }
    except (OSError, ValueError):
        return None
