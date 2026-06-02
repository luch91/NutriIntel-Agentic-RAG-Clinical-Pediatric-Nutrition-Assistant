# NutriIntel — Agentic RAG Clinical Pediatric Nutrition Assistant

An agentic RAG system that answers clinical pediatric nutrition queries using deterministic therapy planning, hybrid retrieval across medical textbooks and food composition tables, and structured conversation state management.

**Frontend:** [nutriintel-frontend.vercel.app](https://nutriintel-frontend.vercel.app) · **API:** [nutriintel-api.vercel.app](https://nutriintel-api.vercel.app/api/health) · **Eval:** [cpna-eval-one.vercel.app](https://cpna-eval-one.vercel.app)

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
Intent Classifier (ONNX all-MiniLM-L6-v2 + LogisticRegression, 98.6% F1)
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
                                  ├── Qdrant Cloud (all-MiniLM-L6-v2, 384 dims)
                                  └── BM25 (rank-bm25, pre-serialised corpus)
                                       │
                                       └── Synthesised prose via Groq (llama-3.1-8b-instant)
```

**Key design properties:**
- Intent classifier uses **ONNX-exported** `all-MiniLM-L6-v2` — no `torch` or `sentence-transformers` at runtime, compatible with Vercel's 250 MB Lambda limit
- Phase-aware conversation state (`IDLE → SLOT_FILLING → DISPATCHING → RESPONDING`) prevents bare slot values ("10 year old", "30kg") from being misclassified as new queries
- Source filter uses `source_title` matching — not `passage_id` — because passage IDs are MD5 hashes
- On Vercel, startup ingestion is **lazy per-request** (FastAPI `lifespan` does not fire on serverless); Qdrant Cloud is pre-populated and BM25 corpus is pre-serialised
- Response prose is synthesised by Groq after retrieval; all numeric targets come from the deterministic engine
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
| Vector store | **Qdrant Cloud** (production) / in-memory (local dev) |
| Embeddings | `all-MiniLM-L6-v2` via **ONNX Runtime** (no torch required) |
| BM25 | `rank-bm25`, pre-serialised corpus (`bm25_corpus.pkl`) |
| Intent classifier | ONNX all-MiniLM-L6-v2 + scikit-learn LogisticRegression |
| LLM synthesis | **Groq** `llama-3.1-8b-instant` (prose fields only; numeric values never LLM-generated) |
| PDF extraction | LangChain PyPDFLoader + PyMuPDF/Tesseract OCR fallback |
| State | Redis (in-memory fallback when unavailable) |
| Observability | structlog (JSON), Prometheus metrics |
| Deployment | Vercel — backend (`nutriintel-api`) + frontend (`nutriintel-frontend`), separate projects |
| Eval platform | CPNA Eval (`cpna-eval-one.vercel.app`) — 10 E2E scenarios, 96%+ overall score |

---

## Project Structure

```
app/
├── agents/           # RetrievalAgent, SlotFillingAgent, QueryRewriteAgent, ResponseSynthesiser
├── api/              # FastAPI router, schemas, eval endpoint (/api/eval)
├── classification/   # Intent classifier wrapper + MockIntentClassifier fallback
├── common/           # PDF loader, chapter extractor, metadata enricher, nutrient calculator
├── config/           # Condition routing config (source-to-condition mappings)
├── contracts/        # Response contracts, display adapter
├── engine/           # DeterministicNutrientEngine, DRI lookup, condition adjustments
├── models/           # Trained intent classifier artifacts (98.6% F1)
│   └── intent_classifier/
│       ├── embedding_model.onnx   # ONNX export of all-MiniLM-L6-v2 (87 MB, Git LFS)
│       ├── classifier.pkl         # LogisticRegression weights (Git LFS)
│       └── label_encoder.pkl      # Label encoder (Git LFS)
├── observability/    # Structured logger, Prometheus metrics
├── retrieval/        # VectorRetriever, BM25Retriever, IngestionPipeline, startup ingestion
├── state/            # ConversationState, StateManager
├── tests/            # Unit + integration + e2e tests
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

The backend runs at `http://localhost:8000`. On first request in local mode (no `QDRANT_URL` set), startup ingestion indexes all PDFs in `app/common/data/` — this takes ~2–3 minutes.

**Environment variables (for cloud mode):**

| Variable | Purpose |
|---|---|
| `QDRANT_URL` | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Qdrant Cloud API key |
| `GROQ_API_KEY` | Groq API key for prose synthesis |

All three must be set in Vercel dashboard without a UTF-8 BOM — the code strips BOM (`﻿`) defensively.

---

## Tests

```bash
# Unit tests
pytest app/tests/unit/

# Integration tests
pytest app/tests/integration/

# E2E (uses MockIntentClassifier + stub retrieval, no real Qdrant needed)
pytest app/tests/e2e/ --timeout=30
```

---

## API

```
POST /api/chat
  Body: { "session_id": "...", "message": "..." }
  Returns: ChatResponse (intent, response, slot_prompt if filling)

POST /api/eval
  Body: { "userMessage": "...", "conversationHistory": [...], "sessionState": {...} }
  Headers: X-Eval-Secret: <EVAL_SECRET>
  Returns: Full eval contract response (intent, gatekeeper, evidence, retrieval log)

POST /api/session/reset
  Body: { "session_id": "..." }

GET  /api/health
GET  /metrics        (Prometheus)
```

---

## Retrieval Pipeline

```
Query → LLM rewrite → vector search (top 20, Qdrant Cloud)
                     → BM25 search (top 20, pre-serialised corpus)
      → merge + deduplicate → condition-aware source filter
      → priority source boosting → rerank → top 7 passages
      → Groq synthesis → prose fields in response
```

Source filtering uses `source_title` matching with case/separator normalisation so that routing keys like `"Shaw2020"` correctly match passages stored with titles like `"Clinical Paediatric Dietetics, 5th ed."`.

---

## Conversation State

Four buckets: `session_memory`, `active_task_context`, `turn_entities`, `inherited_context`.

Four phases: `IDLE → SLOT_FILLING → DISPATCHING → RESPONDING`

During `SLOT_FILLING`, the intent classifier is bypassed — bare values like `"30kg"` are treated as slot answers, not new queries. On `DISPATCHING`, therapy workflow is forced regardless of the next classified intent.

---

## Eval Platform

The CPNA Eval platform ([cpna-eval-one.vercel.app](https://cpna-eval-one.vercel.app)) runs 10 E2E scenarios against the live API via `/api/eval`, scoring across six dimensions:

| Dimension | Score |
|---|---|
| Intent Accuracy | 100% |
| Gatekeeper Pass Rate | 93% |
| Contract Conformance | 93% |
| Context Safety | 98% |
| Retrieval Quality | 93% |
| **Overall** | **96%** |

---

## License

MIT
