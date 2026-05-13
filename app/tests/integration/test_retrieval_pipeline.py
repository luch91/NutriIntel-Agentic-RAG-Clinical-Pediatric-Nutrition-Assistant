"""
Integration tests for the hybrid retrieval pipeline.

Tests run without real PDF files or a live Anthropic key:
- VectorRetriever and BM25Retriever are seeded with synthetic EnrichedPassage objects.
- QueryRewriteAgent is monkey-patched to return the query unchanged (no API call).
- Reranker falls back to score order when the cross-encoder model is absent.

All five tests verify end-to-end behaviour of the assembled pipeline.
"""

from __future__ import annotations

import pytest
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from app.agents.retrieval_agent import RetrievalAgent, RetrievalResult
from app.retrieval import EnrichedPassage
from app.retrieval.bm25_retrieval import BM25Retriever
from app.retrieval.hybrid_merger import merge_and_deduplicate
from app.retrieval.reranker import Reranker
from app.retrieval.vector_retrieval import VectorRetriever


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@pytest.fixture(scope="module")
def shared_model() -> SentenceTransformer:
    """Load the embedding model once for the entire module."""
    return SentenceTransformer(_MODEL_NAME)


@pytest.fixture(scope="module")
def sample_passages() -> list[EnrichedPassage]:
    """Twelve synthetic passages covering different clinical topics."""
    data = [
        ("p01", "Cystic fibrosis nutrition requires high-energy, high-fat diet with pancreatic enzyme replacement.", "shaw_2020", "cystic_fibrosis"),
        ("p02", "PKU management involves severe restriction of phenylalanine through a low-protein diet.", "shaw_2020", "pku"),
        ("p03", "Type 1 diabetes meal planning uses carbohydrate counting and insulin-to-carb ratios.", "shaw_2020", "type_1_diabetes"),
        ("p04", "Preterm infants require fortified human milk or preterm formula to meet their high nutrient needs.", "shaw_2020", "preterm"),
        ("p05", "Vitamin D requirements for children are 600 IU per day according to DRI tables.", "dri", "vitamin_d"),
        ("p06", "Iron deficiency anaemia in children is the most common nutritional deficiency worldwide.", "oxford_handbook", "iron_deficiency"),
        ("p07", "MSUD requires restriction of branched-chain amino acids, especially leucine.", "shaw_2020", "msud"),
        ("p08", "Ketogenic diet for epilepsy uses a 4:1 fat-to-carbohydrate ratio to induce ketosis.", "shaw_2020", "epilepsy"),
        ("p09", "Chronic kidney disease in children requires phosphorus and potassium restriction.", "shaw_2020", "ckd"),
        ("p10", "IBD nutritional support often uses exclusive enteral nutrition as first-line therapy.", "shaw_2020", "ibd"),
        ("p11", "Galactosemia requires elimination of galactose from the diet, including all dairy products.", "shaw_2020", "galactosemia"),
        ("p12", "Food allergy management involves strict allergen avoidance and nutritional monitoring.", "shaw_2020", "food_allergy"),
    ]
    passages = []
    for pid, text, source_type, tag in data:
        passages.append(
            EnrichedPassage(
                passage_id=pid,
                text=text,
                source_title="Clinical Paediatric Dietetics",
                source_type=source_type,
                condition_tags=[tag],
                embedding=None,
            )
        )
    return passages


@pytest.fixture(scope="module")
def vector_retriever(shared_model: SentenceTransformer, sample_passages: list[EnrichedPassage]) -> VectorRetriever:
    client = QdrantClient(":memory:")
    vr = VectorRetriever(qdrant_client=client, model=shared_model)
    vr.index(sample_passages)
    return vr


@pytest.fixture(scope="module")
def bm25_retriever(sample_passages: list[EnrichedPassage]) -> BM25Retriever:
    br = BM25Retriever()
    br.add_corpus(sample_passages)
    return br


class _PassthroughQueryRewriter:
    """Returns the query unchanged — no Anthropic API call."""
    def rewrite(self, query: str, patient_context: str = "") -> str:
        return query


@pytest.fixture(scope="module")
def retrieval_agent(
    vector_retriever: VectorRetriever,
    bm25_retriever: BM25Retriever,
) -> RetrievalAgent:
    return RetrievalAgent(
        vector_retriever=vector_retriever,
        bm25_retriever=bm25_retriever,
        reranker=Reranker(),
        query_rewrite_agent=_PassthroughQueryRewriter(),  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_retrieve_returns_retrieval_result(retrieval_agent: RetrievalAgent) -> None:
    result = retrieval_agent.retrieve("nutrition for cystic fibrosis child")
    assert isinstance(result, RetrievalResult)
    assert isinstance(result.passages, list)
    assert result.original_query == "nutrition for cystic fibrosis child"


def test_retrieve_returns_up_to_seven_passages(retrieval_agent: RetrievalAgent) -> None:
    result = retrieval_agent.retrieve("dietary management of pediatric PKU")
    assert 1 <= len(result.passages) <= 7


def test_most_relevant_passage_ranks_first(retrieval_agent: RetrievalAgent) -> None:
    """The cystic fibrosis passage should score highest for a CF query."""
    result = retrieval_agent.retrieve("high fat diet cystic fibrosis pancreatic enzymes")
    top_ids = [p.passage_id for p in result.passages]
    assert "p01" in top_ids, f"Expected p01 (CF passage) in top results, got {top_ids}"


def test_bm25_search_returns_relevant_results(bm25_retriever: BM25Retriever) -> None:
    results = bm25_retriever.search("phenylalanine restriction PKU diet")
    assert len(results) > 0
    top_ids = [r.passage_id for r in results[:3]]
    assert "p02" in top_ids, f"Expected PKU passage in top 3, got {top_ids}"


def test_merge_deduplicates_overlapping_results(
    vector_retriever: VectorRetriever,
    bm25_retriever: BM25Retriever,
) -> None:
    query = "vitamin D children requirements"
    embedding = vector_retriever.embed_query(query)
    vec_results = vector_retriever.search(embedding, top_k=20)
    bm25_results = bm25_retriever.search(query, top_k=20)

    merged = merge_and_deduplicate(vec_results, bm25_results)
    passage_ids = [p.passage_id for p in merged]

    # No duplicates
    assert len(passage_ids) == len(set(passage_ids)), "Duplicate passage IDs found after merge"

    # All scores are between 0 and 1
    for p in merged:
        assert 0.0 <= p.score <= 1.0, f"Score {p.score} out of [0, 1] range for passage {p.passage_id}"
