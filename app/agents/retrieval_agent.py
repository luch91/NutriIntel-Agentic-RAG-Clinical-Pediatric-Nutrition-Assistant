"""
RetrievalAgent — orchestrates the full hybrid retrieval pipeline.

Pipeline (per CLAUDE.md):
  query rewrite → vector search top 20 → BM25 search top 20
  → merge + deduplicate → rerank → top 7 contexts

Returns a RetrievalResult containing the final passages and the rewritten query.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from app.agents.query_rewrite_agent import QueryRewriteAgent
from app.config.routing_config import (
    normalize_condition,
    get_allowed_sources,
    get_priority_source,
)
from app.retrieval import RetrievedPassage
from app.retrieval.bm25_retrieval import BM25Retriever
from app.retrieval.hybrid_merger import merge_and_deduplicate
from app.retrieval.reranker import Reranker
from app.retrieval.vector_retrieval import VectorRetriever

logger = logging.getLogger(__name__)

_VECTOR_TOP_K = 20
_BM25_TOP_K = 20
_RERANK_TOP_K = 7


def _source_matches(passage: "RetrievedPassage", source_id: str) -> bool:
    """
    Match a retrieved passage against a routing source_id.

    passage_id is a 16-char MD5 hex and cannot encode the source. Instead we
    compare source_title (set from metadata["source"] during ingestion) against
    the routing source_id, normalising case and separators so that e.g.
    "WestAfricaFCT2019" matches source_title "WestAfricaFCT2019" or
    "West Africa FCT 2019".
    """
    def _norm(s: str) -> str:
        return s.lower().replace("_", "").replace("-", "").replace(" ", "")

    return _norm(passage.source_title).startswith(_norm(source_id))


@dataclass
class RetrievalResult:
    """Returned by RetrievalAgent.retrieve()."""
    passages: List[RetrievedPassage] = field(default_factory=list)
    rewritten_query: str = ""
    original_query: str = ""
    retrieval_metadata: dict = field(default_factory=dict)


class RetrievalAgent:
    """
    End-to-end retrieval agent.

    Dependency-inject the four sub-components for testability.
    """

    def __init__(
        self,
        vector_retriever: VectorRetriever,
        bm25_retriever: BM25Retriever,
        reranker: Optional[Reranker] = None,
        query_rewrite_agent: Optional[QueryRewriteAgent] = None,
    ) -> None:
        self._vector = vector_retriever
        self._bm25 = bm25_retriever
        self._reranker = reranker or Reranker()
        self._rewrite_agent = query_rewrite_agent or QueryRewriteAgent()

    def retrieve(
        self,
        query: str,
        patient_context: str = "",
        top_k: int = _RERANK_TOP_K,
        diagnosis: Optional[str] = None,
    ) -> RetrievalResult:
        """
        Run the full pipeline and return up to top_k reranked passages.

        Steps:
        1. Rewrite query for retrieval
        2. Condition-aware source resolution
        3. Embed rewritten query
        4. Vector search (top 20) + post-retrieval source filter
        5. BM25 search (top 20) + post-retrieval source filter
        6. Merge + deduplicate
        7. Priority source boosting
        8. Rerank → top_k
        """
        if not query.strip():
            return RetrievalResult(original_query=query)

        # Step 1: query rewrite
        rewritten = self._rewrite_agent.rewrite(query, patient_context)

        # Step 2: condition-aware source resolution
        routing_key = normalize_condition(diagnosis) if diagnosis else None
        allowed_sources = get_allowed_sources(routing_key) if routing_key else []
        condition_filter_applied = bool(allowed_sources)

        # Step 3: embed
        query_embedding = self._vector.embed_query(rewritten)

        # Step 4: vector search + post-retrieval source filter
        vec_results = self._vector.search(query_embedding, top_k=_VECTOR_TOP_K)
        logger.info("RetrievalAgent: vector_hits=%d", len(vec_results))
        if allowed_sources:
            vec_results = [
                p for p in vec_results
                if any(_source_matches(p, src) for src in allowed_sources)
            ]
        logger.info("RetrievalAgent: vector_after_filter=%d", len(vec_results))

        # Step 5: BM25 search + post-retrieval source filter
        bm25_results = self._bm25.search(rewritten, top_k=_BM25_TOP_K)
        logger.info("RetrievalAgent: bm25_hits=%d", len(bm25_results))
        if allowed_sources:
            bm25_results = [
                p for p in bm25_results
                if any(_source_matches(p, src) for src in allowed_sources)
            ]
        logger.info("RetrievalAgent: bm25_after_filter=%d", len(bm25_results))

        # Step 6: merge + deduplicate
        merged = merge_and_deduplicate(vec_results, bm25_results)
        logger.info("RetrievalAgent: merged=%d", len(merged))

        # Step 7: priority source boosting (before reranker)
        priority_source = get_priority_source(routing_key) if routing_key else None
        priority_source_boosted = None
        if priority_source:
            priority_passages = [
                p for p in merged if _source_matches(p, priority_source)
            ]
            other_passages = [
                p for p in merged if not _source_matches(p, priority_source)
            ]
            merged = priority_passages + other_passages
            priority_source_boosted = priority_source

        # Step 8: rerank
        final = self._reranker.rerank(rewritten, merged, top_k=top_k)
        logger.info(
            "RetrievalAgent: query='%s' → rewritten='%s', top_k=%d returned, "
            "condition_filter=%s, priority_source=%s",
            query[:60],
            rewritten[:60],
            len(final),
            routing_key,
            priority_source_boosted,
        )

        return RetrievalResult(
            passages=final,
            rewritten_query=rewritten,
            original_query=query,
            retrieval_metadata={
                "condition_filter_applied": condition_filter_applied,
                "priority_source_boosted": priority_source_boosted,
                "routing_key": routing_key,
                "allowed_sources": allowed_sources,
            },
        )
