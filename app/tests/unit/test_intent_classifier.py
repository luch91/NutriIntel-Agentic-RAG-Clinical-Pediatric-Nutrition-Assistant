"""
Unit tests for the intent classification service.

All mock-based tests use MockIntentClassifier — no model loading.
One integration test exercises the real IntentClassifier and is skipped
when the model directory is absent.
"""

import os

import pytest

from app.classification.intent_classifier import (
    ClassificationResult,
    IntentClassifier,
    MockIntentClassifier,
)
from app.classification.intent_labels import CONFIDENCE_THRESHOLD
from app.state.conversation_state import IntentLabel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_clf() -> MockIntentClassifier:
    return MockIntentClassifier()


# ---------------------------------------------------------------------------
# MockIntentClassifier — keyword routing
# ---------------------------------------------------------------------------

def test_mock_therapy_query(mock_clf: MockIntentClassifier) -> None:
    result = mock_clf.classify("meal plan for my 8 year old with type 1 diabetes")
    assert result.label == IntentLabel.THERAPY
    assert result.needs_clarification is False


def test_mock_therapy_via_personalized_keyword(mock_clf: MockIntentClassifier) -> None:
    result = mock_clf.classify("Give me a personalized nutrition plan")
    assert result.label == IntentLabel.THERAPY


def test_mock_comparison_query(mock_clf: MockIntentClassifier) -> None:
    result = mock_clf.classify("compare bambara nut to groundnut")
    assert result.label == IntentLabel.COMPARISON
    assert result.needs_clarification is False


def test_mock_comparison_via_vs_keyword(mock_clf: MockIntentClassifier) -> None:
    result = mock_clf.classify("brown rice vs white rice for diabetic children")
    assert result.label == IntentLabel.COMPARISON


def test_mock_general_query(mock_clf: MockIntentClassifier) -> None:
    result = mock_clf.classify("what does vitamin D do in children")
    assert result.label == IntentLabel.GENERAL
    assert result.needs_clarification is False


def test_mock_recommendation_query(mock_clf: MockIntentClassifier) -> None:
    result = mock_clf.classify("diet for a child with IBD")
    assert result.label == IntentLabel.RECOMMENDATION
    assert result.needs_clarification is False


def test_mock_recommendation_via_recommend_keyword(mock_clf: MockIntentClassifier) -> None:
    result = mock_clf.classify("I recommend guidance on cystic fibrosis nutrition")
    assert result.label == IntentLabel.RECOMMENDATION


# ---------------------------------------------------------------------------
# MockIntentClassifier — short input triggers clarification
# ---------------------------------------------------------------------------

def test_mock_short_input_needs_clarification(mock_clf: MockIntentClassifier) -> None:
    result = mock_clf.classify("ok")   # 2 chars < 4
    assert result.needs_clarification is True
    assert result.label is None


def test_mock_three_char_input_needs_clarification(mock_clf: MockIntentClassifier) -> None:
    result = mock_clf.classify("yes")  # exactly 3 chars
    assert result.needs_clarification is True


def test_mock_four_char_input_does_not_need_clarification(mock_clf: MockIntentClassifier) -> None:
    result = mock_clf.classify("iron")  # exactly 4 chars — general
    assert result.needs_clarification is False
    assert result.label == IntentLabel.GENERAL


# ---------------------------------------------------------------------------
# MockIntentClassifier — confidence and scores
# ---------------------------------------------------------------------------

def test_mock_normal_confidence_is_0_85(mock_clf: MockIntentClassifier) -> None:
    result = mock_clf.classify("what is the RDA for zinc in toddlers")
    assert result.confidence == 0.85


def test_mock_all_scores_present(mock_clf: MockIntentClassifier) -> None:
    result = mock_clf.classify("meal plan for cystic fibrosis child")
    assert set(result.all_scores.keys()) == {"therapy", "recommendation", "comparison", "general"}


def test_mock_winning_label_has_highest_score(mock_clf: MockIntentClassifier) -> None:
    result = mock_clf.classify("meal plan for cystic fibrosis child")
    assert result.all_scores["therapy"] == max(result.all_scores.values())


# ---------------------------------------------------------------------------
# is_low_confidence helper
# ---------------------------------------------------------------------------

def test_is_low_confidence_below_threshold(mock_clf: MockIntentClassifier) -> None:
    low = ClassificationResult(
        label=None,
        confidence=CONFIDENCE_THRESHOLD - 0.01,
        all_scores={},
        needs_clarification=True,
    )
    assert mock_clf.is_low_confidence(low) is True


def test_is_low_confidence_at_threshold_is_false(mock_clf: MockIntentClassifier) -> None:
    at = ClassificationResult(
        label=IntentLabel.GENERAL,
        confidence=CONFIDENCE_THRESHOLD,
        all_scores={},
        needs_clarification=False,
    )
    assert mock_clf.is_low_confidence(at) is False


def test_is_low_confidence_above_threshold(mock_clf: MockIntentClassifier) -> None:
    high = ClassificationResult(
        label=IntentLabel.THERAPY,
        confidence=0.95,
        all_scores={},
        needs_clarification=False,
    )
    assert mock_clf.is_low_confidence(high) is False


# ---------------------------------------------------------------------------
# ClassificationResult dataclass
# ---------------------------------------------------------------------------

def test_classification_result_fields_accessible() -> None:
    r = ClassificationResult(
        label=IntentLabel.COMPARISON,
        confidence=0.91,
        all_scores={"comparison": 0.91, "general": 0.05},
        needs_clarification=False,
    )
    assert r.label == IntentLabel.COMPARISON
    assert r.confidence == 0.91
    assert r.needs_clarification is False


# ---------------------------------------------------------------------------
# Real model integration test (skipped if model not present)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.path.exists("app/models/intent_classifier/classifier.pkl"),
    reason="Real model artifacts not present",
)
def test_real_model_loads_and_classifies() -> None:
    clf = IntentClassifier()
    result = clf.classify("How much protein does a 5-year-old with PKU need daily?")
    assert isinstance(result, ClassificationResult)
    assert result.confidence > 0.0
    assert result.label in (list(IntentLabel) + [None])
    assert set(result.all_scores.keys()) == {"therapy", "recommendation", "comparison", "general"}


@pytest.mark.skipif(
    not os.path.exists("app/models/intent_classifier/classifier.pkl"),
    reason="Real model artifacts not present",
)
def test_real_model_therapy_query() -> None:
    clf = IntentClassifier()
    result = clf.classify("Create a personalized meal plan for an 8-year-old girl with cystic fibrosis")
    assert result.label == IntentLabel.THERAPY
    assert result.needs_clarification is False


@pytest.mark.skipif(
    not os.path.exists("app/models/intent_classifier/classifier.pkl"),
    reason="Real model artifacts not present",
)
def test_real_model_comparison_query() -> None:
    clf = IntentClassifier()
    result = clf.classify("Compare bambara nut vs groundnut for iron content")
    assert result.label == IntentLabel.COMPARISON
