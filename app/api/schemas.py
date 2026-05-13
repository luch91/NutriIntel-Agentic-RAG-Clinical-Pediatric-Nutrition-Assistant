"""
API request/response schemas for CPNA v1.
All Pydantic BaseModel. Extended across Prompts 3 and 9.
"""

from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Prompt 3 — Intent classification endpoint schemas
# ---------------------------------------------------------------------------

class ClassifyRequest(BaseModel):
    text: str
    session_id: str


class ClassifyResponse(BaseModel):
    session_id: str
    label: Optional[str] = None
    confidence: float
    needs_clarification: bool
    clarification_prompt: Optional[str] = None


# ---------------------------------------------------------------------------
# Prompt 9 — Chat, session, and health schemas
# ---------------------------------------------------------------------------

from typing import Any, List

class StateSnapshot(BaseModel):
    current_intent: Optional[str] = None
    workflow_stage: str = "idle"
    pending_slots: List[str] = []
    clarification_needed: bool = False


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: Any  # CPNAResponse — typed as Any for JSON passthrough flexibility
    state_snapshot: StateSnapshot


class ResetRequest(BaseModel):
    session_id: str


class ResetResponse(BaseModel):
    status: str
    session_id: str


class HealthResponse(BaseModel):
    status: str
    version: str
