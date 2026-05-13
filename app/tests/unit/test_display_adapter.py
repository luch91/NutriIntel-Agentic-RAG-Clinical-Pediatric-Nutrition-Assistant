"""
Unit tests for Prompt 8 — Response Contracts and DisplayAdapter.

Tests:
  1. Valid therapy workflow result → TherapyResponse with correct fields
  2. Workflow result with debug_trace_internal → field absent from adapted output
  3. Comparison with "Food A" entity → raises DisplayAdapterError
  4. Therapy query_type but no engine result → raises DisplayAdapterError
  5. Evidence matches only current-turn passages (not prior turn)
  6. Empty optional fields (None nutrient_preview) → absent from output, no KeyError
"""

from app.classification.intent_labels import IntentLabel
from app.contracts.display_adapter import DisplayAdapter, DisplayAdapterError, strip_forbidden_fields
from app.contracts.response_contracts import (
    ComparisonResponse,
    GeneralResponse,
    RecommendationResponse,
    TherapyResponse,
)
from app.workflows.therapy_workflow import WorkflowResult


# ---------------------------------------------------------------------------
# Helpers — build WorkflowResult stubs
# ---------------------------------------------------------------------------

def _therapy_result(include_engine_data: bool = True, extra_keys: dict = None) -> WorkflowResult:
    data = {}
    if include_engine_data:
        data = {
            "patient_summary": "10.0y male, 30 kg, diagnosis: type 1 diabetes, medications: none",
            "nutrient_targets": [
                {
                    "nutrient": "Energy",
                    "final_value": 1800.0,
                    "unit": "kcal/day",
                    "clinical_rationale": "Standard DRI with 1.2x activity factor",
                },
                {
                    "nutrient": "Protein",
                    "final_value": 55.0,
                    "unit": "g/day",
                    "clinical_rationale": "Base DRI",
                },
            ],
            "drug_nutrient_notes": [
                {
                    "drug": "metformin",
                    "nutrient": "Vitamin B12",
                    "severity": "MODERATE",
                    "clinical_note": "Monitor B12 annually",
                }
            ],
            "food_sources": {
                "Energy": [{"food_name": "Rice", "nutrient_content_per_100g": 130.0, "unit": "kcal"}],
                "Protein": [{"food_name": "Beans", "nutrient_content_per_100g": 9.0, "unit": "g"}],
            },
            "meal_plan": {
                "days": [
                    {
                        "day": 1,
                        "meals": [
                            {"meal_name": "Breakfast", "foods": ["Oats"], "estimated_nutrients": {"Energy": 300.0}}
                        ],
                    }
                ]
            },
            "evidence": [
                {"source_title": "Shaw 2020", "excerpt": "T1D dietary management guidelines."},
            ],
            "precision_note": None,
        }
    if extra_keys:
        data.update(extra_keys)
    return WorkflowResult(
        response_data=data,
        query_type=IntentLabel.THERAPY,
        updated_state=None,
    )


def _recommendation_result(include_dri: bool = False, therapy_upgrade: bool = False) -> WorkflowResult:
    data: dict = {
        "query_type": "recommendation",
        "evidence": [
            {"source_title": "Oxford Handbook 2012", "excerpt": "Iron-rich foods for children."},
        ],
    }
    if include_dri:
        data["dri_preview"] = {
            "Energy": {"rda": 1600.0, "ai": None, "unit": "kcal/day", "age_band": "4.0-9.0y"},
            "Protein": {"rda": 19.0, "ai": None, "unit": "g/day", "age_band": "4.0-9.0y"},
        }
    if therapy_upgrade:
        data["therapy_upgrade_note"] = (
            "To receive a personalised therapy plan, please provide full patient details."
        )
    return WorkflowResult(
        response_data=data,
        query_type=IntentLabel.RECOMMENDATION,
        updated_state=None,
    )


def _comparison_result(entity_a: str = "Rice", entity_b: str = "Bread") -> WorkflowResult:
    return WorkflowResult(
        response_data={
            "entity_a": entity_a,
            "entity_b": entity_b,
            "comparison_mode": "qualitative",
            "context_inherited": False,
            "inherited_fields": [],
            "evidence": [],
        },
        query_type=IntentLabel.COMPARISON,
        updated_state=None,
    )


def _general_result() -> WorkflowResult:
    return WorkflowResult(
        response_data={
            "query_type": "general",
            "evidence": [
                {"source_title": "DRI 2006", "excerpt": "Micronutrient requirements overview."},
            ],
        },
        query_type=IntentLabel.GENERAL,
        updated_state=None,
    )


