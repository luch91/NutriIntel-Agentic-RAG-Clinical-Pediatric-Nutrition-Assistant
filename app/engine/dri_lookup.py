"""
DRILookup — returns Dietary Reference Intake values by age, sex, and nutrient.

nutrient_calculator.py has no DRI logic; all values are implemented here.
Data source: DRI Tables 2023-2024 (National Academies of Sciences).

Age bands: 0-0.5y, 0.5-1y, 1-3y, 4-8y, 9-13y, 14-18y
"""

from __future__ import annotations

from typing import Dict, Optional
from pydantic import BaseModel

_SOURCE = "DRI Tables 2023-2024"


class DRIResult(BaseModel):
    nutrient: str
    age_band: str
    sex: str
    rda: Optional[float] = None
    ai: Optional[float] = None
    ul: Optional[float] = None
    unit: str
    source: str = _SOURCE


class DRINotFoundError(Exception):
    pass


# ---------------------------------------------------------------------------
# DRI tables
# Each entry: (age_lo_inclusive, age_hi_exclusive) -> {sex: (rda, ai, ul, unit)}
# rda=None means use AI instead; ul=None means not established
# ---------------------------------------------------------------------------

# Structure: nutrient -> list of (age_lo, age_hi, sex, rda, ai, ul, unit)
# sex: "any" means applies to both male and female
_DRI_TABLE: list[tuple] = [
    # ---- Energy (EER kcal/day — representative values at moderate activity) ----
    # age_hi is exclusive upper bound; "4–8y" covers ages 4.0 <= age < 9.0
    ("Energy", 0.0,  0.5,  "any",    None, 570.0,  None,   "kcal/day"),
    ("Energy", 0.5,  1.0,  "any",    None, 743.0,  None,   "kcal/day"),
    ("Energy", 1.0,  4.0,  "any",    None, 1046.0, None,   "kcal/day"),
    ("Energy", 4.0,  9.0,  "male",   None, 1742.0, None,   "kcal/day"),
    ("Energy", 4.0,  9.0,  "female", None, 1642.0, None,   "kcal/day"),
    ("Energy", 9.0,  14.0, "male",   None, 2279.0, None,   "kcal/day"),
    ("Energy", 9.0,  14.0, "female", None, 2071.0, None,   "kcal/day"),
    ("Energy", 14.0, 19.0, "male",   None, 3152.0, None,   "kcal/day"),
    ("Energy", 14.0, 19.0, "female", None, 2368.0, None,   "kcal/day"),

    # ---- Protein (g/day) ----
    ("Protein", 0.0,  0.5,  "any",    None, 9.1,   None,  "g/day"),
    ("Protein", 0.5,  1.0,  "any",    None, 11.0,  None,  "g/day"),
    ("Protein", 1.0,  4.0,  "any",    13.0, None,  None,  "g/day"),
    ("Protein", 4.0,  9.0,  "any",    19.0, None,  None,  "g/day"),
    ("Protein", 9.0,  14.0, "any",    34.0, None,  None,  "g/day"),
    ("Protein", 14.0, 19.0, "male",   52.0, None,  None,  "g/day"),
    ("Protein", 14.0, 19.0, "female", 46.0, None,  None,  "g/day"),

    # ---- Calcium (mg/day) ----
    ("Calcium", 0.0,  0.5,  "any",    None,  200.0, 1000.0, "mg/day"),
    ("Calcium", 0.5,  1.0,  "any",    None,  260.0, 1500.0, "mg/day"),
    ("Calcium", 1.0,  4.0,  "any",    700.0, None,  2500.0, "mg/day"),
    ("Calcium", 4.0,  9.0,  "any",   1000.0, None,  2500.0, "mg/day"),
    ("Calcium", 9.0,  14.0, "any",   1300.0, None,  3000.0, "mg/day"),
    ("Calcium", 14.0, 19.0, "any",   1300.0, None,  3000.0, "mg/day"),

    # ---- Iron (mg/day) ----
    ("Iron", 0.0,  0.5,  "any",    None,  0.27, 40.0,  "mg/day"),
    ("Iron", 0.5,  1.0,  "any",    11.0,  None, 40.0,  "mg/day"),
    ("Iron", 1.0,  4.0,  "any",     7.0,  None, 40.0,  "mg/day"),
    ("Iron", 4.0,  9.0,  "any",    10.0,  None, 40.0,  "mg/day"),
    ("Iron", 9.0,  14.0, "any",     8.0,  None, 40.0,  "mg/day"),
    ("Iron", 14.0, 19.0, "male",    11.0, None, 45.0,  "mg/day"),
    ("Iron", 14.0, 19.0, "female",  15.0, None, 45.0,  "mg/day"),

    # ---- Zinc (mg/day) ----
    ("Zinc", 0.0,  0.5,  "any",    None, 2.0,  4.0,  "mg/day"),
    ("Zinc", 0.5,  1.0,  "any",    3.0,  None, 5.0,  "mg/day"),
    ("Zinc", 1.0,  4.0,  "any",    3.0,  None, 7.0,  "mg/day"),
    ("Zinc", 4.0,  9.0,  "any",    5.0,  None, 12.0, "mg/day"),
    ("Zinc", 9.0,  14.0, "any",    8.0,  None, 23.0, "mg/day"),
    ("Zinc", 14.0, 19.0, "male",   11.0, None, 34.0, "mg/day"),
    ("Zinc", 14.0, 19.0, "female",  9.0, None, 34.0, "mg/day"),

    # ---- Vitamin D (IU/day) ----
    ("Vitamin D", 0.0,  1.0,  "any",    None, 400.0, 1000.0, "IU/day"),
    ("Vitamin D", 1.0,  14.0, "any",   600.0, None,  4000.0, "IU/day"),
    ("Vitamin D", 14.0, 19.0, "any",   600.0, None,  4000.0, "IU/day"),

    # ---- Folate (mcg DFE/day) ----
    ("Folate", 0.0,  0.5,  "any",    None,  65.0, None,   "mcg DFE/day"),
    ("Folate", 0.5,  1.0,  "any",    None,  80.0, None,   "mcg DFE/day"),
    ("Folate", 1.0,  4.0,  "any",   150.0,  None, 300.0,  "mcg DFE/day"),
    ("Folate", 4.0,  9.0,  "any",   200.0,  None, 400.0,  "mcg DFE/day"),
    ("Folate", 9.0,  14.0, "any",   300.0,  None, 600.0,  "mcg DFE/day"),
    ("Folate", 14.0, 19.0, "any",   400.0,  None, 800.0,  "mcg DFE/day"),

    # ---- Vitamin B12 (mcg/day) ----
    ("Vitamin B12", 0.0,  0.5,  "any",    None, 0.4,  None, "mcg/day"),
    ("Vitamin B12", 0.5,  1.0,  "any",    None, 0.5,  None, "mcg/day"),
    ("Vitamin B12", 1.0,  4.0,  "any",   0.9,  None,  None, "mcg/day"),
    ("Vitamin B12", 4.0,  9.0,  "any",   1.2,  None,  None, "mcg/day"),
    ("Vitamin B12", 9.0,  14.0, "any",   1.8,  None,  None, "mcg/day"),
    ("Vitamin B12", 14.0, 19.0, "any",   2.4,  None,  None, "mcg/day"),
]


