"""
build_cloud_index.py — run ONCE locally to populate Qdrant Cloud.

What it does:
  1. Reads QDRANT_URL + QDRANT_API_KEY from environment (or .env file)
  2. Ingests all PDFs in app/common/data/ into Qdrant Cloud
  3. Serializes the BM25 corpus to bm25_corpus.pkl (commit this file)

Run from the project root with rag_env activated:

    cp .env.example .env          # fill in QDRANT_URL and QDRANT_API_KEY
    rag_env\\Scripts\\python.exe scripts/build_cloud_index.py

You only need to re-run this when you add new PDFs or change the ingestion pipeline.
The bm25_corpus.pkl produced here must be committed to git so Vercel can access it.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap — ensure project root is on sys.path and .env is loaded
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("build_cloud_index")

# ---------------------------------------------------------------------------
# Validate environment
# ---------------------------------------------------------------------------

QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
DATA_DIR = PROJECT_ROOT / "app" / "common" / "data"
BM25_OUTPUT = PROJECT_ROOT / "bm25_corpus.pkl"

if not QDRANT_URL:
    logger.error("QDRANT_URL is not set. Add it to your .env file.")
    logger.error("  QDRANT_URL=https://<cluster-id>.us-east4-0.gcp.cloud.qdrant.io")
    logger.error("  QDRANT_API_KEY=<your-api-key>")
    sys.exit(1)

if not DATA_DIR.is_dir():
    logger.error("Data directory not found: %s", DATA_DIR)
    sys.exit(1)

logger.info("Qdrant Cloud URL : %s", QDRANT_URL)
logger.info("Data directory   : %s", DATA_DIR)
logger.info("BM25 output      : %s", BM25_OUTPUT)

# ---------------------------------------------------------------------------
# Build index
# ---------------------------------------------------------------------------

from qdrant_client import QdrantClient

from app.retrieval.bm25_retrieval import BM25Retriever
from app.retrieval.ingestion_pipeline import IngestionPipeline
from app.retrieval.vector_retrieval import VectorRetriever

logger.info("Connecting to Qdrant Cloud...")
cloud_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# Pass the cloud client directly so VectorRetriever doesn't create in-memory
vector_retriever = VectorRetriever(qdrant_client=cloud_client)
bm25_retriever = BM25Retriever()

pdf_paths = sorted([
    str(p) for p in DATA_DIR.iterdir()
    if p.suffix.lower() == ".pdf" and p.is_file()
])

if not pdf_paths:
    logger.error("No PDF files found in %s", DATA_DIR)
    sys.exit(1)

logger.info("Found %d PDF files", len(pdf_paths))
for p in pdf_paths:
    logger.info("  %s", Path(p).name)

logger.info("")
logger.info("Starting ingestion — this will take several minutes...")

pipeline = IngestionPipeline(vector_retriever, bm25_retriever)
summary = pipeline.run(pdf_paths)

logger.info("")
logger.info("Ingestion complete")
logger.info("  Passages indexed : %d", summary.total_passages)
logger.info("  Skipped          : %d  %s", len(summary.skipped_paths),
            [Path(p).name for p in summary.skipped_paths])
if summary.errors:
    logger.warning("  Errors           : %d", len(summary.errors))
    for path, err in summary.errors.items():
        logger.warning("    %s : %s", Path(path).name, err)

# ---------------------------------------------------------------------------
# Save BM25 corpus
# ---------------------------------------------------------------------------

if summary.total_passages > 0:
    bm25_retriever.save(str(BM25_OUTPUT))
    logger.info("")
    logger.info("BM25 corpus saved to %s", BM25_OUTPUT)
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. git add bm25_corpus.pkl")
    logger.info("  2. git commit -m 'add pre-built BM25 corpus'")
    logger.info("  3. Set QDRANT_URL and QDRANT_API_KEY in Vercel environment variables")
    logger.info("  4. git push  →  Vercel redeploys and connects to cloud index")
else:
    logger.error("No passages were indexed — check errors above. bm25_corpus.pkl not written.")
    sys.exit(1)
