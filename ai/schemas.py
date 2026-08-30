"""Pydantic schemas for the structured output of the menu extraction.

Every field is required (no defaults) so the JSON schema sent to the API is fully constrained;
"absent" is expressed with empty strings / empty lists.
"""

from typing import Literal

from pydantic import BaseModel, Field

from menus.constants import ALLERGENS, DIETS, SPECIAL_KINDS

AllergenCode = Literal[tuple(ALLERGENS)]
DietCode = Literal[tuple(DIETS)]
SpecialKind = Literal[tuple(SPECIAL_KINDS)]


class PriceOption(BaseModel):
    label: str = Field(
        description="Size or variant label as printed ('25 cl', 'Grande', 'le verre'); empty for a single price"
    )
    price_text: str = Field(description="The price exactly as printed, e.g. '12,50 €', '8€50', '14'")


class ExtractedItem(BaseModel):
    name: str
    description: str = Field(description="Description as printed; empty if none")
    prices: list[PriceOption]
    allergens: list[AllergenCode] = Field(
        description="Only allergens explicitly marked on the menu; usually empty"
    )
    diets: list[DietCode] = Field(
        description="Only diets explicitly marked on the menu (e.g. a V or vegan symbol); usually empty"
    )


class ExtractedCategory(BaseModel):
    name: str
    description: str = Field(
        description="Sub-heading or note printed under the category title; empty if none"
    )
    items: list[ExtractedItem]


class ExtractedSpecial(BaseModel):
    kind: SpecialKind
    title: str
    description: str
    prices: list[PriceOption]


class DetectedRestaurant(BaseModel):
    name: str = Field(description="Restaurant name if printed on the menu, else empty")
    phone: str
    address: str
    hours: str = Field(description="Opening hours, one line per day range, else empty")


class ExtractedMenu(BaseModel):
    restaurant: DetectedRestaurant
    categories: list[ExtractedCategory]
    specials: list[ExtractedSpecial] = Field(
        description="Plat du jour / formule / suggestions, if the menu has such a block"
    )


class TranslationEntry(BaseModel):
    key: str
    text: str


class TranslationBatch(BaseModel):
    translations: list[TranslationEntry]
