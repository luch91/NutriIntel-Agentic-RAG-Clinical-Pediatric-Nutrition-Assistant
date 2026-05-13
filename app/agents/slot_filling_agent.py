"""
SlotFillingAgent — generates natural-language prompts for missing therapy slots.

Always asks for ONE slot at a time (the first in missing_slots).
Updates state.last_assistant_prompt_type before returning the prompt string.
"""

from __future__ import annotations

import re
from typing import Any, List

from app.state.conversation_state import ConversationState


def parse_slot_value(slot_name: str, raw_value: str) -> Any:
    """
    Normalizes raw user-typed slot values before storing.
    Strips units, converts to correct types.
    Returns parsed value or original string if unparseable.
    """
    if slot_name == "weight":
        match = re.search(
            r"(\d+\.?\d*)\s*(kg|lbs?|pounds?)?",
            raw_value.strip(), re.IGNORECASE
        )
        if match:
            val = float(match.group(1))
            unit = (match.group(2) or "kg").lower().rstrip("s")
            if unit in ("lb", "lbs", "pound"):
                val = round(val * 0.453592, 2)
            return val  # Always stored as kg float
        return raw_value

    if slot_name == "height":
        m_match  = re.search(r"(\d+\.?\d*)\s*m(?:eters?)?(?!\w)", raw_value, re.IGNORECASE)
        cm_match = re.search(r"(\d+\.?\d*)\s*cm", raw_value, re.IGNORECASE)
        ft_match = re.search(r"(\d+)\s*(?:ft|feet)[,\s]*(\d+)?\s*(?:in|inches?)?", raw_value, re.IGNORECASE)
        in_match = re.search(r"(\d+\.?\d*)\s*in(?:ches?)?", raw_value, re.IGNORECASE)

        if m_match:  return round(float(m_match.group(1)) * 100, 1)   # → cm
        if cm_match: return round(float(cm_match.group(1)), 1)
        if ft_match:
            feet   = int(ft_match.group(1))
            inches = int(ft_match.group(2)) if ft_match.group(2) else 0
            return round((feet * 30.48) + (inches * 2.54), 1)
        if in_match: return round(float(in_match.group(1)) * 2.54, 1)
        # Bare number with no unit — assume cm
        bare = re.search(r"^\s*(\d+\.?\d*)\s*$", raw_value)
        if bare:
            return round(float(bare.group(1)), 1)
        return raw_value

    if slot_name == "medications":
        if raw_value.strip().lower() in ("none", "no", "n/a", "nil", "nothing", "no medications"):
            return []   # Valid empty list — not an unfilled slot
        return raw_value

    if slot_name == "age":
        match = re.search(r"(\d+)", raw_value.strip())
        return int(match.group(1)) if match else raw_value

    if slot_name == "diagnosis":
        from app.config.routing_config import normalize_condition
        raw = raw_value.strip().lower()
        return normalize_condition(raw) or raw

    return raw_value.strip()

SLOT_PROMPTS: dict = {
    "age": "How old is your child?",
    "sex": "Is your child male or female?",
    "weight": "What is your child's current weight (in kg or lbs)?",
    "height": "What is your child's height?",
    "diagnosis": "What is the primary diagnosis or condition you'd like me to plan for?",
    "medications": "Is your child currently on any medications? If none, just say 'none'.",
    "biomarkers": (
        "Do you have any recent lab values (e.g. HbA1c, FEV1, creatinine)? "
        "These help me give more precise targets — but you can skip this if unavailable."
    ),
    "country": "Which country are you based in? This helps me suggest locally available foods.",
}


class SlotFillingAgent:

    def generate_slot_prompt(
        self,
        missing_slots: List[str],
        state: ConversationState,
    ) -> str:
        """
        Return the prompt for the FIRST missing slot and update
        state.last_assistant_prompt_type in place.
        """
        if not missing_slots:
            return "It looks like I have all the information I need. Let me proceed."

        first_slot = missing_slots[0]
        state.last_assistant_prompt_type = f"slot_request_{first_slot}"

        return SLOT_PROMPTS.get(first_slot, f"Could you provide your {first_slot}?")
