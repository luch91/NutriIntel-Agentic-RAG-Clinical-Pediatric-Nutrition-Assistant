"""
startup_ingestion.py — runs ingestion once at app startup.

Builds VectorRetriever + BM25Retriever + RetrievalAgent singletons and
ingests the known PDF knowledge base into them. Returns the ready
RetrievalAgent for injection into WorkflowRouter.

All PDFs live in app/common/data/. Only files recognised by
_FILENAME_DOC_TYPE_MAP in ingestion_pipeline.py are ingested — unrecognised
files are skipped automatically by the pipeline.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Resolved once — relative to this file's location (app/retrieval/)
_DATA_DIR = Path(__file__).resolve().parent.parent / "common" / "data"

# Singleton holders — module-level so they survive across lazy getter calls
_retrieval_agent: Optional[object] = None


def get_retrieval_agent():
    """Return the singleton RetrievalAgent, building it if needed."""
    global _retrieval_agent
    if _retrieval_agent is None:
        _retrieval_agent = _build_and_ingest()
    return _retrieval_agent


def _build_and_ingest():
    """
    Heavy path — called once at startup.
    Imports are deferred here so the module is safe to import without ML deps.

    Cloud mode  (QDRANT_URL set): connects to pre-built Qdrant Cloud index and
                loads pre-serialized BM25 corpus — no PDF ingestion needed.
    Local mode  (no QDRANT_URL) : ingests PDFs into in-memory Qdrant + BM25.
    """
    import os

    from app.agents.retrieval_agent import RetrievalAgent
    from app.retrieval.bm25_retrieval import BM25Retriever
    from app.retrieval.vector_retrieval import VectorRetriever

    logger.info("startup_ingestion: initialising retrieval components")
    vector_retriever = VectorRetriever()   # auto-detects cloud vs in-memory
    bm25_retriever = BM25Retriever()

    if os.environ.get("QDRANT_URL"):
        # Cloud mode — vector index already populated by build_cloud_index.py.
        # Load the pre-serialized BM25 corpus if it exists next to this file.
        bm25_path = _DATA_DIR.parent.parent / "bm25_corpus.pkl"
        if bm25_path.exists():
            bm25_retriever.load(str(bm25_path))
            logger.info("startup_ingestion: loaded BM25 corpus from %s", bm25_path)
        else:
            logger.warning(
                "startup_ingestion: QDRANT_URL set but no bm25_corpus.pkl found at %s "
                "— BM25 search will be empty. Run scripts/build_cloud_index.py first.",
                bm25_path,
            )
    else:
        # Local mode — ingest PDFs on the fly.
        from app.retrieval.ingestion_pipeline import IngestionPipeline

        pdf_paths = _collect_pdf_paths()
        if not pdf_paths:
            logger.warning(
                "startup_ingestion: no PDFs found in %s — retrieval will be empty", _DATA_DIR
            )
        else:
            logger.info(
                "startup_ingestion: ingesting %d PDFs from %s", len(pdf_paths), _DATA_DIR
            )
            pipeline = IngestionPipeline(vector_retriever, bm25_retriever)
            summary = pipeline.run(pdf_paths)
            logger.info(
                "startup_ingestion: complete — passages=%d, skipped=%d, errors=%d",
                summary.total_passages,
                len(summary.skipped_paths),
                len(summary.errors),
            )
            if summary.errors:
                for path, err in summary.errors.items():
                    logger.error("startup_ingestion: error ingesting %s: %s", path, err)

    agent = RetrievalAgent(vector_retriever=vector_retriever, bm25_retriever=bm25_retriever)
    logger.info("startup_ingestion: RetrievalAgent ready")
    return agent


def _collect_pdf_paths() -> list[str]:
    """Return all .pdf / .PDF files found in _DATA_DIR."""
    if not _DATA_DIR.is_dir():
        logger.warning("startup_ingestion: data dir not found: %s", _DATA_DIR)
        return []
    paths = [
        str(p)
        for p in _DATA_DIR.iterdir()
        if p.suffix.lower() == ".pdf" and p.is_file()
    ]
    paths.sort()
    return paths
