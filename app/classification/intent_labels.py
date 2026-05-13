# Single source of truth re-exports for the classification layer.
# IntentLabel enum lives in app/state/conversation_state — import from there only.

from app.state.conversation_state import IntentLabel as IntentLabel  # re-export

CONFIDENCE_THRESHOLD: float = 0.70
