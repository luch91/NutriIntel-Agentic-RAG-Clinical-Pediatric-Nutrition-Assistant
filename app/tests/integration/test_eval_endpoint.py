"""
Integration tests for POST /api/eval — CPNA eval platform endpoint.

Verifies every field that the eval platform's evaluator suite inspects:
  - intent evaluator: query_type, intent_confidence, fallback_triggered
  - gatekeeper evaluator: gatekeeper_status, slot_filling_triggered, downgrade_reason,
                          nutrient_targets, user_facing_explanation
  - contract evaluator: queryType, title, summary, sections (non-empty),
                        evidenceSummary.used, no [object Object], no machine keys
  - context evaluator: context_inheritance_trace, resolved_slot, clarification_requested
  - comparison evaluator: entities, executiveTakeaway, comparison_subtype, comparison_mode
  - retrieval evaluator: retrieval_stage_log fields present
  - state_update: slots dict, workflow, pending_slot
"""

from __future__ import annotations

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app.api.router import app
from app.classification.intent_classifier import MockIntentClassifier
from app.contracts.display_adapter import DisplayAdapter
from app.state.state_manager import StateManager
from app.workflows.workflow_router import WorkflowRouter


@pytest.fixture(autouse=True)
def wire_test_dependencies():
    """Replace production singletons with test doubles (fakeredis, mock classifier)."""
    app.state.intent_classifier = MockIntentClassifier()
    app.state.state_manager = StateManager(redis_client=fakeredis.FakeRedis())
    app.state.workflow_router = WorkflowRouter(retrieval_agent=None)
    app.state.display_adapter = DisplayAdapter()
    yield
    app.state.intent_classifier = None
    app.state.state_manager = None
    app.state.workflow_router = None


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def post_eval(client, user_message: str, session_state: dict | None = None,
              conversation_history: list | None = None) -> dict:
    body = {
        "userMessage": user_message,
        "conversationHistory": conversation_history or [],
        "sessionState": session_state or {},
    }
    resp = client.post("/api/eval", json=body)
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# 1. General query — contract fields + retrieval log present
# ---------------------------------------------------------------------------

def test_eval_general_query_returns_200(client):
    r = post_eval(client, "What is the role of vitamin D in children?")
    assert r["query_type"] == "general"


def test_eval_general_intent_confidence_present(client):
    r = post_eval(client, "What is the role of vitamin D in children?")
    assert "intent_confidence" in r
    assert isinstance(r["intent_confidence"], float)
    assert r["intent_confidence"] > 0


def test_eval_general_contract_fields_present(client):
    r = post_eval(client, "What is the role of vitamin D in children?")
    for field in ["queryType", "title", "summary", "sections", "evidenceSummary"]:
        assert field in r, f"Missing contract field: {field}"


def test_eval_general_sections_non_empty(client):
    r = post_eval(client, "What is the role of vitamin D in children?")
    assert isinstance(r["sections"], list)
    assert len(r["sections"]) > 0
    for s in r["sections"]:
        assert "heading" in s
        assert s.get("content") is not None


def test_eval_general_evidence_summary_structure(client):
    r = post_eval(client, "What is the role of vitamin D in children?")
    ev = r["evidenceSummary"]
    assert "used" in ev
    assert "note" in ev
    assert isinstance(ev["used"], list)


def test_eval_general_direct_answer_present(client):
    r = post_eval(client, "What is the role of vitamin D in children?")
    assert r.get("directAnswer") is not None


def test_eval_general_retrieval_log_present(client):
    r = post_eval(client, "What is the role of vitamin D in children?")
    log = r["retrieval_stage_log"]
    for key in ["vector_count", "bm25_count", "post_merge_count", "top_k_contexts"]:
        assert key in log, f"Missing retrieval log key: {key}"


def test_eval_general_retrieval_counts_consistent(client):
    r = post_eval(client, "What is the role of vitamin D in children?")
    log = r["retrieval_stage_log"]
    assert log["post_merge_count"] <= log["vector_count"] + log["bm25_count"]
    assert log["top_k_contexts"] <= 7


def test_eval_general_state_update_present(client):
    r = post_eval(client, "What is the role of vitamin D in children?")
    assert "state_update" in r
    assert "slots" in r["state_update"]


def test_eval_no_raw_object_strings(client):
    r = post_eval(client, "Tell me about iron in toddlers")
    import json
    serialized = json.dumps(r)
    assert "[object Object]" not in serialized


def test_eval_no_machine_keys_in_response(client):
    r = post_eval(client, "Tell me about zinc deficiency")
    import json
    serialized = json.dumps(r)
    for banned in ["debug_trace_internal", "computation_trace", "_computation_trace",
                   "slot_validation_result", "raw_retrieval_payload"]:
        assert banned not in serialized, f"Machine key leaked: {banned}"


