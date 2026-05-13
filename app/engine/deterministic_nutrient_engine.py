"""
DeterministicNutrientEngine — orchestrates the full therapy computation pipeline.

Pipeline:
  1. Validate required patient slots (raises TherapyEngineError if missing)
  2. DRI lookup for all 8 nutrients
  3. Condition adjustments (wraps DRI with clinical multipliers)
  4. Drug-nutrient interaction check
  5. Food source mapping
  6. Meal plan generation (uses nutrient_calculator internally)

nutrient_calculator.py is used as the computation core via MealPlanGenerator.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from pydantic import BaseModel

# Core computation library (existing, do not rewrite)
from app.common.nutrient_calculator import (
    convert_fct_rows_to_foods,
    greedy_allocation,
    meal_planner,
    optimize_diet,
)

from app.engine.condition_adjustments import AdjustedTarget, ConditionAdjustmentEngine
from app.engine.dri_lookup import DRILookup
from app.engine.drug_nutrient_interactions import DrugNutrientInteraction, DrugNutrientInteractionChecker
from app.engine.food_source_mapper import FoodSource, FoodSourceMapper
from app.engine.meal_plan_generator import MealPlanDisplay, MealPlanGenerator
from app.state.conversation_state import ConfirmedEntities

logger = logging.getLogger(__name__)

_REQUIRED_SLOTS = ("age", "sex", "weight", "height", "diagnosis")
_NUTRIENTS_FOR_FOOD_MAP = ["Protein", "Iron", "Calcium", "Zinc", "Energy", "Vitamin D", "Vitamin A"]


class TherapyEngineError(Exception):
    pass


class TherapyEngineResult(BaseModel):
    patient_summary: str
    nutrient_targets: List[AdjustedTarget]
    drug_nutrient_notes: List[DrugNutrientInteraction]
    food_sources: Dict[str, List[FoodSource]]
    meal_plan: MealPlanDisplay
    computation_trace: Dict[str, Any]  # INTERNAL ONLY — stripped by DisplayAdapter


class DeterministicNutrientEngine:
    """
    Wraps nutrient_calculator.py and the four engine sub-modules to produce
    a complete, evidence-based therapy plan for a paediatric patient.
    """

    def __init__(self) -> None:
        self._dri = DRILookup()
        self._adjustments = ConditionAdjustmentEngine()
        self._drug_checker = DrugNutrientInteractionChecker()
        self._food_mapper = FoodSourceMapper()
        self._meal_generator = MealPlanGenerator()

    def compute_therapy_plan(self, patient: ConfirmedEntities) -> TherapyEngineResult:
        """
        Compute a full therapy plan.

        Raises TherapyEngineError if any required slot is None.
        """
        self._validate(patient)

        age_years = self._parse_age(patient.age)  # type: ignore[arg-type]
        weight_kg = float(patient.weight)          # type: ignore[arg-type]
        sex = patient.sex.strip().lower()           # type: ignore[union-attr]
        # Convert routing key (e.g. "cystic_fibrosis") back to human form for
        # substring matching in ConditionAdjustmentEngine._CONDITION_HANDLERS.
        diagnosis = patient.diagnosis.strip().replace("_", " ")  # type: ignore[union-attr]
        country = (patient.country or "INT").strip().upper()
        medications = patient.medications or []

        trace: Dict[str, Any] = {
            "age_years": age_years,
            "weight_kg": weight_kg,
            "sex": sex,
            "diagnosis": diagnosis,
            "country": country,
            "medications": medications,
        }

        # Step 1 – DRI baseline
        baseline_dri = self._dri.get_all_nutrients(age_years, sex)
        trace["baseline_dri"] = {k: v.model_dump() for k, v in baseline_dri.items()}

        # Step 2 – Condition adjustments
        adjustment_result = self._adjustments.adjust(baseline_dri, diagnosis, weight_kg)
        adjusted_targets = adjustment_result.adjusted_targets
        trace["adjustments_applied"] = [n.model_dump() for n in adjustment_result.adjustments_applied]

        # Step 3 – Drug-nutrient interactions
        # Empty nutrients list returns all interactions for the medications (no filter)
        drug_notes = self._drug_checker.check(medications, [])
        trace["drug_nutrient_interactions"] = [d.model_dump() for d in drug_notes]

        # Step 4 – Food sources
        nutrient_names = list(adjusted_targets.keys())
        food_sources = self._food_mapper.map_nutrients_to_foods(nutrient_names, country)
        trace["food_sources_country"] = country

        # Step 5 – Meal plan (delegates to nutrient_calculator via MealPlanGenerator)
        meal_plan = self._meal_generator.generate(adjusted_targets, country, days=3)
        trace["meal_plan_days"] = len(meal_plan.days)

        patient_summary = self._build_summary(patient, age_years, weight_kg, diagnosis)

        return TherapyEngineResult(
            patient_summary=patient_summary,
            nutrient_targets=list(adjusted_targets.values()),
            drug_nutrient_notes=drug_notes,
            food_sources=food_sources,
            meal_plan=meal_plan,
            computation_trace=trace,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _validate(self, patient: ConfirmedEntities) -> None:
        missing = [s for s in _REQUIRED_SLOTS if getattr(patient, s) is None]
        if missing:
            raise TherapyEngineError(
                f"Cannot compute therapy plan — missing required slots: {missing}"
            )

    @staticmethod
    def _parse_age(age_str) -> float:
        """Parse age values (int, float, or string like '8 years', '18 months') into decimal years."""
        if isinstance(age_str, (int, float)):
            return float(age_str)
        s = str(age_str).strip().lower()
        if "month" in s:
            digits = "".join(c for c in s if c.isdigit() or c == ".")
            return float(digits) / 12.0 if digits else 0.0
        digits = "".join(c for c in s if c.isdigit() or c == ".")
        return float(digits) if digits else 0.0

    @staticmethod
    def _build_summary(
        patient: ConfirmedEntities,
        age_years: float,
        weight_kg: float,
        diagnosis: str,
    ) -> str:
        meds = ", ".join(patient.medications) if patient.medications else "none"
        return (
            f"{age_years:.1f}y {patient.sex}, {weight_kg} kg, "
            f"diagnosis: {diagnosis}, medications: {meds}"
        )
