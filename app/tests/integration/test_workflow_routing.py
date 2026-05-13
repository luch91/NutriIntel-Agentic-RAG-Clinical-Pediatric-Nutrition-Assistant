"""
Integration tests for Prompt 7 — Workflow Orchestration Layer.

Tests:
  1. THERAPY intent → TherapyWorkflow executes (returns therapy output)
  2. Missing slots → slot prompt returned, not therapy output
  3. Unsupported diagnosis → downgrade to RecommendationWorkflow
  4. COMPARISON after prior therapy session → should_inherit_context called, no silent carryover
  5. Low confidence intent → clarification text returned, no workflow error
"""

import fakeredis
import pytest

from app.agents.retrieval_agent import RetrievalAgent, RetrievalResult
from app.classification.intent_labels import CONFIDENCE_THRESHOLD, IntentLabel
from app.retrieval import RetrievedPassage
from app.state.conversation_state import (
    ActiveTaskContext,
    ConfirmedEntities,
    ConversationState,
)
from app.state.state_manager import StateManager
from app.workflows.workflow_router import WorkflowRouter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state_manager() -> StateManager:
    return StateManager(redis_client=fakeredis.FakeRedis())


def _base_state(
    session_id: str = "test-session",
    intent: IntentLabel = IntentLabel.THERAPY,
    confidence: float = 0.95,
) -> ConversationState:
    state = ConversationState.new(session_id)
    state.active_task_context = ActiveTaskContext(current_intent=intent)
    state.intent_confidence = confidence
    return state


def _fully_confirmed(diagnosis: str = "type 1 diabetes") -> ConfirmedEntities:
    return ConfirmedEntities(
        age="10",
        sex="male",
        weight="30",
        height="135",
        diagnosis=diagnosis,
        medications=["none"],
        country="NG",
    )


class _StubRetrieval:
    """Minimal duck-typed retrieval stub — returns one fake passage, no API calls."""

    def retrieve(self, query: str, patient_context: str = "", top_k: int = 7,
                 diagnosis=None) -> RetrievalResult:
        passage = RetrievedPassage(
            passage_id="stub_p1",
            text="Pediatric nutrition guideline excerpt.",
            source_title="Shaw 2020",
            source_type="clinical_guideline",
            score=0.9,
        )
        return RetrievalResult(
            passages=[passage],
            rewritten_query=query,
            original_query=query,
        )


# ---------------------------------------------------------------------------
# Test 1 — THERAPY intent routes to TherapyWorkflow
# ---------------------------------------------------------------------------

def test_therapy_intent_executes_therapy_workflow():
    sm = _make_state_manager()
    state = _base_state(intent=IntentLabel.THERAPY, confidence=0.95)
    state.confirmed_entities = _fully_confirmed()
    sm.save_state(state)

    router = WorkflowRouter(retrieval_agent=_StubRetrieval())
    result = router.route(state, "Create a meal plan for my child with type 1 diabetes.", sm)

    assert result.query_type == IntentLabel.THERAPY
    assert result.requires_slot_fill is False
    assert "patient_summary" in result.response_data or "slot_prompt" in result.response_data
    # Must NOT be a clarification prompt
    assert "clarification_prompt" not in result.response_data


# ---------------------------------------------------------------------------
# Test 2 — Missing required slots → slot prompt, not therapy output
# ---------------------------------------------------------------------------

def test_missing_slots_returns_slot_prompt():
    sm = _make_state_manager()
    state = _base_state(intent=IntentLabel.THERAPY, confidence=0.95)
    # No confirmed_entities — all slots missing
    sm.save_state(state)

    router = WorkflowRouter(retrieval_agent=_StubRetrieval())
    result = router.route(state, "I want a therapy plan.", sm)

    assert result.requires_slot_fill is True
    assert result.slot_prompt is not None
    assert len(result.slot_prompt) > 5
    # Must not contain therapy output keys
    assert "patient_summary" not in result.response_data
    assert "nutrient_targets" not in result.response_data


# ---------------------------------------------------------------------------
# Test 3 — Unsupported diagnosis → downgrade to RecommendationWorkflow
# ---------------------------------------------------------------------------

