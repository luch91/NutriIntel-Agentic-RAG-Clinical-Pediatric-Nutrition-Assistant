"""
Unit tests for the Deterministic Therapy Engine (Prompt 6).
No external API calls, no PDFs, no Redis.
"""

from __future__ import annotations

import pytest

from app.engine.condition_adjustments import ConditionAdjustmentEngine
from app.engine.deterministic_nutrient_engine import (
    DeterministicNutrientEngine,
    TherapyEngineError,
)
from app.engine.dri_lookup import DRILookup, DRINotFoundError
from app.engine.drug_nutrient_interactions import (
    DrugNutrientInteractionChecker,
    InteractionType,
    Severity,
)
from app.engine.food_source_mapper import FoodSourceMapper
from app.state.conversation_state import ConfirmedEntities


# ---------------------------------------------------------------------------
# DRI lookup
# ---------------------------------------------------------------------------

def test_dri_calcium_8yo_female() -> None:
    dri = DRILookup().get_dri(8.0, "female", "Calcium")
    assert dri.rda == 1000.0
    assert dri.unit == "mg/day"
    assert dri.nutrient == "Calcium"


def test_dri_returns_correct_age_band() -> None:
    dri = DRILookup().get_dri(8.0, "female", "Calcium")
    # DRI "4–8 years" group: band spans 4.0–9.0 (exclusive upper bound)
    assert "4" in dri.age_band and "9" in dri.age_band


def test_dri_not_found_raises() -> None:
    with pytest.raises(DRINotFoundError):
        DRILookup().get_dri(25.0, "female", "Calcium")


def test_dri_protein_toddler() -> None:
    dri = DRILookup().get_dri(2.0, "male", "Protein")
    assert dri.rda == 13.0


def test_dri_vitamin_d_uses_ai_for_infant() -> None:
    dri = DRILookup().get_dri(0.3, "female", "Vitamin D")
    assert dri.ai == 400.0
    assert dri.rda is None


# ---------------------------------------------------------------------------
# Condition adjustments
# ---------------------------------------------------------------------------

def test_cf_energy_target_greater_than_baseline() -> None:
    dri_map = DRILookup().get_all_nutrients(8.0, "female")
    result = ConditionAdjustmentEngine().adjust(dri_map, "cystic fibrosis", 25.0)
    baseline_energy = dri_map["Energy"].ai or 0.0
    adjusted_energy = result.adjusted_targets["Energy"].final_value
    assert adjusted_energy > baseline_energy


def test_cf_vitamin_d_doubled() -> None:
    dri_map = DRILookup().get_all_nutrients(8.0, "female")
    result = ConditionAdjustmentEngine().adjust(dri_map, "cystic fibrosis", 25.0)
    vit_d_adjusted = result.adjusted_targets["Vitamin D"].final_value
    vit_d_baseline = dri_map["Vitamin D"].rda or dri_map["Vitamin D"].ai or 0.0
    assert vit_d_adjusted == pytest.approx(vit_d_baseline * 2.0, rel=0.01)


def test_pku_phenylalanine_restriction_flag_present() -> None:
    dri_map = DRILookup().get_all_nutrients(5.0, "male")
    result = ConditionAdjustmentEngine().adjust(dri_map, "PKU", 18.0)
    assert "Phenylalanine_restriction" in result.adjusted_targets
    assert result.adjusted_targets["Phenylalanine_restriction"].final_value == 1.0


def test_pku_tyrosine_supplement_present() -> None:
    dri_map = DRILookup().get_all_nutrients(5.0, "male")
    result = ConditionAdjustmentEngine().adjust(dri_map, "PKU", 18.0)
    assert "Tyrosine_supplement" in result.adjusted_targets


def test_ckd_protein_restricted() -> None:
    dri_map = DRILookup().get_all_nutrients(10.0, "male")
    baseline_protein = dri_map["Protein"].rda
    result = ConditionAdjustmentEngine().adjust(dri_map, "chronic kidney disease", 30.0)
    assert result.adjusted_targets["Protein"].final_value < baseline_protein


def test_ketogenic_carbohydrate_limit_set() -> None:
    dri_map = DRILookup().get_all_nutrients(8.0, "female")
    result = ConditionAdjustmentEngine().adjust(dri_map, "epilepsy", 25.0)
    assert "Carbohydrate_limit" in result.adjusted_targets
    assert result.adjusted_targets["Carbohydrate_limit"].final_value == 10.0


def test_no_matching_condition_returns_standard_dri() -> None:
    dri_map = DRILookup().get_all_nutrients(8.0, "female")
    result = ConditionAdjustmentEngine().adjust(dri_map, "food allergy", 25.0)
    # No adjustments applied — energy unchanged
    assert result.adjusted_targets["Energy"].adjustment_factor == 1.0
    assert len(result.adjustments_applied) == 0


