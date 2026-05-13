"""
ConditionAdjustmentEngine — applies condition-specific multipliers and clinical rules
on top of baseline DRI values.

nutrient_calculator.py has no condition adjustment logic; all rules are new here.
"""

from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel

from app.engine.dri_lookup import DRIResult


class AdjustedTarget(BaseModel):
    nutrient: str
    final_value: float
    unit: str
    adjustment_factor: float  # 1.0 = no change
    clinical_rationale: str


class AdjustmentNote(BaseModel):
    nutrient: str
    rule_applied: str
    source: str


class AdjustmentResult(BaseModel):
    adjusted_targets: Dict[str, AdjustedTarget]
    adjustments_applied: List[AdjustmentNote]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _baseline_targets(baseline_dri: Dict[str, DRIResult]) -> Dict[str, AdjustedTarget]:
    targets: Dict[str, AdjustedTarget] = {}
    for nutrient, dri in baseline_dri.items():
        ref_value = dri.rda if dri.rda is not None else (dri.ai or 0.0)
        targets[nutrient] = AdjustedTarget(
            nutrient=nutrient,
            final_value=ref_value,
            unit=dri.unit,
            adjustment_factor=1.0,
            clinical_rationale="Standard DRI",
        )
    return targets


def _apply_cf(targets: Dict[str, AdjustedTarget], notes: List[AdjustmentNote], weight_kg: float) -> None:
    source = "ESPGHAN 2016 CF Nutrition Consensus"
    if "Energy" in targets:
        t = targets["Energy"]
        factor = 1.30
        targets["Energy"] = t.model_copy(update={
            "final_value": round(t.final_value * factor, 1),
            "adjustment_factor": factor,
            "clinical_rationale": "CF: energy requirement 120–150% EER due to malabsorption and increased respiratory work",
        })
        notes.append(AdjustmentNote(nutrient="Energy", rule_applied="CF energy 130% EER", source=source))

    # Fat-soluble vitamins ADEK: 2× RDA
    for vit in ("Vitamin A", "Vitamin D", "Vitamin E", "Vitamin K"):
        if vit in targets:
            t = targets[vit]
            targets[vit] = t.model_copy(update={
                "final_value": round(t.final_value * 2.0, 1),
                "adjustment_factor": 2.0,
                "clinical_rationale": f"CF: fat-soluble vitamin {vit} at 2× RDA due to fat malabsorption",
            })
            notes.append(AdjustmentNote(nutrient=vit, rule_applied="CF fat-soluble vitamins 2× RDA", source=source))

    if "Vitamin D" in targets and not any(n.nutrient == "Vitamin D" for n in notes):
        t = targets["Vitamin D"]
        targets["Vitamin D"] = t.model_copy(update={
            "final_value": round(t.final_value * 2.0, 1),
            "adjustment_factor": 2.0,
            "clinical_rationale": "CF: Vitamin D at 2× RDA due to fat malabsorption",
        })
        notes.append(AdjustmentNote(nutrient="Vitamin D", rule_applied="CF fat-soluble vitamins 2× RDA", source=source))


def _apply_t1dm(targets: Dict[str, AdjustedTarget], notes: List[AdjustmentNote], weight_kg: float) -> None:
    source = "ISPAD 2022 Nutrition Guidelines"
    if "Energy" in targets:
        t = targets["Energy"]
        targets["Energy"] = t.model_copy(update={
            "clinical_rationale": "T1DM: standard EER; distribute carbohydrates evenly across meals with insulin-to-carb ratio guidance",
        })
        notes.append(AdjustmentNote(
            nutrient="Energy",
            rule_applied="T1DM: standard DRI, carbohydrate timing note",
            source=source,
        ))


