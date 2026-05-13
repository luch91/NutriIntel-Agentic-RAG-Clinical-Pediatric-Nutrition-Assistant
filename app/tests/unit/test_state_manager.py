"""
Unit tests for StateManager.
All tests use fakeredis — no real Redis server required.
"""

import fakeredis
import pytest

from app.state.conversation_state import (
    ConfirmedEntities,
    ConversationState,
    IntentLabel,
    SessionMemory,
    TurnEntities,
)
from app.state.state_manager import (
    ContextInheritanceDecision,
    LooseReplyResolution,
    ResolutionType,
    StateManager,
)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def sm() -> StateManager:
    """StateManager backed by an in-memory fakeredis instance."""
    return StateManager(redis_client=fakeredis.FakeRedis())


# ---------------------------------------------------------------------------
# get_state
# ---------------------------------------------------------------------------

def test_get_state_creates_new_for_unknown_session(sm: StateManager) -> None:
    state = sm.get_state("unknown-session-xyz")
    assert state.session_id == "unknown-session-xyz"
    assert state.active_task_context.workflow_stage == "idle"
    assert state.confirmed_entities.age is None


def test_get_state_returns_saved_state(sm: StateManager) -> None:
    state = ConversationState.new("sess-a")
    state.confirmed_entities.age = "10"
    sm.save_state(state)

    loaded = sm.get_state("sess-a")
    assert loaded.confirmed_entities.age == "10"


# ---------------------------------------------------------------------------
# save_state / round-trip
# ---------------------------------------------------------------------------

def test_save_and_reload_preserves_all_fields(sm: StateManager) -> None:
    state = ConversationState.new("sess-roundtrip")
    state.session_memory = SessionMemory(confirmed_diagnosis="PKU", confirmed_age="5")
    state.active_task_context.current_intent = IntentLabel.THERAPY
    state.intent_confidence = 0.92
    sm.save_state(state)

    loaded = sm.get_state("sess-roundtrip")
    assert loaded.session_memory.confirmed_diagnosis == "PKU"
    assert loaded.active_task_context.current_intent == IntentLabel.THERAPY
    assert abs(loaded.intent_confidence - 0.92) < 1e-6


# ---------------------------------------------------------------------------
# update_intent
# ---------------------------------------------------------------------------

def test_update_intent_sets_label_and_confidence(sm: StateManager) -> None:
    sm.get_state("sess-intent")  # ensure exists
    state = sm.update_intent("sess-intent", IntentLabel.RECOMMENDATION, 0.88)
    assert state.active_task_context.current_intent == IntentLabel.RECOMMENDATION
    assert abs(state.intent_confidence - 0.88) < 1e-6


def test_update_intent_persists(sm: StateManager) -> None:
    sm.update_intent("sess-intent-persist", IntentLabel.COMPARISON, 0.77)
    reloaded = sm.get_state("sess-intent-persist")
    assert reloaded.active_task_context.current_intent == IntentLabel.COMPARISON


# ---------------------------------------------------------------------------
# update_turn_entities
# ---------------------------------------------------------------------------

def test_update_turn_entities_replaces_entities(sm: StateManager) -> None:
    entities = TurnEntities(age_mentioned="8", diagnosis_mentioned="cystic fibrosis")
    state = sm.update_turn_entities("sess-te", entities)
    assert state.turn_entities.age_mentioned == "8"
    assert state.turn_entities.diagnosis_mentioned == "cystic fibrosis"


# ---------------------------------------------------------------------------
# confirm_slot
# ---------------------------------------------------------------------------

def test_confirm_slot_moves_field_to_confirmed_entities(sm: StateManager) -> None:
    # Set up state with pending slot
    state = ConversationState.new("sess-slot")
    state.active_task_context.pending_slots = ["age", "weight"]
    sm.save_state(state)

    updated = sm.confirm_slot("sess-slot", "age", "10")
    assert updated.confirmed_entities.age == "10"


def test_confirm_slot_removes_from_pending_slots(sm: StateManager) -> None:
    state = ConversationState.new("sess-slot2")
    state.active_task_context.pending_slots = ["age", "weight"]
    sm.save_state(state)

    updated = sm.confirm_slot("sess-slot2", "age", "10")
    assert "age" not in updated.active_task_context.pending_slots
    assert "weight" in updated.active_task_context.pending_slots


def test_confirm_slot_medications_parses_list(sm: StateManager) -> None:
    state = ConversationState.new("sess-meds")
    state.active_task_context.pending_slots = ["medications"]
    sm.save_state(state)

    updated = sm.confirm_slot("sess-meds", "medications", "creon, vitamin D")
    assert updated.confirmed_entities.medications == ["creon", "vitamin D"]