# ---------------------------------------------------------------------------
# Test 1 — Valid therapy result → TherapyResponse with correct fields
# ---------------------------------------------------------------------------

def test_therapy_result_produces_therapy_response():
    adapter = DisplayAdapter()
    result = adapter.adapt(_therapy_result())

    assert isinstance(result, TherapyResponse)
    assert result.query_type == "therapy"
    assert "10.0y" in result.patient_summary
    assert len(result.nutrient_targets) == 2
    assert result.nutrient_targets[0].nutrient == "Energy"
    assert result.nutrient_targets[0].value == 1800.0
    assert result.nutrient_targets[0].unit == "kcal/day"
    assert len(result.drug_nutrient_notes) == 1
    assert result.drug_nutrient_notes[0].drug == "metformin"
    assert len(result.food_sources) == 2
    assert result.meal_plan is not None
    assert len(result.meal_plan.days) == 1
    assert result.evidence_summary.used_sources[0].source_title == "Shaw 2020"
    # Internal IDs must not be present
    assert not hasattr(result, "source_id")
    assert not hasattr(result, "computation_trace")
    assert not hasattr(result, "debug_trace_internal")


# ---------------------------------------------------------------------------
# Test 2 — debug_trace_internal stripped from output
# ---------------------------------------------------------------------------

def test_forbidden_field_debug_trace_stripped():
    adapter = DisplayAdapter()
    result_with_trace = _therapy_result(extra_keys={
        "debug_trace_internal": {"internal_key": "SECRET"},
        "_computation_trace": {"step": "dri_lookup"},
    })
    response = adapter.adapt(result_with_trace)

    # Serialized output must not contain the forbidden field value
    serialized = response.model_dump_json()
    assert "SECRET" not in serialized
    assert "debug_trace_internal" not in serialized
    assert "_computation_trace" not in serialized


def test_strip_forbidden_fields_recursive():
    data = {
        "safe_key": "value",
        "debug_trace_internal": {"nested": "secret"},
        "nested_dict": {
            "computation_trace": "trace_data",
            "safe_nested": 42,
        },
        "list_field": [
            {"debug_trace_internal": "in_list", "keep": "this"},
        ],
    }
    cleaned = strip_forbidden_fields(data)
    assert "safe_key" in cleaned
    assert "debug_trace_internal" not in cleaned
    assert "computation_trace" not in cleaned["nested_dict"]
    assert cleaned["nested_dict"]["safe_nested"] == 42
    assert "debug_trace_internal" not in cleaned["list_field"][0]
    assert cleaned["list_field"][0]["keep"] == "this"


# ---------------------------------------------------------------------------
# Test 3 — Comparison with "Food A" → raises DisplayAdapterError
# ---------------------------------------------------------------------------

def test_comparison_placeholder_entity_raises():
    adapter = DisplayAdapter()
    result = _comparison_result(entity_a="Food A", entity_b="Bread")
    try:
        adapter.adapt(result)
        assert False, "Expected DisplayAdapterError"
    except DisplayAdapterError as exc:
        assert "placeholder" in str(exc).lower() or "Food A" in str(exc)


def test_comparison_placeholder_entity_b_raises():
    adapter = DisplayAdapter()
    result = _comparison_result(entity_a="Rice", entity_b="Food B")
    try:
        adapter.adapt(result)
        assert False, "Expected DisplayAdapterError"
    except DisplayAdapterError as exc:
        assert "placeholder" in str(exc).lower() or "Food B" in str(exc)


def test_comparison_real_entities_succeeds():
    adapter = DisplayAdapter()
    result = _comparison_result(entity_a="Rice", entity_b="Yam")
    response = adapter.adapt(result)
    assert isinstance(response, ComparisonResponse)
    assert response.entities == ["Rice", "Yam"]
    assert "Food A" not in response.entities
    assert "Food B" not in response.entities


# ---------------------------------------------------------------------------
# Test 4 — Therapy query_type but no engine result → raises DisplayAdapterError
# ---------------------------------------------------------------------------

def test_therapy_without_engine_data_raises():
    adapter = DisplayAdapter()
    result = _therapy_result(include_engine_data=False)
    try:
        adapter.adapt(result)
        assert False, "Expected DisplayAdapterError"
    except DisplayAdapterError as exc:
        assert "TherapyResponse requires" in str(exc) or "engine" in str(exc).lower()


def test_therapy_with_slot_prompt_raises():
    adapter = DisplayAdapter()
    result = WorkflowResult(
        response_data={"slot_prompt": "How old is your child?"},
        query_type=IntentLabel.THERAPY,
        updated_state=None,
    )
    try:
        adapter.adapt(result)
        assert False, "Expected DisplayAdapterError"
    except DisplayAdapterError:
        pass


