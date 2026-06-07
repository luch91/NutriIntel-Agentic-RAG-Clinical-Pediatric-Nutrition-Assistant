"""
RecommendationWorkflow — retrieval-backed dietary guidance.

No gatekeeper. No deterministic engine.
Age-aware DRI preview when age is available.
Accepts downgraded_from_therapy flag to annotate the output.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from app.classification.intent_labels import IntentLabel
from app.engine.dri_lookup import DRILookup, DRINotFoundError
from app.state.conversation_state import ConversationPhase, ConversationState
from app.state.state_manager import StateManager
from app.workflows.therapy_workflow import WorkflowResult

logger = logging.getLogger(__name__)

_THERAPY_UPGRADE_NOTE = (
    "To receive a personalised therapy plan with precise nutrient targets, "
    "please provide your child's age, sex, weight, height, diagnosis, and current medications."
)


class RecommendationWorkflow:

    def __init__(self, retrieval_agent: Any = None) -> None:
        self._retrieval = retrieval_agent
        self._dri = DRILookup()

    def execute(
        self,
        state: ConversationState,
        user_message: str,
        state_manager: StateManager,
        downgraded_from_therapy: bool = False,
    ) -> WorkflowResult:
        # Age-aware DRI preview
        dri_preview: Optional[Dict[str, Any]] = None
        age_str = state.confirmed_entities.age or (
            state.turn_entities.age_mentioned
        )
        sex_str = state.confirmed_entities.sex
        if age_str and sex_str:
            try:
                age_years = _parse_age(age_str)
                dri_data = self._dri.get_all_nutrients(age_years, sex_str)
                dri_preview = {
                    nutrient: {
                        "rda": r.rda,
                        "ai": r.ai,
                        "unit": r.unit,
                        "age_band": r.age_band,
                    }
                    for nutrient, r in dri_data.items()
                }
            except (DRINotFoundError, Exception) as exc:
                logger.debug("RecommendationWorkflow: DRI preview skipped — %s", exc)

        # Retrieval
        evidence_passages = []
        if self._retrieval is not None:
            try:
                diagnosis = (
                    state.confirmed_entities.diagnosis
                    or state.turn_entities.diagnosis_mentioned
                )
                retrieval_result = self._retrieval.retrieve(
                    user_message,
                    diagnosis=diagnosis,
                )
                evidence_passages = [
                    {"source_title": p.source_title, "excerpt": p.text[:300]}
                    for p in retrieval_result.passages
                ]
            except Exception as exc:
                logger.warning("RecommendationWorkflow: retrieval failed — %s", exc)

        response_data: Dict[str, Any] = {
            "query_type": "recommendation",
            "dri_preview": dri_preview,
            "evidence": evidence_passages,
        }

        if downgraded_from_therapy:
            response_data["therapy_upgrade_note"] = _THERAPY_UPGRADE_NOTE
        else:
            # Only set pending_intent when a therapy upgrade CTA is explicitly presented
            # (i.e. no confirmed patient data yet). If the user already has a therapy
            # session in progress or just asked a comparison/general query, do NOT
            # set pending_intent — it would hijack the next unrelated turn.
            has_confirmed_therapy_context = any(
                getattr(state.confirmed_entities, f) is not None
                for f in ("age", "sex", "weight", "height", "diagnosis")
            )
            if not has_confirmed_therapy_context:
                state.pending_intent = "therapy"
                response_data["therapy_upgrade_note"] = _THERAPY_UPGRADE_NOTE
            state_manager.save_state(state)

        return WorkflowResult(
            response_data=response_data,
            query_type=IntentLabel.RECOMMENDATION,
            updated_state=state,
        )


def _parse_age(age_str) -> float:
    import re
    if isinstance(age_str, (int, float)):
        return float(age_str)
    s = age_str.strip().lower()
    if "month" in s:
        digits = "".join(c for c in s if c.isdigit() or c == ".")
        return float(digits) / 12.0 if digits else 0.0
    digits = re.sub(r"[^\d.]", "", s)
    return float(digits) if digits else 0.0
