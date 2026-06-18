"""
Reranker — reranking of merged retrieval results.

rerank(query, passages, top_k) -> List[RetrievedPassage]

Strategy (in priority order):
  1. Cohere Rerank 4 Fast via OpenRouter (OPENROUTER_API_KEY) — best quality
  2. Local cross-encoder (ms-marco-MiniLM-L-6-v2) — no API key needed
  3. Input order — if both above fail
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

import httpx

from app.retrieval import RetrievedPassage

logger = logging.getLogger(__name__)

_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_OPENROUTER_RERANK_URL = "https://openrouter.ai/api/v1/rerank"
_RERANK_MODEL = "cohere/rerank-4-fast"
_RERANK_TIMEOUT = 10.0


class Reranker:
    """
    Hybrid reranker: prefers Cohere Rerank via OpenRouter when
    OPENROUTER_API_KEY is set, falls back to a local cross-encoder,
    then to input order.
    """

    def __init__(self, model_name: str = _CROSS_ENCODER_MODEL) -> None:
        self._model_name = model_name
        self._local_model: Optional[object] = None
        self._api_key: Optional[str] = None
        self._api_available: Optional[bool] = None
        self._local_available: Optional[bool] = None

    def _resolve_api(self) -> bool:
        if self._api_available is not None:
            return self._api_available
        key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
        if key:
            self._api_key = key
            self._api_available = True
            logger.info("Reranker: OpenRouter key found — using %s", _RERANK_MODEL)
        else:
            self._api_available = False
        return self._api_available

    def _load_local(self) -> bool:
        if self._local_available is not None:
            return self._local_available
        try:
            from sentence_transformers import CrossEncoder  # type: ignore[attr-defined]
            self._local_model = CrossEncoder(self._model_name)
            self._local_available = True
            logger.info("Reranker: loaded local %s", self._model_name)
        except Exception as exc:
            self._local_available = False
            logger.warning("Reranker: local cross-encoder unavailable (%s)", exc)
        return self._local_available

    def _api_rerank(
        self,
        query: str,
        passages: List[RetrievedPassage],
        top_k: int,
    ) -> Optional[List[RetrievedPassage]]:
        docs = [p.text for p in passages]
        try:
            resp = httpx.post(
                _OPENROUTER_RERANK_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _RERANK_MODEL,
                    "query": query,
                    "documents": docs,
                    "top_n": top_k,
                },
                timeout=_RERANK_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("Reranker: OpenRouter rerank failed (%s) — falling back", exc)
            return None

        results = data.get("results", [])
        reranked: List[RetrievedPassage] = []
        for item in results:
            idx = item["index"]
            score = float(item["relevance_score"])
            p = passages[idx]
            reranked.append(RetrievedPassage(
                passage_id=p.passage_id,
                text=p.text,
                source_title=p.source_title,
                source_type=p.source_type,
                score=score,
            ))
        logger.debug(
            "Reranker: Cohere rerank-4-fast returned %d results, top score=%.4f",
            len(reranked),
            reranked[0].score if reranked else 0.0,
        )
        return reranked

    def _local_rerank(
        self,
        query: str,
        passages: List[RetrievedPassage],
        top_k: int,
    ) -> List[RetrievedPassage]:
        pairs = [(query, p.text) for p in passages]
        scores = self._local_model.predict(pairs)  # type: ignore[union-attr]
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

    def rerank(
        self,
        query: str,
        passages: List[RetrievedPassage],
        top_k: int = 7,
    ) -> List[RetrievedPassage]:
        """Return up to top_k passages ordered by relevance score."""
        if not passages:
            return []

        if self._resolve_api():
            result = self._api_rerank(query, passages, top_k)
            if result is not None:
                return result

        if self._load_local():
            return self._local_rerank(query, passages, top_k)

        return passages[:top_k]
