import pytest

from app.state.conversation_state import (
    ConfirmedEntities,
    ConversationState,
    DowngradeState,
    IntentLabel,
    SessionMemory,
)


# ---------------------------------------------------------------------------
# new() initializes with correct defaults
# ---------------------------------------------------------------------------

def test_new_creates_state_with_session_id():
    state = ConversationState.new("sess-001")
    assert state.session_id == "sess-001"


def test_new_default_workflow_stage_is_idle():
    state = ConversationState.new("sess-001")
    assert state.active_task_context.workflow_stage == "idle"


def test_new_pending_slots_empty():
    state = ConversationState.new("sess-001")
    assert state.active_task_context.pending_slots == []


def test_new_no_current_intent():
    state = ConversationState.new("sess-001")
    assert state.active_task_context.current_intent is None


def test_new_session_memory_all_none():
    state = ConversationState.new("sess-001")
    sm = state.session_memory
    assert sm.confirmed_diagnosis is None
    assert sm.confirmed_age is None
    assert sm.confirmed_country is None
    assert sm.confirmed_sex is None


def test_new_confirmed_entities_all_none():
    state = ConversationState.new("sess-001")
    ce = state.confirmed_entities
    assert ce.age is None
    assert ce.sex is None
    assert ce.weight is None
    assert ce.height is None
    assert ce.diagnosis is None
    assert ce.medications is None


def test_new_turn_count_zero():
    state = ConversationState.new("sess-001")
    assert state.turn_count == 0


def test_new_clarification_not_needed():
    state = ConversationState.new("sess-001")
    assert state.clarification_needed is False


# ---------------------------------------------------------------------------
# reset_active_task() preserves session_memory, clears active_task_context
# ---------------------------------------------------------------------------

def test_reset_preserves_session_memory():
    state = ConversationState.new("sess-002")
    state.session_memory = SessionMemory(
        confirmed_diagnosis="cystic fibrosis",
        confirmed_age="8",
        confirmed_country="NG",
        confirmed_sex="female",
    )
    state.active_task_context.workflow_stage = "slot_filling"
    state.active_task_context.pending_slots = ["weight", "height"]
    state.clarification_needed = True

    state.reset_active_task()

    assert state.session_memory.confirmed_diagnosis == "cystic fibrosis"
    assert state.session_memory.confirmed_age == "8"
    assert state.session_memory.confirmed_country == "NG"
    assert state.session_memory.confirmed_sex == "female"


def test_reset_preserves_session_id():
    state = ConversationState.new("sess-preserve")
    state.reset_active_task()
    assert state.session_id == "sess-preserve"


def test_reset_clears_active_task_context():
    state = ConversationState.new("sess-003")
    state.active_task_context.current_intent = IntentLabel.THERAPY
    state.active_task_context.workflow_stage = "slot_filling"
    state.active_task_context.pending_slots = ["weight"]
    state.active_task_context.therapy_downgrade_status = True

    state.reset_active_task()

    assert state.active_task_context.current_intent is None
    assert state.active_task_context.workflow_stage == "idle"
    assert state.active_task_context.pending_slots == []
    assert state.active_task_context.therapy_downgrade_status is False


def test_reset_clears_turn_entities():
    state = ConversationState.new("sess-004")
    state.turn_entities.age_mentioned = "10"
    state.turn_entities.diagnosis_mentioned = "PKU"

    state.reset_active_task()

    assert state.turn_entities.age_mentioned is None
    assert state.turn_entities.diagnosis_mentioned is None


def test_reset_clears_inherited_context():
    state = ConversationState.new("sess-005")
    state.inherited_context.fields = ["age", "diagnosis"]
    state.inherited_context.inheritance_confirmed = True

    state.reset_active_task()

    assert state.inherited_context.fields == []
    assert state.inherited_context.inheritance_confirmed is False


def test_reset_clears_clarification_state():
    state = ConversationState.new("sess-006")
    state.clarification_needed = True
    state.clarification_prompt = "What is your child's age?"

    state.reset_active_task()

    assert state.clarification_needed is False
    assert state.clarification_prompt is None


