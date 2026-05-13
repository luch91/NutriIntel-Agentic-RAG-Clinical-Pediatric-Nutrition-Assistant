"""
MealPlanGenerator — rule-based v1 meal plan scaffold.

Wraps app/common/nutrient_calculator.meal_planner() using a built-in food list
derived from the FoodSourceMapper.  Not LLM-generated.
"""

from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel

from app.engine.condition_adjustments import AdjustedTarget
from app.engine.food_source_mapper import FoodSourceMapper

# nutrient_calculator provides the LP optimiser and meal splitter
from app.common.nutrient_calculator import meal_planner, convert_fct_rows_to_foods


class MealEntry(BaseModel):
    meal_name: str
    foods: List[str]
    estimated_nutrients: Dict[str, float]


class DayPlan(BaseModel):
    day: int
    meals: List[MealEntry]


class MealPlanDisplay(BaseModel):
    days: List[DayPlan]


# ---------------------------------------------------------------------------
# Built-in simplified food composition table (per 100 g)
# Used when no external FCT is provided
# ---------------------------------------------------------------------------

_BUILTIN_FCT = [
    {"food": "rice (cooked)",    "energy": 130.0, "protein": 2.7,  "calcium": 10.0,  "iron": 0.2, "zinc": 0.5, "vitamin_c": 0.0},
    {"food": "chicken breast",   "energy": 165.0, "protein": 31.0, "calcium": 15.0,  "iron": 1.0, "zinc": 1.0, "vitamin_c": 0.0},
    {"food": "egg",              "energy": 155.0, "protein": 13.0, "calcium": 56.0,  "iron": 1.8, "zinc": 1.3, "vitamin_c": 0.0},
    {"food": "liver (beef)",     "energy": 175.0, "protein": 29.0, "calcium": 11.0,  "iron": 6.5, "zinc": 4.0, "vitamin_c": 2.0},
    {"food": "moringa (dried)",  "energy": 329.0, "protein": 27.0, "calcium": 2003.0,"iron": 28.2,"zinc": 0.6, "vitamin_c": 17.3},
    {"food": "soybean",          "energy": 446.0, "protein": 36.5, "calcium": 277.0, "iron": 15.7,"zinc": 4.9, "vitamin_c": 6.0},
    {"food": "groundnut",        "energy": 567.0, "protein": 25.8, "calcium": 92.0,  "iron": 4.6, "zinc": 3.3, "vitamin_c": 0.0},
    {"food": "sweet potato",     "energy":  86.0, "protein": 1.6,  "calcium": 30.0,  "iron": 0.6, "zinc": 0.3, "vitamin_c": 2.4},
    {"food": "spinach (cooked)", "energy":  23.0, "protein": 3.0,  "calcium": 136.0, "iron": 3.6, "zinc": 0.8, "vitamin_c": 9.8},
    {"food": "black-eyed peas",  "energy": 116.0, "protein": 7.7,  "calcium": 24.0,  "iron": 2.5, "zinc": 1.3, "vitamin_c": 0.0},
    {"food": "banana",           "energy":  89.0, "protein": 1.1,  "calcium": 5.0,   "iron": 0.3, "zinc": 0.2, "vitamin_c": 8.7},
    {"food": "palm oil",         "energy": 884.0, "protein": 0.0,  "calcium": 0.0,   "iron": 0.0, "zinc": 0.0, "vitamin_c": 0.0},
    {"food": "crayfish (dried)", "energy": 295.0, "protein": 58.0, "calcium": 2055.0,"iron": 5.2, "zinc": 2.5, "vitamin_c": 0.0},
    {"food": "moi moi",          "energy": 102.0, "protein": 12.5, "calcium": 55.0,  "iron": 2.2, "zinc": 1.1, "vitamin_c": 0.0},
    {"food": "egusi soup",       "energy": 320.0, "protein": 15.0, "calcium": 60.0,  "iron": 3.0, "zinc": 2.8, "vitamin_c": 1.0},
    {"food": "ogi (porridge)",   "energy": 140.0, "protein": 3.5,  "calcium": 120.0, "iron": 1.8, "zinc": 0.4, "vitamin_c": 0.0},
]


def _build_targets(nutrient_targets: Dict[str, AdjustedTarget]) -> Dict:
    """Convert AdjustedTarget dict to the format expected by nutrient_calculator."""
    energy = nutrient_targets.get("Energy")
    protein = nutrient_targets.get("Protein")
    calcium = nutrient_targets.get("Calcium")
    iron = nutrient_targets.get("Iron")
    zinc = nutrient_targets.get("Zinc")

    return {
        "energy_kcal": energy.final_value if energy else 1800.0,
        "macros": {
            "protein_g": protein.final_value if protein else 30.0,
        },
        "micros": {
            "calcium": calcium.final_value if calcium else 800.0,
            "iron": iron.final_value if iron else 10.0,
            "zinc": zinc.final_value if zinc else 6.0,
            "vitamin_c": 40.0,
        },
    }


def _split_into_entries(meals_dict: dict) -> List[MealEntry]:
    """Convert meal_planner output into MealEntry objects."""
    entries = []
    meal_map = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner"}
    for key, display in meal_map.items():
        items = meals_dict.get(key, [])
        foods = [f"{item['food']} ({item['portion_g']}g)" for item in items]
        nutrients: Dict[str, float] = {}
        for item in items:
            nutrients["energy_kcal"] = round(nutrients.get("energy_kcal", 0) + item["energy"], 1)
            nutrients["protein_g"] = round(nutrients.get("protein_g", 0) + item["protein"], 1)
            for k, v in item["micros"].items():
                nutrients[k] = round(nutrients.get(k, 0) + v, 1)
        entries.append(MealEntry(meal_name=display, foods=foods, estimated_nutrients=nutrients))
    return entries


class MealPlanGenerator:
    """
    Rule-based meal plan generator.

    Uses nutrient_calculator.meal_planner() as the computation core and
    repeats the daily plan across the requested number of days (v1 scaffold).
    """

    def __init__(self, fct_rows: list | None = None) -> None:
        raw_rows = fct_rows if fct_rows is not None else _BUILTIN_FCT
        self._foods = convert_fct_rows_to_foods(raw_rows)

    def generate(
        self,
        nutrient_targets: Dict[str, AdjustedTarget],
        country: str,
        days: int = 3,
    ) -> MealPlanDisplay:
        """
        Generate a multi-day meal plan.

        v1 generates one optimised day plan and repeats it across all days.
        Country is recorded but does not yet filter foods (food selection
        improvement is deferred to v2).
        """
        targets = _build_targets(nutrient_targets)
        result = meal_planner(self._foods, targets)
        meals_dict = result.get("meals", {})
        day_entries = _split_into_entries(meals_dict)

        day_plans = [DayPlan(day=d + 1, meals=day_entries) for d in range(days)]
        return MealPlanDisplay(days=day_plans)
