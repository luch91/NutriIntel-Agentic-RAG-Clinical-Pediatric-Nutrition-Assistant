"""
Hybrid merger — combines vector and BM25 results, deduplicates, and normalises scores.

merge_and_deduplicate(vector_results, bm25_results, alpha) -> List[RetrievedPassage]

alpha controls the vector weight (1-alpha is BM25 weight).
Scores are min-max normalised within each list before blending.
"""

from __future__ import annotations

from typing import Dict, List

from app.retrieval import RetrievedPassage

_DEFAULT_ALPHA = 0.6  # 60 % vector, 40 % BM25


def _normalise(passages: List[RetrievedPassage]) -> Dict[str, float]:
    """Return {passage_id: normalised_score} with scores in [0, 1]."""
    if not passages:
        return {}
    scores = [p.score for p in passages]
    lo, hi = min(scores), max(scores)
    span = hi - lo if hi != lo else 1.0
    return {p.passage_id: (p.score - lo) / span for p in passages}


def merge_and_deduplicate(
    vector_results: List[RetrievedPassage],
    bm25_results: List[RetrievedPassage],
    alpha: float = _DEFAULT_ALPHA,
) -> List[RetrievedPassage]:
    """
    Blend vector and BM25 scores, deduplicate by passage_id, and return
    results sorted by blended score descending.

    A passage that appears in only one list receives 0.0 for the absent list.
    """
    vec_scores = _normalise(vector_results)
    bm25_scores = _normalise(bm25_results)

    # Build a lookup from passage_id → passage object (vector list takes priority
    # for metadata since embeddings are already attached there)
    passage_map: Dict[str, RetrievedPassage] = {}
    for p in vector_results:
        passage_map[p.passage_id] = p
    for p in bm25_results:
        if p.passage_id not in passage_map:
            passage_map[p.passage_id] = p

    all_ids = set(passage_map)
    blended: List[RetrievedPassage] = []
    for pid in all_ids:
        v_score = vec_scores.get(pid, 0.0)
        b_score = bm25_scores.get(pid, 0.0)
        combined = alpha * v_score + (1.0 - alpha) * b_score
        p = passage_map[pid]
        blended.append(
            RetrievedPassage(
                passage_id=p.passage_id,
                text=p.text,
                source_title=p.source_title,
                source_type=p.source_type,
                score=combined,
            )
        )

    blended.sort(key=lambda x: x.score, reverse=True)
    return blended