# ---------------------------------------------------------------------------
# Drug-nutrient interactions
# ---------------------------------------------------------------------------

def test_metformin_b12_high_severity() -> None:
    checker = DrugNutrientInteractionChecker()
    results = checker.check(["metformin"], ["Vitamin B12"])
    assert len(results) == 1
    assert results[0].severity == Severity.HIGH
    assert results[0].interaction_type == InteractionType.DEPLETION
    assert results[0].nutrient == "Vitamin B12"


def test_creon_absorption_note_not_depletion() -> None:
    checker = DrugNutrientInteractionChecker()
    results = checker.check(["creon"], [])
    assert len(results) == 1
    assert results[0].interaction_type == InteractionType.ABSORPTION_EFFECT
    assert results[0].severity == Severity.LOW


def test_anticonvulsant_vitamin_d_depletion() -> None:
    checker = DrugNutrientInteractionChecker()
    results = checker.check(["carbamazepine"], ["Vitamin D"])
    assert any(r.nutrient == "Vitamin D" and r.severity == Severity.MODERATE for r in results)


def test_corticosteroid_calcium_depletion() -> None:
    checker = DrugNutrientInteractionChecker()
    results = checker.check(["prednisolone"], ["Calcium"])
    assert any(r.nutrient == "Calcium" for r in results)


def test_no_interaction_for_unknown_drug() -> None:
    checker = DrugNutrientInteractionChecker()
    results = checker.check(["paracetamol"], ["Iron"])
    assert results == []


# ---------------------------------------------------------------------------
# Food source mapper
# ---------------------------------------------------------------------------

def test_ng_iron_includes_liver_and_crayfish() -> None:
    mapper = FoodSourceMapper()
    result = mapper.map_nutrients_to_foods(["Iron"], "NG")
    food_names = [f.food_name.lower() for f in result["Iron"]]
    assert any("liver" in n for n in food_names)
    assert any("crayfish" in n for n in food_names)


def test_ng_calcium_includes_moringa() -> None:
    mapper = FoodSourceMapper()
    result = mapper.map_nutrients_to_foods(["Calcium"], "NG")
    food_names = [f.food_name.lower() for f in result["Calcium"]]
    assert any("moringa" in n for n in food_names)


def test_international_country_no_ng_specific_foods() -> None:
    mapper = FoodSourceMapper()
    result = mapper.map_nutrients_to_foods(["Iron"], "US")
    food_names = [f.food_name.lower() for f in result.get("Iron", [])]
    # crayfish and moringa are NG-specific — should not appear for US
    assert not any("crayfish" in n for n in food_names)


# ---------------------------------------------------------------------------
# DeterministicNutrientEngine
# ---------------------------------------------------------------------------

def _make_patient(**overrides) -> ConfirmedEntities:
    defaults = dict(age="8", sex="female", weight="25", height="128", diagnosis="cystic fibrosis", medications=["creon"])
    defaults.update(overrides)
    return ConfirmedEntities(**defaults)


def test_engine_raises_when_age_none() -> None:
    engine = DeterministicNutrientEngine()
    patient = _make_patient(age=None)
    with pytest.raises(TherapyEngineError):
        engine.compute_therapy_plan(patient)


def test_engine_raises_when_diagnosis_none() -> None:
    engine = DeterministicNutrientEngine()
    patient = _make_patient(diagnosis=None)
    with pytest.raises(TherapyEngineError):
        engine.compute_therapy_plan(patient)


def test_computation_trace_present() -> None:
    engine = DeterministicNutrientEngine()
    patient = _make_patient()
    result = engine.compute_therapy_plan(patient)
    assert isinstance(result.computation_trace, dict)
    assert "baseline_dri" in result.computation_trace


def test_nutrient_targets_returned() -> None:
    engine = DeterministicNutrientEngine()
    patient = _make_patient()
    result = engine.compute_therapy_plan(patient)
    assert len(result.nutrient_targets) > 0


def test_drug_notes_present_for_creon() -> None:
    engine = DeterministicNutrientEngine()
    patient = _make_patient(medications=["creon"])
    result = engine.compute_therapy_plan(patient)
    assert len(result.drug_nutrient_notes) > 0
    assert any("creon" in n.drug.lower() for n in result.drug_nutrient_notes)


def test_patient_summary_contains_diagnosis() -> None:
    engine = DeterministicNutrientEngine()
    patient = _make_patient()
    result = engine.compute_therapy_plan(patient)
    assert "cystic fibrosis" in result.patient_summary.lower()
