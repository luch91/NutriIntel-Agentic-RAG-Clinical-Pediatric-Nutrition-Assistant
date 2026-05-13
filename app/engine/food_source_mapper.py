"""
FoodSourceMapper — maps nutrients to food sources, with Nigeria-specific entries.

nutrient_calculator.py has no food-source mapping logic; all data is new here.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List
from pydantic import BaseModel


class LocalAvailability(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


class FoodSource(BaseModel):
    food_name: str
    nutrient_content_per_100g: float
    unit: str
    local_availability: LocalAvailability
    notes: str = ""


# ---------------------------------------------------------------------------
# Food database
# Structure: nutrient_key -> {country_code -> [FoodSource], "INT" -> [FoodSource]}
# "INT" = international fallback; country-specific entries are prepended
# ---------------------------------------------------------------------------

_NG_PROTEIN: List[FoodSource] = [
    FoodSource(food_name="Egusi (melon seeds)", nutrient_content_per_100g=28.4, unit="g protein/100g", local_availability=LocalAvailability.HIGH, notes="High-protein seed used in soups; also provides zinc and iron"),
    FoodSource(food_name="Moi moi (bean pudding)", nutrient_content_per_100g=12.5, unit="g protein/100g", local_availability=LocalAvailability.HIGH, notes="Steamed black-eyed pea cake; easily digestible"),
    FoodSource(food_name="Crayfish (dried)", nutrient_content_per_100g=58.0, unit="g protein/100g", local_availability=LocalAvailability.HIGH, notes="Concentrated protein and calcium source; used as seasoning"),
    FoodSource(food_name="Soybean", nutrient_content_per_100g=36.5, unit="g protein/100g", local_availability=LocalAvailability.HIGH, notes="Complete protein; available as flour, milk, or tofu"),
    FoodSource(food_name="Liver (beef)", nutrient_content_per_100g=29.1, unit="g protein/100g", local_availability=LocalAvailability.HIGH, notes="Excellent source of protein, iron, zinc, and Vitamin A"),
    FoodSource(food_name="Bambara nut", nutrient_content_per_100g=19.6, unit="g protein/100g", local_availability=LocalAvailability.HIGH, notes="Legume with good amino acid profile; grown widely in West Africa"),
]

_INT_PROTEIN: List[FoodSource] = [
    FoodSource(food_name="Chicken breast", nutrient_content_per_100g=31.0, unit="g protein/100g", local_availability=LocalAvailability.MODERATE),
    FoodSource(food_name="Egg", nutrient_content_per_100g=13.0, unit="g protein/100g", local_availability=LocalAvailability.HIGH, notes="High biological value protein"),
    FoodSource(food_name="Lentils (cooked)", nutrient_content_per_100g=9.0, unit="g protein/100g", local_availability=LocalAvailability.MODERATE),
    FoodSource(food_name="Greek yoghurt", nutrient_content_per_100g=10.0, unit="g protein/100g", local_availability=LocalAvailability.LOW),
]

_NG_IRON: List[FoodSource] = [
    FoodSource(food_name="Liver (beef)", nutrient_content_per_100g=6.5, unit="mg iron/100g", local_availability=LocalAvailability.HIGH, notes="Haem iron; highly bioavailable"),
    FoodSource(food_name="Crayfish (dried)", nutrient_content_per_100g=5.2, unit="mg iron/100g", local_availability=LocalAvailability.HIGH, notes="Non-haem iron; pair with Vitamin C to enhance absorption"),
    FoodSource(food_name="Moringa leaves (dried)", nutrient_content_per_100g=28.2, unit="mg iron/100g", local_availability=LocalAvailability.HIGH, notes="Exceptional iron density; also provides calcium and Vitamin A"),
    FoodSource(food_name="Ugba (African oil bean)", nutrient_content_per_100g=3.8, unit="mg iron/100g", local_availability=LocalAvailability.MODERATE, notes="Fermented seed; good iron and protein source"),
]

_INT_IRON: List[FoodSource] = [
    FoodSource(food_name="Red meat (beef)", nutrient_content_per_100g=2.6, unit="mg iron/100g", local_availability=LocalAvailability.MODERATE, notes="Haem iron"),
    FoodSource(food_name="Fortified breakfast cereal", nutrient_content_per_100g=12.0, unit="mg iron/100g", local_availability=LocalAvailability.MODERATE),
    FoodSource(food_name="Spinach", nutrient_content_per_100g=2.7, unit="mg iron/100g", local_availability=LocalAvailability.MODERATE, notes="Non-haem iron; bioavailability enhanced by Vitamin C"),
]

_NG_CALCIUM: List[FoodSource] = [
    FoodSource(food_name="Crayfish (dried)", nutrient_content_per_100g=2055.0, unit="mg calcium/100g", local_availability=LocalAvailability.HIGH, notes="Exceptional calcium density; commonly used as soup seasoning"),
    FoodSource(food_name="Moringa leaves (dried)", nutrient_content_per_100g=2003.0, unit="mg calcium/100g", local_availability=LocalAvailability.HIGH, notes="High calcium; can be added to porridge or soups"),
    FoodSource(food_name="Uziza leaves", nutrient_content_per_100g=810.0, unit="mg calcium/100g", local_availability=LocalAvailability.MODERATE, notes="Used in soups; also provides iron"),
    FoodSource(food_name="Ogi (fortified maize porridge)", nutrient_content_per_100g=120.0, unit="mg calcium/100g", local_availability=LocalAvailability.HIGH, notes="Commonly fortified; good base for infant/toddler nutrition"),
]

_INT_CALCIUM: List[FoodSource] = [
    FoodSource(food_name="Milk (whole)", nutrient_content_per_100g=113.0, unit="mg calcium/100g", local_availability=LocalAvailability.MODERATE),
    FoodSource(food_name="Yoghurt", nutrient_content_per_100g=121.0, unit="mg calcium/100g", local_availability=LocalAvailability.LOW),
    FoodSource(food_name="Tofu (calcium-set)", nutrient_content_per_100g=350.0, unit="mg calcium/100g", local_availability=LocalAvailability.LOW),
]

_NG_ZINC: List[FoodSource] = [
    FoodSource(food_name="Liver (beef)", nutrient_content_per_100g=4.0, unit="mg zinc/100g", local_availability=LocalAvailability.HIGH),
    FoodSource(food_name="Egusi (melon seeds)", nutrient_content_per_100g=7.3, unit="mg zinc/100g", local_availability=LocalAvailability.HIGH),
    FoodSource(food_name="Soybean", nutrient_content_per_100g=4.9, unit="mg zinc/100g", local_availability=LocalAvailability.HIGH),
]

_INT_ZINC: List[FoodSource] = [
    FoodSource(food_name="Beef (lean)", nutrient_content_per_100g=4.8, unit="mg zinc/100g", local_availability=LocalAvailability.MODERATE),
    FoodSource(food_name="Pumpkin seeds", nutrient_content_per_100g=7.6, unit="mg zinc/100g", local_availability=LocalAvailability.LOW),
    FoodSource(food_name="Chickpeas (cooked)", nutrient_content_per_100g=1.5, unit="mg zinc/100g", local_availability=LocalAvailability.MODERATE),
]

_NG_ENERGY: List[FoodSource] = [
    FoodSource(food_name="Palm oil", nutrient_content_per_100g=884.0, unit="kcal/100g", local_availability=LocalAvailability.HIGH, notes="Energy-dense; also provides Vitamin A (as beta-carotene)"),
    FoodSource(food_name="Groundnut (peanut)", nutrient_content_per_100g=567.0, unit="kcal/100g", local_availability=LocalAvailability.HIGH, notes="High energy and protein; watch for allergy"),
    FoodSource(food_name="Coconut (dried)", nutrient_content_per_100g=660.0, unit="kcal/100g", local_availability=LocalAvailability.MODERATE),
]

_INT_ENERGY: List[FoodSource] = [
    FoodSource(food_name="Olive oil", nutrient_content_per_100g=884.0, unit="kcal/100g", local_availability=LocalAvailability.LOW),
    FoodSource(food_name="Avocado", nutrient_content_per_100g=160.0, unit="kcal/100g", local_availability=LocalAvailability.LOW),
    FoodSource(food_name="Oats", nutrient_content_per_100g=389.0, unit="kcal/100g", local_availability=LocalAvailability.MODERATE),
]

_NG_VITAMIN_A: List[FoodSource] = [
    FoodSource(food_name="Moringa leaves (dried)", nutrient_content_per_100g=18900.0, unit="IU Vitamin A/100g", local_availability=LocalAvailability.HIGH, notes="Exceptional Vitamin A density as beta-carotene"),
    FoodSource(food_name="Liver (beef)", nutrient_content_per_100g=31718.0, unit="IU Vitamin A/100g", local_availability=LocalAvailability.HIGH, notes="Preformed retinol; do not over-consume in pregnancy"),
    FoodSource(food_name="Palm oil (red)", nutrient_content_per_100g=30000.0, unit="IU Vitamin A/100g", local_availability=LocalAvailability.HIGH, notes="Rich in beta-carotene; red colour indicates high provitamin A"),
    FoodSource(food_name="Uziza leaves", nutrient_content_per_100g=4200.0, unit="IU Vitamin A/100g", local_availability=LocalAvailability.MODERATE),
]

_INT_VITAMIN_A: List[FoodSource] = [
    FoodSource(food_name="Carrot", nutrient_content_per_100g=16706.0, unit="IU Vitamin A/100g", local_availability=LocalAvailability.MODERATE),
    FoodSource(food_name="Sweet potato", nutrient_content_per_100g=19218.0, unit="IU Vitamin A/100g", local_availability=LocalAvailability.MODERATE),
]

_NG_VITAMIN_D: List[FoodSource] = []  # Few Nigerian-specific sources; fall back to international

_INT_VITAMIN_D: List[FoodSource] = [
    FoodSource(food_name="Salmon (cooked)", nutrient_content_per_100g=526.0, unit="IU Vitamin D/100g", local_availability=LocalAvailability.LOW),
    FoodSource(food_name="Fortified milk", nutrient_content_per_100g=100.0, unit="IU Vitamin D/100g", local_availability=LocalAvailability.MODERATE),
    FoodSource(food_name="Egg yolk", nutrient_content_per_100g=218.0, unit="IU Vitamin D/100g", local_availability=LocalAvailability.HIGH),
    FoodSource(food_name="Mackerel (canned)", nutrient_content_per_100g=360.0, unit="IU Vitamin D/100g", local_availability=LocalAvailability.MODERATE),
]

_INT_FOLATE: List[FoodSource] = [
    FoodSource(food_name="Black-eyed peas (cooked)", nutrient_content_per_100g=208.0, unit="mcg folate/100g", local_availability=LocalAvailability.HIGH),
    FoodSource(food_name="Spinach (cooked)", nutrient_content_per_100g=146.0, unit="mcg folate/100g", local_availability=LocalAvailability.MODERATE),
    FoodSource(food_name="Fortified flour", nutrient_content_per_100g=128.0, unit="mcg folate/100g", local_availability=LocalAvailability.HIGH),
]

_INT_B12: List[FoodSource] = [
    FoodSource(food_name="Liver (beef)", nutrient_content_per_100g=70.7, unit="mcg B12/100g", local_availability=LocalAvailability.HIGH),
    FoodSource(food_name="Mackerel", nutrient_content_per_100g=19.0, unit="mcg B12/100g", local_availability=LocalAvailability.MODERATE),
    FoodSource(food_name="Egg", nutrient_content_per_100g=1.1, unit="mcg B12/100g", local_availability=LocalAvailability.HIGH),
    FoodSource(food_name="Fortified soy milk", nutrient_content_per_100g=1.0, unit="mcg B12/100g", local_availability=LocalAvailability.LOW),
]

# ---------------------------------------------------------------------------
# Registry: nutrient_key -> (ng_sources, int_sources)
# ---------------------------------------------------------------------------

_FOOD_DB: Dict[str, tuple] = {
    "protein":    (_NG_PROTEIN,    _INT_PROTEIN),
    "iron":       (_NG_IRON,       _INT_IRON),
    "calcium":    (_NG_CALCIUM,    _INT_CALCIUM),
    "zinc":       (_NG_ZINC,       _INT_ZINC),
    "energy":     (_NG_ENERGY,     _INT_ENERGY),
    "fat":        (_NG_ENERGY,     _INT_ENERGY),
    "vitamin a":  (_NG_VITAMIN_A,  _INT_VITAMIN_A),
    "vitamin d":  (_NG_VITAMIN_D,  _INT_VITAMIN_D),
    "folate":     ([],             _INT_FOLATE),
    "vitamin b12": ([],            _INT_B12),
}


class FoodSourceMapper:
    """Maps a list of nutrients to recommended food sources, country-aware."""

    def map_nutrients_to_foods(
        self,
        nutrients: List[str],
        country: str,
    ) -> Dict[str, List[FoodSource]]:
        """
        Return a dict of {nutrient: [FoodSource]} for each requested nutrient.

        For country="NG", Nigeria-specific sources are listed first, followed
        by international fallbacks.  For all other countries, only international
        sources are returned.
        """
        country_upper = country.strip().upper()
        result: Dict[str, List[FoodSource]] = {}

        for nutrient in nutrients:
            key = nutrient.strip().lower()
            # Strip condition-specific suffixes like "_restriction", "_limit"
            for suffix in ("_restriction", "_supplement", "_limit", "_ketogenic"):
                key = key.replace(suffix, "")
            key = key.strip()

            ng_sources, int_sources = _FOOD_DB.get(key, ([], []))

            if country_upper == "NG":
                combined = list(ng_sources) + [s for s in int_sources if s not in ng_sources]
            else:
                combined = list(int_sources)

            if combined:
                result[nutrient] = combined

        return result
