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


def extract_comparison_entities(
    query: str,
) -> tuple[str, str, Optional[str]]:
    """
    Extracts two food/nutrient entities and an optional comparison dimension.

    Returns:
        (entity1, entity2, dimension)
        e.g. ("bambara nut", "groundnut", "zinc content")

    Handles:
        "compare X vs Y"
        "X vs Y for Z"
        "X versus Y in terms of Z"
        "compare X and Y"
    """
    q = query.strip()
    q = re.sub(r"^compare\s+", "", q, flags=re.IGNORECASE).strip()

    parts = re.split(
        r"\s+vs\.?\s+|\s+versus\s+|\s+and\s+",
        q,
        maxsplit=1,
        flags=re.IGNORECASE,
    )

    if len(parts) != 2:
        return q, "", None

    entity1 = parts[0].strip()
    entity2_raw = parts[1].strip()

    dimension_match = re.search(
        r"\s+(?:for|in terms of|regarding|with respect to|"
        r"in relation to|when it comes to|by)\s+(.+)$",
        entity2_raw,
        flags=re.IGNORECASE,
    )
    dimension = dimension_match.group(1).strip() if dimension_match else None

    entity2 = re.sub(
        r"\s+(?:for|in terms of|regarding|with respect to|"
        r"in relation to|when it comes to|by)\s+.+$",
        "",
        entity2_raw,
        flags=re.IGNORECASE,
    ).strip()

    return entity1, entity2, dimension


def _extract_compared_entities(user_message: str) -> List[str]:
    """Thin wrapper kept for backward compat — delegates to extract_comparison_entities."""
    entity1, entity2, _dimension = extract_comparison_entities(user_message)
    if entity2:
        return [entity1, entity2]
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
        # Extract compared entities and optional dimension
        entity_a, entity_b, dimension = extract_comparison_entities(user_message)
        if not entity_b:
            # Fall back to turn_entities if extraction failed
            entities = list(state.turn_entities.compared_entities)
            if len(entities) < 2:
                raise WorkflowError(
                    "Could not identify two items to compare. "
                    "Please use phrasing like 'X vs Y' or 'compare X with Y'."
                )
            entity_a, entity_b = entities[0], entities[1]
            dimension = None

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

        # Retrieval — separate queries per entity, enriched with dimension
        evidence_passages = []
        if self._retrieval is not None:
            try:
                query_a = f"{entity_a} {dimension}" if dimension else entity_a
                query_b = f"{entity_b} {dimension}" if dimension else entity_b
                result_a = self._retrieval.retrieve(query_a)
                result_b = self._retrieval.retrieve(query_b)
                passages_a = [
                    {"source_title": p.source_title, "excerpt": p.text[:300], "entity": entity_a}
                    for p in result_a.passages
                ]
                passages_b = [
                    {"source_title": p.source_title, "excerpt": p.text[:300], "entity": entity_b}
                    for p in result_b.passages
                ]
                evidence_passages = passages_a + passages_b
            except Exception as exc:
                logger.warning("ComparisonWorkflow: retrieval failed — %s", exc)

        response_data: Dict[str, Any] = {
            "query_type": "comparison",
            "entity_a": entity_a,
            "entity_b": entity_b,
            "dimension": dimension,
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
