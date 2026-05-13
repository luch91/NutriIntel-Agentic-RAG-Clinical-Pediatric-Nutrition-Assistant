"""
TherapyGatekeeperAgent — validates that state is ready for therapy computation.

Rules (in order):
  a. Diagnosis not in SUPPORTED_CONDITIONS → downgrade to recommendation
  b. Any of [age, sex, weight, height, diagnosis, medications] missing → slot fill
  c. Biomarkers missing → proceed with precision warning
"""

from __future__ import annotations

import logging
from typing import List, Optional

from pydantic import BaseModel

from app.observability.metrics import cpna_downgrade_total
from app.state.conversation_state import ConversationState

logger = logging.getLogger(__name__)

SUPPORTED_CONDITIONS: List[str] = [
    "type 1 diabetes",
    "cystic fibrosis",
    "food allergy",
    "preterm nutrition",
    "chronic kidney disease",
    "pku",
    "msud",
    "galactosemia",
    "epilepsy/ketogenic therapy",
    "ibd",
    "gerd",
]

_REQUIRED_SLOTS = ["age", "sex", "weight", "height", "diagnosis", "medications"]


class GatekeeperDecision(BaseModel):
    can_proceed: bool
    missing_slots: List[str] = []
    downgrade_reason: Optional[str] = None
    user_explanation: Optional[str] = None


class TherapyGatekeeperAgent:

    def evaluate(self, state: ConversationState) -> GatekeeperDecision:
        ce = state.confirmed_entities

        diagnosis = ce.diagnosis
        if diagnosis is not None:
            if diagnosis.strip().lower() not in SUPPORTED_CONDITIONS:
                cpna_downgrade_total.labels(downgrade_reason="unsupported_condition").inc()
                logger.info(
                    "TherapyGatekeeperAgent: downgrade — unsupported condition '%s'",
                    diagnosis,
                )
                return GatekeeperDecision(
                    can_proceed=False,
                    downgrade_reason="unsupported_condition",
                    user_explanation=(
                        "I can provide general guidance for this condition, but detailed "
                        "therapy planning requires one of the conditions I'm trained on. "
                        "Let me give you a recommendation instead."
                    ),
                )

        missing = [
            slot for slot in _REQUIRED_SLOTS
            if getattr(ce, slot) is None
        ]
        if missing:
            logger.info(
                "TherapyGatekeeperAgent: slot fill required — missing=%s",
                missing,
            )
            return GatekeeperDecision(
                can_proceed=False,
                missing_slots=missing,
            )

        note: Optional[str] = None
        if ce.biomarkers is None:
            note = (
                "Note: no lab values were provided. Nutrient targets may be less precise "
                "without recent biomarker data (e.g. HbA1c, FEV1, creatinine)."
            )

        logger.info(
            "TherapyGatekeeperAgent: pass — biomarkers_present=%s",
            ce.biomarkers is not None,
        )
        return GatekeeperDecision(
            can_proceed=True,
            user_explanation=note,
        )
