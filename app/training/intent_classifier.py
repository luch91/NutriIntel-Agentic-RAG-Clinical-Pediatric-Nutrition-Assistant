"""
CPNA Intent Classifier — Production Inference Wrapper

Uses onnxruntime + transformers tokenizer so sentence-transformers/torch are
NOT required at inference time. The ONNX model was exported from the original
all-MiniLM-L6-v2 weights and produces bit-identical embeddings (cosine=1.0).

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

    Architecture: ONNX-exported all-MiniLM-L6-v2 embeddings + LogisticRegression.
    Trained on 4,100 synthetic pediatric nutrition queries.

    Classes: therapy, recommendation, comparison, general

    Requires only: onnxruntime, transformers (tokenizer only — no torch).
    """

    _instance = None
    _MAX_LEN = 128

    def __init__(self, model_dir: Path | str | None = None):
        if model_dir is None:
            model_dir = Path(__file__).resolve().parent.parent / "models" / "intent_classifier"
        self.model_dir = Path(model_dir)

        # --- Tokenizer (transformers, no torch needed) ---
        from transformers import AutoTokenizer
        self._tokenizer = AutoTokenizer.from_pretrained(
            str(self.model_dir / "embedding_model")
        )

        # --- ONNX session ---
        import onnxruntime as ort
        onnx_path = self.model_dir / "embedding_model.onnx"
        if not onnx_path.exists():
            raise FileNotFoundError(
                f"ONNX model not found at {onnx_path}. "
                "Run scripts/export_onnx.py to generate it."
            )
        self._session = ort.InferenceSession(
            str(onnx_path),
            providers=["CPUExecutionProvider"],
        )

        # --- LogisticRegression + label encoder ---
        with open(self.model_dir / "classifier.pkl", "rb") as f:
            self.classifier = pickle.load(f)
        with open(self.model_dir / "label_encoder.pkl", "rb") as f:
            self.label_encoder = pickle.load(f)

        # --- Label mapping (reference) ---
        with open(self.model_dir / "label_mapping.json", "r") as f:
            self.label_mapping = json.load(f)

        eval_path = self.model_dir / "evaluation_results.json"
        self.eval_results = json.loads(eval_path.read_text()) if eval_path.exists() else None

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def _embed(self, texts: list[str]) -> np.ndarray:
        """Tokenize → ONNX forward pass → mean-pool → L2-normalise."""
        enc = self._tokenizer(
            texts,
            return_tensors="np",
            padding="max_length",
            truncation=True,
            max_length=self._MAX_LEN,
        )
        input_ids = enc["input_ids"].astype(np.int64)
        attention_mask = enc["attention_mask"].astype(np.int64)
        token_type_ids = enc.get(
            "token_type_ids", np.zeros_like(input_ids)
        ).astype(np.int64)

        (last_hidden,) = self._session.run(
            ["last_hidden_state"],
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids,
            },
        )
        # Mean pooling over non-padding tokens
        mask = attention_mask[..., np.newaxis].astype(np.float32)
        summed = (last_hidden * mask).sum(axis=1)
        count = mask.sum(axis=1).clip(min=1e-9)
        embeddings = summed / count  # (batch, 384)

        # L2 normalise
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True).clip(min=1e-9)
        return embeddings / norms

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(self, query: str) -> IntentResult:
        embedding = self._embed([query])
        pred = self.classifier.predict(embedding)[0]
        probs = self.classifier.predict_proba(embedding)[0]
        intent = self.label_encoder.inverse_transform([pred])[0]
        all_scores = {
            label: float(probs[i])
            for i, label in enumerate(self.label_encoder.classes_)
        }
        return IntentResult(
            intent=intent,
            confidence=float(probs.max()),
            all_scores=all_scores,
            raw_probabilities=probs,
        )

    def predict_batch(self, queries: list[str]) -> list[IntentResult]:
        embeddings = self._embed(queries)
        preds = self.classifier.predict(embeddings)
        probs = self.classifier.predict_proba(embeddings)
        results = []
        for pred, prob in zip(preds, probs):
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

    print("CPNA Intent Classifier — ONNX Inference")
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
        downgrade_flag = " DOWNGRADE" if result.should_downgrade else ""
        print(f"Query: \"{q}\"")
        print(f"  Intent: {result.intent} (confidence: {result.confidence:.4f}){downgrade_flag}")
        scores_str = ", ".join(
            f"{k}: {v:.3f}" for k, v in sorted(result.all_scores.items(), key=lambda x: -x[1])
        )
        print(f"  Scores: {scores_str}")
        print()