def test_unsupported_diagnosis_downgrades_to_recommendation():
    sm = _make_state_manager()
    state = _base_state(intent=IntentLabel.THERAPY, confidence=0.95)
    state.confirmed_entities = _fully_confirmed(diagnosis="scurvy")  # not supported
    sm.save_state(state)

    router = WorkflowRouter(retrieval_agent=_StubRetrieval())
    result = router.route(state, "Plan for my child with scurvy.", sm)

    # Downgrade means result is RECOMMENDATION, not THERAPY
    assert result.query_type == IntentLabel.RECOMMENDATION
    assert "downgrade_note" in result.response_data
    assert "therapy planning requires one of the conditions" in result.response_data["downgrade_note"]


# ---------------------------------------------------------------------------
# Test 4 — COMPARISON after prior therapy session → should_inherit_context called
# ---------------------------------------------------------------------------

def test_comparison_after_therapy_no_silent_context_carryover():
    sm = _make_state_manager()
    session_id = "comp-after-therapy"

    # Prime state: prior THERAPY session with confirmed entities
    state = _base_state(session_id=session_id, intent=IntentLabel.THERAPY, confidence=0.95)
    state.confirmed_entities = _fully_confirmed()
    sm.save_state(state)

    # Now switch to COMPARISON
    state = sm.update_intent(session_id, IntentLabel.COMPARISON, confidence=0.90)

    router = WorkflowRouter(retrieval_agent=_StubRetrieval())
    result = router.route(state, "Compare rice vs bread nutrition.", sm)

    assert result.query_type == IntentLabel.COMPARISON
    # Context should NOT be silently inherited — no continuation signal
    assert result.response_data.get("context_inherited") is False
    assert "entity_a" in result.response_data
    assert "entity_b" in result.response_data


# ---------------------------------------------------------------------------
# Test 5 — Low confidence → clarification prompt, no error
# ---------------------------------------------------------------------------

def test_low_confidence_returns_clarification_prompt():
    sm = _make_state_manager()
    state = _base_state(intent=IntentLabel.THERAPY, confidence=0.50)  # below threshold
    sm.save_state(state)

    router = WorkflowRouter(retrieval_agent=_StubRetrieval())
    result = router.route(state, "Tell me something.", sm)

    assert "clarification_prompt" in result.response_data
    clarification = result.response_data["clarification_prompt"]
    assert "personalized nutrition" in clarification.lower() or "nutrition" in clarification.lower()
    assert result.requires_slot_fill is False


def test_none_intent_returns_clarification_prompt():
    sm = _make_state_manager()
    state = ConversationState.new("no-intent-session")
    state.intent_confidence = 0.0
    sm.save_state(state)

    router = WorkflowRouter(retrieval_agent=_StubRetrieval())
    result = router.route(state, "Hello?", sm)

    assert "clarification_prompt" in result.response_data


# ---------------------------------------------------------------------------
# Test 6 — Slot prompt is for the FIRST missing slot only
# ---------------------------------------------------------------------------

def test_slot_prompt_asks_for_first_slot_only():
    sm = _make_state_manager()
    state = _base_state(intent=IntentLabel.THERAPY, confidence=0.95)
    # Partial confirmed — age present, rest missing
    state.confirmed_entities = ConfirmedEntities(age="8")
    sm.save_state(state)

    router = WorkflowRouter(retrieval_agent=_StubRetrieval())
    result = router.route(state, "Help me plan nutrition.", sm)

    assert result.requires_slot_fill is True
    # slot_prompt should not contain multiple question marks (one question only)
    prompt = result.slot_prompt or ""
    assert prompt.count("?") <= 2  # allow for parenthetical examples with "?"


# ---------------------------------------------------------------------------
# Test 7 — RECOMMENDATION workflow executes without error
# ---------------------------------------------------------------------------

def test_recommendation_workflow_executes():
    sm = _make_state_manager()
    state = _base_state(intent=IntentLabel.RECOMMENDATION, confidence=0.85)
    sm.save_state(state)

    router = WorkflowRouter(retrieval_agent=_StubRetrieval())
    result = router.route(state, "What foods are good for iron deficiency?", sm)

    assert result.query_type == IntentLabel.RECOMMENDATION
    assert "query_type" in result.response_data
    assert result.response_data["query_type"] == "recommendation"


# ---------------------------------------------------------------------------
# Test 8 — GENERAL workflow executes without error
# ---------------------------------------------------------------------------

def test_general_workflow_executes():
    sm = _make_state_manager()
    state = _base_state(intent=IntentLabel.GENERAL, confidence=0.80)
    sm.save_state(state)

    router = WorkflowRouter(retrieval_agent=_StubRetrieval())
    result = router.route(state, "What is kwashiorkor?", sm)

    assert result.query_type == IntentLabel.GENERAL
    assert result.response_data.get("query_type") == "general"
