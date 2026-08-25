"""Shared vocabularies. Codes are stable identifiers stored in the database — never rename them."""

DEFAULT_LANGUAGE = "fr"
SUPPORTED_LANGUAGES = {
    "fr": {"label": "Français", "short": "FR"},
    "en": {"label": "English", "short": "EN"},
}

# The 14 allergens that must be declared in the EU (Regulation 1169/2011, Annex II).
ALLERGENS = {
    "gluten": {"fr": "Gluten", "en": "Gluten"},
    "crustaceans": {"fr": "Crustacés", "en": "Crustaceans"},
    "eggs": {"fr": "Œufs", "en": "Eggs"},
    "fish": {"fr": "Poisson", "en": "Fish"},
    "peanuts": {"fr": "Arachides", "en": "Peanuts"},
    "soy": {"fr": "Soja", "en": "Soy"},
    "milk": {"fr": "Lait", "en": "Milk"},
    "nuts": {"fr": "Fruits à coque", "en": "Tree nuts"},
    "celery": {"fr": "Céleri", "en": "Celery"},
    "mustard": {"fr": "Moutarde", "en": "Mustard"},
    "sesame": {"fr": "Sésame", "en": "Sesame"},
    "sulphites": {"fr": "Sulfites", "en": "Sulphites"},
    "lupin": {"fr": "Lupin", "en": "Lupin"},
    "molluscs": {"fr": "Mollusques", "en": "Molluscs"},
}

DIETS = {
    "vegetarian": {"fr": "Végétarien", "en": "Vegetarian"},
    "vegan": {"fr": "Vegan", "en": "Vegan"},
    "gluten_free": {"fr": "Sans gluten", "en": "Gluten-free"},
}

THEMES = {
    "bistro": {"label": "Bistro", "hint": "Parisian bistro / brasserie"},
    "trattoria": {"label": "Trattoria", "hint": "Pizzeria / Italian"},
    "cafe": {"label": "Café", "hint": "Café, salon de thé, bakery"},
    "gastro": {"label": "Gastronomique", "hint": "Fine dining"},
    "auberge": {"label": "Auberge", "hint": "Country inn, terroir, farm produce"},
}
DEFAULT_THEME = "bistro"

COLOR_MODES = {"auto": "Follow phone setting", "light": "Light", "dark": "Dark"}

SPECIAL_KINDS = {
    "plat": {"fr": "Plat du jour", "en": "Dish of the day"},
    "formule": {"fr": "Formule du jour", "en": "Set menu of the day"},
    "dessert": {"fr": "Dessert du jour", "en": "Dessert of the day"},
    "suggestion": {"fr": "Suggestion du chef", "en": "Chef's suggestion"},
}
