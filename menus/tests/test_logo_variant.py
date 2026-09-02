from io import BytesIO

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image

from menus.images import LOGO_VARIANT_BOX, logo_variant_name, logo_view, process_logo
from menus.models import Restaurant


def _png(w, h):
    buf = BytesIO()
    Image.new("RGBA", (w, h), (120, 40, 40, 255)).save(buf, "PNG")
    return ContentFile(buf.getvalue(), name="logo.png")


@pytest.mark.django_db
def test_logo_variant_is_small_webp_and_removed_with_logo():
    r = Restaurant.objects.create(name="Logo Test", slug="logo-test")
    r.logo.save("logo.png", process_logo(_png(1000, 500), "logo.png"), save=True)
    view = logo_view(r.logo)
    vname = logo_variant_name(r.logo.name)
    assert view["src"].endswith(".logo.webp") and default_storage.exists(vname)
    assert view["width"] <= LOGO_VARIANT_BOX[0] and view["height"] <= LOGO_VARIANT_BOX[1]
    with default_storage.open(vname, "rb") as fh, Image.open(fh) as img:
        assert img.format == "WEBP" and img.size == (view["width"], view["height"])

    old = r.logo.name
    r.logo.save("logo2.png", process_logo(_png(200, 200), "logo2.png"), save=True)
    assert not default_storage.exists(old) and not default_storage.exists(vname)
    view2 = logo_view(r.logo)
    assert (view2["width"], view2["height"]) == (112, 112)
    r.delete()
    assert not default_storage.exists(logo_variant_name(r.logo.name))