def test_confirm_slot_single_medication(sm: StateManager) -> None:
    state = ConversationState.new("sess-meds2")
    sm.save_state(state)

    updated = sm.confirm_slot("sess-meds2", "medications", "insulin")
    assert updated.confirmed_entities.medications == ["insulin"]


def test_confirm_slot_none_value_reports_none(sm: StateManager) -> None:
    state = ConversationState.new("sess-meds3")
    state.active_task_context.pending_slots = ["medications"]
    sm.save_state(state)

    updated = sm.confirm_slot("sess-meds3", "medications", "none")
    assert updated.confirmed_entities.medications == ["none"]


@pytest.mark.parametrize("slot,value", [
    ("sex", "female"),
    ("weight", "25"),
    ("height", "128"),
    ("diagnosis", "cystic fibrosis"),
    ("country", "NG"),
])
def test_confirm_slot_scalar_fields(sm: StateManager, slot: str, value: str) -> None:
    state = ConversationState.new(f"sess-scalar-{slot}")
    sm.save_state(state)
    updated = sm.confirm_slot(f"sess-scalar-{slot}", slot, value)
    assert getattr(updated.confirmed_entities, slot) == value


# ---------------------------------------------------------------------------
# set_downgrade
# ---------------------------------------------------------------------------

def test_set_downgrade_records_state(sm: StateManager) -> None:
    state = sm.set_downgrade(
        "sess-dg",
        reason="unsupported_condition",
        user_explanation="I can provide general guidance instead.",
        from_intent=IntentLabel.THERAPY,
    )
    assert state.downgrade_state is not None
    assert state.downgrade_state.reason == "unsupported_condition"
    assert state.downgrade_state.downgraded_from == IntentLabel.THERAPY
    assert state.active_task_context.therapy_downgrade_status is True


def test_set_downgrade_persists(sm: StateManager) -> None:
    sm.set_downgrade("sess-dg2", "missing_slots", "Please provide more info.", IntentLabel.THERAPY)
    reloaded = sm.get_state("sess-dg2")
    assert reloaded.downgrade_state is not None
    assert reloaded.active_task_context.therapy_downgrade_status is True


# ---------------------------------------------------------------------------
# resolve_loose_reply
# ---------------------------------------------------------------------------

def test_resolve_slot_fill_age(sm: StateManager) -> None:
    state = ConversationState.new("sess-loose-1")
    state.active_task_context.pending_slots = ["age"]
    sm.save_state(state)

    resolution = sm.resolve_loose_reply("sess-loose-1", "10")
    assert resolution.resolution_type == ResolutionType.SLOT_FILL
    assert resolution.resolved_slot == "age"
    assert resolution.resolved_value == "10"
    assert resolution.confidence >= 0.8


def test_resolve_slot_fill_weight(sm: StateManager) -> None:
    state = ConversationState.new("sess-loose-w")
    state.active_task_context.pending_slots = ["weight"]
    sm.save_state(state)

    resolution = sm.resolve_loose_reply("sess-loose-w", "25 kg")
    assert resolution.resolution_type == ResolutionType.SLOT_FILL
    assert resolution.resolved_slot == "weight"


def test_resolve_confirmation_yes(sm: StateManager) -> None:
    state = ConversationState.new("sess-loose-2")
    state.last_assistant_prompt_type = "confirmation_meal_plan"
    sm.save_state(state)

    resolution = sm.resolve_loose_reply("sess-loose-2", "yes")
    assert resolution.resolution_type == ResolutionType.CONFIRMATION
    assert resolution.confidence >= 0.9


@pytest.mark.parametrize("word", ["ok", "sure", "go ahead", "proceed"])
def test_resolve_confirmation_variants(sm: StateManager, word: str) -> None:
    state = ConversationState.new(f"sess-conf-{word}")
    state.last_assistant_prompt_type = "confirmation_therapy_plan"
    sm.save_state(state)

    resolution = sm.resolve_loose_reply(f"sess-conf-{word}", word)
    assert resolution.resolution_type == ResolutionType.CONFIRMATION


def test_resolve_unknown_when_no_context(sm: StateManager) -> None:
    state = ConversationState.new("sess-loose-3")
    sm.save_state(state)

    resolution = sm.resolve_loose_reply("sess-loose-3", "maybe")
    assert resolution.resolution_type == ResolutionType.UNKNOWN
    assert resolution.confidence == 0.4


