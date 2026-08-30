"""Service layer: fake mode, disabled mode, image preprocessing, error mapping, request shape."""

import base64
import io
import json

import anthropic
import httpx2
import pytest
from PIL import Image

from ai import services
from ai.schemas import ExtractedMenu

# ------------------------------------------------------------------ fake / disabled


def test_fake_extraction_is_realistic(fake_ai, sample_jpeg):
    menu = services.extract_menu([sample_jpeg], ["image/jpeg"])
    assert isinstance(menu, ExtractedMenu)
    assert len(menu.categories) == 3
    items = [i for c in menu.categories for i in c.items]
    assert len(items) >= 12
    assert any(len(i.prices) == 2 for i in items)  # two sizes
    assert any(p.price_text == "selon arrivage" for i in items for p in i.prices)  # unparseable
    assert any(i.allergens for i in items)
    assert menu.specials and menu.restaurant.phone


def test_fake_translation_is_deterministic(fake_ai):
    out = services.translate_texts({"a": "Entrées", "b": "Pâté maison", "c": "  ", "d": ""})
    assert out == {"a": "Starters", "b": "[EN] Pâté maison", "c": "", "d": ""}
    assert out == services.translate_texts({"a": "Entrées", "b": "Pâté maison", "c": "  ", "d": ""})


def test_disabled_mode_raises(no_ai, sample_jpeg):
    with pytest.raises(services.AIUnavailable, match="ANTHROPIC_API_KEY"):
        services.extract_menu([sample_jpeg], ["image/jpeg"])
    with pytest.raises(services.AIUnavailable, match="AI is disabled"):
        services.translate_texts({"a": "Bonjour"})


def test_translate_rejects_bad_languages(fake_ai):
    with pytest.raises(ValueError):
        services.translate_texts({"a": "x"}, "fr", "fr")
    with pytest.raises(ValueError):
        services.translate_texts({"a": "x"}, "fr", "de")


# ------------------------------------------------------------------ images


def _big_jpeg(size=(3200, 4200), orientation=None) -> bytes:
    img = Image.effect_noise(size, 60).convert("RGB")
    buf = io.BytesIO()
    exif = Image.Exif()
    if orientation:
        exif[0x0112] = orientation
    img.save(buf, "JPEG", quality=95, exif=exif)
    return buf.getvalue()


def test_prepare_image_downsizes_and_rotates():
    data = _big_jpeg((3200, 2400), orientation=6)  # landscape pixels, rotate 90 deg -> portrait
    out, media_type = services.prepare_image(data)
    img = Image.open(io.BytesIO(out))
    assert media_type == "image/jpeg" and img.format == "JPEG"
    assert max(img.size) == services.MAX_EDGE_PX
    assert img.height > img.width  # EXIF rotation applied
    assert len(out) < 5_000_000
    assert not img.getexif().get(0x0112)  # orientation not carried over


def test_prepare_image_small_png_with_alpha_is_flattened():
    buf = io.BytesIO()
    Image.new("RGBA", (300, 200), (255, 0, 0, 0)).save(buf, "PNG")
    out, _ = services.prepare_image(buf.getvalue())
    img = Image.open(io.BytesIO(out))
    assert img.size == (300, 200) and img.mode == "RGB"
    assert img.getpixel((10, 10))[0] > 240  # transparent -> white, not black


def test_prepare_image_rejects_garbage():
    with pytest.raises(services.ImageError):
        services.prepare_image(b"definitely not an image")


def test_extract_menu_validates_image_count(fake_ai, sample_jpeg):
    with pytest.raises(services.ImageError):
        services.extract_menu([], [])
    with pytest.raises(services.ImageError):
        services.extract_menu([sample_jpeg] * 7, ["image/jpeg"] * 7)
    with pytest.raises(services.ImageError):
        services.extract_menu([b"nope"], ["image/jpeg"])


# ------------------------------------------------------------------ SDK error mapping


class _Boom:
    """Stand-in client whose create() calls raise ``exc``."""

    def __init__(self, exc):
        self.beta = self
        self.messages = self
        self._exc = exc

    def create(self, **kwargs):
        raise self._exc


def _response(status, body=None):
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return httpx2.Response(status, request=request, json=body or {"error": {"message": "nope"}})


def _status_error(cls, status):
    return cls("nope", response=_response(status), body=None)


@pytest.mark.parametrize(
    ("exc", "needle"),
    [
        (_status_error(anthropic.AuthenticationError, 401), "API key is invalid"),
        (_status_error(anthropic.PermissionDeniedError, 403), "permission"),
        (_status_error(anthropic.NotFoundError, 404), "ANTHROPIC_MODEL"),
        (_status_error(anthropic.RateLimitError, 429), "rate-limited"),
        (_status_error(anthropic.BadRequestError, 400), "rejected"),
        (_status_error(anthropic.InternalServerError, 503), "temporarily unavailable"),
        (
            anthropic.APITimeoutError(request=httpx2.Request("POST", "https://x")),
            "too long",
        ),
        (
            anthropic.APIConnectionError(request=httpx2.Request("POST", "https://x")),
            "Could not reach",
        ),
    ],
)
def test_sdk_errors_become_ai_unavailable(real_ai, monkeypatch, exc, needle):
    monkeypatch.setattr(services, "_client", lambda: _Boom(exc))
    with pytest.raises(services.AIUnavailable) as info:
        services.translate_texts({"a": "Bonjour"})
    assert needle in info.value.user_message
    assert "test-key-not-real" not in info.value.user_message


