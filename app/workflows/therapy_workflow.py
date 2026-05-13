"""
TherapyWorkflow — end-to-end therapy query handler.

Steps:
  1. Basic entity extraction from user_message → update turn_entities
  2. TherapyGatekeeperAgent.evaluate(state)
  3a. Missing slots → SlotFillingAgent prompt
  3b. Unsupported condition → delegate to RecommendationWorkflow with downgrade flag
  4. Gatekeeper pass → DeterministicNutrientEngine.compute_therapy_plan
  5. RetrievalAgent.retrieve for supporting evidence
  6. Assemble raw output dict
  7. Return WorkflowResult
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from typing import Any

from app.agents.retrieval_agent import RetrievalAgent
from app.agents.slot_filling_agent import SlotFillingAgent
from app.agents.therapy_gatekeeper_agent import TherapyGatekeeperAgent
from app.classification.intent_labels import IntentLabel
from app.engine.deterministic_nutrient_engine import DeterministicNutrientEngine
from app.state.conversation_state import ConversationPhase, ConversationState, TurnEntities
from app.state.state_manager import StateManager

logger = logging.getLogger(__name__)

_PLACEHOLDER_PATTERN = re.compile(r"^(food [ab]|entity [ab]|item [ab])$", re.IGNORECASE)


@dataclass
class WorkflowResult:
    response_data: Dict[str, Any] = field(default_factory=dict)
    query_type: IntentLabel = IntentLabel.THERAPY
    updated_state: Optional[ConversationState] = None
    requires_slot_fill: bool = False
    slot_prompt: Optional[str] = None


def _extract_turn_entities(user_message: str) -> TurnEntities:
    """Lightweight regex + keyword extraction from a single turn message."""
    entities = TurnEntities()

    # Age — "8 years", "8y", "18 months", bare digit strings like "8"
    age_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:years?|y(?:rs?)?|months?|mo)\b", user_message, re.IGNORECASE)
    if age_match:
        entities.age_mentioned = age_match.group(0).strip()

    # Country keywords — simple heuristic
    country_match = re.search(r"\b(?:in|from|based in)\s+([A-Z][a-z]{2,}(?:\s[A-Z][a-z]+)?)\b", user_message)
    if country_match:
        entities.country_mentioned = country_match.group(1)

    # Diagnosis keywords
    diagnosis_keywords = {
        "type 1 diabetes": "type 1 diabetes",
        "t1d": "type 1 diabetes",
        "cystic fibrosis": "cystic fibrosis",
        "pku": "pku",
        "ckd": "chronic kidney disease",
        "preterm": "preterm nutrition",
        "ketogenic": "epilepsy/ketogenic therapy",
        "epilepsy": "epilepsy/ketogenic therapy",
        "ibd": "ibd",
        "gerd": "gerd",
    }
    msg_lower = user_message.lower()
    for keyword, label in diagnosis_keywords.items():
        if keyword in msg_lower:
            entities.diagnosis_mentioned = label
            break

    return entities


class TherapyWorkflow:

    def __init__(
        self,
        retrieval_agent: Any = None,
        engine: Optional[DeterministicNutrientEngine] = None,
    ) -> None:
        self._retrieval = retrieval_agent
        self._engine = engine or DeterministicNutrientEngine()
        self._gatekeeper = TherapyGatekeeperAgent()
        self._slot_filler = SlotFillingAgent()

    def execute(
        self,
        state: ConversationState,
        user_message: str,
        state_manager: StateManager,
    ) -> WorkflowResult:
        # Step 1 — entity extraction
        turn_entities = _extract_turn_entities(user_message)
        state = state_manager.update_turn_entities(state.session_id, turn_entities)

        # Step 2 — gatekeeper
        decision = self._gatekeeper.evaluate(state)

        # Step 3a — missing slots
        if not decision.can_proceed and decision.missing_slots:
            prompt = self._slot_filler.generate_slot_prompt(decision.missing_slots, state)
            # Persist pending_slots and enter SLOT_FILLING phase
            state.active_task_context.pending_slots = decision.missing_slots
            state.phase = ConversationPhase.SLOT_FILLING
            if state.active_task_context.current_intent is None:
                state.active_task_context.current_intent = IntentLabel.THERAPY
            state_manager.save_state(state)
            return WorkflowResult(
                response_data={"slot_prompt": prompt},
                query_type=IntentLabel.THERAPY,
                updated_state=state,
                requires_slot_fill=True,
                slot_prompt=prompt,
            )

        # Step 3b — unsupported condition → downgrade
        if not decision.can_proceed and decision.downgrade_reason == "unsupported_condition":
            state = state_manager.set_downgrade(
                state.session_id,
                reason="unsupported_condition",
                user_explanation=decision.user_explanation or "",
                from_intent=IntentLabel.THERAPY,
            )
            from app.workflows.recommendation_workflow import RecommendationWorkflow
            reco_result = RecommendationWorkflow(retrieval_agent=self._retrieval).execute(
                state, user_message, state_manager, downgraded_from_therapy=True
            )
            reco_result.response_data["downgrade_note"] = decision.user_explanation
            return reco_result

        # Step 4 — compute therapy plan
        try:
            engine_result = self._engine.compute_therapy_plan(state.confirmed_entities)
        except Exception as exc:
            logger.error("TherapyWorkflow: engine error — %s", exc)
            return WorkflowResult(
                response_data={"error": str(exc)},
                query_type=IntentLabel.THERAPY,
                updated_state=state,
            )

        # Step 5 — retrieval for evidence
        evidence_passages = []
        if self._retrieval is not None:
            try:
                retrieval_result = self._retrieval.retrieve(
                    user_message,
                    diagnosis=state.confirmed_entities.diagnosis,
                )
                evidence_passages = [
                    {"source_title": p.source_title, "excerpt": p.text[:300]}
                    for p in retrieval_result.passages
                ]
            except Exception as exc:
                logger.warning("TherapyWorkflow: retrieval failed — %s", exc)

        # Step 6 — assemble raw output
        precision_note = decision.user_explanation  # may carry biomarker note
        response_data: Dict[str, Any] = {
            "patient_summary": engine_result.patient_summary,
            "nutrient_targets": [t.model_dump() for t in engine_result.nutrient_targets],
            "drug_nutrient_notes": [n.model_dump() for n in engine_result.drug_nutrient_notes],
            "food_sources": {k: [fs.model_dump() for fs in v] for k, v in engine_result.food_sources.items()},
            "meal_plan": engine_result.meal_plan.model_dump(),
            "evidence": evidence_passages,
            "precision_note": precision_note,
            # computation_trace is INTERNAL — DisplayAdapter must strip this
            "_computation_trace": engine_result.computation_trace,
        }

        return WorkflowResult(
            response_data=response_data,
            query_type=IntentLabel.THERAPY,
            updated_state=state,
        )
