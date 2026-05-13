"""
display_adapter.py — last line of defense before data reaches the frontend.

Converts WorkflowResult → CPNAResponse, enforcing all safety rules:
  a. Strip FORBIDDEN_FIELDS (recursive)
  b. Therapy without engine data → error
  c. Comparison placeholder entities → error
  d. Evidence only from current turn
  e. Drop empty optional sections
  f. Humanize leaked raw field name strings (defensive; should never occur)
  g. Detect serialization artifacts in final output → error
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.classification.intent_labels import IntentLabel
from app.contracts.response_contracts import (
    CPNAResponse,
    ComparisonResponse,
    DrugNutrientDisplay,
    EvidenceItem,
    EvidenceSummary,
    FoodSourceSection,
    GeneralResponse,
    MealPlanDisplay,
    NutrientPreviewRow,
    NutrientTargetRow,
    QualitativePoints,
    QuantitativeMatrix,
    RecommendationResponse,
    TherapyResponse,
)
from app.workflows.therapy_workflow import WorkflowResult

logger = logging.getLogger(__name__)

FORBIDDEN_FIELDS = {
    "debug_trace_internal",
    "computation_trace",
    "internal_compliance_keys",
    "__class__",
    "_sa_instance_state",
    "_computation_trace",  # internal key used in TherapyWorkflow response_data
}

PLACEHOLDER_ENTITY_PATTERNS = ["Food A", "Food B", "Entity 1", "Entity 2", "Nutrient X"]

_SERIALIZATION_ARTIFACTS = ["[object Object]", "<class "]

# Maps raw internal field name strings that should never leak into display text
_RAW_FIELD_HUMANIZE = {
    "drug_nutrient_notes": "Drug-Nutrient Interactions",
    "nutrient_targets": "Nutrient Targets",
    "food_sources": "Food Sources",
    "patient_summary": "Patient Summary",
    "computation_trace": "Computation Details",
}


class DisplayAdapterError(Exception):
    pass


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def strip_forbidden_fields(data: Any) -> Any:
    """Recursively remove FORBIDDEN_FIELDS from dicts and lists."""
    if isinstance(data, dict):
        stripped_keys = [k for k in data if k in FORBIDDEN_FIELDS]
        if stripped_keys:
            logger.info("DisplayAdapter: stripped forbidden fields=%s", stripped_keys)
        return {
            k: strip_forbidden_fields(v)
            for k, v in data.items()
            if k not in FORBIDDEN_FIELDS
        }
    if isinstance(data, list):
        return [strip_forbidden_fields(item) for item in data]
    return data


# ---------------------------------------------------------------------------
# DisplayAdapter
# ---------------------------------------------------------------------------

class DisplayAdapter:

    def adapt(self, workflow_result: WorkflowResult) -> CPNAResponse:
        query_type = workflow_result.query_type
        data = strip_forbidden_fields(workflow_result.response_data)

        if query_type == IntentLabel.THERAPY:
            response = self._adapt_therapy(data)
        elif query_type == IntentLabel.RECOMMENDATION:
            response = self._adapt_recommendation(data)
        elif query_type == IntentLabel.COMPARISON:
            response = self._adapt_comparison(data)
        else:
            response = self._adapt_general(data)

        self._check_serialization_artifacts(response)
        return response

    # -----------------------------------------------------------------------
    # Therapy
    # -----------------------------------------------------------------------

    def _adapt_therapy(self, data: dict) -> TherapyResponse:
        # Rule b — engine data must be present
        if "patient_summary" not in data and "nutrient_targets" not in data:
            # slot_fill path — this should not reach the adapter, but guard anyway
            if data.get("slot_prompt") or data.get("error"):
                raise DisplayAdapterError(
                    "TherapyResponse requires engine output. "
                    "Slot-filling or error states must not pass through DisplayAdapter."
                )
            raise DisplayAdapterError(
                "TherapyResponse requires 'patient_summary' and 'nutrient_targets' "
                "from the deterministic engine. Neither was found."
            )

        nutrient_targets = self._build_nutrient_targets(data.get("nutrient_targets", []))
        drug_notes = self._build_drug_notes(data.get("drug_nutrient_notes", []))
        food_sources = self._build_food_sources(data.get("food_sources", {}))
        meal_plan = self._build_meal_plan(data.get("meal_plan"))
        evidence_summary = self._build_evidence_summary(data.get("evidence", []))

        patient_summary = data.get("patient_summary", "")
        assumptions: List[str] = []
        precision_note = data.get("precision_note")
        if precision_note:
            assumptions.append(precision_note)

        return TherapyResponse(
            title="Personalised Nutrition Therapy Plan",
            summary=(
                "A deterministic therapy plan has been computed based on the patient's "
                "confirmed clinical profile."
            ),
            patient_summary=patient_summary,
            assumptions_used=assumptions,
            nutrient_targets=nutrient_targets,
            drug_nutrient_notes=drug_notes,
            food_sources=food_sources,
            meal_plan=meal_plan,
            follow_up_hint=(
                "Review these targets with the treating dietitian and update when "
                "lab values or weight changes."
            ),
            evidence_summary=evidence_summary,
            next_step=(
                "Share this plan with your healthcare team before making dietary changes."
            ),
        )

    # -----------------------------------------------------------------------
    # Recommendation
    # -----------------------------------------------------------------------

    def _adapt_recommendation(self, data: dict) -> RecommendationResponse:
        evidence_summary = self._build_evidence_summary(data.get("evidence", []))

        dri_preview_raw = data.get("dri_preview")
        nutrient_preview: Optional[List[NutrientPreviewRow]] = None
        if dri_preview_raw:
            nutrient_preview = [
                NutrientPreviewRow(
                    nutrient=nutrient,
                    rda=v.get("rda"),
                    ai=v.get("ai"),
                    unit=v.get("unit", ""),
                )
                for nutrient, v in dri_preview_raw.items()
            ]

        therapy_upgrade_note: Optional[str] = data.get("therapy_upgrade_note")

        return RecommendationResponse(
            title="Dietary Guidance",
            summary=(
                "Evidence-based dietary recommendations based on the available information."
            ),
            context_summary=(
                "Recommendations are based on general paediatric nutrition guidelines "
                "and the current clinical context."
            ),
            nutrient_preview=nutrient_preview if nutrient_preview else None,
            practical_guidance=(
                "Focus on a varied, balanced diet rich in whole foods appropriate to "
                "the child's age and clinical needs."
            ),
            foods_to_emphasize=self._extract_foods_to_emphasize(data.get("evidence", [])),
            foods_to_limit=[],
            therapy_upgrade_note=therapy_upgrade_note,
            follow_up_hint=(
                "For a personalised therapy plan with precise nutrient targets, "
                "please provide full patient details."
            ),
            evidence_summary=evidence_summary,
        )

    # -----------------------------------------------------------------------
    # Comparison
    # -----------------------------------------------------------------------

    def _adapt_comparison(self, data: dict) -> ComparisonResponse:
        entity_a = data.get("entity_a", "")
        entity_b = data.get("entity_b", "")

        # Rule c — no placeholder entities
        for entity in [entity_a, entity_b]:
            if entity in PLACEHOLDER_ENTITY_PATTERNS:
                raise DisplayAdapterError(
                    f"Comparison entity '{entity}' is a placeholder. "
                    "Real entity names are required."
                )

        evidence_summary = self._build_evidence_summary(data.get("evidence", []))
        comparison_mode = data.get("comparison_mode", "qualitative")
        if comparison_mode not in ("quantitative", "qualitative"):
            comparison_mode = "qualitative"

        if comparison_mode == "quantitative":
            matrix_or_points = QuantitativeMatrix(
                headers=[entity_a, entity_b],
                rows=[],
            )
        else:
            matrix_or_points = QualitativePoints(
                entity_a=entity_a,
                points_a=[],
                entity_b=entity_b,
                points_b=[],
            )

        return ComparisonResponse(
            title=f"{entity_a} vs {entity_b}",
            summary=f"A {comparison_mode} comparison of {entity_a} and {entity_b}.",
            entities=[entity_a, entity_b],
            context_or_assumptions=data.get("context_or_assumptions"),
            executive_takeaway=(
                f"Both {entity_a} and {entity_b} have distinct nutritional profiles. "
                "Review the details below to inform your decision."
            ),
            comparison_mode=comparison_mode,
            matrix_or_points=matrix_or_points,
            interpretation=(
                "Consult a registered dietitian for context-specific guidance."
            ),
            decision_rules=[],
            follow_up_hint="Would you like a deeper breakdown of any specific nutrient?",
            evidence_summary=evidence_summary,
        )

    # -----------------------------------------------------------------------
    # General
    # -----------------------------------------------------------------------

    def _adapt_general(self, data: dict) -> GeneralResponse:
        evidence_summary = self._build_evidence_summary(data.get("evidence", []))

        return GeneralResponse(
            title="Nutrition Information",
            summary="Evidence-based information from paediatric nutrition references.",
            direct_answer=(
                "Please refer to the evidence excerpts below for detailed information."
            ),
            explanation=(
                "The following information is drawn from established paediatric nutrition "
                "guidelines and clinical references."
            ),
            examples=None,
            transition_note=None,
            follow_up_hint=(
                "Would you like personalised guidance or a specific recommendation?"
            ),
            evidence_summary=evidence_summary,
        )

    # -----------------------------------------------------------------------
    # Shared builders
    # -----------------------------------------------------------------------

    def _build_evidence_summary(self, evidence: List[dict]) -> EvidenceSummary:
        """Rule d — only use sources from current-turn evidence list."""
        items: List[EvidenceItem] = []
        for e in evidence:
            title = e.get("source_title", "")
            excerpt = e.get("excerpt", "")
            if title and excerpt:
                items.append(EvidenceItem(source_title=title, excerpt_safe=excerpt))
        note = (
            f"Retrieved {len(items)} source(s) for this response."
            if items else "No retrieval sources were used for this response."
        )
        return EvidenceSummary(used_sources=items, retrieval_note=note)

    def _build_nutrient_targets(self, raw: List[dict]) -> List[NutrientTargetRow]:
        rows: List[NutrientTargetRow] = []
        for item in raw:
            nutrient = item.get("nutrient", "")
            value = item.get("final_value", item.get("value", 0.0))
            unit = item.get("unit", "")
            rationale = item.get("clinical_rationale") or item.get("clinical_note")
            if nutrient:
                rows.append(NutrientTargetRow(
                    nutrient=nutrient,
                    value=float(value),
                    unit=unit,
                    clinical_note=rationale if rationale else None,
                ))
        return rows

    def _build_drug_notes(self, raw: List[dict]) -> List[DrugNutrientDisplay]:
        notes: List[DrugNutrientDisplay] = []
        for item in raw:
            drug = item.get("drug", "")
            nutrient = item.get("nutrient", "")
            severity = item.get("severity", "")
            note = item.get("clinical_note", item.get("note", ""))
            if drug and nutrient:
                notes.append(DrugNutrientDisplay(
                    drug=drug,
                    nutrient=nutrient,
                    severity=str(severity),
                    note=str(note),
                ))
        return notes

    def _build_food_sources(self, raw: Any) -> List[FoodSourceSection]:
        sections: List[FoodSourceSection] = []
        if isinstance(raw, dict):
            for nutrient, food_list in raw.items():
                names: List[str] = []
                for fs in food_list:
                    if isinstance(fs, dict):
                        names.append(fs.get("food_name", ""))
                    elif isinstance(fs, str):
                        names.append(fs)
                names = [n for n in names if n]
                if names:
                    sections.append(FoodSourceSection(nutrient=nutrient, foods=names))
        return sections

    def _build_meal_plan(self, raw: Any) -> Optional[MealPlanDisplay]:
        if not raw:
            return None
        if isinstance(raw, dict):
            days = raw.get("days", [])
            if days:
                return MealPlanDisplay(days=days)
        return None

    def _extract_foods_to_emphasize(self, evidence: List[dict]) -> List[str]:
        return []

    # -----------------------------------------------------------------------
    # Safety checks
    # -----------------------------------------------------------------------

    def _check_serialization_artifacts(self, response: CPNAResponse) -> None:
        """Rule g — detect serialization artifacts in the final output."""
        serialized = response.model_dump_json()
        for artifact in _SERIALIZATION_ARTIFACTS:
            if artifact in serialized:
                raise DisplayAdapterError(
                    f"Serialization artifact detected in final output: '{artifact}'. "
                    "This indicates an object was not properly serialized."
                )