def _apply_ckd(targets: Dict[str, AdjustedTarget], notes: List[AdjustmentNote], weight_kg: float) -> None:
    source = "KDOQI Pediatric CKD Nutrition 2009"
    if "Protein" in targets:
        t = targets["Protein"]
        factor = 0.90
        targets["Protein"] = t.model_copy(update={
            "final_value": round(t.final_value * factor, 1),
            "adjustment_factor": factor,
            "clinical_rationale": "CKD: protein restricted to 80–100% DRI to reduce uraemic load; adjust per GFR stage",
        })
        notes.append(AdjustmentNote(nutrient="Protein", rule_applied="CKD protein restriction 90% DRI", source=source))

    potassium_limit = round(weight_kg * 40, 1)
    targets["Potassium_limit"] = AdjustedTarget(
        nutrient="Potassium_limit",
        final_value=potassium_limit,
        unit="mg/day",
        adjustment_factor=1.0,
        clinical_rationale="CKD: potassium restriction ~40 mg/kg/day depending on serum levels",
    )
    notes.append(AdjustmentNote(nutrient="Potassium", rule_applied="CKD potassium limit 40 mg/kg/day", source=source))

    phosphorus_limit = round(weight_kg * 20, 1)
    targets["Phosphorus_limit"] = AdjustedTarget(
        nutrient="Phosphorus_limit",
        final_value=phosphorus_limit,
        unit="mg/day",
        adjustment_factor=1.0,
        clinical_rationale="CKD: phosphorus restriction ~20 mg/kg/day to prevent hyperphosphataemia",
    )
    notes.append(AdjustmentNote(nutrient="Phosphorus", rule_applied="CKD phosphorus limit 20 mg/kg/day", source=source))


def _apply_pku(targets: Dict[str, AdjustedTarget], notes: List[AdjustmentNote], weight_kg: float) -> None:
    source = "ACMG PKU Management Guidelines 2018"
    targets["Phenylalanine_restriction"] = AdjustedTarget(
        nutrient="Phenylalanine_restriction",
        final_value=1.0,
        unit="flag",
        adjustment_factor=1.0,
        clinical_rationale="PKU: phenylalanine strictly restricted; use Phe-free amino acid formula as primary protein source",
    )
    notes.append(AdjustmentNote(
        nutrient="Phenylalanine",
        rule_applied="PKU: severe phenylalanine restriction",
        source=source,
    ))
    targets["Tyrosine_supplement"] = AdjustedTarget(
        nutrient="Tyrosine_supplement",
        final_value=1.0,
        unit="flag",
        adjustment_factor=1.0,
        clinical_rationale="PKU: tyrosine becomes conditionally essential; supplement via medical formula",
    )
    notes.append(AdjustmentNote(
        nutrient="Tyrosine",
        rule_applied="PKU: tyrosine supplementation required",
        source=source,
    ))


def _apply_ketogenic(targets: Dict[str, AdjustedTarget], notes: List[AdjustmentNote], weight_kg: float) -> None:
    source = "Charlie Foundation Ketogenic Diet Protocol"
    if "Energy" in targets:
        energy_kcal = targets["Energy"].final_value
        fat_g = round(energy_kcal * 0.80 / 9.0, 1)
        targets["Fat_ketogenic"] = AdjustedTarget(
            nutrient="Fat_ketogenic",
            final_value=fat_g,
            unit="g/day",
            adjustment_factor=1.0,
            clinical_rationale="Epilepsy/Ketogenic: fat supplies 70–90% of total energy; classical 4:1 ratio",
        )
        notes.append(AdjustmentNote(nutrient="Fat", rule_applied="Ketogenic 80% energy from fat", source=source))

    targets["Carbohydrate_limit"] = AdjustedTarget(
        nutrient="Carbohydrate_limit",
        final_value=10.0,
        unit="g/day",
        adjustment_factor=1.0,
        clinical_rationale="Epilepsy/Ketogenic: carbohydrate strictly <10 g/day to maintain ketosis",
    )
    notes.append(AdjustmentNote(nutrient="Carbohydrate", rule_applied="Ketogenic CHO <10 g/day", source=source))


_CONDITION_HANDLERS = {
    "cystic fibrosis": _apply_cf,
    "type 1 diabetes": _apply_t1dm,
    "t1dm": _apply_t1dm,
    "chronic kidney disease": _apply_ckd,
    "ckd": _apply_ckd,
    "pku": _apply_pku,
    "phenylketonuria": _apply_pku,
    "epilepsy": _apply_ketogenic,
    "ketogenic": _apply_ketogenic,
}


class ConditionAdjustmentEngine:
    """Applies evidence-based condition adjustments to baseline DRI targets."""

    def adjust(
        self,
        baseline_dri: Dict[str, DRIResult],
        diagnosis: str,
        weight_kg: float,
    ) -> AdjustmentResult:
        targets = _baseline_targets(baseline_dri)
        notes: List[AdjustmentNote] = []

        diagnosis_lower = diagnosis.strip().lower()
        for key, fn in _CONDITION_HANDLERS.items():
            if key in diagnosis_lower:
                fn(targets, notes, weight_kg)
                break

        return AdjustmentResult(adjusted_targets=targets, adjustments_applied=notes)