def _age_band_label(age_lo: float, age_hi: float) -> str:
    return f"{age_lo}–{age_hi}y"


class DRILookup:
    """Returns DRI values for a given age, sex, and nutrient."""

    def get_dri(self, age_years: float, sex: str, nutrient: str) -> DRIResult:
        """
        Look up the DRI for a specific nutrient.

        sex must be "male" or "female" (case-insensitive).
        nutrient must match one of the names in the DRI table (case-insensitive).
        Raises DRINotFoundError if no matching row found.
        """
        sex_norm = sex.strip().lower()
        nutrient_norm = nutrient.strip().lower()

        for (nut, age_lo, age_hi, row_sex, rda, ai, ul, unit) in _DRI_TABLE:
            if nut.lower() != nutrient_norm:
                continue
            if not (age_lo <= age_years < age_hi):
                continue
            if row_sex != "any" and row_sex != sex_norm:
                continue
            return DRIResult(
                nutrient=nut,
                age_band=_age_band_label(age_lo, age_hi),
                sex=sex_norm,
                rda=rda,
                ai=ai,
                ul=ul,
                unit=unit,
            )

        # Handle exact upper boundary (18.0 years covered by 14–19 band)
        # Nothing to special-case — table now uses 19.0 as upper bound

        raise DRINotFoundError(
            f"No DRI entry for nutrient='{nutrient}', age={age_years}, sex='{sex}'"
        )

    def get_all_nutrients(self, age_years: float, sex: str) -> Dict[str, DRIResult]:
        """Return DRI for all nutrients for a given age/sex."""
        nutrients = ["Energy", "Protein", "Calcium", "Iron", "Zinc", "Vitamin D", "Folate", "Vitamin B12"]
        results: Dict[str, DRIResult] = {}
        for nutrient in nutrients:
            try:
                results[nutrient] = self.get_dri(age_years, sex, nutrient)
            except DRINotFoundError:
                pass
        return results
