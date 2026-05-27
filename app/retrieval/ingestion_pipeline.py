"""
IngestionPipeline — orchestrates the full document → index pipeline.

Pipeline order (mandatory per CLAUDE.md):
  pdf_loader → chapter_extractor → metadata_enricher → EnrichedPassage adapter
  → VectorRetriever.index + BM25Retriever.add_corpus

Notes on existing modules:
- app/common/pdf_loader.py is a stub (empty). Loading is handled inside
  chapter_extractor via PyPDFLoader. We call extract_chapters_from_pdf() directly.
- chapter_extractor returns List[Document] (LangChain), one per chapter/section.
- metadata_enricher.enrich_documents() adds condition_tags, therapy_area,
  document_type to each Document's .metadata dict.
- doc_type must be inferred from the file path since the pipeline receives raw paths.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import TYPE_CHECKING, List, Optional

from app.common.chapter_extractor import extract_chapters_from_pdf
from app.common.metadata_enricher import enrich_documents
from app.retrieval import EnrichedPassage, IngestionSummary
from app.retrieval.semantic_chunker import chunk_all_chapters
from app.config.routing_config import get_condition_tags_for_chunk

if TYPE_CHECKING:
    from app.retrieval.bm25_retrieval import BM25Retriever
    from app.retrieval.vector_retrieval import VectorRetriever

logger = logging.getLogger(__name__)

# Map filename fragments → doc_type recognised by chapter_extractor
_FILENAME_DOC_TYPE_MAP = {
    "vanessa shaw": "shaw_2020",
    "clinical paediatric dietetics": "shaw_2020",
    "dietary reference intakes": "dri",
    "dri": "dri",
    "oxford handbook": "oxford_handbook",
    "clinical nutrition": "clinical_nutrition_2013",
    "vitamins and mineral": "vitamin_mineral_requirements",
    "preterm": "preterm_2013",
    "drug-nutrient": "drug_nutrient",
    "handbook of drug": "drug_nutrient",
    "integrative human biochemistry": "biochemistry",
    "west africa": "west_africa_fct_2019",
    "food composition table for west africa": "west_africa_fct_2019",
    "kenya food composition": "kenya_fct_2018",
    "kenya fct": "kenya_fct_2018",
    "tanzania food composition": "tanzania_fct_2008",
    "tanzania_food composition": "tanzania_fct_2008",
    "tanzania fct": "tanzania_fct_2008",
    "malawi food composition": "malawi_fct_2019",
    "malawian food composition": "malawi_fct_2019",
    "malawi fct": "malawi_fct_2019",
    "mozambique food composition": "mozambique_fct_2009",
    "mozambique fct": "mozambique_fct_2009",
    "congo basin": "congo_basin_fct_2012",
    "uganda food composition": "uganda_fct_2012",
    "uganda fct": "uganda_fct_2012",
}


def _infer_doc_type(path: str) -> Optional[str]:
    name = os.path.basename(path).lower()
    for fragment, doc_type in _FILENAME_DOC_TYPE_MAP.items():
        if fragment in name:
            return doc_type
    return None


def _passage_id(source_id: str, chapter_key: str) -> str:
    raw = f"{source_id}::{chapter_key}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _doc_to_enriched_passage(doc) -> EnrichedPassage:
    """Adapt a LangChain Document (post-enrichment) to EnrichedPassage."""
    meta = doc.metadata
    source_id = meta.get("source", "unknown")
    chapter_num = str(meta.get("chapter_num", meta.get("section_num", "0")))
    chunk_index = str(meta.get("chunk_index", ""))
    chunk_key = f"{chapter_num}__c{chunk_index}" if chunk_index else chapter_num
    pid = _passage_id(source_id, chunk_key)

    return EnrichedPassage(
        passage_id=pid,
        text=doc.page_content,
        source_title=meta.get("source", "Unknown Source"),
        source_type=meta.get("document_type", "other"),
        condition_tags=meta.get("condition_tags", []),
        embedding=None,
    )


class IngestionPipeline:
    """
    Runs the full ingestion pipeline for a list of PDF paths.

    Usage:
        pipeline = IngestionPipeline(vector_retriever, bm25_retriever)
        summary = pipeline.run(["path/to/shaw_2020.pdf", ...])
    """

    def __init__(
        self,
        vector_retriever: "VectorRetriever",
        bm25_retriever: "BM25Retriever",
    ) -> None:
        self._vector = vector_retriever
        self._bm25 = bm25_retriever

    def run(self, pdf_paths: List[str]) -> IngestionSummary:
        all_passages: List[EnrichedPassage] = []
        skipped: List[str] = []
        errors: dict = {}

        for path in pdf_paths:
            doc_type = _infer_doc_type(path)
            if doc_type is None:
                logger.warning("Cannot infer doc_type for '%s' — skipping", path)
                skipped.append(path)
                continue

            if not os.path.exists(path):
                logger.error("File not found: %s", path)
                errors[path] = "file_not_found"
                continue

            try:
                # Step 1 + 2: load PDF and extract chapters
                docs = extract_chapters_from_pdf(path, doc_type)
                if not docs:
                    logger.warning("No chapters extracted from %s", path)
                    skipped.append(path)
                    continue

                # Step 2b: semantic chunking (sub-chunk chapter-level docs)
                chunk_docs = chunk_all_chapters(docs)
                if not chunk_docs:
                    logger.warning("No chunks produced from %s", path)
                    skipped.append(path)
                    continue

                # Step 3: enrich metadata (input is now chunk-level docs)
                enriched_docs = enrich_documents(chunk_docs, doc_type)

                # Step 4: adapt to EnrichedPassage
                passages = [_doc_to_enriched_passage(d) for d in enriched_docs]

                # Step 4b: merge routing-config condition tags into each passage
                # Walk enriched_docs in parallel to access original source/chapter metadata
                final_passages = []
                for passage, doc in zip(passages, enriched_docs):
                    meta = doc.metadata
                    src_id = meta.get("source", "")
                    chapter_key = meta.get("chapter_num")
                    routing_tags = get_condition_tags_for_chunk(src_id, chapter_key)
                    existing = list(passage.condition_tags or [])
                    merged_tags = list(set(existing + routing_tags))
                    if merged_tags != existing:
                        passage = passage.model_copy(update={"condition_tags": merged_tags})
                    final_passages.append(passage)
                passages = final_passages
                all_passages.extend(passages)
                logger.info("Ingested %d passages from %s", len(passages), os.path.basename(path))

            except Exception as exc:
                logger.error("Error ingesting %s: %s", path, exc, exc_info=True)
                errors[path] = str(exc)

        # Step 5: push to indexes
        if all_passages:
            self._vector.index(all_passages)
            self._bm25.add_corpus(all_passages)

        return IngestionSummary(
            total_passages=len(all_passages),
            indexed_in_vector_store=len(all_passages),
            indexed_in_bm25=len(all_passages),
            skipped_paths=skipped,
            errors=errors,
        )
