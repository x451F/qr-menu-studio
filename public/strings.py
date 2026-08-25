"""Public menu UI strings."""

STRINGS = {
    "fr": {
        "sold_out": "Épuisé",
        "allergens": "Allergènes",
        "today": "Aujourd'hui",
        "call": "Appeler",
        "directions": "Itinéraire",
        "hours": "Horaires",
    },
    "en": {
        "sold_out": "Sold out",
        "allergens": "Allergens",
        "today": "Today",
        "call": "Call",
        "directions": "Directions",
        "hours": "Opening hours",
    },
}


def strings_for(lang: str) -> dict[str, str]:
    return STRINGS.get(lang, STRINGS["fr"])