# ------------------------------------------------------------------ request shape (real path)


def _beta_message(text, stop_reason="end_turn"):
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 10},
    }


def _client_with(handler):
    return anthropic.Anthropic(
        api_key="test-key-not-real",
        max_retries=0,
        timeout=anthropic.Timeout(services.CLIENT_TIMEOUT_S),
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)),
    )


def test_extract_request_shape(real_ai, monkeypatch, sample_jpeg):
    seen = []
    sample = (services.FIXTURE_DIR / "sample_extraction.json").read_text()

    def handler(request):
        seen.append(request)
        return httpx2.Response(200, json=_beta_message(sample))

    monkeypatch.setattr(services, "_client", lambda: _client_with(handler))
    big = _big_jpeg((2600, 3400))
    menu = services.extract_menu([sample_jpeg, big], ["image/jpeg", "image/jpeg"])

    assert len(menu.categories) == 3  # parsed_output validated against ExtractedMenu
    assert len(seen) == 1
    req = seen[0]
    assert req.url.path == "/v1/messages"
    assert "server-side-fallback-2026-07-01" in req.headers["anthropic-beta"]
    body = json.loads(req.content)
    assert body["model"] == "claude-opus-5-5"
    assert body["fallbacks"] == "default"
    assert body["output_config"]["effort"] == "medium"
    fmt = body["output_config"]["format"]
    assert fmt["type"] == "json_schema"
    assert set(fmt["schema"]["properties"]) == {"restaurant", "categories", "specials"}
    assert "thinking" not in body and "temperature" not in body and "tool_choice" not in body
    (message,) = body["messages"]
    assert message["role"] == "user"  # no assistant prefill
    blocks = message["content"]
    assert [b["type"] for b in blocks] == ["image", "image", "text"]
    for block in blocks[:2]:
        assert block["source"]["type"] == "base64"
        assert block["source"]["media_type"] == "image/jpeg"
        raw = base64.b64decode(block["source"]["data"])
        assert len(raw) < 5_000_000
        assert max(Image.open(io.BytesIO(raw)).size) <= services.MAX_EDGE_PX
    assert "French" in body["system"] and "EXACTLY as printed" in body["system"]
    assert body["max_tokens"] == services.EXTRACT_MAX_TOKENS


def test_translate_request_shape(real_ai, monkeypatch):
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        payload = {"translations": [{"key": "a", "text": "Duck confit"}, {"key": "b", "text": "Cahors"}]}
        return httpx2.Response(200, json=_beta_message(json.dumps(payload)))

    monkeypatch.setattr(services, "_client", lambda: _client_with(handler))
    out = services.translate_texts({"a": "Confit de canard", "b": "Cahors", "c": ""})
    assert out == {"a": "Duck confit", "b": "Cahors", "c": ""}
    assert len(seen) == 1
    content = seen[0]["messages"][0]["content"]
    assert json.loads(content[0]["text"]) == [
        {"key": "a", "text": "Confit de canard"},
        {"key": "b", "text": "Cahors"},
    ]
    assert "crème brûlée" in seen[0]["system"] and "Cahors" in seen[0]["system"]


def test_stop_reasons_are_handled(real_ai, monkeypatch, sample_jpeg):
    for stop, needle in [("refusal", "declined"), ("max_tokens", "too long")]:
        monkeypatch.setattr(
            services,
            "_client",
            lambda stop=stop: _client_with(
                lambda request, stop=stop: httpx2.Response(200, json=_beta_message("{}", stop))
            ),
        )
        with pytest.raises(services.AIUnavailable, match=needle):
            services.extract_menu([sample_jpeg], ["image/jpeg"])


def test_falls_back_to_stable_endpoint_if_beta_is_rejected(real_ai, monkeypatch):
    paths = []

    def handler(request):
        paths.append((request.url.path, dict(request.url.params)))
        if "beta" in request.url.params:
            return httpx2.Response(
                400, json={"type": "error", "error": {"type": "invalid_request_error", "message": "unknown beta header"}}
            )
        payload = {"translations": [{"key": "a", "text": "Hello"}]}
        return httpx2.Response(200, json=_beta_message(json.dumps(payload)))

    monkeypatch.setattr(services, "_client", lambda: _client_with(handler))
    assert services.translate_texts({"a": "Bonjour"}) == {"a": "Hello"}
    assert len(paths) == 2 and "beta" not in paths[1][1]


def test_translation_is_chunked_and_incomplete_answers_fail(real_ai, monkeypatch):
    calls = []

    def fake_chunk(chunk, source, target):
        calls.append([k for k, _ in chunk])
        return {k: t.upper() for k, t in chunk}

    monkeypatch.setattr(services, "_translate_chunk", fake_chunk)
    texts = {f"k{i}": f"texte {i}" for i in range(services.TRANSLATE_CHUNK_KEYS + 5)}
    out = services.translate_texts(texts)
    assert len(calls) == 2 and out["k0"] == "TEXTE 0"

    monkeypatch.setattr(services, "_translate_chunk", lambda chunk, s, t: {})
    with pytest.raises(services.AIUnavailable, match="incomplete"):
        services.translate_texts({"a": "Bonjour"})
