"""
CPNA Intent Classifier — Production Inference Wrapper

Usage:
    from app.training.intent_classifier import IntentClassifier

    clf = IntentClassifier()
    result = clf.predict("How much zinc should a 3-year-old with CF get?")
    print(result.intent)         # "recommendation"
    print(result.confidence)     # 0.9766
    print(result.all_scores)     # {"therapy": 0.01, "recommendation": 0.97, ...}
"""

import json
import pickle
from pathlib import Path
from dataclasses import dataclass
from typing import Dict

import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass
class IntentResult:
    """Result from intent classification."""
    intent: str
    confidence: float
    all_scores: Dict[str, float]
    raw_probabilities: np.ndarray

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.85

    @property
    def is_medium_confidence(self) -> bool:
        return self.confidence >= 0.65

    @property
    def should_downgrade(self) -> bool:
        return self.confidence < 0.65


class IntentClassifier:
    """
    Production intent classifier for CPNA.

    Architecture: sentence-transformer embeddings + LogisticRegression.
    Trained on 4,100 synthetic pediatric nutrition queries.

    Classes: therapy, recommendation, comparison, general
    """

    _instance = None

    def __init__(self, model_dir: Path | str | None = None):
        if model_dir is None:
            model_dir = Path(__file__).resolve().parent.parent / "models" / "intent_classifier"
        self.model_dir = Path(model_dir)

        # Load embedding model
        self.embedder = SentenceTransformer(str(self.model_dir / "embedding_model"))

        # Load classifier
        with open(self.model_dir / "classifier.pkl", "rb") as f:
            self.classifier = pickle.load(f)

        # Load label encoder
        with open(self.model_dir / "label_encoder.pkl", "rb") as f:
            self.label_encoder = pickle.load(f)

        # Load label mapping
        with open(self.model_dir / "label_mapping.json", "r") as f:
            self.label_mapping = json.load(f)

        # Load evaluation results (for reference)
        eval_path = self.model_dir / "evaluation_results.json"
        if eval_path.exists():
            with open(eval_path, "r") as f:
                self.eval_results = json.load(f)
        else:
            self.eval_results = None

    def predict(self, query: str) -> IntentResult:
        """
        Classify a single query.

        Args:
            query: User query text

        Returns:
            IntentResult with intent, confidence, and all scores
        """
        # Embed
        embedding = self.embedder.encode([query])

        # Predict
        pred = self.classifier.predict(embedding)[0]
        probs = self.classifier.predict_proba(embedding)[0]

        # Convert to label
        intent = self.label_encoder.inverse_transform([pred])[0]

        # Build score dict
        all_scores = {}
        for i, label in enumerate(self.label_encoder.classes_):
            all_scores[label] = float(probs[i])

        return IntentResult(
            intent=intent,
            confidence=float(probs.max()),
            all_scores=all_scores,
            raw_probabilities=probs,
        )

    def predict_batch(self, queries: list[str]) -> list[IntentResult]:
        """
        Classify multiple queries in batch.

        Args:
            queries: List of query texts

        Returns:
            List of IntentResult
        """
        # Embed all at once
        embeddings = self.embedder.encode(queries, batch_size=32)

        # Predict
        preds = self.classifier.predict(embeddings)
        probs = self.classifier.predict_proba(embeddings)

        results = []
        for i, (pred, prob) in enumerate(zip(preds, probs)):
            intent = self.label_encoder.inverse_transform([pred])[0]
            all_scores = {
                label: float(prob[j])
                for j, label in enumerate(self.label_encoder.classes_)
            }
            results.append(IntentResult(
                intent=intent,
                confidence=float(prob.max()),
                all_scores=all_scores,
                raw_probabilities=prob,
            ))
        return results

    def get_eval_summary(self) -> dict:
        """Return evaluation summary for monitoring."""
        if self.eval_results is None:
            return {}
        return {
            "accuracy": self.eval_results.get("accuracy"),
            "f1_macro": self.eval_results.get("f1_macro"),
            "ece": self.eval_results.get("ece_test"),
            "test_samples": self.eval_results.get("test_samples"),
            "per_class": self.eval_results.get("per_class"),
        }


# ── Convenience function ────────────────────────────────────────────────────

def classify_intent(query: str) -> IntentResult:
    """Quick single-query classification."""
    if IntentClassifier._instance is None:
        IntentClassifier._instance = IntentClassifier()
    return IntentClassifier._instance.predict(query)


# ── CLI demo ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    clf = IntentClassifier()

    print("CPNA Intent Classifier — Production Inference")
    print("=" * 50)
    print()

    if clf.eval_results:
        print(f"Model: {clf.eval_results.get('model_type', 'unknown')}")
        print(f"Test F1: {clf.eval_results.get('f1_macro', 'N/A')}")
        print(f"Test Accuracy: {clf.eval_results.get('accuracy', 'N/A')}")
        print()

    queries = [
        "How much protein does a 5-year-old with nephrotic syndrome need?",
        "Compare the vitamin C in fresh vs frozen spinach",
        "What is the RDA for calcium in toddlers?",
        "Best nutrition strategy for a premature infant with BPD",
        "What foods are high in iron?",
        "Is keto diet safe for a 2-year-old with epilepsy?",
        "Compare NG tube vs G-tube for cerebral palsy feeding",
        "How does vitamin D deficiency affect bone growth?",
    ]

    for q in queries:
        result = clf.predict(q)
        downgrade_flag = " ⚠️ DOWNGRADE" if result.should_downgrade else ""
        print(f"Query: \"{q}\"")
        print(f"  Intent: {result.intent} (confidence: {result.confidence:.4f}){downgrade_flag}")
        scores_str = ", ".join(f"{k}: {v:.3f}" for k, v in sorted(result.all_scores.items(), key=lambda x: -x[1]))
        print(f"  Scores: {scores_str}")
        print()
