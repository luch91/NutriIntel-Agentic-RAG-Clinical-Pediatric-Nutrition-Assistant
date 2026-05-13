# KNOWN_GAPS.md — CPNA v1 Handoff Audit

Generated: 2026-05-13

---

## Existing Module Integration Status

### app/common/nutrient_calculator.py
**Used:** `optimize_diet()`, `greedy_allocation()`, `meal_planner()`, `convert_fct_rows_to_foods()` are all called indirectly through `DeterministicNutrientEngine.compute_therapy_plan()`. The engine translates `ConfirmedEntities` into the targets dict that `nutrient_calculator` expects, runs `greedy_allocation()` for per-nutrient food sourcing, and calls `meal_planner()` to generate a `MealPlanDisplay`.

**Not used:** The `pulp`-based linear program (`optimize_diet()` with full LP) is present in the file but the engine defaults to the greedy path because `pulp` is an optional dependency not guaranteed present in `rag_env`. The LP path would improve optimality on complex multi-constraint plans but requires `pip install pulp` and a solver.

### app/common/chapter_extractor.py
**Integration point:** `IngestionPipeline.ingest_pdf()` calls `extract_chapters_from_pdf(file_path, doc_type)` directly (line ~24 of `app/retrieval/ingestion_pipeline.py`). It returns `List[Document]` (LangChain Document objects), one per chapter/section. These are passed to `metadata_enricher.enrich_documents()` and then to `SemanticChunker.chunk_all_chapters()`.

**Note:** `app/common/pdf_loader.py` is an empty stub — actual PDF loading is handled internally by `chapter_extractor` via `PyPDFLoader`. The pipeline calls `extract_chapters_from_pdf()` directly and never touches `pdf_loader.py`.

### app/common/metadata_enricher.py
**Fields produced** and their mapping to `EnrichedPassage`:
- `condition_tags` → `EnrichedPassage.condition_tags` (List[str], used for post-retrieval source filtering)
- `document_type` → `EnrichedPassage.source_type` (string key matching routing config source IDs)
- `therapy_area` → stored in passage metadata; not currently surfaced in `EnrichedPassage` or display contracts
- `age_relevance` → stored in passage metadata; not currently surfaced
- `drug_classes` → stored in passage metadata; not currently surfaced

`get_citation_metadata(doc)` and `get_document_priority_for_intent(intent)` are available but not called in the current pipeline — priority is handled by `routing_config.get_priority_source()` instead.

### app/models/intent_classifier/
**Real model (IntentClassifier):** Sentence-transformer (all-MiniLM-L6-v2) + LogisticRegression. Artifacts at `app/models/intent_classifier/`: `classifier.pkl`, `label_encoder.pkl`, `label_mapping.json`, `embedding_model/`. Trained F1: 98.6% on 4 labels. Located in `app/training/intent_classifier.py`.

**MockIntentClassifier:** Keyword-based, zero model loading, used for all tests (unit, integration, E2E). Located at `app/classification/intent_classifier.py`. The mock covers all 4 intent labels and `needs_clarification=True` for ambiguous queries.

**Which tests use which:**
- All unit tests (`app/tests/unit/`) → `MockIntentClassifier`
- All integration tests (`app/tests/integration/`) → `MockIntentClassifier`
- All E2E tests (`app/tests/e2e/`) → `MockIntentClassifier` (injected via `app.state.intent_classifier`)
- 3 tests in `app/tests/unit/test_intent_classifier.py` → real `IntentClassifier`, **skipped** if `classifier.pkl` is absent (which it is in the current dev environment — model artifacts not committed to repo)

---

## Stubs and Incomplete Implementations

| File | Status | Notes |
|------|--------|-------|
| `app/agents/intent_agent.py` | Empty stub (1 line) | Superseded by `MockIntentClassifier` + direct `IntentClassifier` calls; not wired into any workflow |
| `app/agents/comparison_router_agent.py` | Empty stub (1 line) | Routing logic lives in `WorkflowRouter` + `ComparisonWorkflow` directly |
| `app/agents/response_synthesis_agent.py` | Empty stub (1 line) | LLM synthesis layer not implemented; `DisplayAdapter` does deterministic assembly instead |
| `app/agents/reranking_agent.py` | Empty stub (1 line) | Reranking logic lives in `app/retrieval/reranker.py` (`Reranker` class); this stub is unused |
| `app/agents/kg_retrieval_agent.py` | Empty stub (1 line) | Knowledge graph retrieval not implemented (see Knowledge Base Status below) |
| `app/knowledge_graph/kg_client.py` | Empty stub (1 line) | No Neo4j/graph DB connection; KG queries not reachable |
| `app/knowledge_graph/case_study_schema.py` | Empty stub (1 line) | Case study schema not defined |
| `app/common/pdf_loader.py` | Empty stub | Loading handled by `chapter_extractor` internals; this file is never imported at runtime |
| `app/contracts/display_adapter.py:_extract_foods_to_emphasize()` | Returns `[]` always | Intended to extract food recommendations from evidence excerpts; no NLP extraction implemented |
| `app/contracts/display_adapter.py:_adapt_comparison()` | Builds empty `rows=[]` / `points_a=[]` / `points_b=[]` | Comparison detail rows are not populated from evidence; only entity names and mode are set |
| `app/workflows/general_workflow.py` | Minimal | Returns evidence excerpts as-is; no answer synthesis or NLP summarization |
| `app/workflows/recommendation_workflow.py` | Minimal | DRI preview uses lookup table, not dynamic LLM; practical guidance is boilerplate text |

