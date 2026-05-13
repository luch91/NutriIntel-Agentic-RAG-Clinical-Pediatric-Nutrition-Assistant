"""
response_contracts.py — canonical display-safe response shapes for CPNA v1.

These are the ONLY shapes the frontend ever receives.
Raw orchestration objects must NEVER reach the frontend — all output goes
through DisplayAdapter first, which builds one of these models.

Import rule: app/api/ and app/contracts/display_adapter.py import from here.
No other layer should return these directly.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class NutrientTargetRow(BaseModel):
    nutrient: str
    value: float
    unit: str
    clinical_note: Optional[str] = None


class NutrientPreviewRow(BaseModel):
    nutrient: str
    rda: Optional[float] = None
    ai: Optional[float] = None
    unit: str


class DrugNutrientDisplay(BaseModel):
    drug: str
    nutrient: str
    severity: str
    note: str


class FoodSourceSection(BaseModel):
    nutrient: str
    foods: List[str]


class MealPlanDisplay(BaseModel):
    days: List[dict]


class QuantitativeMatrix(BaseModel):
    headers: List[str]
    rows: List[dict]


class QualitativePoints(BaseModel):
    entity_a: str
    points_a: List[str]
    entity_b: str
    points_b: List[str]


class EvidenceItem(BaseModel):
    """Display-safe evidence. source_id and internal identifiers are NEVER included."""
    source_title: str
    excerpt_safe: str


class EvidenceSummary(BaseModel):
    used_sources: List[EvidenceItem]
    retrieval_note: str


# ---------------------------------------------------------------------------
# Top-level response contracts
# ---------------------------------------------------------------------------

class RecommendationResponse(BaseModel):
    query_type: Literal["recommendation"] = "recommendation"
    title: str
    summary: str
    context_summary: str
    nutrient_preview: Optional[List[NutrientPreviewRow]] = None
    practical_guidance: str
    foods_to_emphasize: List[str]
    foods_to_limit: List[str]
    therapy_upgrade_note: Optional[str] = None
    follow_up_hint: str
    evidence_summary: EvidenceSummary


class TherapyResponse(BaseModel):
    query_type: Literal["therapy"] = "therapy"
    title: str
    summary: str
    patient_summary: str
    assumptions_used: List[str]
    nutrient_targets: List[NutrientTargetRow]
    drug_nutrient_notes: List[DrugNutrientDisplay]
    food_sources: List[FoodSourceSection]
    meal_plan: Optional[MealPlanDisplay] = None
    follow_up_hint: str
    evidence_summary: EvidenceSummary
    next_step: str


class ComparisonResponse(BaseModel):
    query_type: Literal["comparison"] = "comparison"
    title: str
    summary: str
    entities: List[str]  # MUST be real names — never "Food A"
    context_or_assumptions: Optional[str] = None
    executive_takeaway: str
    comparison_mode: Literal["quantitative", "qualitative"]
    matrix_or_points: Union[QuantitativeMatrix, QualitativePoints]
    interpretation: str
    decision_rules: List[str]
    follow_up_hint: str
    evidence_summary: EvidenceSummary


class GeneralResponse(BaseModel):
    query_type: Literal["general"] = "general"
    title: str
    summary: str
    direct_answer: str
    explanation: str
    examples: Optional[List[str]] = None
    transition_note: Optional[str] = None
    follow_up_hint: str
    evidence_summary: EvidenceSummary


# ---------------------------------------------------------------------------
# Union type — the only shape that should cross the API boundary
# ---------------------------------------------------------------------------

CPNAResponse = Union[TherapyResponse, RecommendationResponse, ComparisonResponse, GeneralResponse]
