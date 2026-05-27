"""
GeneralWorkflow — lightweight retrieval-backed educational response.

No therapy logic, no gatekeeper, no engine.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from app.classification.intent_labels import IntentLabel
from app.state.conversation_state import ConversationState
from app.state.state_manager import StateManager
from app.workflows.therapy_workflow import WorkflowResult

logger = logging.getLogger(__name__)


class GeneralWorkflow:

    def __init__(self, retrieval_agent: Any = None) -> None:
        self._retrieval = retrieval_agent

    def execute(
        self,
        state: ConversationState,
        user_message: str,
        state_manager: StateManager,
    ) -> WorkflowResult:
        evidence_passages = []
        if self._retrieval is not None:
            try:
                retrieval_result = self._retrieval.retrieve(user_message)
                evidence_passages = [
                    {"source_title": p.source_title, "excerpt": p.text[:300]}
                    for p in retrieval_result.passages
                ]
            except Exception as exc:
                logger.warning("GeneralWorkflow: retrieval failed — %s", exc)

        response_data: Dict[str, Any] = {
            "query_type": "general",
            "query": user_message,
            "evidence": evidence_passages,
        }

        return WorkflowResult(
            response_data=response_data,
            query_type=IntentLabel.GENERAL,
            updated_state=state,
        )
