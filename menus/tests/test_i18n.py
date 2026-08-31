from menus.i18n import has_translation, tr


def test_tr_returns_requested_language():
    assert tr({"fr": "Canard", "en": "Duck"}, "en") == "Duck"
    assert tr({"fr": "Canard", "en": "Duck"}, "fr") == "Canard"


def test_tr_falls_back_to_french_when_missing_or_blank():
    assert tr({"fr": "Canard", "en": ""}, "en") == "Canard"
    assert tr({"fr": "Canard", "en": "   "}, "en") == "Canard"
    assert tr({"fr": "Canard"}, "en") == "Canard"


def test_tr_falls_back_to_any_non_empty_value():
    assert tr({"fr": "", "en": "Duck"}, "fr") == "Duck"
    assert tr({"de": " Ente "}, "en") == "Ente"


def test_tr_default_language_is_french():
    assert tr({"fr": "Canard", "en": "Duck"}) == "Canard"


def test_tr_handles_empty_and_plain_values():
    assert tr({}, "en") == ""
    assert tr(None, "en") == ""
    assert tr({"fr": "", "en": ""}, "en") == ""
    assert tr("Texte", "en") == "Texte"


def test_has_translation():
    assert has_translation({"fr": "a", "en": "b"}, "en")
    assert not has_translation({"fr": "a", "en": " "}, "en")
    assert not has_translation({"fr": "a"}, "en")
    assert not has_translation(None, "en")