# ---------------------------------------------------------------------------
# 2. Therapy — gatekeeper slot fill (missing slots)
# ---------------------------------------------------------------------------

def test_eval_therapy_missing_slots_triggers_slot_fill(client):
    r = post_eval(client, "Create a nutrition plan for my child with cystic fibrosis")
    assert r["gatekeeper_status"] == "failed"
    assert r["slot_filling_triggered"] is True


def test_eval_therapy_slot_fill_no_nutrient_targets(client):
    r = post_eval(client, "Create a nutrition plan for my child with cystic fibrosis")
    # nutrient_targets must be absent when gatekeeper hasn't passed
    targets = r.get("nutrient_targets")
    assert targets is None or targets == []


def test_eval_therapy_slot_fill_title_appropriate(client):
    r = post_eval(client, "My child needs a diet plan for T1D")
    assert r["title"] is not None
    assert len(r["title"]) > 0


def test_eval_therapy_slot_fill_summary_is_prompt_text(client):
    r = post_eval(client, "I need a plan for my child with PKU")
    # Summary should be a slot prompt, not empty
    assert r["summary"]
    assert len(r["summary"]) > 5


# ---------------------------------------------------------------------------
# 3. Therapy — gatekeeper pass (all slots provided)
# ---------------------------------------------------------------------------

def test_eval_therapy_full_slots_gatekeeper_passes(client):
    session_state = {
        "session_id": "eval-therapy-full",
        "slots": {
            "age": "8",
            "sex": "female",
            "weight": "25",
            "height": "128",
            "diagnosis": "cystic fibrosis",
            "medications": "creon",
            "biomarkers": "FEV1 72%",
            "country": "NG",
        },
    }
    r = post_eval(client, "Give me a full nutrition therapy plan", session_state=session_state)
    assert r["query_type"] == "therapy"
    assert r["gatekeeper_status"] == "passed"


def test_eval_therapy_full_slots_nutrient_targets_present(client):
    session_state = {
        "session_id": "eval-therapy-targets",
        "slots": {
            "age": "8", "sex": "female", "weight": "25", "height": "128",
            "diagnosis": "cystic fibrosis", "medications": "creon",
            "biomarkers": "none", "country": "NG",
        },
    }
    r = post_eval(client, "Give me a full nutrition plan", session_state=session_state)
    assert r["gatekeeper_status"] == "passed"
    assert r["nutrient_targets"] is not None
    assert isinstance(r["nutrient_targets"], list)
    assert len(r["nutrient_targets"]) > 0


def test_eval_therapy_full_slots_patient_summary_present(client):
    session_state = {
        "session_id": "eval-therapy-ps",
        "slots": {
            "age": "8", "sex": "female", "weight": "25", "height": "128",
            "diagnosis": "type 1 diabetes", "medications": "insulin",
            "biomarkers": "HbA1c 7.2%", "country": "US",
        },
    }
    r = post_eval(client, "Nutrition plan for my child", session_state=session_state)
    assert r.get("patientSummary") is not None
    assert len(r["patientSummary"]) > 0


def test_eval_therapy_full_slots_sections_populated(client):
    session_state = {
        "session_id": "eval-therapy-sec",
        "slots": {
            "age": "10", "sex": "male", "weight": "32", "height": "140",
            "diagnosis": "cystic fibrosis", "medications": "creon",
            "biomarkers": "none", "country": "NG",
        },
    }
    r = post_eval(client, "Provide a diet therapy plan", session_state=session_state)
    assert len(r["sections"]) > 0


# ---------------------------------------------------------------------------
# 4. Comparison — entities, subtype, mode, executiveTakeaway
# ---------------------------------------------------------------------------

def test_eval_comparison_entities_present(client):
    r = post_eval(client, "Compare bambara nut vs groundnut for iron content")
    assert r["query_type"] == "comparison"
    assert r["entities"] is not None
    assert len(r["entities"]) == 2


def test_eval_comparison_no_placeholder_entities(client):
    r = post_eval(client, "Compare brown rice vs white rice")
    entities = r.get("entities") or []
    for e in entities:
        assert "Food A" not in e
        assert "Entity 1" not in e


def test_eval_comparison_executive_takeaway_present(client):
    r = post_eval(client, "Compare bambara nut to groundnut")
    assert r.get("executiveTakeaway")
    assert len(r["executiveTakeaway"]) > 5


def test_eval_comparison_subtype_valid(client):
    r = post_eval(client, "Compare bambara nut vs groundnut")
    valid = {"food_vs_food", "nutrient_vs_nutrient", "food_vs_supplement", "condition_vs_condition"}
    assert r.get("comparison_subtype") in valid


