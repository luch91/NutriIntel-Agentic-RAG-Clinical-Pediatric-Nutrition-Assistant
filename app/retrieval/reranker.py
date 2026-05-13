"""
Reranker — cross-encoder reranking of merged retrieval results.

rerank(query, passages, top_k) -> List[RetrievedPassage]

Uses cross-encoder/ms-marco-MiniLM-L-6-v2 from sentence-transformers.
Falls back to input order when the model is unavailable.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.retrieval import RetrievedPassage

logger = logging.getLogger(__name__)

_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class Reranker:
    """
    Cross-encoder reranker.  Lazy-loads the model on first use to avoid
    blocking startup when the model weights are not yet cached.
    """

    def __init__(self, model_name: str = _CROSS_ENCODER_MODEL) -> None:
        self._model_name = model_name
        self._model: Optional[object] = None  # sentence_transformers.CrossEncoder

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import CrossEncoder  # type: ignore[attr-defined]
            self._model = CrossEncoder(self._model_name)
            logger.info("Reranker: loaded %s", self._model_name)
        except Exception as exc:
            logger.warning("Reranker: failed to load cross-encoder (%s) — falling back to score order", exc)

    def rerank(
        self,
        query: str,
        passages: List[RetrievedPassage],
        top_k: int = 7,
    ) -> List[RetrievedPassage]:
        """Return up to top_k passages ordered by cross-encoder relevance score."""
        if not passages:
            return []

        self._load()

        if self._model is None:
            # Fall back: return input list truncated to top_k
            return passages[:top_k]

        pairs = [(query, p.text) for p in passages]
        scores = self._model.predict(pairs)  # type: ignore[union-attr]

        scored = sorted(zip(scores, passages), key=lambda x: x[0], reverse=True)
        return [
            RetrievedPassage(
                passage_id=p.passage_id,
                text=p.text,
                source_title=p.source_title,
                source_type=p.source_type,
                score=float(s),
            )
            for s, p in scored[:top_k]
        ]
