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
    vector_retriever = VectorRetriever()   # auto-detects cloud vs in-memory; model loaded lazily
    bm25_retriever = BM25Retriever()

    if (os.environ.get("QDRANT_URL") or "").strip().lstrip("﻿"):
        # Cloud mode — vector index already populated by build_cloud_index.py.
        # Load the pre-serialized BM25 corpus if it exists next to this file.
        bm25_path = _DATA_DIR.parent.parent.parent / "bm25_corpus.pkl"
        if bm25_path.exists():
            # Guard against Git LFS pointer files being deployed instead of the
            # actual binary (Vercel does not pull LFS objects by default).
            raw = bm25_path.read_bytes()
            if raw[:4] == b"vers" and b"git-lfs" in raw[:200]:
                logger.warning(
                    "startup_ingestion: bm25_corpus.pkl is a Git LFS pointer, not the real "
                    "binary — BM25 search will be empty. Enable LFS on Vercel or upload the "
                    "corpus to external storage."
                )
            else:
                try:
                    bm25_retriever.load(str(bm25_path))
                    logger.info("startup_ingestion: loaded BM25 corpus from %s", bm25_path)
                except Exception as exc:
                    logger.warning(
                        "startup_ingestion: failed to load BM25 corpus (%s) — BM25 will be empty",
                        exc,
                    )
        else:
            logger.info(
                "startup_ingestion: bm25_corpus.pkl not found — rebuilding from Qdrant "
                "(cold-start cost, kept in-memory only to preserve /tmp space)."
            )
            _rebuild_bm25_from_qdrant(bm25_retriever, vector_retriever, save_to=None)
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


def _rebuild_bm25_from_qdrant(bm25_retriever, vector_retriever, save_to=None) -> None:
    """
    Scroll all passages from Qdrant and build an in-memory BM25 index.
    Called only when bm25_corpus.pkl is absent (e.g. first deploy on Vercel).
    Typically takes 20-60 seconds for ~37k passages — happens once per cold start.
    """
    from app.retrieval import EnrichedPassage

    try:
        client = vector_retriever._client
        collection = "cpna_passages"

        # Check the collection exists and has points
        info = client.get_collection(collection)
        total = info.points_count or 0
        if total == 0:
            logger.warning("_rebuild_bm25_from_qdrant: collection '%s' is empty", collection)
            return

        logger.info(
            "_rebuild_bm25_from_qdrant: scrolling %d points from Qdrant to rebuild BM25",
            total,
        )

        passages = []
        offset = None
        batch_size = 500
        while True:
            points, next_offset = client.scroll(
                collection_name=collection,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                p = point.payload or {}
                text = p.get("text", "")
                if text:
                    passages.append(EnrichedPassage(
                        passage_id=p.get("passage_id", str(point.id)),
                        text=text,
                        source_title=p.get("source_title", ""),
                        source_type=p.get("source_type", ""),
                    ))
            if next_offset is None:
                break
            offset = next_offset

        logger.info(
            "_rebuild_bm25_from_qdrant: fetched %d passages, building BM25 index",
            len(passages),
        )
        bm25_retriever.add_corpus(passages)
        logger.info("_rebuild_bm25_from_qdrant: BM25 index ready (%d passages)", len(passages))

        if save_to is not None:
            try:
                bm25_retriever.save(str(save_to))
                logger.info("_rebuild_bm25_from_qdrant: corpus cached to %s", save_to)
            except Exception as save_exc:
                logger.warning("_rebuild_bm25_from_qdrant: could not cache to %s: %s", save_to, save_exc)

    except Exception as exc:
        logger.warning(
            "_rebuild_bm25_from_qdrant: failed (%s) — BM25 will be empty",
            str(exc).encode("ascii", "replace").decode("ascii"),
        )


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
