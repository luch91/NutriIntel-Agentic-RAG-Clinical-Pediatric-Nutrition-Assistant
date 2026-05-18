# NutriIntel — Agentic RAG Clinical Pediatric Nutrition Assistant

An agentic RAG system that answers clinical pediatric nutrition queries using deterministic therapy planning, hybrid retrieval across medical textbooks and food composition tables, and structured conversation state management.

**Live:** [frontend-kappa-umber-23.vercel.app](https://frontend-kappa-umber-23.vercel.app) · API: [nutriintel-api.vercel.app](https://nutriintel-api.vercel.app/api/health)

---

## What It Does

NutriIntel handles four query types:

| Intent | Example |
|---|---|
| **Therapy** | "Create a nutrition plan for a 10-year-old girl with cystic fibrosis, 28kg, 132cm" |
| **Recommendation** | "What foods are high in iron for a toddler?" |
| **Comparison** | "Compare bambara nut vs groundnut for zinc content" |
| **General** | "What is the ketogenic diet?" |

For **therapy queries**, the system collects required clinical slots (age, sex, weight, height, diagnosis, medications, biomarkers, country) through a structured conversation before computing a deterministic nutrition plan — no LLM-generated targets. Nutrient targets trace to DRI tables and evidence-based clinical protocols.

---

## Architecture

```
User message
    │
    ▼
Intent Classifier (sentence-transformers + LogisticRegression, 98.6% F1)
    │
    ├── THERAPY ──► Slot-filling agent → Therapy gatekeeper → Deterministic engine
    │                                                              ├── DRI lookup
    │                                                              ├── Condition adjustments
    │                                                              ├── Drug-nutrient interactions
    │                                                              └── Food source mapper
    │
    ├── RECOMMENDATION ──► Recommendation workflow
    ├── COMPARISON ──► Comparison workflow (entity extraction + dual retrieval)
    └── GENERAL ──► General workflow
         │
         └── All workflows → Hybrid retrieval (vector + BM25 → rerank → top 7)
                                  ├── Qdrant (sentence-transformers/all-MiniLM-L6-v2)
                                  └── BM25 (rank-bm25)
```

**Key design properties:**
- Phase-aware conversation state (`IDLE → SLOT_FILLING → DISPATCHING → RESPONDING`) prevents bare slot values ("10 year old", "30kg") from being misclassified as new queries
- Source filter uses `source_title` matching — not `passage_id` — because passage IDs are MD5 hashes
- Startup ingestion runs once at FastAPI lifespan, indexing all 34 knowledge PDFs before the first request
- OCR fallback (PyMuPDF + Tesseract) for scanned PDFs where `PyPDFLoader` returns empty pages

---

## Knowledge Base

**Clinical textbooks (9 sources):**
- Clinical Paediatric Dietetics, 5th ed. (Shaw 2020)
- Dietary Reference Intakes: Essential Guide to Nutrient Requirements
- Oxford Handbook of Nutrition and Dietetics (2012)
- Clinical Nutrition: The Nutrition Society Textbook Series (2013)
- Vitamins and Mineral Requirements in Human Nutrition (WHO/FAO)
- Nutrition for the Preterm Neonate: A Clinical Perspective (2013)
- Handbook of Drug-Nutrient Interactions, 3rd ed. (2024)
- Integrative Human Biochemistry (2022)

**Food composition tables (African-focused):**
- West Africa FCT 2019 (Ghana, Senegal, Mali, Burkina Faso, Nigeria, Côte d'Ivoire)
- East and Central Uganda FCT
- Tanzania, Kenya, Gambia, Lesotho, Mozambique, Zimbabwe FCTs
- Congo Basin FCT + others

---

## Supported Therapy Conditions (v1)

Type 1 diabetes · Cystic fibrosis · Food allergy · Preterm nutrition · Chronic kidney disease · PKU · MSUD · Galactosemia · Epilepsy/ketogenic therapy · IBD · GERD

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Frontend | Next.js 14 (App Router), TypeScript |
| Vector store | Qdrant (in-memory) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (384 dims) |
| BM25 | `rank-bm25` |
| Intent classifier | sentence-transformers + scikit-learn LogisticRegression |
| PDF extraction | LangChain PyPDFLoader + PyMuPDF/Tesseract OCR fallback |
| State | Redis (in-memory fallback when unavailable) |
| Observability | structlog (JSON), Prometheus metrics |
| Deployment | Vercel (backend + frontend, separate projects) |

---

## Project Structure

```
app/
├── agents/           # RetrievalAgent, SlotFillingAgent, QueryRewriteAgent
├── api/              # FastAPI router, schemas, eval endpoint
├── classification/   # Intent classifier wrapper
├── common/           # PDF loader, chapter extractor, metadata enricher, nutrient calculator
├── config/           # Condition routing config (source-to-condition mappings)
├── contracts/        # Response contracts, display adapter
├── engine/           # DeterministicNutrientEngine, DRI lookup, condition adjustments
├── models/           # Trained intent classifier artifacts (98.6% F1)
├── observability/    # Structured logger, Prometheus metrics
├── retrieval/        # VectorRetriever, BM25Retriever, IngestionPipeline, startup ingestion
├── state/            # ConversationState, StateManager
├── tests/            # 217 unit + integration + e2e tests
└── workflows/        # TherapyWorkflow, RecommendationWorkflow, ComparisonWorkflow, GeneralWorkflow

frontend/
└── src/app/
    ├── page.tsx      # Landing page
    └── chat/         # Chat interface
```

---

## Running Locally

**Prerequisites:** Python 3.11+, Node.js 18+

```bash
# Backend
python -m venv rag_env
rag_env\Scripts\activate          # Windows
# source rag_env/bin/activate     # macOS/Linux

pip install -r api/requirements.txt
uvicorn app.api.router:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

The backend runs at `http://localhost:8000`. On first request, startup ingestion indexes all PDFs in `app/common/data/` — this takes ~2–3 minutes on first run.

---

## Tests

```bash
# All unit tests
pytest app/tests/unit/

# Integration tests (requires sentence-transformers)
pytest app/tests/integration/

# E2E
pytest app/tests/e2e/
```

217 tests, all passing.

---

## API

```
POST /api/chat
  Body: { "session_id": "...", "message": "..." }
  Returns: ChatResponse (intent, response, slot_prompt if filling)

POST /api/session/reset
  Body: { "session_id": "..." }

GET  /api/health
GET  /metrics        (Prometheus)
```

---

## Retrieval Pipeline

```
Query → LLM rewrite → vector search (top 20) → BM25 search (top 20)
      → merge + deduplicate → condition-aware source filter
      → priority source boosting → rerank → top 7 passages
```

Source filtering uses `source_title` matching with case/separator normalisation so that routing keys like `"Shaw2020"` correctly match passages stored with titles like `"Clinical Paediatric Dietetics, 5th ed."`.

---

## Conversation State

Four buckets: `session_memory`, `active_task_context`, `turn_entities`, `inherited_context`.

Four phases: `IDLE → SLOT_FILLING → DISPATCHING → RESPONDING`

During `SLOT_FILLING`, the intent classifier is bypassed — bare values like `"30kg"` are treated as slot answers, not new queries. On `DISPATCHING`, therapy workflow is forced regardless of the next classified intent.

---

## License

MIT
