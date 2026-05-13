"""
ComparisonWorkflow — compares two food items, nutrients, or dietary strategies.

Raises WorkflowError if either compared entity is a placeholder.
Respects context inheritance via state_manager.should_inherit_context().
Determines comparison_mode: quantitative or qualitative.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from app.classification.intent_labels import IntentLabel
from app.state.conversation_state import ConversationState
from app.state.state_manager import StateManager
from app.workflows.therapy_workflow import WorkflowResult

logger = logging.getLogger(__name__)

_PLACEHOLDER_RE = re.compile(
    r"^(?:food [ab]|entity [ab]|item [ab]|option [ab]|thing [ab])$",
    re.IGNORECASE,
)

# Simple nutrient quantity pattern — "100g", "400 mg", "2.5 kcal"
_QUANTITY_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:g|mg|ug|µg|kcal|kj|ml|iu)\b", re.IGNORECASE)


class WorkflowError(Exception):
    pass


def _extract_compared_entities(user_message: str) -> List[str]:
    """Extract up to two compared items from 'X vs Y' or 'X compared to Y' patterns."""
    vs_match = re.search(
        r"(?:compare\s+)?(.+?)\s+(?:vs\.?|versus|compared (?:to|with)|to|and)\s+(.+)",
        user_message,
        re.IGNORECASE,
    )
    if vs_match:
        return [vs_match.group(1).strip(), vs_match.group(2).strip()]
    return []


class ComparisonWorkflow:

    def __init__(self, retrieval_agent: Any = None) -> None:
        self._retrieval = retrieval_agent

    def execute(
        self,
        state: ConversationState,
        user_message: str,
        state_manager: StateManager,
    ) -> WorkflowResult:
        # Extract compared entities
        entities = _extract_compared_entities(user_message)
        if len(entities) < 2:
            # Fall back to turn_entities if extraction failed
            entities = list(state.turn_entities.compared_entities)

        if len(entities) < 2:
            raise WorkflowError(
                "Could not identify two items to compare. "
                "Please use phrasing like 'X vs Y' or 'compare X with Y'."
            )

        entity_a, entity_b = entities[0], entities[1]

        if _PLACEHOLDER_RE.match(entity_a) or _PLACEHOLDER_RE.match(entity_b):
            raise WorkflowError(
                f"Comparison entities must be real items, not placeholders "
                f"(got '{entity_a}' and '{entity_b}')."
            )

        # Context inheritance decision
        inheritance = state_manager.should_inherit_context(
            state.session_id,
            new_intent=IntentLabel.COMPARISON,
            user_message=user_message,
        )
        patient_context: Optional[Dict[str, Any]] = None
        if inheritance.inherit:
            ce = state.confirmed_entities
            patient_context = {f: getattr(ce, f) for f in inheritance.fields_to_inherit}

        # Determine comparison mode
        comparison_mode = "quantitative" if _QUANTITY_RE.search(user_message) else "qualitative"

        # Retrieval for both entities
        evidence_passages = []
        if self._retrieval is not None:
            try:
                retrieval_result = self._retrieval.retrieve(user_message)
                evidence_passages = [
                    {"source_title": p.source_title, "excerpt": p.text[:300]}
                    for p in retrieval_result.passages
                ]
            except Exception as exc:
                logger.warning("ComparisonWorkflow: retrieval failed — %s", exc)

        response_data: Dict[str, Any] = {
            "query_type": "comparison",
            "entity_a": entity_a,
            "entity_b": entity_b,
            "comparison_mode": comparison_mode,
            "context_inherited": inheritance.inherit,
            "inherited_fields": inheritance.fields_to_inherit,
            "patient_context": patient_context,
            "evidence": evidence_passages,
        }

        return WorkflowResult(
            response_data=response_data,
            query_type=IntentLabel.COMPARISON,
            updated_state=state,
        )
