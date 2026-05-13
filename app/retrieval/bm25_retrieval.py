"""
BM25Retriever — keyword search over ingested passages using rank_bm25.

add_corpus(passages) : build / extend the BM25 index.
search(query)        : return top-k RetrievedPassage by BM25 score.
"""

from __future__ import annotations

import logging
import re
from typing import List

from app.retrieval import EnrichedPassage, RetrievedPassage

# rank_bm25 import is deferred to first use so this module is safe to import
# on Vercel where rank_bm25 may not be installed.

logger = logging.getLogger(__name__)


def _tokenise(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


class BM25Retriever:
    """
    BM25 index built on top of rank_bm25.BM25Okapi.

    The index is rebuilt in full each time add_corpus is called, which is
    acceptable for batch ingestion at startup.  For incremental updates,
    call add_corpus again with the full accumulated passage list.
    """

    def __init__(self) -> None:
        self._passages: List[EnrichedPassage] = []
        self._index: object | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_corpus(self, passages: List[EnrichedPassage]) -> None:
        """Add passages and (re)build the BM25 index."""
        from rank_bm25 import BM25Okapi
        if not passages:
            return
        self._passages.extend(passages)
        tokenised = [_tokenise(p.text) for p in self._passages]
        self._index = BM25Okapi(tokenised)
        logger.info("BM25Retriever: corpus now contains %d passages", len(self._passages))

    def search(self, query: str, top_k: int = 20) -> List[RetrievedPassage]:
        """Return up to top_k passages ranked by BM25 score."""
        if self._index is None or not self._passages:
            return []

        tokens = _tokenise(query)
        scores = self._index.get_scores(tokens)

        # Pair each passage with its score and sort descending
        scored = sorted(
            zip(scores, self._passages),
            key=lambda x: x[0],
            reverse=True,
        )

        results = []
        for score, passage in scored[:top_k]:
            results.append(
                RetrievedPassage(
                    passage_id=passage.passage_id,
                    text=passage.text,
                    source_title=passage.source_title,
                    source_type=passage.source_type,
                    score=float(score),
                )
            )
        return results
