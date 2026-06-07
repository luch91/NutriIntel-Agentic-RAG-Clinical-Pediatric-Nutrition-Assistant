# This is the canonical conversation state model for CPNA v1.
# Do not import from app/common/* here — state has no dependency on retrieval or computation modules.

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ConversationPhase(str, Enum):
    IDLE        = "idle"
    SLOT_FILLING = "slot_filling"
    DISPATCHING  = "dispatching"
    RESPONDING   = "responding"


class IntentLabel(str, Enum):
    THERAPY = "therapy"
    RECOMMENDATION = "recommendation"
    COMPARISON = "comparison"
    GENERAL = "general"


class ComparisonSubtype(str, Enum):
    FOOD_VS_FOOD = "food_vs_food"
    NUTRIENT_VS_NUTRIENT = "nutrient_vs_nutrient"
    DIET_VS_DIET = "diet_vs_diet"
    STRATEGY_VS_STRATEGY = "strategy_vs_strategy"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class SessionMemory(BaseModel):
    """Persisted across turns — confirmed facts about the patient/context."""
    confirmed_diagnosis: Optional[str] = None
    confirmed_age: Optional[str] = None
    confirmed_country: Optional[str] = None
    confirmed_sex: Optional[str] = None


class ActiveTaskContext(BaseModel):
    """Tracks the current in-flight query type and slot-filling state."""
    current_intent: Optional[IntentLabel] = None
    workflow_stage: str = "idle"
    pending_slots: List[str] = Field(default_factory=list)
    comparison_subtype: Optional[ComparisonSubtype] = None
    therapy_downgrade_status: bool = False
    comparison_entities: List[str] = Field(default_factory=list)  # persists across follow-up turns


class TurnEntities(BaseModel):
    """Entities extracted from the current turn only."""
    age_mentioned: Optional[str] = None
    compared_entities: List[str] = Field(default_factory=list)
    biomarkers_mentioned: Optional[Dict[str, str]] = None
    country_mentioned: Optional[str] = None
    diagnosis_mentioned: Optional[str] = None


class InheritedContext(BaseModel):
    """Tracks what was selectively carried over from a prior turn."""
    fields: List[str] = Field(default_factory=list)
    source_turn_id: Optional[str] = None
    inheritance_confirmed: bool = False


class ExtractedEntities(BaseModel):
    """Raw entities extracted from user input before confirmation."""
    age: Optional[str] = None
    sex: Optional[str] = None
    weight: Optional[str] = None
    height: Optional[str] = None
    diagnosis: Optional[str] = None
    medications: Optional[List[str]] = None
    biomarkers: Optional[Dict[str, str]] = None
    country: Optional[str] = None


class ConfirmedEntities(BaseModel):
    """Confirmed and validated patient data — used by therapy engine."""
    # age/weight/height accept str or numeric (parse_slot_value normalizes at write time)
    age: Optional[Any] = None
    sex: Optional[str] = None
    weight: Optional[Any] = None
    height: Optional[Any] = None
    diagnosis: Optional[str] = None
    medications: Optional[List[str]] = None
    biomarkers: Optional[Dict[str, str]] = None
    country: Optional[str] = None


class DowngradeState(BaseModel):
    """Records when and why a therapy request was downgraded."""
    reason: str
    downgraded_from: IntentLabel
    user_explanation: str


class EvidenceItem(BaseModel):
    """A single retrieved evidence item.
    excerpt_safe is the only field ever shown in UI — no internal IDs exposed."""
    source_id: str        # INTERNAL — stripped by DisplayAdapter before sending to frontend
    source_title: str
    relevance_score: float
    excerpt_safe: str     # Only this field is rendered in the UI


# ---------------------------------------------------------------------------
# Top-level ConversationState
# ---------------------------------------------------------------------------

class ConversationState(BaseModel):
    """
    Canonical conversation state for CPNA v1.
    All agents read and write through this model — never via raw dicts.
    """
    session_id: str

    # Four state buckets (never conflate)
    session_memory: SessionMemory = Field(default_factory=SessionMemory)
    active_task_context: ActiveTaskContext = Field(default_factory=ActiveTaskContext)
    turn_entities: TurnEntities = Field(default_factory=TurnEntities)
    inherited_context: InheritedContext = Field(default_factory=InheritedContext)

    # Patient data pipeline
    extracted_entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    confirmed_entities: ConfirmedEntities = Field(default_factory=ConfirmedEntities)

    # Downgrade tracking
    downgrade_state: Optional[DowngradeState] = None

    # Clarification state
    clarification_needed: bool = False
    clarification_prompt: Optional[str] = None

    # Intent confidence (updated each turn)
    intent_confidence: float = 0.0

    # Slot-filling context for loose reply resolution
    last_assistant_prompt_type: Optional[str] = None

    # Evidence from current retrieval turn
    current_turn_evidence: List[EvidenceItem] = Field(default_factory=list)

    # Conversation phase — drives phase-aware routing (Fix 4-8)
    phase: ConversationPhase = ConversationPhase.IDLE
    pending_intent: Optional[str] = None

    # Turn counter
    turn_count: int = 0

    debug_trace_internal: Dict[str, Any] = Field(default_factory=dict)  # INTERNAL ONLY — strip in DisplayAdapter

    # -----------------------------------------------------------------------
    # Class methods
    # -----------------------------------------------------------------------

    @classmethod
    def new(cls, session_id: str) -> "ConversationState":
        """Return a default-initialized state for a new session."""
        return cls(session_id=session_id)

    # -----------------------------------------------------------------------
    # Instance methods
    # -----------------------------------------------------------------------

    def reset_active_task(self) -> None:
        """
        Clear all task-scoped state.
        Preserves session_memory and session_id.
        """
        self.active_task_context = ActiveTaskContext()
        self.turn_entities = TurnEntities()
        self.inherited_context = InheritedContext()
        self.clarification_needed = False
        self.clarification_prompt = None
        self.downgrade_state = None
        self.last_assistant_prompt_type = None
        self.current_turn_evidence = []
        self.debug_trace_internal = {}
        self.phase = ConversationPhase.IDLE
        self.pending_intent = None

    def is_therapy_eligible(self) -> bool:
        """
        Returns True only when all six required therapy slots are confirmed.
        Missing biomarkers or country do NOT block therapy — they reduce precision.
        """
        ce = self.confirmed_entities
        required = [ce.age, ce.sex, ce.weight, ce.height, ce.diagnosis, ce.medications]
        return all(v is not None for v in required)