def test_reset_clears_downgrade_state():
    state = ConversationState.new("sess-007")
    state.downgrade_state = DowngradeState(
        reason="unsupported_condition",
        downgraded_from=IntentLabel.THERAPY,
        user_explanation="Condition not supported.",
    )

    state.reset_active_task()

    assert state.downgrade_state is None


def test_reset_clears_debug_trace():
    state = ConversationState.new("sess-008")
    state.debug_trace_internal = {"step": "gatekeeper", "result": "pass"}

    state.reset_active_task()

    assert state.debug_trace_internal == {}


# ---------------------------------------------------------------------------
# is_therapy_eligible()
# ---------------------------------------------------------------------------

def test_therapy_eligible_false_when_all_none():
    state = ConversationState.new("sess-elig-1")
    assert state.is_therapy_eligible() is False


def test_therapy_eligible_false_when_one_field_missing():
    state = ConversationState.new("sess-elig-2")
    state.confirmed_entities = ConfirmedEntities(
        age="8",
        sex="female",
        weight="25",
        height="128",
        diagnosis="cystic fibrosis",
        medications=None,   # missing
    )
    assert state.is_therapy_eligible() is False


@pytest.mark.parametrize("missing_field", ["age", "sex", "weight", "height", "diagnosis", "medications"])
def test_therapy_eligible_false_for_each_missing_field(missing_field: str) -> None:
    state = ConversationState.new("sess-elig-param")
    state.confirmed_entities = ConfirmedEntities(
        age=None if missing_field == "age" else "8",
        sex=None if missing_field == "sex" else "female",
        weight=None if missing_field == "weight" else "25",
        height=None if missing_field == "height" else "128",
        diagnosis=None if missing_field == "diagnosis" else "cystic fibrosis",
        medications=None if missing_field == "medications" else ["creon"],
    )
    assert state.is_therapy_eligible() is False


def test_therapy_eligible_true_when_all_six_present():
    state = ConversationState.new("sess-elig-3")
    state.confirmed_entities = ConfirmedEntities(
        age="8",
        sex="female",
        weight="25",
        height="128",
        diagnosis="cystic fibrosis",
        medications=["creon"],
    )
    assert state.is_therapy_eligible() is True


def test_therapy_eligible_true_without_optional_biomarkers():
    """biomarkers and country are optional — their absence must not block therapy."""
    state = ConversationState.new("sess-elig-4")
    state.confirmed_entities = ConfirmedEntities(
        age="5",
        sex="male",
        weight="18",
        height="110",
        diagnosis="type 1 diabetes",
        medications=["insulin"],
        biomarkers=None,   # optional
        country=None,      # optional
    )
    assert state.is_therapy_eligible() is True


# ---------------------------------------------------------------------------
# debug_trace_internal exists on the model
# ---------------------------------------------------------------------------

def test_debug_trace_internal_field_exists():
    state = ConversationState.new("sess-debug")
    assert hasattr(state, "debug_trace_internal")
    assert isinstance(state.debug_trace_internal, dict)


def test_debug_trace_internal_can_store_arbitrary_data():
    state = ConversationState.new("sess-debug-2")
    state.debug_trace_internal["engine_output"] = {"energy": 1800, "protein": 45}
    assert state.debug_trace_internal["engine_output"]["energy"] == 1800


# ---------------------------------------------------------------------------
# Model serialisation round-trip
# ---------------------------------------------------------------------------

def test_state_serialises_and_deserialises():
    state = ConversationState.new("sess-serial")
    state.confirmed_entities = ConfirmedEntities(age="10", sex="male", diagnosis="PKU", medications=["phe-free formula"])
    state.active_task_context.current_intent = IntentLabel.THERAPY

    json_str = state.model_dump_json()
    restored = ConversationState.model_validate_json(json_str)

    assert restored.session_id == "sess-serial"
    assert restored.confirmed_entities.age == "10"
    assert restored.active_task_context.current_intent == IntentLabel.THERAPY
