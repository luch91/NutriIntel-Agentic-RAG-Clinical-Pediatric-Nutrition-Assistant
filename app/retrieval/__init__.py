"""
Shared data-transfer types for the retrieval layer.
All retrieval modules import EnrichedPassage and RetrievedPassage from here.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class EnrichedPassage(BaseModel):
    """
    A document chunk after the full ingestion pipeline:
    pdf_loader → chapter_extractor → metadata_enricher → adapter.
    """
    passage_id: str
    text: str
    source_title: str
    source_type: str          # value produced by metadata_enricher (document_type field)
    condition_tags: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None   # populated by VectorRetriever.index


class RetrievedPassage(BaseModel):
    """A passage returned from vector or BM25 search, with a relevance score."""
    passage_id: str
    text: str
    source_title: str
    source_type: str
    score: float


class IngestionSummary(BaseModel):
    """Summary returned by IngestionPipeline.run()."""
    total_passages: int
    indexed_in_vector_store: int
    indexed_in_bm25: int
    skipped_paths: List[str] = Field(default_factory=list)
    errors: Dict[str, str] = Field(default_factory=dict)
