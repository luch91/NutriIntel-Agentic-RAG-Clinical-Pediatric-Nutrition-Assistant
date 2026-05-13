"""
WorkflowRouter — routes a ConversationState to the correct workflow.

Routes by state.active_task_context.current_intent.
Falls back to a clarification prompt when intent is None or confidence is low.
Logs routing decisions.
"""

from __future__ import annotations

import logging
from typing import Any
from app.classification.intent_labels import CONFIDENCE_THRESHOLD, IntentLabel
from app.observability.metrics import (
    cpna_intent_confidence,
    cpna_low_confidence_total,
)
from app.state.conversation_state import ConversationState
from app.state.state_manager import StateManager
from app.workflows.comparison_workflow import ComparisonWorkflow
from app.workflows.general_workflow import GeneralWorkflow
from app.workflows.recommendation_workflow import RecommendationWorkflow
from app.workflows.therapy_workflow import TherapyWorkflow, WorkflowResult

logger = logging.getLogger(__name__)

_CLARIFICATION_PROMPT = (
    "I want to make sure I help you correctly — are you looking for personalized nutrition "
    "planning, dietary guidance, a food comparison, or general nutrition information?"
)


class WorkflowRouter:

    def __init__(self, retrieval_agent: Any = None) -> None:
        self._retrieval = retrieval_agent

    def route(
        self,
        state: ConversationState,
        user_message: str,
        state_manager: StateManager,
    ) -> WorkflowResult:
        intent = state.active_task_context.current_intent
        confidence = state.intent_confidence

        cpna_intent_confidence.observe(confidence)
        if intent is None or confidence < CONFIDENCE_THRESHOLD:
            cpna_low_confidence_total.inc()
            logger.info(
                "WorkflowRouter: low-confidence or missing intent (intent=%s, conf=%.2f) — "
                "returning clarification prompt",
                intent,
                confidence,
            )
            return WorkflowResult(
                response_data={"clarification_prompt": _CLARIFICATION_PROMPT},
                query_type=intent or IntentLabel.GENERAL,
                updated_state=state,
                requires_slot_fill=False,
                slot_prompt=None,
            )

        logger.info(
            "WorkflowRouter: routing intent=%s (conf=%.2f) for session=%s",
            intent.value,
            confidence,
            state.session_id,
        )

        if intent == IntentLabel.THERAPY:
            return TherapyWorkflow(retrieval_agent=self._retrieval).execute(
                state, user_message, state_manager
            )

        if intent == IntentLabel.RECOMMENDATION:
            return RecommendationWorkflow(retrieval_agent=self._retrieval).execute(
                state, user_message, state_manager
            )

        if intent == IntentLabel.COMPARISON:
            return ComparisonWorkflow(retrieval_agent=self._retrieval).execute(
                state, user_message, state_manager
            )

        # IntentLabel.GENERAL (and any future labels)
        return GeneralWorkflow(retrieval_agent=self._retrieval).execute(
            state, user_message, state_manager
        )
