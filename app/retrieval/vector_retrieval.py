"""
VectorRetriever — Qdrant backend with sentence-transformer embeddings.

Connects to Qdrant Cloud when QDRANT_URL + QDRANT_API_KEY env vars are set,
falls back to in-memory Qdrant for local development.

index(passages)  : embed (if not already embedded) and upsert into Qdrant collection.
search(embedding): return top-k RetrievedPassage by cosine similarity.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

from app.retrieval import EnrichedPassage, RetrievedPassage

# Heavy ML/Qdrant imports are deferred to first use (inside __init__/methods)
# so this module is safe to import on Vercel without torch/qdrant installed.

logger = logging.getLogger(__name__)

_COLLECTION = "cpna_passages"
_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_VECTOR_DIM = 384


class VectorRetriever:
    """
    Wraps Qdrant for passage indexing and similarity search.

    When QDRANT_URL and QDRANT_API_KEY env vars are set, connects to Qdrant Cloud.
    Otherwise uses an in-memory instance (local dev / testing).
    """

    def __init__(
        self,
        qdrant_client: Optional[object] = None,
        model: Optional[object] = None,
    ) -> None:
        from qdrant_client import QdrantClient

        if qdrant_client is not None:
            self._client = qdrant_client
        else:
            qdrant_url = (os.environ.get("QDRANT_URL") or "").strip().lstrip("﻿") or None
            qdrant_api_key = (os.environ.get("QDRANT_API_KEY") or "").strip().lstrip("﻿") or None
            if qdrant_url:
                self._client = QdrantClient(
                    url=qdrant_url,
                    api_key=qdrant_api_key,
                    timeout=120,  # seconds — long enough for large batch upserts
                )
                logger.info("VectorRetriever: connected to Qdrant Cloud at %s", qdrant_url)
            else:
                self._client = QdrantClient(":memory:")
                logger.info("VectorRetriever: using in-memory Qdrant (no QDRANT_URL set)")

        # Model is loaded lazily on first embed_query/index call so this class
        # can be constructed even when sentence-transformers is not installed.
        self._model = model  # None → lazy-loaded in _get_model()
        # Collection check is deferred to index() — skipped on cloud mode where
        # the collection is pre-built, avoiding an HTTP roundtrip during __init__.

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _get_model(self):
        """Return the embedding model, loading it lazily on first call.

        Tries sentence-transformers first (full accuracy, requires torch).
        Falls back to fastembed (ONNX-based, no torch, ~same quality for MiniLM).
        """
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(_MODEL_NAME)
            logger.info("VectorRetriever: loaded SentenceTransformer model %s", _MODEL_NAME)
        except ImportError:
            try:
                from fastembed import TextEmbedding
                # Must use the same model as the indexed collection (all-MiniLM-L6-v2, 384-dim)
                self._model = _FastEmbedWrapper(TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2"))
                logger.info("VectorRetriever: sentence-transformers unavailable, using fastembed (all-MiniLM-L6-v2)")
            except ImportError:
                logger.error("VectorRetriever: neither sentence-transformers nor fastembed available — vector search disabled")
                self._model = None
        return self._model

    def _ensure_collection(self) -> None:
        """Create the Qdrant collection if it doesn't exist. Called only during index()."""
        from qdrant_client.http.models import Distance, VectorParams
        existing = {c.name for c in self._client.get_collections().collections}
        if _COLLECTION not in existing:
            self._client.create_collection(
                collection_name=_COLLECTION,
                vectors_config=VectorParams(size=_VECTOR_DIM, distance=Distance.COSINE),
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index(self, passages: List[EnrichedPassage]) -> None:
        """Embed passages that lack embeddings, then upsert into Qdrant."""
        from qdrant_client.http.models import PointStruct
        if not passages:
            return
        self._ensure_collection()

        to_embed = [p for p in passages if p.embedding is None]
        if to_embed:
            model = self._get_model()
            texts = [p.text for p in to_embed]
            vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
            for passage, vec in zip(to_embed, vectors):
                passage.embedding = vec.tolist()

        points = [
            PointStruct(
                id=_stable_int_id(p.passage_id),
                vector=p.embedding,
                payload={
                    "passage_id": p.passage_id,
                    "text": p.text,
                    "source_title": p.source_title,
                    "source_type": p.source_type,
                    "condition_tags": p.condition_tags,
                },
            )
            for p in passages
        ]
        _UPSERT_BATCH = 100
        _MAX_RETRIES = 3
        for i in range(0, len(points), _UPSERT_BATCH):
            batch = points[i : i + _UPSERT_BATCH]
            for attempt in range(1, _MAX_RETRIES + 1):
                try:
                    self._client.upsert(collection_name=_COLLECTION, points=batch)
                    break
                except Exception as exc:
                    if attempt == _MAX_RETRIES:
                        raise
                    logger.warning(
                        "VectorRetriever: upsert batch %d failed (attempt %d/%d): %s — retrying",
                        i // _UPSERT_BATCH,
                        attempt,
                        _MAX_RETRIES,
                        exc,
                    )
                    import time; time.sleep(5 * attempt)
            logger.info(
                "VectorRetriever: upserted %d/%d passages",
                min(i + _UPSERT_BATCH, len(points)),
                len(points),
            )
        logger.info("VectorRetriever: indexed %d passages total", len(points))

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 20,
    ) -> List[RetrievedPassage]:
        """Return up to top_k passages ranked by cosine similarity."""
        response = self._client.query_points(
            collection_name=_COLLECTION,
            query=query_embedding,
            limit=top_k,
            with_payload=True,
        )
        results = []
        for hit in response.points:
            p = hit.payload
            results.append(
                RetrievedPassage(
                    passage_id=p["passage_id"],
                    text=p["text"],
                    source_title=p["source_title"],
                    source_type=p["source_type"],
                    score=float(hit.score),
                )
            )
        return results

    def embed_query(self, text: str) -> List[float]:
        """Encode a query string into a vector."""
        model = self._get_model()
        if model is None:
            return [0.0] * _VECTOR_DIM
        vec = model.encode([text], show_progress_bar=False, convert_to_numpy=True)
        return vec[0].tolist()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FastEmbedWrapper:
    """Thin adapter so fastembed.TextEmbedding has the same .encode() interface as SentenceTransformer."""

    def __init__(self, model) -> None:
        self._model = model

    def encode(self, texts, show_progress_bar=False, convert_to_numpy=True):
        import numpy as np
        embeddings = list(self._model.embed(texts))
        return np.array(embeddings)


def _stable_int_id(passage_id: str) -> int:
    """Convert any passage_id string to a stable positive int for Qdrant point IDs."""
    import hashlib
    return int(hashlib.md5(passage_id.encode()).hexdigest(), 16) % (2**63)
