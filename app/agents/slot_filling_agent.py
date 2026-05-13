"""
SlotFillingAgent — generates natural-language prompts for missing therapy slots.

Always asks for ONE slot at a time (the first in missing_slots).
Updates state.last_assistant_prompt_type before returning the prompt string.
"""

from __future__ import annotations

from typing import List

from app.state.conversation_state import ConversationState

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