# ---------------------------------------------------------------------------
# Test 5 — Evidence only from current-turn passages
# ---------------------------------------------------------------------------

def test_evidence_only_from_current_turn():
    adapter = DisplayAdapter()
    current_evidence = [
        {"source_title": "Shaw 2020", "excerpt": "Current turn excerpt."},
    ]
    result = WorkflowResult(
        response_data={
            "patient_summary": "Test patient",
            "nutrient_targets": [{"nutrient": "Iron", "final_value": 8.0, "unit": "mg/day"}],
            "drug_nutrient_notes": [],
            "food_sources": {},
            "meal_plan": None,
            "evidence": current_evidence,
            "precision_note": None,
        },
        query_type=IntentLabel.THERAPY,
        updated_state=None,
    )
    response = adapter.adapt(result)
    assert isinstance(response, TherapyResponse)
    assert len(response.evidence_summary.used_sources) == 1
    assert response.evidence_summary.used_sources[0].source_title == "Shaw 2020"
    assert response.evidence_summary.used_sources[0].excerpt_safe == "Current turn excerpt."
    # source_id field must not exist on EvidenceItem
    assert not hasattr(response.evidence_summary.used_sources[0], "source_id")


def test_evidence_item_has_no_internal_ids():
    adapter = DisplayAdapter()
    result = _general_result()
    response = adapter.adapt(result)
    assert isinstance(response, GeneralResponse)
    for ev in response.evidence_summary.used_sources:
        ev_dict = ev.model_dump()
        assert "source_id" not in ev_dict
        assert "passage_id" not in ev_dict
        assert "internal" not in " ".join(ev_dict.keys()).lower()


# ---------------------------------------------------------------------------
# Test 6 — Empty optional fields → absent from output, no KeyError
# ---------------------------------------------------------------------------

def test_recommendation_without_dri_preview_no_error():
    adapter = DisplayAdapter()
    result = _recommendation_result(include_dri=False)
    response = adapter.adapt(result)
    assert isinstance(response, RecommendationResponse)
    # nutrient_preview should be None (optional field absent)
    assert response.nutrient_preview is None


def test_recommendation_with_dri_preview_populated():
    adapter = DisplayAdapter()
    result = _recommendation_result(include_dri=True)
    response = adapter.adapt(result)
    assert isinstance(response, RecommendationResponse)
    assert response.nutrient_preview is not None
    assert len(response.nutrient_preview) == 2
    nutrients = {row.nutrient for row in response.nutrient_preview}
    assert "Energy" in nutrients
    assert "Protein" in nutrients


def test_therapy_upgrade_note_present_when_downgraded():
    adapter = DisplayAdapter()
    result = _recommendation_result(therapy_upgrade=True)
    response = adapter.adapt(result)
    assert isinstance(response, RecommendationResponse)
    assert response.therapy_upgrade_note is not None
    assert "personalised therapy plan" in response.therapy_upgrade_note.lower()


def test_therapy_meal_plan_none_is_optional():
    adapter = DisplayAdapter()
    result = WorkflowResult(
        response_data={
            "patient_summary": "Test patient",
            "nutrient_targets": [{"nutrient": "Iron", "final_value": 8.0, "unit": "mg/day"}],
            "drug_nutrient_notes": [],
            "food_sources": {},
            "meal_plan": None,
            "evidence": [],
            "precision_note": None,
        },
        query_type=IntentLabel.THERAPY,
        updated_state=None,
    )
    response = adapter.adapt(result)
    assert isinstance(response, TherapyResponse)
    assert response.meal_plan is None


# ---------------------------------------------------------------------------
# Test 7 — General and Recommendation responses are well-formed
# ---------------------------------------------------------------------------

def test_general_response_is_well_formed():
    adapter = DisplayAdapter()
    response = adapter.adapt(_general_result())
    assert isinstance(response, GeneralResponse)
    assert response.query_type == "general"
    assert response.title
    assert response.direct_answer
    assert response.follow_up_hint
    assert isinstance(response.evidence_summary.used_sources, list)


def test_recommendation_response_is_well_formed():
    adapter = DisplayAdapter()
    response = adapter.adapt(_recommendation_result())
    assert isinstance(response, RecommendationResponse)
    assert response.query_type == "recommendation"
    assert isinstance(response.foods_to_emphasize, list)
    assert isinstance(response.foods_to_limit, list)
    assert response.follow_up_hint