---

## Knowledge Base Status

| Component | Status | Notes |
|-----------|--------|-------|
| **Qdrant index** | Mock only (in-memory, empty) | `VectorRetriever` is initialized with `QdrantClient(":memory:")` in tests. No PDF sources have been ingested. Running `IngestionPipeline.ingest_pdf()` against real PDF paths would populate it, but no PDFs are present in the repo. |
| **BM25 corpus** | Mock only (empty) | `BM25Retriever` corpus is populated via `add_corpus()`. No documents loaded. Tests inject synthetic `EnrichedPassage` fixtures directly. |
| **PDF sources ingested** | None yet | The 9 supported `doc_type` sources (shaw_2020, dri, oxford_handbook, clinical_nutrition_2013, vitamin_mineral_requirements, preterm_2013, drug_nutrient, biochemistry, west_africa_fct_2019) require the corresponding PDFs. PDFs are not included in the repository. |
| **E2E test retrieval** | Synthetic fixture injection | `app/tests/fixtures/passages.py` provides 10 `EnrichedPassage` objects. Tests build a `VectorRetriever` + `BM25Retriever` pre-loaded with these fixtures via `add_corpus()` / direct index population. |

**To populate a real index:** Provide PDF files, set `KNOWLEDGE_BASE_DIR` env var to the folder containing them, and run `IngestionPipeline.ingest_all()`. The pipeline will route each file by filename/path match to the correct `doc_type`.

---

## Known Test Gaps

| Test | Status | Reason |
|------|--------|--------|
| `test_real_model_loads_and_classifies` | Skipped (`@pytest.mark.skipif`) | `app/models/intent_classifier/classifier.pkl` not present in current environment; model artifacts not committed to repo |
| `test_real_model_therapy_query` | Skipped (`@pytest.mark.skipif`) | Same reason |
| `test_real_model_general_query` | Skipped (`@pytest.mark.skipif`) | Same reason |
| Comparison detail rows | Not tested | `_adapt_comparison()` returns empty `rows`/`points_a`/`points_b` — no test asserts on populated comparison table content because the data is not synthesized from evidence |
| KG retrieval path | Not tested | `kg_retrieval_agent.py` is a stub; no integration tests for knowledge-graph-backed retrieval |
| Frontend component tests | Not present | No Jest/React Testing Library tests; only `npm run build` is verified |
| Prometheus counter values | Not tested | Metrics counters increment correctly but no unit tests assert on `cpna_requests_total._value.get()` etc. |

---

## Recommended Next Steps for v1.1

1. **Populate the knowledge base.** Provide the 9 PDF sources and run `IngestionPipeline.ingest_all()` to build a real Qdrant index + BM25 corpus. Validate retrieval quality against the E2E test queries.

2. **Wire the real IntentClassifier in production.** Replace `MockIntentClassifier` with `IntentClassifier` in `app/api/router.py`'s `_get_classifier()` factory (a one-line change). Ensure model artifacts are shipped with the container image.

3. **Implement response synthesis.** Replace the boilerplate strings in `DisplayAdapter._adapt_general()`, `_adapt_recommendation()`, and `_adapt_comparison()` with LLM-generated summaries using `response_synthesis_agent.py`. This is the highest-leverage quality improvement.

4. **Populate ComparisonResponse detail rows.** `_adapt_comparison()` currently returns empty `rows` / `points_a` / `points_b`. Use retrieved evidence passages to generate quantitative nutrient rows (for quantitative mode) and qualitative bullet points (for qualitative mode).

5. **Implement the knowledge graph layer.** Wire `kg_client.py` to a Neo4j instance and implement `kg_retrieval_agent.py` for condition → food → drug entity lookups. Integrate into the retrieval merge step.

6. **Add frontend component tests.** Add Jest + React Testing Library for `TherapyCard`, `ComparisonCard`, and `InputBar`. Add Cypress or Playwright for E2E browser flows.

7. **Redis for production state.** Replace `fakeredis` with a real Redis instance. Add `REDIS_URL` env var to the FastAPI startup event and wire `StateManager` to use it.

8. **Observability dashboards.** Connect the Prometheus `/metrics` endpoint to Grafana. Build panels for `cpna_latency_seconds`, `cpna_requests_total`, and `cpna_downgrade_total`.

9. **Clinician review gate.** Before v1.1 clinical use, add a human-in-the-loop review step for therapy plans above a configurable energy/nutrient threshold deviation from DRI reference values.

10. **Deployment.** Containerise the FastAPI service and Next.js frontend. Add a `docker-compose.yml` with Qdrant, Redis, and the CPNA services. Write a production readiness checklist.
