"""
ComparisonWorkflow — compares two food items, nutrients, or dietary strategies.

Raises WorkflowError if either compared entity is a placeholder.
Respects context inheritance via state_manager.should_inherit_context().
Determines comparison_mode: quantitative or qualitative.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from app.classification.intent_labels import IntentLabel
from app.state.conversation_state import ConversationState
from app.state.state_manager import StateManager
from app.workflows.therapy_workflow import WorkflowResult
from app.agents.response_synthesiser import NUTRIENT_DEFINITIONS

logger = logging.getLogger(__name__)

_PLACEHOLDER_RE = re.compile(
    r"^(?:food [ab]|entity [ab]|item [ab]|option [ab]|thing [ab])$",
    re.IGNORECASE,
)

# Simple nutrient quantity pattern — "100g", "400 mg", "2.5 kcal"
_QUANTITY_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:g|mg|ug|µg|kcal|kj|ml|iu)\b", re.IGNORECASE)

_MAX_COMPARISON_ENTITIES = 5

# Flat set of all nutrient display names and their aliases (lowercase) for fast lookup.
# Used to detect when a parsed "entity" is actually a nutrient dimension, not a food.
_NUTRIENT_LOOKUP: set = set()
for _nd in NUTRIENT_DEFINITIONS:
    _NUTRIENT_LOOKUP.add(_nd["display"].lower())
    for _alias in _nd["aliases"]:
        _NUTRIENT_LOOKUP.add(_alias.lower())

_ENTITY_SEPARATORS = re.compile(
    r'\s+vs\.?\s+|\s+versus\s+|\s+and\s+|\s*,\s*|\s+or\s+|\s+to\s+',
    flags=re.IGNORECASE,
)
_TRAILING_CONTEXT = re.compile(
    r'\s+(?:for|in terms of|regarding|with respect to|in relation to|when it comes to|by|in)\s+.+$',
    flags=re.IGNORECASE,
)
_LEADING_STRIP = re.compile(
    r'^(?:compare|contrast|show me|what is the (?:difference between|nutrient content of)|rank|list|which of|how do)\s+',
    flags=re.IGNORECASE,
)

# Colon-style preambles like "which has more zinc: X or Y" or "which food is higher in iron: X or Y"
# Group 1 captures the embedded dimension (e.g. "zinc", "iron")
_COLON_PREAMBLE = re.compile(
    r'^(?:has more|is (?:higher|lower|better|richer|worse))\s+(?:in\s+)?(\w[\w\s]*?)\s*:\s*',
    flags=re.IGNORECASE,
)


class WorkflowError(Exception):
    pass


def _extract_two_entities_legacy(query: str) -> tuple[str, str, Optional[str]]:
    """Legacy two-entity extractor — kept for reference."""
    q = query.strip()
    q = re.sub(r"^compare\s+", "", q, flags=re.IGNORECASE).strip()
    parts = re.split(r"\s+vs\.?\s+|\s+versus\s+|\s+and\s+|\s+to\s+", q, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return q, "", None
    entity1 = parts[0].strip()
    entity2_raw = parts[1].strip()
    dimension_match = re.search(
        r"\s+(?:for|in terms of|regarding|with respect to|in relation to|when it comes to|by)\s+(.+)$",
        entity2_raw, flags=re.IGNORECASE,
    )
    dimension = dimension_match.group(1).strip() if dimension_match else None
    entity2 = re.sub(
        r"\s+(?:for|in terms of|regarding|with respect to|in relation to|when it comes to|by)\s+.+$",
        "", entity2_raw, flags=re.IGNORECASE,
    ).strip()
    return entity1, entity2, dimension


def extract_comparison_entities(query: str) -> Tuple[List[str], Optional[str]]:
    """
    Extracts 2–5 food/nutrient entity names and an optional comparison dimension.

    Returns:
        (entities, dimension)

    Examples:
        "Compare bambara nut vs groundnut for zinc"
            → (["bambara nut", "groundnut"], "zinc")
        "Compare bambara nut, groundnut, and cowpea for protein"
            → (["bambara nut", "groundnut", "cowpea"], "protein")
        "Which has more iron: ogi, millet, or sorghum?"
            → (["ogi", "millet", "sorghum"], "iron")
    """
    q = query.strip()
    q = _LEADING_STRIP.sub('', q).strip()

    # Extract dimension from end of query before splitting
    dimension_match = re.search(
        r'\s+(?:for|in terms of|regarding|by)\s+(.+)$', q, flags=re.IGNORECASE,
    )
    dimension = dimension_match.group(1).strip() if dimension_match else None
    if dimension_match:
        q = q[:dimension_match.start()].strip()

    # Strip trailing question marks, "which of", and "which <phrase>:" preambles.
    # Handles: "which has more zinc: X or Y" → entities=[X,Y], dimension="zinc"
    #           "which food is higher in iron: X or Y" → entities=[X,Y], dimension="iron"
    q = re.sub(r'^which\s+(?:food\s+)?', '', q, flags=re.IGNORECASE).strip()
    colon_match = _COLON_PREAMBLE.match(q)
    if colon_match:
        if dimension is None:
            dimension = colon_match.group(1).strip()
        q = q[colon_match.end():].strip()
    q = re.sub(r'\?$', '', q).strip()

    # Extract leading nutrient names before "in <foods>" pattern.
    # Handles: "zinc and iron in bambara nut vs groundnut"
    #           "zinc, iron, calcium in bambara nut and cowpea"
    # Pattern: one or more known-nutrient tokens separated by and/comma, then "in <foods>"
    _leading_nutrient_in = re.compile(
        r'^((?:(?:' + '|'.join(re.escape(n) for n in sorted(_NUTRIENT_LOOKUP, key=len, reverse=True))
        + r')(?:\s*(?:,|and|or)\s*)?)+'
        + r')\s+in\s+', flags=re.IGNORECASE,
    )
    lead_match = _leading_nutrient_in.match(q)
    if lead_match:
        if dimension is None:
            dimension = lead_match.group(1).strip().rstrip(',').strip()
        q = q[lead_match.end():].strip()

    raw_parts = _ENTITY_SEPARATORS.split(q)

    entities = []
    for part in raw_parts:
        cleaned = part.strip().strip('.,;:')

        # Strip leading "and"/"or" that survive when splitting "X, Y, and Z" or "X, Y, or Z" on commas
        cleaned = re.sub(r'^(?:and|or)\s+', '', cleaned, flags=re.IGNORECASE).strip()

        # Strip trailing context from last entity when no dimension found yet
        if not dimension:
            ctx_match = _TRAILING_CONTEXT.search(cleaned)
            if ctx_match:
                dim_raw = ctx_match.group(0).strip()
                dimension = re.sub(
                    r'^(?:for|in terms of|regarding|by|in)\s+', '', dim_raw, flags=re.IGNORECASE,
                ).strip()
                cleaned = cleaned[:ctx_match.start()].strip()

        if len(cleaned) < 2:
            continue
        if cleaned.lower() in ('the', 'a', 'an', 'of', 'me', 'i'):
            continue
        entities.append(cleaned.lower())

    # Separate food entities from nutrient names.
    # Queries like "compare zinc and iron in bambara nut vs groundnut" may leave
    # "zinc" and "iron" in the entity list after splitting on "and".
    food_entities: List[str] = []
    nutrient_entities: List[str] = []
    for e in entities:
        if e.lower() in _NUTRIENT_LOOKUP:
            nutrient_entities.append(e)
        else:
            food_entities.append(e)

    # Fold detected nutrient names into dimension (join with " and " if multiple)
    if nutrient_entities:
        nutrient_dim = " and ".join(nutrient_entities)
        if dimension:
            # Only override if what we found is more specific
            dimension = nutrient_dim
        else:
            dimension = nutrient_dim
        entities = food_entities
    else:
        entities = food_entities or entities

    # Deduplicate preserving order
    seen: set = set()
    unique: List[str] = []
    for e in entities:
        if e not in seen:
            seen.add(e)
            unique.append(e)

    if len(unique) > _MAX_COMPARISON_ENTITIES:
        logger.warning("ComparisonWorkflow: truncating %d entities to %d", len(unique), _MAX_COMPARISON_ENTITIES)
        unique = unique[:_MAX_COMPARISON_ENTITIES]

    if len(unique) < 2:
        # Last-resort fallback: split on and/vs only
        fallback = re.split(r'\s+(?:and|vs)\s+', query.lower(), maxsplit=1)
        unique = [f.strip() for f in fallback if len(f.strip()) > 1]

    return unique, dimension


def _extract_compared_entities(user_message: str) -> List[str]:
    """Thin wrapper for backward compat."""
    entities, _ = extract_comparison_entities(user_message)
    return entities


_RETRIEVAL_TOTAL_CAP = 16
_RETRIEVAL_TOP_K_DEFAULT = 4


def retrieve_per_entity(
    entities: List[str],
    dimension: Optional[str],
    retriever: Any,
    top_k_per_entity: int = _RETRIEVAL_TOP_K_DEFAULT,
) -> Dict[str, Any]:
    """
    Fires one retrieval query per entity and returns a dict mapping each
    entity name to its list of passage dicts (source_title, excerpt, entity).

    Caps total passages at _RETRIEVAL_TOTAL_CAP to stay within synthesis context.
    Falls back to "{entity} nutritional composition per 100g" when no dimension given.
    """
    effective_k = min(top_k_per_entity, _RETRIEVAL_TOTAL_CAP // len(entities))
    entity_passages: Dict[str, List[Dict[str, str]]] = {}

    for entity in entities:
        if dimension:
            query = f"{entity} {dimension} per 100g raw dry"
        else:
            # "dry raw" anchors retrieval to standalone FCT entries, not mixed dishes
            query = f"{entity} dry raw nutritional composition per 100g energy protein fat carbohydrate"
        try:
            result = retriever.retrieve(query, top_k=effective_k)
            entity_passages[entity] = [
                {"source_title": p.source_title, "excerpt": p.text[:600], "entity": entity}
                for p in result.passages
            ]
            logger.debug(
                "ComparisonWorkflow retrieve_per_entity: '%s' → %d passages",
                entity, len(entity_passages[entity]),
            )
        except Exception as exc:
            logger.warning(
                "ComparisonWorkflow retrieve_per_entity: retrieval failed for '%s' — %s",
                entity, exc,
            )
            entity_passages[entity] = []

    return entity_passages


class ComparisonWorkflow:

    def __init__(self, retrieval_agent: Any = None) -> None:
        self._retrieval = retrieval_agent

    def execute(
        self,
        state: ConversationState,
        user_message: str,
        state_manager: StateManager,
    ) -> WorkflowResult:
        # Extract compared entities (2–5) and optional dimension
        entities, dimension = extract_comparison_entities(user_message)

        if len(entities) < 2:
            # Fallback 1 — current turn_entities
            entities = list(state.turn_entities.compared_entities)
            # Fallback 2 — prior comparison context from active_task_context
            if len(entities) < 2:
                prior = getattr(state.active_task_context, "comparison_entities", None) or []
                entities = list(prior)
            if len(entities) < 2:
                raise WorkflowError(
                    "Could not identify two items to compare. "
                    "Please use phrasing like 'X vs Y' or 'compare X with Y'."
                )
            dimension = None

        # Reject placeholder entities
        for e in entities:
            if _PLACEHOLDER_RE.match(e):
                raise WorkflowError(
                    f"Comparison entities must be real items, not placeholders (got '{e}')."
                )

        # Persist entities so follow-up turns can reference them
        state.active_task_context.comparison_entities = entities
        state_manager.save_state(state)

        # Context inheritance
        inheritance = state_manager.should_inherit_context(
            state.session_id,
            new_intent=IntentLabel.COMPARISON,
            user_message=user_message,
        )
        patient_context: Optional[Dict[str, Any]] = None
        if inheritance.inherit:
            ce = state.confirmed_entities
            patient_context = {f: getattr(ce, f) for f in inheritance.fields_to_inherit}

        comparison_mode = "quantitative" if _QUANTITY_RE.search(user_message) else "qualitative"

        # Per-entity retrieval — capped total to stay within synthesis context
        evidence_passages = []
        if self._retrieval is not None:
            entity_passages = retrieve_per_entity(
                entities=entities,
                dimension=dimension,
                retriever=self._retrieval,
            )
            evidence_passages = [p for ps in entity_passages.values() for p in ps]

        # entity_a / entity_b kept for downstream display adapter compatibility
        entity_a = entities[0]
        entity_b = entities[1] if len(entities) > 1 else ""

        response_data: Dict[str, Any] = {
            "query_type": "comparison",
            "entity_a": entity_a,
            "entity_b": entity_b,
            "entities": entities,
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
