# CLAUDE.md — CPNA v1 Master Context

## Project Identity
Product: Agentic RAG Clinical Pediatric Nutrition Assistant (CPNA) v1
Stack: Python backend (FastAPI), Next.js 14 frontend (App Router, TypeScript), PostgreSQL, Redis, Qdrant (vector store), sentence-transformer + LogisticRegression intent classifier
Architecture: Agentic RAG with deterministic therapy engine, multi-agent orchestration, hybrid retrieval (vector + BM25), structured conversation state management
Active venv: rag_env (always activate before running or installing)

## EXISTING FILES — DO NOT REWRITE THESE
The following files already exist and are functional. Every agent and workflow must import from them rather than re-implementing their logic:

- app/common/pdf_loader.py
    Loads and parses PDF knowledge source documents.
    Use for: ingestion pipeline document loading.

- app/common/chapter_extractor.py
    Splits loaded documents into passage chunks by chapter or section.
    Entry point: extract_chapters_from_pdf(file_path, doc_type) -> List[Document]
    Use for: producing List[Document] fed to both Qdrant ingestion and BM25 corpus.
    Supports 9 doc_types: dri, shaw_2020, oxford_handbook, clinical_nutrition_2013,
      vitamin_mineral_requirements, preterm_2013, drug_nutrient, biochemistry, west_africa_fct_2019

- app/common/metadata_enricher.py
    Attaches condition_tags, age_relevance, therapy_area, drug_classes, document_type to each passage.
    Entry point: enrich_documents(documents, doc_type) -> List[Document]
    Also: get_citation_metadata(doc), get_document_priority_for_intent(intent)
    Use for: producing RetrievedPassage metadata fields.

- app/common/nutrient_calculator.py
    Core diet optimization: optimize_diet(), greedy_allocation(), meal_planner(), convert_fct_rows_to_foods()
    Takes targets as INPUT — does NOT compute DRI values itself.
    Use for: meal plan generation component inside DeterministicNutrientEngine.
    The DeterministicNutrientEngine wraps this — it does NOT reimplement it.

- app/models/intent_classifier/
    Trained intent classification model: sentence-transformer (all-MiniLM-L6-v2) + LogisticRegression
    Artifacts: classifier.pkl, label_encoder.pkl, label_mapping.json, embedding_model/, evaluation_results.json
    Test F1: 98.6%. Labels: therapy, recommendation, comparison, general
    Production inference wrapper: app/training/intent_classifier.py (IntentClassifier class)
    Do not retrain during build.

- app/training/
    Training scripts and labelled data. Reference only. Do not modify.

## Core Design Rules
- The UI consumes ONLY normalized display-safe response contracts. Raw orchestration objects must NEVER reach the frontend.
- Therapy outputs require a gatekeeper pass. If required slots are missing and cannot be resolved, downgrade to RECOMMENDATION — never hallucinate personalized values.
- Intent classification uses the existing model at app/models/intent_classifier. Low-confidence results (<0.70) must NOT route silently — trigger clarification or fallback.
- Conversation state has four buckets: session_memory, active_task_context, turn_entities, inherited_context. Never conflate them.
- Context inheritance is selective. A new comparison query after therapy must NOT silently inherit patient data.
- Loose replies ("yes", "8 years", "the first one") are resolved using last_assistant_prompt_type + workflow_stage + pending_slots — never guessed.
- Therapy targets must trace to the deterministic engine (wrapping nutrient_calculator.py) or DRI tables. Not LLM generation.
- Debug traces, internal fields, and machine field names must never appear in UI output.

## Supported Query Types
THERAPY | RECOMMENDATION | COMPARISON | GENERAL

## Supported Therapy Conditions (v1)
type 1 diabetes, cystic fibrosis, food allergy, preterm nutrition, chronic kidney disease,
pku, msud, galactosemia, epilepsy/ketogenic therapy, ibd, gerd

## Required Slots for Therapy
age, sex, weight, height, diagnosis, medications, biomarkers, country

## Retrieval Pipeline (mandatory order)
User query → LLM query rewriting → vector search top 20 → BM25 search top 20 → merge + deduplicate → rerank → top 7 contexts
Note: BM25 corpus and Qdrant index are populated from pdf_loader → chapter_extractor → metadata_enricher pipeline.

## Response Contracts (canonical shapes)
Defined in app/contracts/response_contracts.py — always import from here, never redefine inline.

## State Model
Defined in app/state/conversation_state.py — single source of truth. Never pass raw dicts as state.

## Directory Layout (existing + new)
app/
  common/          ← EXISTING — pdf_loader, chapter_extractor, metadata_enricher, nutrient_calculator
  models/          ← EXISTING — intent_classifier/
  training/        ← EXISTING — do not touch
  agents/          ← NEW
  state/           ← NEW
  classification/  ← NEW (wraps app/models/intent_classifier)
  retrieval/       ← NEW (uses app/common/* for ingestion)
  engine/          ← NEW (wraps app/common/nutrient_calculator)
  contracts/       ← NEW
  workflows/       ← NEW
  knowledge_graph/ ← NEW
  api/             ← NEW
  observability/   ← NEW
  tests/           ← NEW

## Non-Goals (v1)
No role-based UX, no EMR integration, no clinician permissions, no autonomous treatment without required data, no noisy button-driven flows

## Test Commands
Unit: pytest app/tests/unit
Integration: pytest app/tests/integration
E2E: pytest app/tests/e2e
