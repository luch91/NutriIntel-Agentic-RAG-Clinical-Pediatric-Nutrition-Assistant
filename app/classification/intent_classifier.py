"""
Intent classification service for CPNA v1.

This module wraps the existing trained model at app/models/intent_classifier/
(sentence-transformer + LogisticRegression, 98.6% F1).

It does NOT define a new model — it delegates all inference to the production
wrapper already implemented in app/training/intent_classifier.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

from app.classification.intent_labels import CONFIDENCE_THRESHOLD, IntentLabel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result contract
# ---------------------------------------------------------------------------

@dataclass
class ClassificationResult:
    label: Optional[IntentLabel]    # None when needs_clarification is True
    confidence: float
    all_scores: Dict[str, float]
    needs_clarification: bool


# ---------------------------------------------------------------------------
# Production classifier — wraps app/training/intent_classifier.py
# ---------------------------------------------------------------------------

class IntentClassifier:
    """
    Wraps the trained sentence-transformer + LogisticRegression model.

    Loads model artifacts from app/models/intent_classifier/:
      - embedding_model/   (all-MiniLM-L6-v2, saved locally)
      - classifier.pkl     (LogisticRegression weights)
      - label_encoder.pkl
      - label_mapping.json

    Label mapping in use: label_mapping.json
      {"therapy": 0, "recommendation": 1, "comparison": 2, "general": 3}
    """

    def __init__(self, model_path: str = "app/models/intent_classifier") -> None:
        # Import here so the module can be imported even when torch is unavailable
        # (tests use MockIntentClassifier and never instantiate this class).
        from app.training.intent_classifier import (
            IntentClassifier as _UpstreamClassifier,
        )

        self._clf = _UpstreamClassifier(model_dir=model_path)
        logger.info(
            "IntentClassifier loaded. Label mapping: label_mapping.json "
            "(therapy=0, recommendation=1, comparison=2, general=3)"
        )

    # Map raw label strings from the upstream model → IntentLabel enum
    _LABEL_MAP: Dict[str, IntentLabel] = {
        "therapy": IntentLabel.THERAPY,
        "recommendation": IntentLabel.RECOMMENDATION,
        "comparison": IntentLabel.COMPARISON,
        "general": IntentLabel.GENERAL,
    }

    def classify(self, text: str) -> ClassificationResult:
        """
        Run inference on a single query string.

        Returns ClassificationResult. label is None when confidence falls
        below CONFIDENCE_THRESHOLD (needs_clarification=True).
        Any inference error returns needs_clarification=True, confidence=0.0.
        """
        try:
            result = self._clf.predict(text)
            confidence = float(result.confidence)
            all_scores: Dict[str, float] = {k: float(v) for k, v in result.all_scores.items()}
            needs_clarification = confidence < CONFIDENCE_THRESHOLD
            label: Optional[IntentLabel] = (
                None if needs_clarification
                else self._LABEL_MAP.get(result.intent)
            )
            return ClassificationResult(
                label=label,
                confidence=confidence,
                all_scores=all_scores,
                needs_clarification=needs_clarification,
            )
        except Exception as exc:
            logger.error("IntentClassifier inference error: %s", exc, exc_info=True)
            return ClassificationResult(
                label=None,
                confidence=0.0,
                all_scores={},
                needs_clarification=True,
            )

    def is_low_confidence(self, result: ClassificationResult) -> bool:
        return result.confidence < CONFIDENCE_THRESHOLD


# ---------------------------------------------------------------------------
# Mock classifier — keyword-based, model-independent (for tests)
# ---------------------------------------------------------------------------

class MockIntentClassifier:
    """
    Deterministic keyword-based classifier for unit and integration tests.
    Same interface as IntentClassifier — no model loading required.
    """

    _THERAPY_KEYWORDS = ["plan", "personalized", "therapy", "meal plan", "targets"]
    _RECOMMENDATION_KEYWORDS = ["recommend", "diet for", "guidance"]
    _COMPARISON_KEYWORDS = ["compare", "vs", "difference between"]

    def classify(self, text: str) -> ClassificationResult:
        if len(text) < 4:
            return ClassificationResult(
                label=None,
                confidence=0.5,
                all_scores={"therapy": 0.125, "recommendation": 0.125,
                            "comparison": 0.125, "general": 0.625},
                needs_clarification=True,
            )

        lower = text.lower()
        if any(kw in lower for kw in self._THERAPY_KEYWORDS):
            label = IntentLabel.THERAPY
        elif any(kw in lower for kw in self._RECOMMENDATION_KEYWORDS):
            label = IntentLabel.RECOMMENDATION
        elif any(kw in lower for kw in self._COMPARISON_KEYWORDS):
            label = IntentLabel.COMPARISON
        else:
            label = IntentLabel.GENERAL

        scores = {i.value: 0.05 for i in IntentLabel}
        scores[label.value] = 0.85

        return ClassificationResult(
            label=label,
            confidence=0.85,
            all_scores=scores,
            needs_clarification=False,
        )

    def is_low_confidence(self, result: ClassificationResult) -> bool:
        return result.confidence < CONFIDENCE_THRESHOLD
