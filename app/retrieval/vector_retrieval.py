"""
VectorRetriever — Qdrant in-memory backend with sentence-transformer embeddings.

index(passages)  : embed (if not already embedded) and upsert into Qdrant collection.
search(embedding): return top-k RetrievedPassage by cosine similarity.
"""

from __future__ import annotations

import logging
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
    Wraps Qdrant (in-memory) for passage indexing and similarity search.

    The same SentenceTransformer used by the intent classifier ensures embedding
    consistency across the pipeline.
    """

    def __init__(
        self,
        qdrant_client: Optional[object] = None,
        model: Optional[object] = None,
    ) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import Distance, VectorParams
        from sentence_transformers import SentenceTransformer
        self._client = qdrant_client or QdrantClient(":memory:")
        self._model = model or SentenceTransformer(_MODEL_NAME)
        self._ensure_collection()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _ensure_collection(self) -> None:
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

        to_embed = [p for p in passages if p.embedding is None]
        if to_embed:
            texts = [p.text for p in to_embed]
            vectors = self._model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
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
        self._client.upsert(collection_name=_COLLECTION, points=points)
        logger.info("VectorRetriever: indexed %d passages", len(points))

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
        vec = self._model.encode([text], show_progress_bar=False, convert_to_numpy=True)
        return vec[0].tolist()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stable_int_id(passage_id: str) -> int:
    """Convert any passage_id string to a stable positive int for Qdrant point IDs."""
    import hashlib
    return int(hashlib.md5(passage_id.encode()).hexdigest(), 16) % (2**63)