def test_resolve_confirmation_word_ignored_without_prompt_type(sm: StateManager) -> None:
    """'yes' is UNKNOWN when there is no pending confirmation prompt."""
    state = ConversationState.new("sess-loose-4")
    state.last_assistant_prompt_type = None
    state.active_task_context.pending_slots = []
    sm.save_state(state)

    resolution = sm.resolve_loose_reply("sess-loose-4", "yes")
    assert resolution.resolution_type == ResolutionType.UNKNOWN


# ---------------------------------------------------------------------------
# should_inherit_context
# ---------------------------------------------------------------------------

def test_no_prior_entities_returns_no_inherit(sm: StateManager) -> None:
    # Fresh session — nothing confirmed
    decision = sm.should_inherit_context("sess-new-empty", IntentLabel.THERAPY)
    assert decision.inherit is False
    assert decision.reason == "no_prior_confirmed_entities"


def test_comparison_after_therapy_no_signal_returns_no_inherit(sm: StateManager) -> None:
    state = ConversationState.new("sess-comp")
    state.active_task_context.current_intent = IntentLabel.THERAPY
    state.confirmed_entities = ConfirmedEntities(
        age="8", sex="female", weight="25", height="128",
        diagnosis="type 1 diabetes", medications=["insulin"],
    )
    sm.save_state(state)

    decision = sm.should_inherit_context("sess-comp", IntentLabel.COMPARISON)
    assert decision.inherit is False
    assert "comparison" in decision.reason


def test_therapy_followup_same_session_inherits(sm: StateManager) -> None:
    state = ConversationState.new("sess-therapy-fu")
    state.active_task_context.current_intent = IntentLabel.THERAPY
    state.confirmed_entities = ConfirmedEntities(
        age="8", sex="female", weight="25", height="128",
        diagnosis="cystic fibrosis", medications=["creon"],
    )
    sm.save_state(state)

    decision = sm.should_inherit_context("sess-therapy-fu", IntentLabel.THERAPY)
    assert decision.inherit is True
    assert "age" in decision.fields_to_inherit
    assert "diagnosis" in decision.fields_to_inherit


def test_recommendation_followup_inherits(sm: StateManager) -> None:
    state = ConversationState.new("sess-rec-fu")
    state.active_task_context.current_intent = IntentLabel.RECOMMENDATION
    state.confirmed_entities = ConfirmedEntities(age="5", diagnosis="IBD")
    sm.save_state(state)

    decision = sm.should_inherit_context("sess-rec-fu", IntentLabel.RECOMMENDATION)
    assert decision.inherit is True


def test_user_continuation_signal_allows_cross_intent_inherit(sm: StateManager) -> None:
    state = ConversationState.new("sess-sig")
    state.active_task_context.current_intent = IntentLabel.THERAPY
    state.confirmed_entities = ConfirmedEntities(age="10", diagnosis="PKU")
    sm.save_state(state)

    decision = sm.should_inherit_context(
        "sess-sig", IntentLabel.COMPARISON, user_message="Can you compare options for her?"
    )
    assert decision.inherit is True
    assert decision.reason == "user_continuation_signal"


def test_general_intent_never_inherits(sm: StateManager) -> None:
    state = ConversationState.new("sess-gen")
    state.active_task_context.current_intent = IntentLabel.THERAPY
    state.confirmed_entities = ConfirmedEntities(age="8", diagnosis="CKD")
    sm.save_state(state)

    decision = sm.should_inherit_context("sess-gen", IntentLabel.GENERAL)
    assert decision.inherit is False


# ---------------------------------------------------------------------------
# reset_task
# ---------------------------------------------------------------------------

def test_reset_task_clears_active_context(sm: StateManager) -> None:
    state = ConversationState.new("sess-reset")
    state.session_memory.confirmed_diagnosis = "cystic fibrosis"
    state.active_task_context.pending_slots = ["weight", "height"]
    state.active_task_context.workflow_stage = "slot_filling"
    state.clarification_needed = True
    sm.save_state(state)

    reset = sm.reset_task("sess-reset")
    assert reset.active_task_context.workflow_stage == "idle"
    assert reset.active_task_context.pending_slots == []
    assert reset.clarification_needed is False


def test_reset_task_preserves_session_memory(sm: StateManager) -> None:
    state = ConversationState.new("sess-reset2")
    state.session_memory.confirmed_diagnosis = "PKU"
    sm.save_state(state)

    reset = sm.reset_task("sess-reset2")
    assert reset.session_memory.confirmed_diagnosis == "PKU"
