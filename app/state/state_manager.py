"""
StateManager — the single gateway for reading and writing ConversationState.

All agents use this class. No agent ever touches ConversationState directly.

Backend : Redis via redis-py
Key     : cpna:state:{session_id}
TTL     : 3600 s
Codec   : state.model_dump_json() / ConversationState.model_validate_json()
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import List, Optional

import redis as redis_lib
from pydantic import BaseModel

from app.state.conversation_state import (
    ConfirmedEntities,
    ConversationState,
    DowngradeState,
    IntentLabel,
    TurnEntities,
)

logger = logging.getLogger(__name__)

_STATE_KEY_PREFIX = "cpna:state:"
_TTL_SECONDS = 3600

# Slot names that map directly to scalar string fields on ConfirmedEntities
_SCALAR_SLOTS = {"age", "sex", "weight", "height", "diagnosis", "country"}

# ---------------------------------------------------------------------------
# Resolution types
# ---------------------------------------------------------------------------

class ResolutionType(str, Enum):
    SLOT_FILL = "slot_fill"
    CONFIRMATION = "confirmation"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------

class LooseReplyResolution(BaseModel):
    resolved_slot: Optional[str] = None
    resolved_value: Optional[str] = None
    resolution_type: ResolutionType
    confidence: float


class ContextInheritanceDecision(BaseModel):
    inherit: bool
    fields_to_inherit: List[str]
    reason: str


# ---------------------------------------------------------------------------
# StateManager
# ---------------------------------------------------------------------------

_CONFIRMATION_WORDS = {"yes", "ok", "sure", "go ahead", "proceed"}


class StateManager:
    """
    All state reads and writes go through this class.

    Pass a redis.Redis (or fakeredis.FakeRedis) client on construction.
    Defaults to localhost:6379 when no client is supplied.
    """

    def __init__(self, redis_client: Optional[redis_lib.Redis] = None) -> None:
        if redis_client is not None:
            self._redis = redis_client
        else:
            self._redis = redis_lib.Redis(host="localhost", port=6379, db=0)

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _key(self, session_id: str) -> str:
        return f"{_STATE_KEY_PREFIX}{session_id}"

    def _load(self, session_id: str) -> ConversationState:
        raw = self._redis.get(self._key(session_id))
        if raw is None:
            return ConversationState.new(session_id)
        return ConversationState.model_validate_json(raw)

    def _save(self, state: ConversationState) -> None:
        self._redis.set(
            self._key(state.session_id),
            state.model_dump_json(),
            ex=_TTL_SECONDS,
        )

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def get_state(self, session_id: str) -> ConversationState:
        """Return existing state or a fresh default state for an unknown session."""
        return self._load(session_id)

    def save_state(self, state: ConversationState) -> None:
        """Persist state with TTL."""
        self._save(state)

    def update_intent(
        self,
        session_id: str,
        label: IntentLabel,
        confidence: float,
    ) -> ConversationState:
        """Update current_intent and intent_confidence, persist, and return."""
        state = self._load(session_id)
        state.active_task_context.current_intent = label
        state.intent_confidence = confidence
        self._save(state)
        return state

    def update_turn_entities(
        self,
        session_id: str,
        entities: TurnEntities,
    ) -> ConversationState:
        """Replace turn_entities for this turn, persist, and return."""
        state = self._load(session_id)
        state.turn_entities = entities
        self._save(state)
        return state

    def confirm_slot(
        self,
        session_id: str,
        slot_name: str,
        value: str,
    ) -> ConversationState:
        """
        Write value into confirmed_entities[slot_name].
        Remove slot_name from active_task_context.pending_slots.
        Persist and return.
        """
        state = self._load(session_id)
        ce = state.confirmed_entities

        if slot_name in _SCALAR_SLOTS:
            setattr(ce, slot_name, value)
        elif slot_name == "medications":
            # Accept comma-separated list or single value
            items = [v.strip() for v in value.split(",") if v.strip()]
            ce.medications = items if items else [value]
        else:
            # Unknown slot — store generically (biomarkers handled separately)
            logger.warning("confirm_slot: unrecognised slot '%s', skipping", slot_name)

        state.confirmed_entities = ce

        # Remove from pending_slots
        state.active_task_context.pending_slots = [
            s for s in state.active_task_context.pending_slots if s != slot_name
        ]

        self._save(state)
        return state

    def set_downgrade(
        self,
        session_id: str,
        reason: str,
        user_explanation: str,
        from_intent: IntentLabel,
    ) -> ConversationState:
        """Record a therapy → recommendation downgrade."""
        state = self._load(session_id)
        state.downgrade_state = DowngradeState(
            reason=reason,
            downgraded_from=from_intent,
            user_explanation=user_explanation,
        )
        state.active_task_context.therapy_downgrade_status = True
        self._save(state)
        return state

    def resolve_loose_reply(
        self,
        session_id: str,
        user_text: str,
    ) -> LooseReplyResolution:
        """
        Interpret a short/ambiguous user reply using session context.

        Priority:
        1. If pending_slots is non-empty and text looks like a slot value → SLOT_FILL
        2. If last_assistant_prompt_type starts with "confirmation_" and text is
           a confirmation word → CONFIRMATION
        3. Otherwise → UNKNOWN (confidence 0.4)
        """
        state = self._load(session_id)
        pending = state.active_task_context.pending_slots
        prompt_type = state.last_assistant_prompt_type or ""
        text_clean = user_text.strip().lower()

        if pending and _is_plausible_slot_value(text_clean, pending[0]):
            return LooseReplyResolution(
                resolved_slot=pending[0],
                resolved_value=user_text.strip(),
                resolution_type=ResolutionType.SLOT_FILL,
                confidence=0.9,
            )

        if prompt_type.startswith("confirmation_") and text_clean in _CONFIRMATION_WORDS:
            return LooseReplyResolution(
                resolved_slot=None,
                resolved_value=None,
                resolution_type=ResolutionType.CONFIRMATION,
                confidence=0.95,
            )

        return LooseReplyResolution(
            resolved_slot=None,
            resolved_value=None,
            resolution_type=ResolutionType.UNKNOWN,
            confidence=0.4,
        )

    def should_inherit_context(
        self,
        session_id: str,
        new_intent: IntentLabel,
        user_message: str = "",
    ) -> ContextInheritanceDecision:
        """
        Decide whether confirmed patient context from a prior turn should carry
        into the new query.

        Safe scenarios (inherit=True):
          - THERAPY → THERAPY follow-up in same session with confirmed_entities
          - RECOMMENDATION → RECOMMENDATION refinement of the same condition
          - User message contains a reference pronoun ("same child", "her", "his",
            "the same patient")

        Unsafe scenarios (inherit=False):
          - New COMPARISON after THERAPY without user signal
          - GENERAL question
          - No prior confirmed_entities at all
        """
        state = self._load(session_id)
        prior_intent = state.active_task_context.current_intent
        ce = state.confirmed_entities

        has_prior_entities = any(
            getattr(ce, f) is not None
            for f in ("age", "sex", "weight", "height", "diagnosis")
        )

        # No prior data — nothing to inherit
        if not has_prior_entities:
            return ContextInheritanceDecision(
                inherit=False,
                fields_to_inherit=[],
                reason="no_prior_confirmed_entities",
            )

        # Check for explicit user continuation signal
        continuation_signals = {"same child", "her", "his", "the same patient", "same patient"}
        user_lower = user_message.lower()
        user_signals_continuation = any(sig in user_lower for sig in continuation_signals)

        # THERAPY → THERAPY follow-up
        if prior_intent == IntentLabel.THERAPY and new_intent == IntentLabel.THERAPY:
            fields = _non_null_entity_fields(ce)
            return ContextInheritanceDecision(
                inherit=True,
                fields_to_inherit=fields,
                reason="therapy_followup_same_session",
            )

        # RECOMMENDATION → RECOMMENDATION refinement
        if (
            prior_intent == IntentLabel.RECOMMENDATION
            and new_intent == IntentLabel.RECOMMENDATION
        ):
            fields = _non_null_entity_fields(ce)
            return ContextInheritanceDecision(
                inherit=True,
                fields_to_inherit=fields,
                reason="recommendation_refinement",
            )

        # User explicitly signals same patient — allow for any intent transition
        if user_signals_continuation and has_prior_entities:
            fields = _non_null_entity_fields(ce)
            return ContextInheritanceDecision(
                inherit=True,
                fields_to_inherit=fields,
                reason="user_continuation_signal",
            )

        # COMPARISON after THERAPY (or any cross-intent) without signal — unsafe
        if new_intent == IntentLabel.COMPARISON:
            return ContextInheritanceDecision(
                inherit=False,
                fields_to_inherit=[],
                reason="comparison_after_therapy_no_signal",
            )

        # GENERAL — never inherit patient context
        if new_intent == IntentLabel.GENERAL:
            return ContextInheritanceDecision(
                inherit=False,
                fields_to_inherit=[],
                reason="general_query_no_inheritance",
            )

        # Any other cross-intent transition without signal — conservative default
        return ContextInheritanceDecision(
            inherit=False,
            fields_to_inherit=[],
            reason="cross_intent_no_signal",
        )

    def reset_task(self, session_id: str) -> ConversationState:
        """Clear active task state, preserve session memory."""
        state = self._load(session_id)
        state.reset_active_task()
        self._save(state)
        return state


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _is_plausible_slot_value(text: str, slot: str) -> bool:
    """
    Heuristic check: does the user text look like a valid value for slot?
    Conservative — returns True for most non-empty inputs to avoid dropping
    legitimate values. Specific slots have tighter checks.
    """
    if not text:
        return False

    if slot == "age":
        # Accept numeric strings like "10", "10 years", "10y", "18 months"
        return any(ch.isdigit() for ch in text)

    if slot == "weight":
        return any(ch.isdigit() for ch in text)

    if slot == "height":
        return any(ch.isdigit() for ch in text)

    if slot == "sex":
        return text in {"male", "female", "m", "f", "boy", "girl"}

    if slot == "country":
        # Accept any non-empty string of reasonable length
        return 1 < len(text) <= 60

    if slot == "medications":
        # "none", "nil", drug names — accept anything non-trivially short
        return len(text) >= 2

    # diagnosis, biomarkers, general slots — accept anything
    return len(text) >= 2


def _non_null_entity_fields(ce: ConfirmedEntities) -> List[str]:
    """Return names of ConfirmedEntities fields that have a value."""
    fields = ["age", "sex", "weight", "height", "diagnosis", "medications", "biomarkers", "country"]
    return [f for f in fields if getattr(ce, f) is not None]