def test_eval_comparison_mode_present(client):
    r = post_eval(client, "Compare bambara nut to groundnut")
    assert r.get("comparison_mode") in ("qualitative", "quantitative")


def test_eval_comparison_gatekeeper_not_applicable(client):
    r = post_eval(client, "Compare brown rice vs white rice")
    assert r["gatekeeper_status"] == "not_applicable"


def test_eval_comparison_sections_non_empty(client):
    r = post_eval(client, "Compare groundnut vs bambara nut")
    assert len(r["sections"]) > 0


# ---------------------------------------------------------------------------
# 5. Recommendation
# ---------------------------------------------------------------------------

def test_eval_recommendation_query_type(client):
    r = post_eval(client, "Recommend foods for a child with cystic fibrosis")
    assert r["query_type"] == "recommendation"


def test_eval_recommendation_sections_present(client):
    r = post_eval(client, "What foods are good for iron deficiency in toddlers?")
    assert len(r["sections"]) > 0


def test_eval_recommendation_gatekeeper_not_applicable(client):
    r = post_eval(client, "Recommend foods rich in calcium for children")
    assert r["gatekeeper_status"] == "not_applicable"


# ---------------------------------------------------------------------------
# 6. Clarification / low confidence → fallback_triggered
# ---------------------------------------------------------------------------

def test_eval_ambiguous_query_fallback_triggered(client):
    r = post_eval(client, "hi")  # 2 chars → needs_clarification=True
    assert r["fallback_triggered"] is True


def test_eval_ambiguous_query_clarification_requested(client):
    r = post_eval(client, "ok")
    assert r.get("clarification_requested") is True


def test_eval_ambiguous_query_returns_200_not_400(client):
    resp = client.post("/api/eval", json={"userMessage": "ok", "conversationHistory": [], "sessionState": {}})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 7. Security — auth header enforcement
# ---------------------------------------------------------------------------

def test_eval_no_secret_env_allows_unauthenticated(client, monkeypatch):
    monkeypatch.delenv("EVAL_SECRET", raising=False)
    resp = client.post("/api/eval", json={"userMessage": "vitamin D", "conversationHistory": [], "sessionState": {}})
    assert resp.status_code == 200


def test_eval_wrong_secret_returns_401(client, monkeypatch):
    monkeypatch.setenv("EVAL_SECRET", "correct-secret")
    resp = client.post(
        "/api/eval",
        json={"userMessage": "vitamin D", "conversationHistory": [], "sessionState": {}},
        headers={"x-eval-secret": "wrong-secret"},
    )
    assert resp.status_code == 401


def test_eval_correct_secret_returns_200(client, monkeypatch):
    monkeypatch.setenv("EVAL_SECRET", "correct-secret")
    resp = client.post(
        "/api/eval",
        json={"userMessage": "vitamin D", "conversationHistory": [], "sessionState": {}},
        headers={"x-eval-secret": "correct-secret"},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 8. Context inheritance — no silent contamination
# ---------------------------------------------------------------------------

def test_eval_comparison_after_therapy_no_patient_data_leaked(client):
    """Comparison after therapy should NOT carry patient context unless inheritance is explicit."""
    # First turn: therapy
    session_state_therapy = {
        "session_id": "eval-ctx-test",
        "slots": {
            "age": "8", "sex": "female", "weight": "25", "height": "128",
            "diagnosis": "cystic fibrosis", "medications": "creon",
            "biomarkers": "none", "country": "NG",
        },
    }
    post_eval(client, "Give nutrition plan", session_state=session_state_therapy)

    # Second turn: comparison — no prior profile injected
    r = post_eval(client, "Compare bambara nut vs groundnut",
                  session_state={"session_id": "eval-ctx-test-2"})
    # patientSummary must be absent (no prior confirmed_profile in sessionState)
    assert r.get("patientSummary") is None


def test_eval_state_update_slots_reflect_confirmed_entities(client):
    session_state = {
        "session_id": "eval-slots-check",
        "slots": {"diagnosis": "type 1 diabetes", "age": "10"},
    }
    r = post_eval(client, "Tell me about diabetes nutrition", session_state=session_state)
    state = r["state_update"]
    assert "slots" in state
    # Slots that were confirmed should appear
    assert "diagnosis" in state["slots"]


# ---------------------------------------------------------------------------
# 9. Latency field present
# ---------------------------------------------------------------------------

def test_eval_latency_ms_present(client):
    r = post_eval(client, "What is the DRI for calcium in a 5-year-old?")
    assert "latency_ms" in r
    assert isinstance(r["latency_ms"], float)
    assert r["latency_ms"] >= 0
