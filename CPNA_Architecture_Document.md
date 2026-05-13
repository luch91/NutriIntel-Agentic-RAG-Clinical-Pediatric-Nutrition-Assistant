# Clinical Pediatric Nutrition Assistant (CPNA)
## Production-Grade Agentic RAG Architecture Document

**Version:** 1.0  
**Date:** 2026-04-14  
**Classification:** Clinical Decision Support System Architecture

---

## Table of Contents

1. Problem Framing
2. System Goals
3. Functional Requirements
4. Non-Functional Requirements
5. High-Level Architecture
6. Agentic Workflow Design
7. Intent Classification Design
8. Conversation State Model
9. Hybrid Retrieval Architecture
10. Knowledge Base and Corpus Design
11. Knowledge Graph Design (Case Studies)
12. Graph + RAG Fusion Strategy
13. Deterministic Therapy Engine Design
14. Recommendation Workflow Design
15. Comparison Workflow Design
16. General Workflow Design
17. Safety and Downgrade Logic
18. Data Flow and Sequence Flows
19. Storage Architecture
20. Evaluation Framework
21. Monitoring and Observability
22. Failure Modes and Mitigations
23. Future Extensibility

---

## 1. Problem Framing

### 1.1 The Clinical Gap

Pediatric nutrition is a high-stakes domain where errors can cause growth failure, metabolic decompensation, or long-term developmental harm. Current AI assistants in this space suffer from:

- **Hallucinated nutrient values**: LLMs generate plausible but incorrect RDA/AI/UL values
- **Missing safety guards**: No gatekeeping between general advice and therapy-grade recommendations
- **No case memory**: Each query is stateless, ignoring prior context in a clinical consultation
- **Guideline conflation**: Clinical guidelines, case anecdotes, and general knowledge are treated as equivalent evidence
- **No deterministic backbone**: Calculations like catch-up growth formulas are treated as generative text, not validated computations

### 1.2 Why Agentic RAG

A single monolithic LLM cannot safely handle pediatric nutrition because:

| Capability | LLM Strength | LLM Weakness | Required Approach |
|---|---|---|---|
| Intent understanding | Strong | Ambiguous queries | DistilBERT classifier |
| Query reformulation | Strong | None | LLM rewriting agent |
| Nutrient calculations | Weak | Hallucination-prone | Deterministic engine |
| Evidence retrieval | Weak | No native access | Hybrid vector + BM25 |
| Case reasoning | Weak | Overgeneralization | Knowledge graph |
| Response synthesis | Strong | Factual drift | Grounded synthesis agent |

Agentic RAG decomposes the problem into specialized components, each with appropriate tools and guardrails.

### 1.3 Scope Boundary

This system is a **clinical decision support tool**, not a replacement for clinical judgment. All therapy outputs are advisory and must be reviewed by a qualified pediatric dietitian or physician. The architecture enforces this through safety gating, confidence thresholds, and explicit downgrade paths.

---

## 2. System Goals

### 2.1 Primary Goals

| ID | Goal | Description |
|---|---|---|
| G1 | Safe intent routing | Classify every query into Therapy, Recommendation, Comparison, or General with calibrated confidence |
| G2 | Evidence-grounded responses | Every clinical claim must be traceable to a retrieved source (guideline, table, or structured case) |
| G3 | Deterministic therapy | All therapy-grade outputs use validated calculations, not LLM-generated numbers |
| G4 | Case-study reasoning | Surface similar clinical cases as analogs without overgeneralizing them as guidelines |
| G5 | Conversational continuity | Maintain session state so follow-up queries inherit context, extracted entities, and evidence |
| G6 | Safe degradation | When data is insufficient, downgrade gracefully rather than fabricate |

### 2.2 Anti-Goals

- **NOT** a diagnostic system (no disease diagnosis)
- **NOT** a prescribing system (no medication changes)
- **NOT** a replacement for clinical guidelines (case studies supplement, never replace)
- **NOT** a general-purpose chatbot (narrowly scoped to pediatric nutrition)

---

## 3. Functional Requirements

### 3.1 Query Processing

| ID | Requirement | Description |
|---|---|---|
| FR-01 | Intent classification | Classify user queries into Therapy, Recommendation, Comparison, General using DistilBERT |
| FR-02 | Confidence scoring | Output calibrated confidence for each intent class; route to fallback below threshold |
| FR-03 | Query rewriting | Rewrite ambiguous queries into search-optimized forms using LLM |
| FR-04 | Entity extraction | Extract age, condition, food, nutrient, medication entities from queries |
| FR-05 | Slot detection | Identify required slots for therapy queries (age, weight, diagnosis, current intake) |

### 3.2 Retrieval

| ID | Requirement | Description |
|---|---|---|
| FR-06 | Vector search | Retrieve top-20 passages from embedding index over clinical corpus |
| FR-07 | BM25 search | Retrieve top-20 passages from lexical index over same corpus |
| FR-08 | Result merging | Merge and deduplicate vector + BM25 results using reciprocal rank fusion |
| FR-09 | Reranking | Cross-encoder rerank merged results to top-7 contexts |
| FR-10 | Knowledge graph query | Traverse graph for similar cases, condition-nutrient links, drug-nutrient interactions |
| FR-11 | Structured data query | Direct SQL/API queries to DRI tables, food composition tables, interaction tables |

### 3.3 Reasoning and Synthesis

| ID | Requirement | Description |
|---|---|---|
| FR-12 | Deterministic nutrient calculation | Calculate RDA/AI/UL from DRI tables given age, sex, condition |
| FR-13 | Condition adjustment | Apply condition-specific multipliers (e.g., CF × 1.2 energy, CKD protein restriction) |
| FR-14 | Drug-nutrient interaction | Flag interactions between medications and nutrients |
| FR-15 | Case analog retrieval | Surface top-3 similar cases from knowledge graph with similarity score |
| FR-16 | Comparison template | Render structured comparison between two entities using defined schema |
| FR-17 | Response synthesis | Generate natural-language response grounded in retrieved evidence |
| FR-18 | Citation generation | Attach source references to every clinical claim |

### 3.4 Safety

| ID | Requirement | Description |
|---|---|---|
| FR-19 | Therapy gatekeeping | Block therapy output if required slots are missing |
| FR-20 | Downgrade logic | Route low-confidence or insufficient-data queries to safer intent types |
| FR-21 | Disclaimer injection | Attach appropriate disclaimers based on intent and confidence |
| FR-22 | Age validation | Reject therapy queries for ages outside pediatric range (0-18 years) |

### 3.5 Conversation

| ID | Requirement | Description |
|---|---|---|
| FR-23 | Session state | Maintain current intent, entities, pending slots, evidence used |
| FR-24 | Context inheritance | Pass prior entities and evidence to follow-up turns |
| FR-25 | Multi-turn slot filling | Prompt for missing slots across multiple turns |

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID | Requirement | Target |
|---|---|---|
| NFR-01 | End-to-end latency (General) | < 2 seconds (p95) |
| NFR-02 | End-to-end latency (Therapy) | < 5 seconds (p95) |
| NFR-03 | Retrieval latency | < 800ms for hybrid retrieval + reranking |
| NFR-04 | Intent classification latency | < 50ms |
| NFR-05 | Throughput | 50 concurrent sessions minimum |

### 4.2 Reliability

| ID | Requirement | Target |
|---|---|---|
| NFR-06 | Availability | 99.9% uptime |
| NFR-07 | Intent classification accuracy | > 95% macro-F1 on held-out test set |
| NFR-08 | Retrieval recall@7 | > 85% for clinical guideline queries |
| NFR-09 | Deterministic calculation correctness | 100% (validated against reference tables) |

### 4.3 Security and Compliance

| ID | Requirement | Description |
|---|---|---|
| NFR-10 | Data privacy | No PHI stored in session state; anonymize case study data |
| NFR-11 | Audit logging | All queries, classifications, and outputs logged for review |
| NFR-12 | Model versioning | All models (classifier, embeddings, LLM) versioned and trackable |
| NFR-13 | Reproducibility | Same query + same state → same output (deterministic seed for generation) |

### 4.4 Maintainability

| ID | Requirement | Description |
|---|---|---|
| NFR-14 | Modular components | Each agent is independently deployable and testable |
| NFR-15 | Configuration-driven | DRI tables, food tables, interaction tables are configurable data sources |
| NFR-16 | Eval harness | Automated regression tests for intent, retrieval, and calculation accuracy |

---

## 5. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│                    Web App / Mobile App / API Consumer                       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP/gRPC
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY + LOAD BALANCER                         │
│              Rate limiting, authentication, request routing                  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER (FastAPI)                        │
│                                                                             │
│  ┌─────────────────────┐  ┌──────────────────────┐  ┌────────────────────┐  │
│  │  Conversation State  │  │  Request/Response    │  │  Audit Logger      │  │
│  │  Manager             │  │  Serializer          │  │                    │  │
│  └─────────────────────┘  └──────────────────────┘  └────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    AGENTIC WORKFLOW ENGINE                          │    │
│  │                                                                     │    │
│  │  ┌──────────────┐                                                   │    │
│  │  │ Intent Agent │  ← DistilBERT classifier                          │    │
│  │  └──────┬───────┘                                                   │    │
│  │         │ intent + confidence                                        │    │
│  │         ▼                                                           │    │
│  │  ┌──────────────────┐                                               │    │
│  │  │ Query Rewriting  │  ← LLM (gpt-4o-mini / claude-haiku)           │    │
│  │  │ Agent            │                                               │    │
│  │  └──────┬───────────┘                                               │    │
│  │         │ rewritten_query                                            │    │
│  │         ▼                                                           │    │
│  │  ┌──────────────────┐                                               │    │
│  │  │ Slot Filling     │  ← NER + rule-based extraction                │    │
│  │  │ Agent            │                                               │    │
│  │  └──────┬───────────┘                                               │    │
│  │         │ entities + pending_slots                                   │    │
│  │         ▼                                                           │    │
│  │  ┌──────────────────┐                                               │    │
│  │  │ Therapy          │  ← Gatekeeper (rules + confidence)            │    │
│  │  │ Gatekeeper Agent │                                               │    │
│  │  └──────┬───────────┘                                               │    │
│  │         │ gate_decision                                              │    │
│  │         ▼                                                           │    │
│  │  ┌──────────────────┐                                               │    │
│  │  │ Retrieval Agent  │  ← Hybrid pipeline (vector + BM25 + rerank)  │    │
│  │  └──────┬───────────┘                                               │    │
│  │         │ contexts (top 7)                                           │    │
│  │         ▼                                                           │    │
│  │  ┌──────────────────┐                                               │    │
│  │  │ Knowledge Graph  │  ← Graph traversal for similar cases          │    │
│  │  │ Retrieval Agent  │                                               │    │
│  │  └──────┬───────────┘                                               │    │
│  │         │ graph_contexts + case_analogs                              │    │
│  │         ▼                                                           │    │
│  │  ┌──────────────────┐                                               │    │
│  │  │ Deterministic    │  ← Nutrient calculations (therapy only)       │    │
│  │  │ Nutrient Engine  │                                               │    │
│  │  └──────┬───────────┘                                               │    │
│  │         │ nutrient_plan                                              │    │
│  │         ▼                                                           │    │
│  │  ┌──────────────────┐                                               │    │
│  │  │ Comparison       │  ← Template router (comparison only)          │    │
│  │  │ Template Router  │                                               │    │
│  │  └──────┬───────────┘                                               │    │
│  │         │ comparison_data                                            │    │
│  │         ▼                                                           │    │
│  │  ┌──────────────────┐                                               │    │
│  │  │ Response         │  ← LLM synthesis (grounded)                   │    │
│  │  │ Synthesis Agent  │                                               │    │
│  │  └──────────────────┘                                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA AND MODEL LAYER                                │
│                                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐   │
│  │ Vector DB    │ │ BM25 Index   │ │ Knowledge    │ │ Relational DB    │   │
│  │ (Qdrant /    │ │ (Elastic-    │ │ Graph        │ │ (PostgreSQL)     │   │
│  │  Weaviate)   │ │  search)     │ │ (Neo4j)      │ │                  │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘   │
│                                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐   │
│  │ DistilBERT   │ │ Embedding    │ │ Cross-       │ │ Deterministic    │   │
│  │ Intent       │ │ Model        │ │ Encoder      │ │ Calculation      │   │
│  │ Classifier   │ │ (text-       │ │ Reranker     │ │ Engine           │   │
│  │              │ │  embedding)   │ │ (bge-reranker)│ │                  │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.1 Layer Responsibilities

| Layer | Components | Responsibility |
|---|---|---|
| Client | Web/Mobile/API | User interaction, display, input capture |
| API Gateway | Nginx / Kong | Auth, rate limiting, TLS, routing |
| Orchestration | FastAPI + workflow engine | Agent coordination, state management, serialization |
| Data/Model | Databases + ML models | Storage, retrieval, inference, calculation |

### 5.2 Deployment Model

```
┌───────────────────────────────────────────┐
│              Kubernetes Cluster            │
│                                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐ │
│  │ API     │ │ Orchestr│ │  Agent      │ │
│  │ Pods    │ │ ator    │ │  Pods       │ │
│  │ (x3)    │ │ (x2)    │ │  (xN)       │ │
│  └─────────┘ └─────────┘ └─────────────┘ │
│                                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐ │
│  │ Vector  │ │ Graph   │ │  Relational │ │
│  │ DB      │ │ DB      │ │  DB         │ │
│  │ Stateful│ │ Stateful│ │  Stateful   │ │
│  └─────────┘ └─────────┘ └─────────────┘ │
│                                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐ │
│  │ Model   │ │ Cache   │ │  Message    │ │
│  │ Server  │ │ (Redis) │ │  Queue      │ │
│  │ (vLLM)  │ │         │ │  (RabbitMQ) │ │
│  └─────────┘ └─────────┘ └─────────────┘ │
└───────────────────────────────────────────┘
```

- **API pods**: Stateless, handle HTTP, auth, rate limiting
- **Orchestrator pods**: Stateless, manage workflow execution
- **Agent pods**: Stateless, each agent type independently scalable
- **Stateful services**: Vector DB, Graph DB, Relational DB with persistent volumes
- **Model server**: vLLM or TGI serving embeddings, reranker, and synthesis LLM
- **Cache**: Redis for session state, frequent query results, DRI table lookups
- **Message queue**: RabbitMQ for async tasks (indexing, graph ingestion, eval jobs)

---

## 6. Agentic Workflow Design

### 6.1 Agent Inventory

| Agent | Type | Input | Output | Technology |
|---|---|---|---|---|
| Intent Agent | Classifier | raw_query | intent, confidence | DistilBERT (fine-tuned) |
| Query Rewriting Agent | Generator | raw_query, session_state | rewritten_query | LLM (gpt-4o-mini) |
| Slot Filling Agent | Extractor | raw_query, rewritten_query, session_state | entities, pending_slots | spaCy NER + rules |
| Therapy Gatekeeper Agent | Rule Engine | intent, entities, pending_slots, confidence | gate_decision | Deterministic rules |
| Retrieval Agent | Retriever | rewritten_query, intent | top_7_contexts | Hybrid (vector + BM25 + rerank) |
| Knowledge Graph Retrieval Agent | Graph Query | entities, intent | graph_contexts, case_analogs | Neo4j Cypher |
| Deterministic Nutrient Engine | Calculator | entities (age, sex, weight, condition) | nutrient_plan | Python (DRI tables) |
| Comparison Template Router | Router | entity_a, entity_b, comparison_type | comparison_data | Template engine |
| Response Synthesis Agent | Generator | contexts, nutrient_plan, case_analogs, intent | response, citations | LLM (grounded) |
| Conversation State Manager | State Machine | session_id, turn_data | updated_state | Redis + Pydantic models |

### 6.2 Workflow Execution Model

Each workflow is a **directed acyclic graph (DAG)** of agent executions. The orchestrator executes agents in topological order, passing outputs as inputs to downstream agents.

```
Workflow DAG for THERAPY intent:
                                                        
  Intent Agent → Query Rewriting Agent → Slot Filling Agent
                                              │
                                              ▼
                                      Therapy Gatekeeper
                                         │         │
                                   PASS  │         │  FAIL (missing slots)
                                         ▼         ▼
                              ┌──────────────┐  ┌─────────────────┐
                              │ Retrieval     │  │ Slot Filling    │
                              │ Agent         │  │ Prompt Agent    │
                              │              │  │ (ask user)      │
                              ▼              │  └─────────────────┘
                              Knowledge Graph│
                              Retrieval Agent│
                              │              │
                              ▼              │
                              Deterministic  │
                              Nutrient Engine│
                              │              │
                              ▼              │
                              Response       │
                              Synthesis Agent│
                              │              │
                              ▼              │
                              Return to user │
                                             │
                              (After slot fulfillment,
                               re-enter at Gatekeeper)
```

```
Workflow DAG for RECOMMENDATION intent:

  Intent Agent → Query Rewriting Agent → Slot Filling Agent
                                              │
                                              ▼
                                      Retrieval Agent
                                      │
                                      ▼
                              Knowledge Graph
                              Retrieval Agent
                                      │
                                      ▼
                              Deterministic Nutrient
                              Engine (preview only)
                                      │
                                      ▼
                              Response Synthesis Agent
                                      │
                                      ▼
                              Return to user
```

```
Workflow DAG for COMPARISON intent:

  Intent Agent → Query Rewriting Agent → Slot Filling Agent
                                              │
                                              ▼
                                      Comparison Template
                                      Router
                                      │
                                      ▼
                              Retrieval Agent
                              (both entities)
                                      │
                                      ▼
                              Knowledge Graph
                              Retrieval Agent
                                      │
                                      ▼
                              Response Synthesis Agent
                                      │
                                      ▼
                              Return to user
```

```
Workflow DAG for GENERAL intent:

  Intent Agent → Query Rewriting Agent
                      │
                      ▼
              Retrieval Agent
                      │
                      ▼
              Response Synthesis Agent
                      │
                      ▼
              Return to user
```

### 6.3 Agent Interface Contract

Every agent implements a standardized interface:

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any

class AgentInput(BaseModel):
    query: str
    session_id: str
    intent: str | None = None
    entities: dict[str, Any] | None = None
    contexts: list[dict] | None = None
    pending_slots: list[str] | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = {}

class AgentOutput(BaseModel):
    success: bool
    data: dict[str, Any]
    error: str | None = None
    latency_ms: float

class BaseAgent(ABC):
    @abstractmethod
    async def execute(self, input: AgentInput) -> AgentOutput:
        ...
```

This contract ensures agents are composable, testable, and independently deployable.

### 6.4 Agent Orchestration Protocol

The orchestrator uses a **workflow definition** (YAML or code) to execute agents:

```yaml
# workflow_therapy.yaml
name: therapy
agents:
  - name: intent_classifier
    agent: IntentAgent
    input:
      query: "{{ user_query }}"
    output_bindings:
      intent: intent
      confidence: confidence

  - name: query_rewriter
    agent: QueryRewritingAgent
    input:
      query: "{{ user_query }}"
      session_state: "{{ session_state }}"
    output_bindings:
      rewritten_query: rewritten_query

  - name: slot_filler
    agent: SlotFillingAgent
    input:
      query: "{{ user_query }}"
      rewritten_query: "{{ rewritten_query }}"
      session_state: "{{ session_state }}"
    output_bindings:
      entities: entities
      pending_slots: pending_slots

  - name: therapy_gatekeeper
    agent: TherapyGatekeeperAgent
    input:
      intent: "{{ intent }}"
      entities: "{{ entities }}"
      pending_slots: "{{ pending_slots }}"
      confidence: "{{ confidence }}"
    output_bindings:
      gate_decision: gate_decision

  - condition: "{{ gate_decision == 'PASS' }}"
    agents:
      - name: retrieval
        agent: RetrievalAgent
        input:
          query: "{{ rewritten_query }}"
          intent: "{{ intent }}"
        output_bindings:
          contexts: contexts

      - name: kg_retrieval
        agent: KnowledgeGraphRetrievalAgent
        input:
          entities: "{{ entities }}"
          intent: "{{ intent }}"
        output_bindings:
          graph_contexts: graph_contexts
          case_analogs: case_analogs

      - name: nutrient_engine
        agent: DeterministicNutrientEngine
        input:
          entities: "{{ entities }}"
        output_bindings:
          nutrient_plan: nutrient_plan

      - name: synthesis
        agent: ResponseSynthesisAgent
        input:
          contexts: "{{ contexts }}"
          graph_contexts: "{{ graph_contexts }}"
          case_analogs: "{{ case_analogs }}"
          nutrient_plan: "{{ nutrient_plan }}"
          intent: "{{ intent }}"
          entities: "{{ entities }}"
        output_bindings:
          response: response
          citations: citations

  - condition: "{{ gate_decision == 'FAIL' }}"
    agents:
      - name: slot_prompt
        agent: SlotFillingAgent
        action: generate_prompt
        input:
          pending_slots: "{{ pending_slots }}"
        output_bindings:
          prompt: prompt
```

---

## 7. Intent Classification Design

### 7.1 Why DistilBERT

| Criterion | DistilBERT | LLM (zero-shot) | Rule-based |
|---|---|---|---|
| Latency | ~10ms | 500-2000ms | <1ms |
| Accuracy (with fine-tuning) | >95% F1 | 85-92% F1 | 70-80% F1 |
| Cost per query | ~$0.00001 | ~$0.0005-0.01 | $0 |
| Confidence calibration | Well-calibrated (softmax) | Poorly calibrated | N/A |
| Interpretability | Attention weights | Black box | Fully interpretable |
| Deployment | Self-hosted, lightweight | Requires GPU or API | Code only |

**Decision**: DistilBERT is chosen because intent classification is a **high-frequency, latency-sensitive, confidence-critical** task. The ~10ms inference time enables real-time routing without blocking. Fine-tuning on pediatric nutrition queries achieves >95% F1. The softmax output provides calibrated confidence scores essential for safety gating.

### 7.2 Intent Taxonomy

```
Intent Classes:
├── THERAPY (class 0)
│   Individualized, patient-specific nutrition intervention
│   Signals: "for my patient", "3 year old with CF", "calculate requirements",
│            "what dose", "how much protein for"
│
├── RECOMMENDATION (class 1)
│   Condition-aware general guidance, not patient-specific
│   Signals: "for children with autism", "best foods for toddlers",
│            "what is recommended for CKD"
│
├── COMPARISON (class 2)
│   Side-by-side analysis of two entities
│   Signals: "vs", "versus", "difference between", "compare", "which is better"
│
└── GENERAL (class 3)
    Educational, factual nutrition knowledge
    Signals: "what is", "define", "list sources of", "how does", "why is"
```

### 7.3 DistilBERT Fine-Tuning Pipeline

```python
# Training data schema
{
    "query": "How much protein does a 5-year-old with nephrotic syndrome need?",
    "intent": "THERAPY",
    "source": "clinical_queries"  # or "synthetic", "manual"
}

# Fine-tuning configuration
training_config = {
    "model": "distilbert-base-uncased",
    "num_labels": 4,
    "max_length": 128,
    "batch_size": 32,
    "learning_rate": 2e-5,
    "epochs": 5,
    "class_weights": "balanced",  # handle class imbalance
    "early_stopping_patience": 2,
    "calibration": "temperature_scaling",  # post-hoc calibration
    "evaluation_metrics": ["f1_macro", "accuracy", "ece"]  # Expected Calibration Error
}
```

### 7.4 Training Data Strategy

| Source | Volume | Method |
|---|---|---|
| Clinical query logs (anonymized) | 5,000+ | Manual labeling by dietitians |
| Synthetic queries (LLM-generated) | 20,000+ | Prompt templates per intent class |
| Edge cases and adversarial | 2,000+ | Targeted generation for boundary cases |
| Multi-turn queries | 3,000+ | Session simulation with context |

**Total target**: 30,000 labeled examples, 80/10/10 train/val/test split.

### 7.5 Confidence Thresholds and Routing

```python
CONFIDENCE_THRESHOLDS = {
    "THERAPY": {
        "high": 0.85,    # Route to full therapy pipeline
        "medium": 0.65,  # Route with enhanced safety checks
        "low": 0.0,      # Downgrade to RECOMMENDATION
    },
    "RECOMMENDATION": {
        "high": 0.80,
        "medium": 0.60,
        "low": 0.0,       # Downgrade to GENERAL
    },
    "COMPARISON": {
        "high": 0.80,
        "medium": 0.55,
        "low": 0.0,       # Downgrade to GENERAL
    },
    "GENERAL": {
        "high": 0.75,
        "medium": 0.50,
        "low": 0.0,       # Fallback: "I'm not sure I understand"
    }
}

def route_intent(classification: dict) -> str:
    intent = classification["intent"]
    confidence = classification["confidence"]
    
    thresholds = CONFIDENCE_THRESHOLDS[intent]
    
    if confidence >= thresholds["high"]:
        return intent
    elif confidence >= thresholds["medium"]:
        return intent  # with enhanced safety flag
    else:
        # Downgrade to safer intent
        downgrade_map = {
            "THERAPY": "RECOMMENDATION",
            "RECOMMENDATION": "GENERAL",
            "COMPARISON": "GENERAL",
            "GENERAL": "GENERAL"
        }
        return downgrade_map[intent]
```

### 7.6 Intent Classification Output

```python
class IntentClassificationOutput(BaseModel):
    intent: Literal["THERAPY", "RECOMMENDATION", "COMPARISON", "GENERAL"]
    confidence: float
    all_scores: dict[str, float]  # all class probabilities
    downgraded_from: str | None   # if confidence was low
    reasoning: str | None         # attention-based explanation (debug)
```

---

## 8. Conversation State Model

### 8.1 Why a State Layer

Without conversation state:
- Each query is isolated, requiring users to repeat context
- Follow-up queries like "what about iron?" have no referent
- Slot filling across turns is impossible
- Evidence used in prior turns is lost
- Therapy sessions cannot track what has been established

### 8.2 State Schema

```python
from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime

class ConversationState(BaseModel):
    session_id: str
    created_at: datetime
    updated_at: datetime
    
    # Current turn context
    current_intent: str | None = None
    current_intent_confidence: float | None = None
    workflow_stage: str = "idle"  # idle, classification, retrieval, synthesis, complete
    
    # Extracted entities (accumulated across turns)
    entities: dict[str, Any] = Field(default_factory=dict)
    # Example: {"age_years": 5, "sex": "male", "condition": "CF", "weight_kg": 16.2}
    
    # Pending slots (for therapy)
    pending_slots: list[str] = Field(default_factory=list)
    # Example: ["weight_kg", "current_intake_kcal"]
    
    # Filled slots
    filled_slots: dict[str, Any] = Field(default_factory=dict)
    
    # Downgrade tracking
    downgrade_state: dict = Field(default_factory=lambda: {
        "original_intent": None,
        "downgraded_to": None,
        "reason": None,
        "turn_count": 0
    })
    
    # Inherited context from prior turns
    inherited_context: dict = Field(default_factory=lambda: {
        "prior_intent": None,
        "prior_entities": {},
        "prior_evidence_ids": [],
        "prior_response_summary": None
    })
    
    # Evidence used in current session (for citation and audit)
    evidence_used: list[dict] = Field(default_factory=list)
    # Example: [{"source_id": "guideline_cfd_2023", "type": "guideline", "passage": "..."}]
    
    # Case analogs retrieved
    case_analogs: list[dict] = Field(default_factory=list)
    
    # Turn history
    turn_history: list[dict] = Field(default_factory=list)
    
    # Safety flags
    safety_flags: dict = Field(default_factory=lambda: {
        "therapy_blocked": False,
        "disclaimer_shown": False,
        "age_validated": False
    })
```

### 8.3 State Lifecycle

```
Session Start
    │
    ▼
[Initialize State] ──→ session_id, empty entities, idle stage
    │
    ▼
[Turn 1: Query Received]
    │
    ├── Classify intent ──→ current_intent, confidence
    ├── Extract entities ──→ entities, pending_slots
    ├── Execute workflow ──→ workflow_stage transitions
    ├── Collect evidence ──→ evidence_used
    └── Update state ──→ turn_history appended
    │
    ▼
[Turn 2: Follow-up Query]
    │
    ├── Inherit prior state ──→ inherited_context populated
    ├── Merge new entities ──→ entities updated (no overwrite of confirmed)
    ├── Check pending slots ──→ resolve if user provided
    ├── Execute workflow with inherited context
    └── Update state
    │
    ▼
[Session Timeout / Explicit End]
    │
    └── Archive state to audit log, clear Redis cache
```

### 8.4 State Manager Implementation

```python
class ConversationStateManager:
    def __init__(self, redis_client, ttl_seconds: int = 1800):  # 30 min session
        self.redis = redis_client
        self.ttl = ttl_seconds
    
    async def get_state(self, session_id: str) -> ConversationState:
        raw = await self.redis.get(f"session:{session_id}")
        if raw is None:
            return ConversationState(session_id=session_id)
        return ConversationState.model_validate_json(raw)
    
    async def update_state(self, state: ConversationState) -> None:
        state.updated_at = datetime.utcnow()
        await self.redis.set(
            f"session:{state.session_id}",
            state.model_dump_json(),
            ex=self.ttl
        )
    
    async def inherit_context(self, state: ConversationState) -> ConversationState:
        """Pack current state into inherited_context for next turn."""
        state.inherited_context = {
            "prior_intent": state.current_intent,
            "prior_entities": dict(state.entities),
            "prior_evidence_ids": [e["source_id"] for e in state.evidence_used],
            "prior_response_summary": self._summarize_last_turn(state)
        }
        return state
    
    async def merge_entities(self, state: ConversationState, new_entities: dict) -> ConversationState:
        """Merge new entities without overwriting confirmed slots."""
        for key, value in new_entities.items():
            if key not in state.filled_slots:  # Don't overwrite confirmed data
                state.entities[key] = value
        return state
    
    async def resolve_slot(self, state: ConversationState, slot: str, value: Any) -> ConversationState:
        """Mark a pending slot as resolved."""
        if slot in state.pending_slots:
            state.pending_slots.remove(slot)
            state.filled_slots[slot] = value
            state.entities[slot] = value
        return state
```

### 8.5 State Inheritance in Query Processing

```python
async def process_turn(session_id: str, user_query: str) -> Response:
    state = await state_manager.get_state(session_id)
    
    # Inherit prior context
    state = await state_manager.inherit_context(state)
    
    # Run intent classification with inherited context as hint
    intent_output = await intent_agent.execute(AgentInput(
        query=user_query,
        session_id=session_id,
        metadata={"inherited_intent": state.inherited_context["prior_intent"]}
    ))
    
    # Merge entities from prior turn with current extraction
    state = await state_manager.merge_entities(state, intent_output.data["entities"])
    
    # Resolve any pending slots from user input
    for slot in list(state.pending_slots):
        if slot in intent_output.data["entities"]:
            state = await state_manager.resolve_slot(
                state, slot, intent_output.data["entities"][slot]
            )
    
    # Continue with workflow...
```

---

## 9. Hybrid Retrieval Architecture

### 9.1 Why Hybrid Retrieval

| Approach | Strength | Weakness |
|---|---|---|
| Vector search (semantic) | Handles paraphrase, conceptual similarity | Misses exact term matches, nutrient names |
| BM25 (lexical) | Exact keyword match, acronym recognition | Fails on paraphrase, synonyms |
| Hybrid (combined) | Covers both semantic and lexical gaps | Requires merging and reranking |

Pediatric nutrition queries contain both conceptual questions ("how to manage failure to thrive") and exact-term queries ("RDA for vitamin D at 12 months"). Hybrid retrieval covers both.

### 9.2 End-to-End Pipeline

```
User Query: "How much zinc does a 2-year-old need?"
                    │
                    ▼
        ┌───────────────────────┐
        │  Query Rewriting      │
        │  Agent (LLM)          │
        │                       │
        │  Rewritten: "zinc     │
        │  dietary reference    │
        │  intake age 2 years   │
        │  toddler RDA"         │
        └───────────┬───────────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
┌──────────────────┐ ┌──────────────────┐
│  Vector Search   │ │  BM25 Search     │
│  (Qdrant)        │ │  (Elasticsearch) │
│                  │ │                  │
│  Embedding:      │ │  Terms:          │
│  text-embed-     │ │  zinc, RDA,      │
│  ding-v3         │ │  dietary,        │
│                  │ │  reference,      │
│  Top 20 results  │ │  intake, 2 years │
│  by cosine sim   │ │                  │
│                  │ │  Top 20 results  │
│                  │ │  by BM25 score   │
└────────┬─────────┘ └────────┬─────────┘
         │                    │
         └──────────┬─────────┘
                    ▼
        ┌───────────────────────┐
        │  Reciprocal Rank      │
        │  Fusion (RRF)         │
        │                       │
        │  RRF_score(d) =       │
        │  Σ 1/(k + rank_i(d))  │
        │  k = 60               │
        │                       │
        │  Merged: 30-35 unique │
        │  passages             │
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │  Cross-Encoder        │
        │  Reranker             │
        │  (bge-reranker-v2)    │
        │                       │
        │  Scores each (query,  │
        │  passage) pair with   │
        │  deep interaction     │
        │                       │
        │  Top 7 passages       │
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │  Output:              │
        │  contexts[0..6]       │
        │  Each with:           │
        │  - passage_text        │
        │  - source_id          │
        │  - source_type        │
        │  - relevance_score    │
        │  - retrieval_method   │
        └───────────────────────┘
```

### 9.3 Reciprocal Rank Fusion

```python
def reciprocal_rank_fusion(vector_results: list, bm25_results: list, k: int = 60) -> list:
    """
    Merge vector and BM25 results using RRF.
    
    RRF handles the score incompatibility problem: vector scores (cosine similarity)
    and BM25 scores are on different scales. RRF uses rank position only.
    """
    scores = {}
    
    for rank, doc in enumerate(vector_results, 1):
        doc_id = doc["source_id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank)
    
    for rank, doc in enumerate(bm25_results, 1):
        doc_id = doc["source_id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank)
    
    # Sort by RRF score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:35]  # Top 35 for reranking
```

### 9.4 Vector Search Configuration

```python
# Embedding model: BGE-M3 or text-embedding-3-small
embedding_config = {
    "model": "BAAI/bge-m3",  # multilingual, 1024-dim
    "dimensions": 1024,
    "max_tokens": 8192,
    "normalization": "cosine",
}

# Qdrant collection setup
collection_config = {
    "name": "pediatric_nutrition_corpus",
    "vector_size": 1024,
    "distance": "Cosine",
    "hnsw_config": {
        "m": 32,
        "ef_construct": 256
    },
    "payload_schema": {
        "source_id": {"type": "keyword"},
        "source_type": {"type": "keyword"},  # guideline, textbook, paper, case_study
        "topic": {"type": "keyword"},
        "age_range": {"type": "keyword"},
        "condition": {"type": "keyword"},
        "nutrient": {"type": "keyword"},
        "passage_index": {"type": "text"}  # for BM25 fallback in Qdrant
    }
}
```

### 9.5 BM25 Configuration

```python
# Elasticsearch index mapping
bm25_mapping = {
    "mappings": {
        "properties": {
            "passage_text": {
                "type": "text",
                "analyzer": "pediatric_nutrition_analyzer",
                "fields": {
                    "keyword": {"type": "keyword", "ignore_above": 256}
                }
            },
            "source_id": {"type": "keyword"},
            "source_type": {"type": "keyword"},
            "topic": {"type": "keyword"},
            "condition": {"type": "keyword"},
            "nutrient": {"type": "keyword"}
        }
    },
    "settings": {
        "analysis": {
            "analyzer": {
                "pediatric_nutrition_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "stop",
                        "stemmer",
                        "synonym_graph"  # custom synonym filter for nutrition terms
                    ]
                }
            },
            "filter": {
                "synonym_graph": {
                    "type": "synonym_graph",
                    "synonyms": [
                        "RDA, recommended dietary allowance, dietary reference intake",
                        "CF, cystic fibrosis",
                        "CKD, chronic kidney disease",
                        "FTT, failure to thrive",
                        "SGA, small for gestational age",
                        "AGA, appropriate for gestational age"
                    ]
                }
            }
        },
        "similarity": {
            "custom_bm25": {
                "type": "BM25",
                "k1": 1.5,
                "b": 0.75
            }
        }
    }
}
```

### 9.6 Reranker Configuration

```python
# Cross-encoder reranker
reranker_config = {
    "model": "BAAI/bge-reranker-v2-m3",
    "max_length": 512,
    "batch_size": 32,
    "top_k": 7
}

# Reranker scoring
def rerank(query: str, passages: list[dict]) -> list[dict]:
    """
    Cross-encoder reranker.
    
    Unlike bi-encoder (vector search), cross-encoder processes
    query and passage together through the full transformer,
    enabling deep interaction modeling.
    
    Input: 30-35 passages from RRF merge
    Output: Top 7 passages ranked by relevance score
    """
    pairs = [(query, p["passage_text"]) for p in passages]
    scores = reranker_model.predict(pairs)
    
    for passage, score in zip(passages, scores):
        passage["relevance_score"] = float(score)
    
    passages.sort(key=lambda x: x["relevance_score"], reverse=True)
    return passages[:7]
```

### 9.7 Retrieval Agent Implementation

```python
class RetrievalAgent(BaseAgent):
    async def execute(self, input: AgentInput) -> AgentOutput:
        start = time.time()
        query = input.metadata.get("rewritten_query", input.query)
        intent = input.intent
        
        # 1. Vector search
        vector_results = await self.vector_db.search(
            query=query,
            top_k=20,
            filters=self._build_intent_filters(intent)
        )
        
        # 2. BM25 search
        bm25_results = await self.bm25_index.search(
            query=query,
            top_k=20,
            filters=self._build_intent_filters(intent)
        )
        
        # 3. Merge with RRF
        merged = reciprocal_rank_fusion(vector_results, bm25_results)
        
        # 4. Fetch full passages
        passages = await self._fetch_passages(merged)
        
        # 5. Rerank
        reranked = rerank(query, passages)
        
        # 6. Format output
        contexts = [
            {
                "passage_text": p["passage_text"],
                "source_id": p["source_id"],
                "source_type": p["source_type"],
                "relevance_score": p["relevance_score"],
                "retrieval_method": p.get("retrieval_method", "hybrid")
            }
            for p in reranked
        ]
        
        return AgentOutput(
            success=True,
            data={"contexts": contexts},
            latency_ms=(time.time() - start) * 1000
        )
    
    def _build_intent_filters(self, intent: str) -> dict:
        """Apply intent-specific retrieval filters."""
        filters = {}
        if intent == "THERAPY":
            # Prioritize guidelines and DRI tables
            filters["source_type"] = ["guideline", "dri_table", "clinical_reference"]
        elif intent == "RECOMMENDATION":
            filters["source_type"] = ["guideline", "textbook", "clinical_reference"]
        elif intent == "COMPARISON":
            # Broader retrieval including review articles
            filters["source_type"] = ["guideline", "review_article", "textbook"]
        elif intent == "GENERAL":
            # All sources
            pass
        return filters
```

---

## 10. Knowledge Base and Corpus Design

### 10.1 Source Corpora

| Corpus | Content | Format | Update Frequency | Volume |
|---|---|---|---|---|
| Dietary Reference Intakes | RDA, AI, UL, EAR by age/sex/life-stage | Structured tables (CSV/JSON) | Annual (IOM updates) | ~500 rows |
| Food Composition Tables | Nutrient values per 100g for 8,000+ foods | Structured (USDA SR Legacy format) | Periodic | ~8,000 foods × 150 nutrients |
| Drug-Nutrient Interactions | Medication → nutrient interaction pairs | Structured table | Quarterly | ~1,200 pairs |
| Clinical Guidelines | ESPGHAN, AAP, CSPEN, WHO pediatric nutrition guidelines | PDF → chunked text | As published | ~200 documents |
| Pediatric Nutrition Textbooks | Nelson, Pediatric Nutrition (AAP), etc. | PDF → chunked text | Edition updates | ~15 textbooks |
| Review Articles | Curated review papers on pediatric conditions | PDF → chunked text | Monthly ingestion | ~2,000 papers |
| Case Studies | Clinical pediatric nutrition case studies | Structured + text | Batch ingestion | ~1,000 cases |

### 10.2 Document Chunking Strategy

```python
chunking_config = {
    "guidelines": {
        "strategy": "semantic_section",  # Respect section boundaries
        "max_chunk_size": 1000,          # tokens
        "overlap": 100,                   # tokens
        "metadata_extraction": ["section_title", "recommendation_grade", "condition"]
    },
    "textbooks": {
        "strategy": "recursive_character",
        "max_chunk_size": 800,
        "overlap": 80,
        "separators": ["\n\n", "\n", ". ", " ", ""]
    },
    "papers": {
        "strategy": "section_based",     # Abstract, Methods, Results, Discussion
        "max_chunk_size": 600,
        "overlap": 50
    },
    "case_studies": {
        "strategy": "structured_plus_narrative",  # Structured fields + narrative
        "max_chunk_size": 500,
        "overlap": 0  # Cases are self-contained
    }
}
```

### 10.3 Structured Data Sources

#### Dietary Reference Intakes Table Schema

```sql
CREATE TABLE dietary_reference_intakes (
    id SERIAL PRIMARY KEY,
    nutrient VARCHAR(100) NOT NULL,
    sex VARCHAR(10) NOT NULL,  -- male, female, both
    age_min_months INTEGER NOT NULL,
    age_max_months INTEGER NOT NULL,
    life_stage VARCHAR(50),     -- infant, toddler, child, adolescent
    rda FLOAT,                  -- Recommended Dietary Allowance
    ai FLOAT,                   -- Adequate Intake
    ul FLOAT,                   -- Tolerable Upper Intake Level
    ear FLOAT,                  -- Estimated Average Requirement
    unit VARCHAR(20) NOT NULL,  -- mg, mcg, IU, g, kcal
    condition_adjustment JSONB, -- condition-specific multipliers
    source VARCHAR(100),        -- "IOM 2023", "ESPGHAN 2022"
    source_id VARCHAR(100),
    last_updated DATE
);

-- Index for fast lookup
CREATE INDEX idx_dri_lookup 
ON dietary_reference_intakes (nutrient, sex, age_min_months, age_max_months);

-- Example row:
INSERT INTO dietary_reference_intakes VALUES (
    nutrient = 'zinc',
    sex = 'both',
    age_min_months = 12,
    age_max_months = 36,
    life_stage = 'toddler',
    rda = 3.0,
    ai = NULL,
    ul = 7.0,
    ear = 2.5,
    unit = 'mg/day',
    condition_adjustment = {
        "CF": {"multiplier": 1.0, "note": "No specific adjustment"},
        "CKD_stage_3": {"multiplier": 1.0, "note": "Monitor serum levels"},
        "nephrotic_syndrome": {"multiplier": 1.5, "note": "Increased losses in urine"}
    },
    source = 'IOM 2023',
    source_id = 'IOM_Zn_2023_001'
);
```

#### Food Composition Table Schema

```sql
CREATE TABLE food_composition (
    id SERIAL PRIMARY KEY,
    food_code VARCHAR(20) UNIQUE NOT NULL,
    food_name VARCHAR(200) NOT NULL,
    food_category VARCHAR(100),      -- cereal, dairy, fruit, vegetable, protein, etc.
    serving_size_g FLOAT,
    nutrients JSONB NOT NULL,         -- {"energy_kcal": 130, "protein_g": 2.5, ...}
    bioavailability JSONB,            -- {"iron": "heme", "zinc": "moderate"}
    allergens TEXT[],                -- ["milk", "soy", "gluten"]
    preparation_method VARCHAR(50),   -- raw, cooked, fortified
    source VARCHAR(100),
    last_updated DATE
);

-- GIN index for JSONB nutrient queries
CREATE INDEX idx_food_nutrients ON food_composition USING GIN (nutrients);

-- Example row:
INSERT INTO food_composition VALUES (
    food_code = 'F001234',
    food_name = 'Chicken breast, skinless, roasted',
    food_category = 'protein',
    serving_size_g = 100,
    nutrients = {
        "energy_kcal": 165,
        "protein_g": 31.0,
        "fat_total_g": 3.6,
        "iron_mg": 1.0,
        "zinc_mg": 1.0,
        "vitamin_b6_mg": 0.6,
        "vitamin_b12_mcg": 0.3,
        "calcium_mg": 15,
        "phosphorus_mg": 228
    },
    bioavailability = {"iron": "heme", "zinc": "high"},
    allergens = [],
    preparation_method = 'roasted',
    source = 'USDA SR Legacy'
);
```

#### Drug-Nutrient Interaction Table Schema

```sql
CREATE TABLE drug_nutrient_interactions (
    id SERIAL PRIMARY KEY,
    drug_name VARCHAR(200) NOT NULL,
    drug_class VARCHAR(100),          -- PPI, anticonvulsant, diuretic, etc.
    nutrient VARCHAR(100) NOT NULL,
    interaction_type VARCHAR(50),      -- depletion, malabsorption, increased_excretion,
                                       -- increased_requirement, antagonism
    severity VARCHAR(20),             -- mild, moderate, severe
    mechanism TEXT,
    recommendation TEXT,              -- "Monitor zinc levels; consider supplementation"
    evidence_grade VARCHAR(20),       -- strong, moderate, weak
    source VARCHAR(100),
    last_updated DATE
);

-- Example row:
INSERT INTO drug_nutrient_interactions VALUES (
    drug_name = 'Omeprazole',
    drug_class = 'Proton Pump Inhibitor',
    nutrient = 'calcium',
    interaction_type = 'malabsorption',
    severity = 'moderate',
    mechanism = 'Reduced gastric acidity decreases calcium carbonate solubility',
    recommendation = 'Use calcium citrate instead; monitor bone health in long-term use',
    evidence_grade = 'strong',
    source = 'Micromedex 2024'
);
```

### 10.4 Corpus Ingestion Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                        │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ PDF      │  │ CSV/JSON │  │ API      │  │ Manual     │  │
│  │ Documents│  │ Tables   │  │ Feeds    │  │ Entry      │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │              │             │               │         │
│       └──────────────┴─────────────┴───────────────┘         │
│                              │                                │
│                              ▼                                │
│                  ┌─────────────────────┐                     │
│                  │  Document Parser    │                     │
│                  │  (PyMuPDF, Tabula)  │                     │
│                  └──────────┬──────────┘                     │
│                             │                                │
│                             ▼                                │
│                  ┌─────────────────────┐                     │
│                  │  Chunker            │                     │
│                  │  (strategy by type) │                     │
│                  └──────────┬──────────┘                     │
│                             │                                │
│              ┌──────────────┴──────────────┐                 │
│              ▼                              ▼                 │
│  ┌─────────────────────┐    ┌─────────────────────────────┐  │
│  │  Embedding Model    │    │  Structured Data Validator  │  │
│  │  → Vector DB        │    │  → PostgreSQL               │  │
│  └─────────────────────┘    └─────────────────────────────┘  │
│              │                              │                 │
│              └──────────────┬───────────────┘                 │
│                             │                                │
│                             ▼                                │
│                  ┌─────────────────────┐                     │
│                  │  BM25 Indexer       │                     │
│                  │  → Elasticsearch    │                     │
│                  └─────────────────────┘                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Quality Checks:                                     │   │
│  │  - Passage length distribution                       │   │
│  │  - Embedding null checks                             │   │
│  │  - Table referential integrity                       │   │
│  │  - Duplicate detection (MinHash)                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. Knowledge Graph Design (Case Studies)

### 11.1 Why a Knowledge Graph from Case Studies

Case studies in pediatric nutrition represent a distinct type of knowledge:
- **Guidelines** say "what should be done" (normative)
- **Case studies** show "what was done and what happened" (descriptive)

A knowledge graph captures the **structured relationships** within and across cases, enabling:
- Similar-case retrieval: "Show me cases like this patient"
- Pattern discovery: "What interventions worked for nephrotic syndrome with growth failure?"
- Reasoning paths: "Condition → symptom → nutrient deficit → intervention → outcome"

Critically, case studies are **not guidelines**. They provide analogical reasoning support, not prescriptive rules.

### 11.2 Graph Schema Design

#### Node Types

```
┌──────────────────────────────────────────────────────────────┐
│                     NODE TYPES                               │
│                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐  │
│  │  CaseStudy   │   │  Patient     │   │   Diagnosis      │  │
│  │              │   │  Profile     │   │                  │  │
│  │  - id        │   │  - id        │   │  - id            │  │
│  │  - year      │   │  - age_months│   │  - name          │  │
│  │  - source    │   │  - sex       │   │  - category      │  │
│  │  - complexity│   │  - gest_age  │   │  - icd_code      │  │
│  │              │   │  - birth_wt  │   │                  │  │
│  └──────────────┘   │  - current_wt│   └────────┬─────────┘  │
│                     │  - height    │              │           │
│                     │  - head_circ │              │           │
│                     │  - bmi_z     │              │           │
│                     │  - wt_z      │              │           │
│                     │  - ht_z      │              │           │
│                     └──────┬───────┘              │           │
│                            │                      │           │
│  ┌──────────────┐   ┌──────┴───────┐   ┌──────────┴─────────┐ │
│  │  Symptom     │   │  Growth      │   │   Medication       │ │
│  │              │   │  Status      │   │                  │  │
│  │  - id        │   │  - id       │   │  - id            │  │
│  │  - name      │   │  - z_scores │   │  - name          │  │
│  │  - severity  │   │  - velocity │   │  - dose          │  │
│  │  - duration  │   │  - percentiles│ │  - duration      │  │
│  └──────┬───────┘   │  - status   │   └────────┬─────────┘  │
│         │           └─────────────┘              │           │
│         │                                        │           │
│  ┌──────┴───────┐                    ┌───────────┴─────────┐ │
│  │  Biomarker   │                    │  Nutrition          │ │
│  │              │                    │  Intervention       │ │
│  │  - id        │                    │                   │ │
│  │  - name      │                    │  - id             │ │
│  │  - value     │                    │  - type           │ │
│  │  - unit      │                    │  - description    │ │
│  │  - normal_range│                  │  - duration       │ │
│  └──────┬───────┘                    └────────┬──────────┘  │
│         │                                     │             │
│  ┌──────┴───────┐                    ┌────────┴──────────┐  │
│  │  Nutrient    │                    │  Feeding          │  │
│  │  Target      │                    │  Modality         │  │
│  │              │                    │                   │  │
│  │  - id        │                    │  - id             │  │
│  │  - nutrient  │                    │  - type           │  │
│  │  - target    │                    │  - route          │  │
│  │  - unit      │                    │  - rate           │  │
│  │  - rationale │                    │  - duration       │  │
│  └──────────────┘                    └───────────────────┘  │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐ │
│  │ Complication │   │  Outcome     │   │  Condition       │ │
│  │              │   │              │   │  (Reference)     │ │
│  │  - id        │   │  - id        │   │                  │ │
│  │  - name      │   │  - type      │   │  - id            │ │
│  │  - severity  │   │  - value     │   │  - name          │ │
│  │  - resolved  │   │  - unit      │   │  - category      │ │
│  └──────────────┘   │  - timeframe │   │  - prevalence    │ │
│                     └──────────────┘   │  - nutrition_impact│ │
│                                        └──────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

#### Edge Types (Relationships)

```
┌──────────────────────────────────────────────────────────────────┐
│                      EDGE TYPES                                  │
│                                                                  │
│  Case-Centric Relationships:                                     │
│  ─────────────────────────                                        │
│  (CaseStudy) ──HAS_PATIENT──→ (PatientProfile)                   │
│  (CaseStudy) ──HAS_DIAGNOSIS──→ (Diagnosis)                      │
│  (CaseStudy) ──PRESENTS_WITH──→ (Symptom)                        │
│  (CaseStudy) ──HAS_GROWTH_STATUS──→ (GrowthStatus)               │
│  (CaseStudy) ──TREATED_WITH──→ (Medication)                      │
│  (CaseStudy) ──HAS_BIOMARKER──→ (Biomarker)                      │
│  (CaseStudy) ──RECEIVED_INTERVENTION──→ (NutritionIntervention)  │
│  (CaseStudy) ──USED_FEEDING──→ (FeedingModality)                  │
│  (CaseStudy) ──TARGETED──→ (NutrientTarget)                      │
│  (CaseStudy) ──HAD_COMPLICATION──→ (Complication)                │
│  (CaseStudy) ──RESULTED_IN──→ (Outcome)                          │
│                                                                  │
│  Cross-Case Reasoning Relationships:                             │
│  ──────────────────────────────                                   │
│  (Diagnosis) ──ASSOCIATED_WITH──→ (NutrientTarget)               │
│  (Diagnosis) ──COMMONLY_PRESENTS──→ (Symptom)                    │
│  (Diagnosis) ──AFFECTS_GROWTH──→ (GrowthStatus)                  │
│  (Medication) ──DEPLETES──→ (NutrientTarget)                     │
│  (Medication) ──INTERACTS_WITH──→ (NutrientTarget)               │
│  (Symptom) ──INDICATES_DEFICIENCY_OF──→ (NutrientTarget)         │
│  (Intervention) ──ADDRESSES──→ (Symptom)                         │
│  (Intervention) ──TARGETS──→ (NutrientTarget)                    │
│  (NutrientTarget) ──FOUND_IN──→ (FeedingModality)                │
│                                                                  │
│  Reference Relationships:                                        │
│  ─────────────────────                                            │
│  (Diagnosis) ──REFERENCES_GUIDELINE──→ (GuidelineChunk)          │
│  (Intervention) ──SUPPORTED_BY──→ (GuidelineChunk)               │
│  (NutrientTarget) ──DEFINED_BY──→ (DRITableRow)                  │
│  (Condition) ──HAS_REFERENCE_DRI──→ (DRITableRow)                │
│                                                                  │
│  Edge Properties:                                                │
│  ───────────────                                                 │
│  All edges can carry:                                            │
│  - confidence: float (0.0-1.0)                                   │
│  - source: str (case ID or guideline ID)                         │
│  - evidence_grade: str (strong, moderate, weak)                  │
│  - frequency: int (how often this relationship appears)          │
│  - date: str (when this relationship was observed)               │
└──────────────────────────────────────────────────────────────────┘
```

### 11.3 Graph Database Schema (Neo4j Cypher)

```cypher
-- Node constraints and indexes
CREATE CONSTRAINT case_id_unique FOR (c:CaseStudy) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT patient_id_unique FOR (p:PatientProfile) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT diagnosis_name_unique FOR (d:Diagnosis) REQUIRE d.name IS UNIQUE;
CREATE CONSTRAINT symptom_name_unique FOR (s:Symptom) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT nutrient_name_unique FOR (n:NutrientTarget) REQUIRE n.nutrient IS UNIQUE;
CREATE CONSTRAINT medication_name_unique FOR (m:Medication) REQUIRE m.name IS UNIQUE;

-- Full-text indexes for search
CREATE FULLTEXT INDEX case_search 
FOR (c:CaseStudy) ON EACH [c.description, c.keywords];

CREATE FULLTEXT INDEX diagnosis_search 
FOR (d:Diagnosis) ON EACH [d.name, d.category];

CREATE FULLTEXT INDEX symptom_search 
FOR (s:Symptom) ON EACH [s.name];

CREATE FULLTEXT INDEX intervention_search 
FOR (i:NutritionIntervention) ON EACH [i.type, i.description];
```

### 11.4 Case Study Ingestion Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│              CASE STUDY INGESTION PIPELINE                    │
│                                                              │
│  Raw Case Study (PDF / structured text)                      │
│  "A 3-year-old male with cystic fibrosis (diagnosed at       │
│   birth) presents with weight faltering. Weight-for-age      │
│   z-score: -2.5. Current intake: 90 kcal/kg/day. Started     │
│   on high-energy formula (1 kcal/mL) + pancreatic enzyme     │
│   replacement. After 3 months, weight gain of 0.8 kg,        │
│   z-score improved to -2.0."                                 │
│                            │                                  │
│                            ▼                                  │
│              ┌─────────────────────────────┐                 │
│              │  LLM Structured Extractor   │                 │
│              │  (gpt-4o with schema)       │                 │
│              │                             │                 │
│              │  Prompt: Extract entities   │                 │
│              │  and relationships from     │                 │
│              │  this case study following  │                 │
│              │  the CPNA graph schema.     │                 │
│              └──────────────┬──────────────┘                 │
│                             │                                │
│                             ▼                                │
│              ┌─────────────────────────────┐                 │
│              │  Validation Layer           │                 │
│              │  - Age range check (0-18)   │                 │
│              │  - Z-score validity          │                 │
│              │  - Nutrient unit validation │                 │
│              │  - Diagnosis code mapping   │                 │
│              │    (ICD-10 to CPNA ontology)│                 │
│              └──────────────┬──────────────┘                 │
│                             │                                │
│                             ▼                                │
│              ┌─────────────────────────────┐                 │
│              │  Normalization Layer        │                 │
│              │  - Age → months             │                 │
│              │  - Weight → kg              │                 │
│              │  - Nutrients → standard     │                 │
│              │    units (mg/day, kcal/kg)  │                 │
│              │  - Diagnosis → canonical    │                 │
│              │    name + ICD code           │                 │
│              └──────────────┬──────────────┘                 │
│                             │                                │
│                             ▼                                │
│              ┌─────────────────────────────┐                 │
│              │  Graph Construction         │                 │
│              │  - Create nodes             │                 │
│              │  - Create relationships     │                 │
│              │  - Link to reference nodes  │                 │
│              │    (DRI, guidelines)        │                 │
│              └──────────────┬──────────────┘                 │
│                             │                                │
│                             ▼                                │
│              ┌─────────────────────────────┐                 │
│              │  Quality Review Queue       │                 │
│              │  - Human-in-loop review     │                 │
│              │  - Flag uncertain extractions│                │
│              │  - Approve/reject/modify    │                 │
│              └─────────────────────────────┘                 │
└──────────────────────────────────────────────────────────────┘
```

### 11.5 Example: Case Study to Graph Transformation

**Input case study text:**
```
Case 47: A 14-month-old female with moderate cerebral palsy (GMFCS Level IV)
presented with feeding difficulties and poor weight gain. Birth weight was
2.8 kg (SGA). Current weight: 7.2 kg (WTZ -3.1), length: 72 cm (HTZ -2.5).
Feeding history: exclusively spoon-fed purees, frequent gagging, meal times
>45 minutes. Labs: albumin 3.2 g/dL (low-normal), prealbumin 12 mg/dL (low),
iron 45 mcg/dL (low). Intervention: NG tube initiated for supplemental feeds
(100 kcal/mL formula, 40 mL/hour overnight for 12 hours). Oral feeding therapy
started (2x/week). After 6 months: weight 8.9 kg (WTZ -2.3), albumin 3.8,
prealbumin 20, iron 80. NG tube weaned to 6 hours overnight.
```

**Extracted graph entities:**

```json
{
  "case_study": {
    "id": "CASE_047",
    "year": 2023,
    "source": "Pediatric Nutrition Case Compendium",
    "complexity": "high",
    "description": "14mo F with CP GMFCS IV, SGA, feeding difficulties, poor weight gain"
  },
  "patient": {
    "id": "PAT_047",
    "age_months": 14,
    "sex": "female",
    "gestational_age_weeks": 38,
    "birth_weight_kg": 2.8,
    "birth_status": "SGA",
    "current_weight_kg": 7.2,
    "current_length_cm": 72,
    "wtz": -3.1,
    "htz": -2.5,
    "bmi_z": -2.0
  },
  "diagnoses": [
    {"id": "DIAG_CP", "name": "Cerebral Palsy", "category": "neurological", "icd_code": "G80", "severity": "moderate", "gmfcs_level": "IV"}
  ],
  "symptoms": [
    {"id": "SYM_047_1", "name": "feeding_difficulties", "severity": "severe", "duration": "unknown"},
    {"id": "SYM_047_2", "name": "poor_weight_gain", "severity": "severe", "duration": "chronic"},
    {"id": "SYM_047_3", "name": "gagging", "severity": "moderate", "duration": "ongoing"},
    {"id": "SYM_047_4", "name": "prolonged_meal_times", "severity": "moderate", "duration": "ongoing"}
  ],
  "growth_status": {
    "id": "GS_047",
    "z_scores": {"wtz": -3.1, "htz": -2.5, "bmiz": -2.0},
    "velocity": "poor",
    "percentiles": {"weight": 3, "length": 5},
    "status": "severe_malnutrition"
  },
  "medications": [],
  "biomarkers": [
    {"id": "BM_047_1", "name": "albumin", "value": 3.2, "unit": "g/dL", "status": "low_normal", "normal_range": "3.5-5.5"},
    {"id": "BM_047_2", "name": "prealbumin", "value": 12, "unit": "mg/dL", "status": "low", "normal_range": "20-40"},
    {"id": "BM_047_3", "name": "iron", "value": 45, "unit": "mcg/dL", "status": "low", "normal_range": "50-120"}
  ],
  "nutrition_intervention": {
    "id": "INT_047",
    "type": "enteral_feeding_supplement",
    "description": "NG tube for supplemental feeds + oral feeding therapy",
    "duration": "6 months"
  },
  "feeding_modality": {
    "id": "FEED_047",
    "type": "NG_tube",
    "route": "nasogastric",
    "formula": "100 kcal/mL formula",
    "rate": "40 mL/hour",
    "duration": "12 hours overnight"
  },
  "nutrient_targets": [
    {"id": "NT_047_1", "nutrient": "energy", "target": "100 kcal/mL", "unit": "kcal/mL", "rationale": "catch_up_growth"},
    {"id": "NT_047_2", "nutrient": "protein", "target": "standard for age", "unit": "g/day", "rationale": "growth_support"}
  ],
  "outcomes": [
    {"id": "OUT_047_1", "type": "weight_gain", "value": 1.7, "unit": "kg", "timeframe": "6 months"},
    {"id": "OUT_047_2", "type": "wtz_improvement", "value": -2.3, "unit": "z_score", "timeframe": "6 months", "improved_from": -3.1},
    {"id": "OUT_047_3", "type": "biomarker_improvement", "details": "albumin 3.2→3.8, prealbumin 12→20, iron 45→80"},
    {"id": "OUT_047_4", "type": "feeding_modality_change", "details": "NG tube weaned from 12h to 6h overnight"}
  ],
  "complications": []
}
```

**Graph relationships created:**

```cypher
CREATE (case:CaseStudy {id: "CASE_047", ...})
CREATE (patient:PatientProfile {id: "PAT_047", ...})
CREATE (diagnosis:Diagnosis {id: "DIAG_CP", ...})
CREATE (symptom1:Symptom {id: "SYM_047_1", ...})
CREATE (symptom2:Symptom {id: "SYM_047_2", ...})
CREATE (symptom3:Symptom {id: "SYM_047_3", ...})
CREATE (symptom4:Symptom {id: "SYM_047_4", ...})
CREATE (growth:GrowthStatus {id: "GS_047", ...})
CREATE (biomarker1:Biomarker {id: "BM_047_1", ...})
CREATE (biomarker2:Biomarker {id: "BM_047_2", ...})
CREATE (biomarker3:Biomarker {id: "BM_047_3", ...})
CREATE (intervention:NutritionIntervention {id: "INT_047", ...})
CREATE (feeding:FeedingModality {id: "FEED_047", ...})
CREATE (outcome1:Outcome {id: "OUT_047_1", ...})
CREATE (outcome2:Outcome {id: "OUT_047_2", ...})
CREATE (outcome3:Outcome {id: "OUT_047_3", ...})
CREATE (outcome4:Outcome {id: "OUT_047_4", ...})

CREATE (case)-[:HAS_PATIENT]->(patient)
CREATE (case)-[:HAS_DIAGNOSIS]->(diagnosis)
CREATE (case)-[:PRESENTS_WITH]->(symptom1)
CREATE (case)-[:PRESENTS_WITH]->(symptom2)
CREATE (case)-[:PRESENTS_WITH]->(symptom3)
CREATE (case)-[:PRESENTS_WITH]->(symptom4)
CREATE (case)-[:HAS_GROWTH_STATUS]->(growth)
CREATE (case)-[:HAS_BIOMARKER]->(biomarker1)
CREATE (case)-[:HAS_BIOMARKER]->(biomarker2)
CREATE (case)-[:HAS_BIOMARKER]->(biomarker3)
CREATE (case)-[:RECEIVED_INTERVENTION]->(intervention)
CREATE (case)-[:USED_FEEDING]->(feeding)
CREATE (case)-[:RESULTED_IN]->(outcome1)
CREATE (case)-[:RESULTED_IN]->(outcome2)
CREATE (case)-[:RESULTED_IN]->(outcome3)
CREATE (case)-[:RESULTED_IN]->(outcome4)

-- Cross-case reasoning edges
CREATE (diagnosis)-[:ASSOCIATED_WITH]->(:NutrientTarget {nutrient: "energy"})
CREATE (diagnosis)-[:COMMONLY_PRESENTS]->(symptom2)
CREATE (diagnosis)-[:AFFECTS_GROWTH {severity: "severe"}]->(growth)
CREATE (symptom1)-[:INDICATES_DEFICIENCY_OF]->(:NutrientTarget {nutrient: "energy"})
CREATE (intervention)-[:ADDRESSES]->(symptom1)
CREATE (intervention)-[:ADDRESSES]->(symptom2)
CREATE (intervention)-[:TARGETS]->(:NutrientTarget {nutrient: "energy"})
```

### 11.6 Graph Query Patterns for Retrieval

#### Pattern 1: Similar Case Retrieval

```cypher
// Given a patient profile, find the top-5 most similar cases
MATCH (target_case:CaseStudy)-[:HAS_PATIENT]->(target_patient:PatientProfile)
WHERE target_patient.age_months = $age_months
  AND target_patient.sex = $sex
MATCH (target_case)-[:HAS_DIAGNOSIS]->(target_diag:Diagnosis)
WHERE target_diag.name IN $diagnoses

// Score similarity based on shared attributes
MATCH (candidate_case:CaseStudy)-[:HAS_PATIENT]->(candidate_patient:PatientProfile)
MATCH (candidate_case)-[:HAS_DIAGNOSIS]->(candidate_diag:Diagnosis)
MATCH (candidate_case)-[:PRESENTS_WITH]->(candidate_symptom:Symptom)

// Count shared features
WITH candidate_case, candidate_patient, candidate_diag,
     COUNT(DISTINCT candidate_symptom) as shared_symptoms,
     CASE WHEN candidate_diag.name IN $diagnoses THEN 3 ELSE 0 END as diagnosis_match,
     CASE WHEN abs(candidate_patient.age_months - $age_months) <= 6 THEN 2 ELSE 0 END as age_proximity,
     CASE WHEN candidate_patient.sex = $sex THEN 1 ELSE 0 END as sex_match

ORDER BY (diagnosis_match + age_proximity + sex_match + shared_symptoms) DESC
LIMIT 5

RETURN candidate_case, candidate_patient, candidate_diag, shared_symptoms,
       (diagnosis_match + age_proximity + sex_match + shared_symptoms) as similarity_score
```

#### Pattern 2: Condition-to-Intervention Path

```cypher
// Given a condition, what interventions have been used and what were outcomes?
MATCH (case:CaseStudy)-[:HAS_DIAGNOSIS]->(diag:Diagnosis {name: $condition})
MATCH (case)-[:RECEIVED_INTERVENTION]->(intervention:NutritionIntervention)
MATCH (case)-[:RESULTED_IN]->(outcome:Outcome)
WHERE outcome.type IN $outcome_types

RETURN intervention.type as intervention_type,
       intervention.description as intervention_detail,
       outcome.type as outcome_type,
       outcome.value as outcome_value,
       count(case) as case_count,
       avg(similarity_score) as avg_effectiveness

ORDER BY case_count DESC
```

#### Pattern 3: Drug-Nutrient Impact Path

```cypher
// Given a medication, what nutrients are at risk?
MATCH (med:Medication {name: $medication})-[:DEPLETES|INTERACTS_WITH]->(nutrient:NutrientTarget)
MATCH (nutrient)<-[:TARGETS]-(intervention:NutritionIntervention)<-[:RECEIVED_INTERVENTION]-(case:CaseStudy)

RETURN nutrient.nutrient as at_risk_nutrient,
       med.name as medication,
       count(DISTINCT case) as cases_affected,
       collect(DISTINCT intervention.type) as intervention_types
```

#### Pattern 4: Growth Status Reasoning

```cypher
// For patients with severe malnutrition (WTZ < -3), what interventions led to improvement?
MATCH (case:CaseStudy)-[:HAS_GROWTH_STATUS]->(growth:GrowthStatus)
WHERE growth.wtz <= -3.0
MATCH (case)-[:RECEIVED_INTERVENTION]->(intervention:NutritionIntervention)
MATCH (case)-[:RESULTED_IN]->(outcome:Outcome)
WHERE outcome.type = 'wtz_improvement' AND outcome.value > outcome.improved_from

RETURN intervention.type, intervention.description,
       outcome.value as final_wtz, outcome.improved_from as initial_wtz,
       outcome.value - outcome.improved_from as improvement,
       count(*) as frequency

ORDER BY improvement DESC
```

### 11.7 Knowledge Graph Retrieval Agent

```python
class KnowledgeGraphRetrievalAgent(BaseAgent):
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
    
    async def execute(self, input: AgentInput) -> AgentOutput:
        start = time.time()
        entities = input.entities or {}
        intent = input.intent
        
        results = {
            "graph_contexts": [],
            "case_analogs": [],
            "drug_nutrient_alerts": []
        }
        
        if intent in ["THERAPY", "RECOMMENDATION"]:
            # Similar case retrieval
            if entities.get("condition") and entities.get("age_months"):
                similar_cases = await self._find_similar_cases(entities)
                results["case_analogs"] = similar_cases[:3]
            
            # Condition-intervention-outcome paths
            if entities.get("condition"):
                intervention_paths = await self._get_intervention_paths(
                    entities["condition"]
                )
                results["graph_contexts"].extend(intervention_paths)
        
        if intent == "THERAPY" and entities.get("medications"):
            # Drug-nutrient interaction check
            for med in entities["medications"]:
                alerts = await self._check_drug_nutrient(med)
                results["drug_nutrient_alerts"].extend(alerts)
        
        if intent == "COMPARISON":
            # Compare case evidence for both entities
            entity_a = entities.get("entity_a")
            entity_b = entities.get("entity_b")
            if entity_a and entity_b:
                comparison_evidence = await self._get_comparison_evidence(
                    entity_a, entity_b
                )
                results["graph_contexts"].append(comparison_evidence)
        
        return AgentOutput(
            success=True,
            data=results,
            latency_ms=(time.time() - start) * 1000
        )
    
    async def _find_similar_cases(self, entities: dict) -> list[dict]:
        """Find top-5 similar cases based on patient profile."""
        query = """
        MATCH (case:CaseStudy)-[:HAS_PATIENT]->(patient:PatientProfile)
        MATCH (case)-[:HAS_DIAGNOSIS]->(diag:Diagnosis)
        MATCH (case)-[:PRESENTS_WITH]->(symptom:Symptom)
        WHERE diag.name = $condition
        WITH case, patient, diag, count(symptom) as symptom_count
        ORDER BY symptom_count DESC
        LIMIT 5
        RETURN case, patient, diag, symptom_count
        """
        # Execute and format...
        pass
    
    async def _get_intervention_paths(self, condition: str) -> list[dict]:
        """Get condition → intervention → outcome paths."""
        query = """
        MATCH (case:CaseStudy)-[:HAS_DIAGNOSIS]->(diag:Diagnosis {name: $condition})
        MATCH (case)-[:RECEIVED_INTERVENTION]->(intervention:NutritionIntervention)
        MATCH (case)-[:RESULTED_IN]->(outcome:Outcome)
        RETURN intervention, outcome, count(case) as frequency
        ORDER BY frequency DESC
        LIMIT 10
        """
        # Execute and format...
        pass
    
    async def _check_drug_nutrient(self, medication: str) -> list[dict]:
        """Check for drug-nutrient interactions."""
        query = """
        MATCH (med:Medication {name: $medication})-[:DEPLETES|INTERACTS_WITH]->(nutrient:NutrientTarget)
        RETURN med, nutrient
        """
        # Execute and format...
        pass
```

---

## 12. Graph + RAG Fusion Strategy

### 12.1 Why Fuse Graph and RAG Retrieval

| Retrieval Type | Answers | Limitation |
|---|---|---|
| Vector/BM25 (RAG) | "What do guidelines say about X?" | No structured reasoning across entities |
| Knowledge Graph | "What happened in similar cases?" | No narrative context, no guideline text |
| Fused | "What do guidelines say AND what happened in similar cases?" | Requires careful orchestration |

The fusion strategy treats graph retrieval as a **complementary evidence channel**, not a replacement for guideline-based RAG.

### 12.2 Fusion Architecture

```
                    ┌──────────────────────┐
                    │   Rewritten Query    │
                    │   + Extracted        │
                    │   Entities           │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
        ┌───────────────────┐  ┌───────────────────┐
        │  Hybrid RAG       │  │  Knowledge Graph  │
        │  Retrieval        │  │  Retrieval        │
        │                   │  │                   │
        │  Vector search    │  │  Similar case     │
        │  BM25 search      │  │  retrieval        │
        │  RRF merge        │  │  Path traversal   │
        │  Reranking        │  │  Pattern matching │
        │                   │  │                   │
        │  Output:          │  │  Output:          │
        │  7 text contexts  │  │  3 case analogs   │
        │  with citations   │  │  + graph paths    │
        └────────┬──────────┘  └────────┬──────────┘
                 │                      │
                 └──────────┬───────────┘
                            ▼
                ┌───────────────────────┐
                │  Evidence Merger      │
                │                       │
                │  Combines:            │
                │  - Guideline excerpts │
                │  - Textbook passages  │
                │  - Case analogs       │
                │  - Graph paths        │
                │  - DRI table rows     │
                │  - Drug-nutrient      │
                │    alerts             │
                │                       │
                │  Deduplicates by      │
                │  source_id            │
                │                       │
                │  Ranks by:            │
                │  1. Evidence grade    │
                │  2. Relevance score   │
                │  3. Recency           │
                │                       │
                │  Output: Unified      │
                │  evidence package     │
                └───────────┬───────────┘
                            ▼
                ┌───────────────────────┐
                │  Response Synthesis   │
                │  Agent                │
                └───────────────────────┘
```

### 12.3 Evidence Merger Logic

```python
class EvidenceMerger:
    """
    Merges RAG contexts, graph contexts, and structured data into
    a unified evidence package for the synthesis agent.
    """
    
    EVIDENCE_WEIGHTS = {
        "guideline": 1.0,       # Highest weight - prescriptive evidence
        "dri_table": 0.95,      # Authoritative reference values
        "clinical_reference": 0.8,
        "textbook": 0.7,
        "review_article": 0.6,
        "case_study": 0.4,      # Lower weight - descriptive, not prescriptive
        "drug_nutrient_table": 0.85,
        "food_composition": 0.9,
    }
    
    def merge(
        self,
        rag_contexts: list[dict],
        graph_contexts: list[dict],
        case_analogs: list[dict],
        nutrient_plan: dict | None,
        drug_alerts: list[dict],
    ) -> dict:
        """
        Produce a unified evidence package.
        
        Critical rule: Case analogs are NEVER used as the primary evidence
        for therapy recommendations. They provide supporting context only.
        """
        evidence_package = {
            "primary_evidence": [],    # Guidelines, DRI tables
            "supporting_evidence": [], # Textbooks, review articles
            "case_context": [],        # Similar cases (supporting only)
            "structured_data": {},     # DRI values, food composition
            "drug_alerts": [],
            "nutrient_plan": nutrient_plan,
        }
        
        # Process RAG contexts
        for ctx in rag_contexts:
            weight = self.EVIDENCE_WEIGHTS.get(ctx["source_type"], 0.3)
            item = {
                "content": ctx["passage_text"],
                "source_id": ctx["source_id"],
                "source_type": ctx["source_type"],
                "relevance_score": ctx["relevance_score"],
                "evidence_weight": weight,
            }
            
            if ctx["source_type"] in ["guideline", "dri_table", "drug_nutrient_table"]:
                evidence_package["primary_evidence"].append(item)
            else:
                evidence_package["supporting_evidence"].append(item)
        
        # Process graph contexts (path traversals)
        for graph_ctx in graph_contexts:
            evidence_package["supporting_evidence"].append({
                "content": graph_ctx["path_description"],
                "source_id": graph_ctx["source_case_ids"],
                "source_type": "graph_path",
                "evidence_weight": 0.35,
            })
        
        # Process case analogs
        for case in case_analogs:
            evidence_package["case_context"].append({
                "case_id": case["case_id"],
                "patient_summary": case["patient_summary"],
                "intervention": case["intervention"],
                "outcome": case["outcome"],
                "similarity_score": case["similarity_score"],
                "disclaimer": "This is a similar case, not a guideline recommendation.",
            })
        
        # Process drug alerts
        evidence_package["drug_alerts"] = drug_alerts
        
        # Sort primary evidence by weight * relevance
        evidence_package["primary_evidence"].sort(
            key=lambda x: x["evidence_weight"] * x["relevance_score"],
            reverse=True
        )
        
        return evidence_package
```

### 12.4 Case Analog Usage Rules

```python
CASE_ANALOG_RULES = """
When incorporating case analogs into responses:

1. NEVER present case outcomes as guidelines or recommendations.
   - Wrong: "In similar cases, NG tube feeding was used, so you should too."
   - Right: "In a similar case of a 14-month-old with CP and feeding difficulties,
     NG tube supplementation was associated with weight z-score improvement
     from -3.1 to -2.3 over 6 months. This is descriptive, not prescriptive."

2. ALWAYS include a disclaimer when referencing case analogs.

3. ALWAYS prioritize guideline-based evidence over case analogs for
   therapy recommendations.

4. CASE ANALOGS are for contextual reasoning and clinical intuition
   support, not for deterministic decision-making.

5. When case evidence conflicts with guideline evidence, follow guidelines.

6. Similarity score must be reported alongside any case analog
   so users can judge relevance.
"""
```

---

## 13. Deterministic Therapy Engine Design

### 13.1 Why Deterministic, Not Generative

Therapy-grade nutrition recommendations involve **calculations** that must be correct:

| Calculation | LLM Risk | Deterministic Solution |
|---|---|---|
| RDA lookup by age/sex | May hallucinate wrong values | Table lookup from DRI database |
| Catch-up growth formula | May misapply formula | Validated mathematical function |
| Condition-specific multiplier | May invent multipliers | Evidence-based multiplier table |
| Drug-nutrient flag | May miss interactions | Structured interaction table |
| Energy requirement (Schofield) | May compute incorrectly | Validated equation implementation |

**Principle**: LLMs synthesize text from evidence; they do not compute clinical values. All numerical therapy outputs come from the deterministic engine.

### 13.2 Therapy Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              DETERMINISTIC THERAPY ENGINE                     │
│                                                              │
│  Input: entities from Slot Filling Agent                     │
│  Required: age_months, sex, condition                        │
│  Optional: weight_kg, height_cm, current_intake, medications │
│                                                              │
│  ┌─────────────────┐                                        │
│  │ 1. Validation   │                                        │
│  │                 │                                        │
│  │ - Age range:    │                                        │
│  │   0-216 months  │                                        │
│  │ - Sex: M/F      │                                        │
│  │ - Condition:    │                                        │
│  │   valid code    │                                        │
│  └────────┬────────┘                                        │
│           │                                                  │
│  ┌────────▼────────┐                                        │
│  │ 2. DRI Lookup   │                                        │
│  │                 │                                        │
│  │ Query DRI table:│                                        │
│  │ SELECT * FROM   │                                        │
│  │ dietary_reference│                                       │
│  │ WHERE age_min   │                                        │
│  │ <= age_months   │                                        │
│  │ AND age_max     │                                        │
│  │ >= age_months   │                                        │
│  │ AND sex IN      │                                        │
│  │ (sex, 'both')   │                                        │
│  └────────┬────────┘                                        │
│           │                                                  │
│           │  Output: baseline nutrient requirements           │
│           │  {nutrient: {rda, ai, ul, ear, unit}}            │
│           │                                                  │
│  ┌────────▼────────────────────────────────┐                 │
│  │ 3. Condition-Specific Adjustment        │                 │
│  │                                         │                 │
│  │ For each nutrient with condition        │                 │
│  │ adjustment:                             │                 │
│  │   adjusted_value = baseline * multiplier│                 │
│  │                                         │                 │
│  │ Example:                                │                 │
│  │   CF → energy × 1.2-1.5                │                 │
│  │   CKD → protein restriction             │                 │
│  │   Nephrotic → protein × 1.2-1.5        │                 │
│  │   Burns → energy × 1.5-2.0             │                 │
│  └────────┬────────────────────────────────┘                 │
│           │                                                  │
│           │  Output: adjusted nutrient requirements           │
│           │                                                  │
│  ┌────────▼────────────────────────────────┐                 │
│  │ 4. Drug-Nutrient Interaction Check      │                 │
│  │                                         │                 │
│  │ If medications present:                  │                 │
│  │   For each medication:                  │                 │
│  │     Query interaction table             │                 │
│  │     Flag depleted/at-risk nutrients     │                 │
│  │     Generate monitoring alerts          │                 │
│  └────────┬────────────────────────────────┘                 │
│           │                                                  │
│           │  Output: drug_nutrient_alerts                     │
│           │                                                  │
│  ┌────────▼────────┐                                        │
│  │ 5. Food Source  │                                        │
│  │   Matching      │                                        │
│  │                 │                                        │
│  │ For each target  │                                        │
│  │ nutrient:       │                                        │
│  │   Query food     │                                        │
│  │   composition    │                                        │
│  │   table for      │                                        │
│  │   top sources    │                                        │
│  │   (age-appropriate│                                       │
│  │    filtering)    │                                        │
│  └────────┬────────┘                                        │
│           │                                                  │
│           │  Output: food_recommendations                     │
│           │  [{nutrient, food, amount, nutrient_value}]      │
│           │                                                  │
│  ┌────────▼────────┐                                        │
│  │ 6. Catch-Up     │                                        │
│  │   Growth Calc   │                                        │
│  │   (if needed)   │                                        │
│  │                 │                                        │
│  │ If WTZ < -2 or  │                                        │
│  │ HTZ < -2:       │                                        │
│  │   k = 1 + (ideal_z│                                     │
│  │        - current_z)│                                     │
│  │   kcal_needed =  │                                        │
│  │   k × RDA × weight│                                      │
│  │                 │                                        │
│  │ ideal_z = 0 (median)│                                    │
│  └────────┬────────┘                                        │
│           │                                                  │
│           │  Output: catch_up_growth_plan                     │
│           │                                                  │
│  ┌────────▼────────┐                                        │
│  │ 7. Meal Plan    │                                        │
│  │   Generation    │                                        │
│  │   (Optional)    │                                        │
│  │                 │                                        │
│  │ If requested and│                                        │
│  │ sufficient data:│                                        │
│  │   Generate      │                                        │
│  │   structured    │                                        │
│  │   meal plan     │                                        │
│  │   meeting       │                                        │
│  │   targets       │                                        │
│  └────────┬────────┘                                        │
│           │                                                  │
│           ▼                                                  │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  Therapy Output Package                                  ││
│  │                                                          ││
│  │  {                                                         ││
│  │    "patient_summary": {...},                              ││
│  │    "nutrient_requirements": {                             ││
│  │      "energy_kcal": {"rda": 1000, "adjusted": 1200,       ││
│  │                       "unit": "kcal/day",                 ││
│  │                       "source": "IOM 2023",               ││
│  │                       "adjustment_reason": "CF × 1.2"},   ││
│  │      "protein_g": {"rda": 13, "adjusted": 16, ...},       ││
│  │      ...                                                  ││
│  │    },                                                     ││
│  │    "drug_nutrient_alerts": [...],                         ││
│  │    "food_recommendations": [...],                         ││
│  │    "catch_up_growth_plan": {... | null},                  ││
│  │    "meal_plan": {... | null},                             ││
│  │    "calculation_sources": ["DRI Table v2023",             ││
│  │                            "ESPGHAN CF Guidelines 2022"] ││
│  │  }                                                        ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### 13.3 Deterministic Engine Implementation

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class NutrientRequirement:
    nutrient: str
    rda: float | None
    ai: float | None
    ul: float | None
    ear: float | None
    adjusted_value: float | None
    unit: str
    source: str
    adjustment_reason: str | None

class DeterministicNutrientEngine:
    def __init__(self, dri_repository, food_repository, interaction_repository):
        self.dri = dri_repository
        self.food = food_repository
        self.interactions = interaction_repository
    
    def calculate_therapy_plan(self, entities: dict) -> dict:
        """
        Full deterministic therapy calculation.
        
        All calculations are validated against reference tables.
        No LLM generation occurs in this pipeline.
        """
        # 1. Validate inputs
        self._validate_inputs(entities)
        
        # 2. Baseline DRI lookup
        baseline_requirements = self._lookup_dri(
            age_months=entities["age_months"],
            sex=entities["sex"]
        )
        
        # 3. Condition-specific adjustments
        condition = entities.get("condition")
        adjusted_requirements = {}
        
        for nutrient, req in baseline_requirements.items():
            adjusted = self._apply_condition_adjustment(
                req, condition, entities
            )
            adjusted_requirements[nutrient] = adjusted
        
        # 4. Drug-nutrient interaction check
        drug_alerts = []
        if entities.get("medications"):
            for med in entities["medications"]:
                alerts = self.interactions.check(med)
                drug_alerts.extend(alerts)
        
        # 5. Food source matching
        food_recommendations = []
        for nutrient, req in adjusted_requirements.items():
            if req["adjusted_value"] is not None:
                foods = self.food.find_top_sources(
                    nutrient=nutrient,
                    target_value=req["adjusted_value"],
                    age_appropriate=True,
                    age_months=entities["age_months"]
                )
                food_recommendations.extend(foods[:5])  # Top 5 per nutrient
        
        # 6. Catch-up growth calculation (if applicable)
        catch_up_plan = None
        if entities.get("wtz") and entities["wtz"] < -2.0:
            catch_up_plan = self._calculate_catch_up_growth(
                current_wtz=entities["wtz"],
                weight_kg=entities.get("weight_kg"),
                adjusted_energy=adjusted_requirements.get("energy"),
            )
        
        # 7. Build output package
        return {
            "patient_summary": {
                "age_months": entities["age_months"],
                "sex": entities["sex"],
                "condition": condition,
                "weight_kg": entities.get("weight_kg"),
                "wtz": entities.get("wtz"),
            },
            "nutrient_requirements": adjusted_requirements,
            "drug_nutrient_alerts": drug_alerts,
            "food_recommendations": food_recommendations,
            "catch_up_growth_plan": catch_up_plan,
            "calculation_sources": [
                "DRI Table (IOM/Dietary Guidelines)",
                f"Condition adjustments: {condition} reference" if condition else None
            ],
        }
    
    def _validate_inputs(self, entities: dict) -> None:
        """Validate all required therapy inputs."""
        if not entities.get("age_months"):
            raise ValidationError("age_months is required for therapy calculation")
        if entities["age_months"] < 0 or entities["age_months"] > 216:
            raise ValidationError("Age must be within pediatric range (0-18 years)")
        if entities.get("sex") not in ["male", "female"]:
            raise ValidationError("sex must be 'male' or 'female'")
    
    def _lookup_dri(self, age_months: int, sex: str) -> dict:
        """Query DRI table for baseline requirements."""
        query = """
        SELECT nutrient, rda, ai, ul, ear, unit, source
        FROM dietary_reference_intakes
        WHERE age_min_months <= :age
          AND age_max_months >= :age
          AND sex IN (:sex, 'both')
        """
        rows = self.dri.execute(query, age=age_months, sex=sex)
        
        requirements = {}
        for row in rows:
            requirements[row["nutrient"]] = {
                "rda": row["rda"],
                "ai": row["ai"],
                "ul": row["ul"],
                "ear": row["ear"],
                "unit": row["unit"],
                "source": row["source"],
                "adjusted_value": row["rda"] or row["ai"],  # Prefer RDA, fall back to AI
                "adjustment_reason": None,
            }
        return requirements
    
    def _apply_condition_adjustment(
        self, requirement: dict, condition: str | None, entities: dict
    ) -> dict:
        """Apply condition-specific nutrient adjustments."""
        if not condition:
            return requirement
        
        adjustment = self.dri.get_condition_adjustment(
            nutrient=requirement["nutrient"],
            condition=condition
        )
        
        if adjustment and adjustment.multiplier != 1.0:
            baseline = requirement["adjusted_value"]
            requirement["adjusted_value"] = round(
                baseline * adjustment.multiplier, 1
            )
            requirement["adjustment_reason"] = (
                f"{condition}: {adjustment.note} "
                f"(multiplier: {adjustment.multiplier})"
            )
        
        return requirement
    
    def _calculate_catch_up_growth(
        self,
        current_wtz: float,
        weight_kg: float | None,
        adjusted_energy: dict | None,
    ) -> dict | None:
        """
        Calculate catch-up growth energy requirements.
        
        Formula:
          k = 1 + (ideal_z - current_z) / ideal_z  (simplified)
          kcal_needed = k × RDA_for_weight × actual_weight
        
        Reference: ESPGHAN catch-up growth guidelines
        """
        if not weight_kg or not adjusted_energy:
            return None
        
        ideal_z = 0.0  # Population median
        k = 1.0 + (ideal_z - current_wtz)  # Simplified k factor
        
        baseline_energy = adjusted_energy["adjusted_value"]
        catch_up_energy = round(k * baseline_energy, 0)
        
        return {
            "current_wtz": current_wtz,
            "target_wtz": 0.0,
            "k_factor": round(k, 2),
            "baseline_energy_kcal": baseline_energy,
            "catch_up_energy_kcal": int(catch_up_energy),
            "formula": "k = 1 + (ideal_z - current_z); kcal = k × RDA × weight",
            "reference": "ESPGHAN Catch-Up Growth Guidelines",
        }
```

### 13.4 Therapy Gatekeeper Agent

```python
class TherapyGatekeeperAgent(BaseAgent):
    """
    Determines if a therapy query has sufficient data to proceed.
    
    This is the critical safety component that prevents under-specified
    therapy recommendations.
    """
    
    REQUIRED_SLOTS_THERAPY = ["age_months", "sex", "condition"]
    OPTIONAL_SLOTS = ["weight_kg", "height_cm", "wtz", "htz", 
                      "current_intake", "medications", "biomarkers"]
    
    MIN_CONFIDENCE = 0.65
    
    async def execute(self, input: AgentInput) -> AgentOutput:
        intent = input.intent
        confidence = input.confidence or 0.0
        entities = input.entities or {}
        pending_slots = input.pending_slots or []
        
        # Check 1: Is this actually a therapy query?
        if intent != "THERAPY":
            return AgentOutput(
                success=True,
                data={"gate_decision": "NOT_THERAPY"}
            )
        
        # Check 2: Confidence threshold
        if confidence < self.MIN_CONFIDENCE:
            return AgentOutput(
                success=True,
                data={
                    "gate_decision": "LOW_CONFIDENCE",
                    "action": "downgrade_to_recommendation",
                    "reason": f"Intent confidence {confidence:.2f} below threshold {self.MIN_CONFIDENCE}"
                }
            )
        
        # Check 3: Required slots
        missing_required = [
            s for s in self.REQUIRED_SLOTS_THERAPY
            if s not in entities
        ]
        
        if missing_required:
            return AgentOutput(
                success=True,
                data={
                    "gate_decision": "MISSING_REQUIRED_SLOTS",
                    "missing_slots": missing_required,
                    "action": "prompt_for_slots",
                    "prompt": self._generate_slot_prompt(missing_required)
                }
            )
        
        # Check 4: Age validation
        age = entities.get("age_months", 0)
        if age < 0 or age > 216:
            return AgentOutput(
                success=True,
                data={
                    "gate_decision": "INVALID_AGE",
                    "action": "reject",
                    "reason": "Age outside pediatric range (0-18 years)"
                }
            )
        
        # All checks passed
        return AgentOutput(
            success=True,
            data={
                "gate_decision": "PASS",
                "action": "proceed_to_therapy_engine"
            }
        )
    
    def _generate_slot_prompt(self, missing_slots: list[str]) -> str:
        """Generate a user-facing prompt for missing slots."""
        prompts = {
            "age_months": "To provide therapy-grade recommendations, I need to know the patient's age. Could you provide the age in months?",
            "sex": "To look up the correct dietary reference intakes, please specify the patient's sex (male/female).",
            "condition": "What is the patient's diagnosis or clinical condition? (e.g., cystic fibrosis, CKD, failure to thrive)",
        }
        return prompts.get(missing_slots[0], "I need additional information to proceed with therapy-grade recommendations.")
```

---

## 14. Recommendation Workflow Design

### 14.1 Purpose

The recommendation pipeline provides **condition-aware general guidance** without claiming personalization. It sits between therapy (individualized) and general (factual) in specificity.

### 14.2 Workflow

```
User Query: "What are the nutrition recommendations for children with autism?"
                    │
                    ▼
        ┌───────────────────────┐
        │  Intent: RECOMMENDATION│
        │  Confidence: 0.92     │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Query Rewriting      │
        │  "autism spectrum     │
        │   disorder pediatric  │
        │   nutrition guidelines │
        │   dietary              │
        │   recommendations"    │
        └───────────┬───────────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
┌──────────────────┐ ┌──────────────────┐
│  Hybrid RAG      │ │  Knowledge Graph │
│  Retrieval       │ │  Retrieval       │
│                  │ │                  │
│  Retrieves:      │ │  Retrieves:      │
│  - Guidelines    │ │  - Condition     │
│    for ASD       │ │    intervention  │
│  - Review papers │ │    paths         │
│  - Textbook      │ │  - Case evidence │
│    chapters      │ │    for ASD       │
└────────┬─────────┘ └────────┬─────────┘
         │                    │
         └─────────┬──────────┘
                   ▼
        ┌───────────────────────┐
        │  Deterministic DRI    │
        │  Preview              │
        │                       │
        │  Shows standard DRI   │
        │  values for relevant  │
        │  age ranges (without  │
        │  patient-specific     │
        │  adjustment)          │
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │  Response Synthesis   │
        │                       │
        │  Generates:           │
        │  - Condition overview │
        │  - Key nutrition      │
        │    concerns           │
        │  - Guideline-based    │
        │    recommendations   │
        │  - Nutrient DRI       │
        │    preview            │
        │  - Value proposition  │
        │    for therapy        │
        │    (if applicable)    │
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │  Output with          │
        │  disclaimer:          │
        │  "For individualized  │
        │  recommendations,     │
        │  please use the       │
        │  therapy workflow     │
        │  with patient details"│
        └───────────────────────┘
```

### 14.3 DRI Preview Logic

```python
def generate_dri_preview(entities: dict, dri_repository) -> dict:
    """
    Generate a DRI preview for recommendation responses.
    
    This shows standard DRI values for the identified age range
    WITHOUT condition-specific adjustments (those require therapy).
    
    Purpose: Show the user what's available in therapy mode
    without pretending personalization.
    """
    age_months = entities.get("age_months")
    sex = entities.get("sex")
    
    if not age_months or not sex:
        # Show DRI ranges for common age groups
        return {
            "preview_type": "age_ranges",
            "ranges": [
                {"label": "Infant (0-6 mo)", "energy_kcal": "500-600", "protein_g": "9.1"},
                {"label": "Infant (7-12 mo)", "energy_kcal": "700-800", "protein_g": "11"},
                {"label": "Toddler (1-3 y)", "energy_kcal": "1000-1400", "protein_g": "13"},
                {"label": "Child (4-8 y)", "energy_kcal": "1200-1800", "protein_g": "19"},
            ],
            "note": "Specific values depend on age and sex. Use therapy mode for precise values."
        }
    
    # Exact DRI lookup (no condition adjustment)
    dri_values = dri_repository.lookup(age_months, sex)
    
    return {
        "preview_type": "specific",
        "age_months": age_months,
        "sex": sex,
        "nutrients": {
            nutrient: {
                "rda": req.rda,
                "ai": req.ai,
                "ul": req.ul,
                "unit": req.unit,
            }
            for nutrient, req in dri_values.items()
        },
        "note": (
            "These are standard Dietary Reference Intakes. "
            "Condition-specific adjustments are available in therapy mode."
        )
    }
```

### 14.4 Response Template for Recommendation

```python
RECOMMENDATION_RESPONSE_TEMPLATE = """
# Nutrition Guidance for {condition}

## Overview
{condition_overview}

## Key Nutrition Concerns
{key_concerns}

## Guideline-Based Recommendations
{guideline_recommendations}

## Nutrient Reference Preview (Standard Values)
{dri_preview}

## Common Interventions from Similar Cases
{case_context}  [Labeled as descriptive, not prescriptive]

---
⚠️ **Disclaimer**: This is general guidance. For individualized,
patient-specific nutrition therapy, please use the therapy workflow
with patient details (age, sex, weight, diagnosis, current intake).
"""
```

---

## 15. Comparison Workflow Design

### 15.1 Comparison Type Taxonomy

```
Comparison Types:
├── FOOD_VS_FOOD
│   "Breast milk vs formula for iron content"
│   "Almond milk vs cow milk for toddlers"
│
├── NUTRIENT_VS_NUTRIENT
│   "Heme iron vs non-heme iron absorption"
│   "Vitamin D2 vs D3 supplementation"
│
├── DIET_PATTERN_VS_DIET_PATTERN
│   "Ketogenic diet vs modified Atkins for epilepsy"
│   "Mediterranean vs DASH for pediatric hypertension"
│
└── CLINICAL_STRATEGY_VS_CLINICAL_STRATEGY
    "NG tube vs G-tube for cerebral palsy feeding"
    "Oral supplementation vs enteral feeding for FTT"
```

### 15.2 Comparison Pipeline

```
User Query: "Compare NG tube vs G-tube for feeding in cerebral palsy"
                    │
                    ▼
        ┌───────────────────────┐
        │  Intent: COMPARISON   │
        │  Entities:            │
        │    entity_a: "NG tube"│
        │    entity_b: "G-tube"│
        │    context: "CP"      │
        │    comparison_type:   │
        │    CLINICAL_STRATEGY  │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Comparison Template  │
        │  Router               │
        │                       │
        │  Selects template     │
        │  based on type:       │
        │  CLINICAL_STRATEGY →  │
        │  clinical_comparison  │
        │  template             │
        └───────────┬───────────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
┌──────────────────┐ ┌──────────────────┐
│  Hybrid RAG for  │ │  Knowledge Graph │
│  entity_a +      │ │  for both        │
│  entity_b        │ │  entities        │
└────────┬─────────┘ └────────┬─────────┘
         │                    │
         └─────────┬──────────┘
                   ▼
        ┌───────────────────────┐
        │  Comparison Data      │
        │  Assembly             │
        │                       │
        │  Structured:          │
        │  {                    │
        │   "entity_a": {...},  │
        │   "entity_b": {...},  │
        │   "dimensions": [     │
        │     "efficacy",       │
        │     "complications",  │
        │     "duration",       │
        │     "reversibility",  │
        │     "quality_of_life" │
        │   ],                  │
        │   "evidence": {       │
        │     "a": [...],       │
        │     "b": [...],       │
        │   }                   │
        │  }                    │
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │  Response Synthesis   │
        │                       │
        │  Generates structured │
        │  comparison with      │
        │  evidence for each    │
        │  dimension            │
        └───────────────────────┘
```

### 15.3 Comparison Template Schema

```python
class ComparisonTemplate(BaseModel):
    comparison_type: str
    entity_a: dict
    entity_b: dict
    dimensions: list[str]  # Comparison dimensions vary by type
    
    # Templates for each comparison type
    TEMPLATES = {
        "FOOD_VS_FOOD": {
            "dimensions": [
                "nutrient_density", "bioavailability", "allergen_profile",
                "age_appropriateness", "preparation", "cost"
            ]
        },
        "NUTRIENT_VS_NUTRIENT": {
            "dimensions": [
                "absorption_rate", "food_sources", "deficiency_symptoms",
                "toxicity_risk", "supplementation_form", "interactions"
            ]
        },
        "DIET_PATTERN_VS_DIET_PATTERN": {
            "dimensions": [
                "efficacy", "safety", "adherence", "nutrient_adequacy",
                "growth_impact", "evidence_quality"
            ]
        },
        "CLINICAL_STRATEGY_VS_CLINICAL_STRATEGY": {
            "dimensions": [
                "efficacy", "complications", "duration", "reversibility",
                "quality_of_life", "caregiver_burden", "evidence_quality"
            ]
        }
    }
```

### 15.4 Comparison Data Assembly

```python
class ComparisonTemplateRouter:
    def route(self, entities: dict) -> dict:
        entity_a = entities.get("entity_a")
        entity_b = entities.get("entity_b")
        context = entities.get("context")
        comparison_type = self._classify_comparison_type(entity_a, entity_b)
        
        template = ComparisonTemplate.TEMPLATES[comparison_type]
        
        return {
            "comparison_type": comparison_type,
            "entity_a": self._lookup_entity(entity_a, context),
            "entity_b": self._lookup_entity(entity_b, context),
            "dimensions": template["dimensions"],
            "template": template,
        }
    
    def _classify_comparison_type(self, a: str, b: str) -> str:
        """Classify comparison type based on entity lookup."""
        a_type = self._entity_type(a)
        b_type = self._entity_type(b)
        
        if a_type == "food" and b_type == "food":
            return "FOOD_VS_FOOD"
        elif a_type == "nutrient" and b_type == "nutrient":
            return "NUTRIENT_VS_NUTRIENT"
        elif a_type == "diet_pattern" and b_type == "diet_pattern":
            return "DIET_PATTERN_VS_DIET_PATTERN"
        elif a_type == "clinical_strategy" and b_type == "clinical_strategy":
            return "CLINICAL_STRATEGY_VS_CLINICAL_STRATEGY"
        else:
            return "GENERAL"
    
    def _lookup_entity(self, entity: str, context: str | None) -> dict:
        """Look up entity in food composition table, knowledge graph, etc."""
        # Check food composition table
        food = self.food_repository.find(entity)
        if food:
            return {"type": "food", **food}
        
        # Check knowledge graph
        graph_entity = self.graph_repository.find(entity, context)
        if graph_entity:
            return graph_entity
        
        # Fallback: general text retrieval
        return {"type": "unknown", "name": entity}
```

---

## 16. General Workflow Design

### 16.1 Purpose

Handles educational, factual nutrition queries that don't require patient-specific data or condition-aware guidance.

### 16.2 Workflow

```
User Query: "What are good sources of iron for toddlers?"
                    │
                    ▼
        ┌───────────────────────┐
        │  Intent: GENERAL      │
        │  Confidence: 0.95     │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Query Rewriting      │
        │  "iron rich foods     │
        │   toddler appropriate │
        │   dietary sources"    │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Hybrid RAG Retrieval │
        │                       │
        │  Retrieves:           │
        │  - Textbook chapters  │
        │  - Educational        │
        │    resources          │
        │  - Food composition   │
        │    data               │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Structured Food      │
        │  Query                │
        │                       │
        │  SELECT food_name,    │
        │  nutrients->'iron_mg' │
        │  FROM food_composition│
        │  WHERE food_category  │
        │  IN ('protein',       │
        │  'cereal', 'vegetable')│
        │  ORDER BY iron DESC   │
        │  LIMIT 10             │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Response Synthesis   │
        │                       │
        │  Generates factual    │
        │  response with:       │
        │  - List of iron-rich  │
        │    foods              │
        │  - Iron content per   │
        │    serving            │
        │  - Bioavailability    │
        │    notes              │
        │  - Age-appropriate    │
        │    preparation tips   │
        └───────────────────────┘
```

### 16.3 General Response Characteristics

- **No disclaimers needed** (unless query touches on therapy territory)
- **Factual, educational tone**
- **Structured data integration** (food composition tables)
- **No patient-specific calculations**
- **Citations for factual claims**

---

## 17. Safety and Downgrade Logic

### 17.1 Safety Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SAFETY LAYER                                 │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  PRE-PROCESSING SAFETY CHECKS                             │  │
│  │                                                           │  │
│  │  1. Age range validation (reject if >18 years)            │  │
│  │  2. Query safety scanning (detect self-harm, abuse etc.) │  │
│  │  3. Confidence threshold enforcement                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  THERAPIE GATEKEEPING                                     │  │
│  │                                                           │  │
│  │  1. Required slot validation                              │  │
│  │  2. Missing slot prompting (not fabrication)              │  │
│  │  3. Confidence-based downgrade                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  RESPONSE SAFETY                                          │  │
│  │                                                           │  │
│  │  1. Disclaimer injection based on intent type             │  │
│  │  2. Case analog disclaimers                               │  │
│  │  3. Citation enforcement (every claim cited)             │  │
│  │  4. No medication changes suggested                       │  │
│  │  5. No diagnosis provided                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  POST-PROCESSING SAFETY CHECKS                            │  │
│  │                                                           │  │
│  │  1. Factuality check against retrieved evidence           │  │
│  │  2. Numerical value validation (match DRI tables)        │  │
│  │  3. Safety phrase detection (flag "should", "must",      │  │
│  │     "diagnosed with")                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 17.2 Downgrade Decision Tree

```
                                    ┌──────────────┐
                                    │ User Query   │
                                    └──────┬───────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │ DistilBERT Classification│
                              └──────────┬──────────────┘
                                         │
                              ┌──────────┴──────────────┐
                              │                         │
                        confidence                  confidence
                        >= 0.85                     < 0.85
                              │                         │
                              ▼                         ▼
                    ┌─────────────────┐    ┌─────────────────────────┐
                    │ Use classified  │    │ Downgrade to next       │
                    │ intent          │    │ safer intent            │
                    └─────────────────┘    └─────────────────────────┘
                                                   │
                                    ┌──────────────┴──────────────┐
                                    │                              │
                              THERAPY <0.85              RECOMMENDATION <0.85
                                    │                              │
                                    ▼                              ▼
                              RECOMMENDATION                GENERAL
                                    │                              │
                                    ▼                              ▼
                              (if therapy gate                (if still
                              fails again)                     low confidence)
                                    │                              │
                                    ▼                              ▼
                              RECOMMENDATION                SAFE FALLBACK:
                              with disclaimer               "I'm not sure I
                                                            understand. Could
                                                            you rephrase?"
```

### 17.3 Disclaimer Injection Rules

```python
DISCLAIMER_RULES = {
    "THERAPY": {
        "required": True,
        "text": (
            "⚠️ This therapy-grade recommendation is based on the information provided "
            "and reference guidelines. It is advisory in nature and should be reviewed "
            "by a qualified pediatric dietitian or physician before implementation."
        ),
        "always_show": True
    },
    "RECOMMENDATION": {
        "required": True,
        "text": (
            "This is general guidance for the specified condition. "
            "For individualized patient-specific recommendations, please use the "
            "therapy workflow with complete patient details."
        ),
        "always_show": True
    },
    "COMPARISON": {
        "required": False,
        "text": (
            "This comparison is based on available evidence and should not "
            "replace clinical judgment. Individual patient factors may influence the "
            "appropriate choice."
        ),
        "always_show": False  # Show only for clinical strategy comparisons
    },
    "GENERAL": {
        "required": False,
        "text": None,
        "always_show": False
    }
}
```

### 17.4 Post-Processing Safety Validator

```python
class ResponseSafetyValidator:
    """
    Validates synthesized responses before they are returned to users.
    """
    
    FORBIDDEN_PATTERNS = [
        r"(?i)you should (diagnose|prescribe|medicate)",
        r"(?i)this confirms (a|the) diagnosis",
        r"(?i)stop (the |this )?(medication|drug|treatment)",
        r"(?i)I recommend (stopping|changing|starting) \w+ (medication|drug)",
    ]
    
    NUMERICAL_VALIDATION = {
        "rda_values": "cross_reference_with_dri_table",
        "calorie_targets": "verify_against_schofield_equation",
        "protein_requirements": "check_dri_range",
    }
    
    async def validate(self, response: str, evidence_package: dict) -> ValidationResult:
        issues = []
        
        # 1. Check forbidden patterns
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, response):
                issues.append(f"Forbidden pattern detected: {pattern}")
        
        # 2. Validate numerical claims against evidence
        numerical_claims = self._extract_numerical_claims(response)
        for claim in numerical_claims:
            if not self._validate_numerical_claim(claim, evidence_package):
                issues.append(f"Unvalidated numerical claim: {claim}")
        
        # 3. Verify all claims have citations
        uncited_claims = self._check_citation_coverage(response, evidence_package)
        if uncited_claims:
            issues.append(f"Uncited claims detected: {uncited_claims}")
        
        # 4. Check disclaimer presence
        if not self._has_required_disclaimer(response, evidence_package):
            issues.append("Required disclaimer missing")
        
        return ValidationResult(
            passed=len(issues) == 0,
            issues=issues
        )
```

---

## 18. Data Flow and Sequence Flows

### 18.1 End-to-End Therapy Query Sequence

```
┌──────┐  ┌──────────┐  ┌─────────────┐  ┌───────┐  ┌────────┐  ┌───────┐  ┌───────┐  ┌───────┐
│Client│  │API Gateway│  │Orchestrator │  │State  │  │Intent  │  │Rewrite│  │Slot   │  │Therapy│
│      │  │          │  │             │  │Manager│  │Agent   │  │Agent  │  │Fill   │  │Gate   │
└──┬───┘  └─────┬────┘  └──────┬──────┘  └───┬───┘  └───┬────┘  └───┬───┘  └───┬───┘  └───┬───┘
   │            │              │              │          │            │          │          │
   │ POST /query│              │              │          │            │          │          │
   │───────────>│              │              │          │            │          │          │
   │            │              │              │          │            │          │          │
   │            │ forward      │              │          │            │          │          │
   │            │─────────────>│              │          │            │          │          │
   │            │              │              │          │            │          │          │
   │            │              │ get_state    │          │            │          │          │
   │            │              │─────────────>│          │            │          │          │
   │            │              │              │          │            │          │          │
   │            │              │ state        │          │            │          │          │
   │            │              │<─────────────│          │            │          │          │
   │            │              │              │          │            │          │          │
   │            │              │ classify(query)        │            │          │          │
   │            │              │─────────────>│          │            │          │          │
   │            │              │              │          │            │          │          │
   │            │              │ intent, conf │          │            │          │          │
   │            │              │<─────────────│          │            │          │          │
   │            │              │              │          │            │          │          │
   │            │              │ rewrite(query, state)  │          │          │          │
   │            │              │───────────────────────>│          │          │          │
   │            │              │              │          │            │          │          │
   │            │              │ rewritten_query        │          │          │          │
   │            │              │<───────────────────────│          │          │          │
   │            │              │              │          │            │          │          │
   │            │              │ extract_slots(query, rewritten)    │          │          │
   │            │              │───────────────────────────────────>│          │          │
   │            │              │              │          │            │          │          │
   │            │              │ entities, pending_slots            │          │          │
   │            │              │<───────────────────────────────────│          │          │
   │            │              │              │          │            │          │          │
   │            │              │ gate_check(intent, entities, slots)           │          │
   │            │              │──────────────────────────────────────────────>│          │
   │            │              │              │          │            │          │          │
   │            │              │ gate_decision = PASS                           │          │
   │            │              │<──────────────────────────────────────────────│          │
   │            │              │              │          │            │          │          │
   │            │              │ [Continue to Retrieval → KG → Deterministic]  │          │
   │            │              │              │          │            │          │          │
```

### 18.2 Multi-Turn Slot Filling Sequence

```
Turn 1:
User: "I need therapy for a patient with failure to thrive"

Orchestrator → Intent Agent: THERAPY (0.91)
Orchestrator → Slot Filling: entities={condition: "FTT"}, pending_slots=["age_months", "sex"]
Orchestrator → Gatekeeper: MISSING_REQUIRED_SLOTS
Orchestrator → Client: "To provide therapy-grade recommendations, I need to know the patient's age. Could you provide the age in months?"

Turn 2:
User: "The patient is 18 months old"

Orchestrator → State Manager: inherit_context(turn_1)
Orchestrator → Intent Agent: GENERAL (0.72) [but inherited context says THERAPY]
Orchestrator → Intent Agent (with context override): THERAPY (0.88)
Orchestrator → Slot Filling: entities={age_months: 18}, merged with prior {condition: "FTT"}
Orchestrator → State Manager: resolve_slot("age_months", 18)
Orchestrator → Gatekeeper: MISSING_REQUIRED_SLOTS, missing=["sex"]
Orchestrator → Client: "To look up the correct dietary reference intakes, please specify the patient's sex (male/female)."

Turn 3:
User: "Male"

Orchestrator → State Manager: inherit_context(turn_2)
Orchestrator → Intent Agent (with context): THERAPY (0.95)
Orchestrator → Slot Filling: entities={sex: "male"}
Orchestrator → State Manager: resolve_slot("sex", "male")
Orchestrator → Gatekeeper: PASS
Orchestrator → [Full therapy pipeline executes]
Orchestrator → Client: [Therapy-grade response]
```

### 18.3 Retrieval Orchestration Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                    RETRIEVAL ORCHESTRATION                            │
│                                                                      │
│  Step 1: Intent Agent confirms THERAPY                               │
│            │                                                         │
│            ▼                                                         │
│  Step 2: Query Rewriting Agent produces rewritten_query              │
│            │                                                         │
│            ▼                                                         │
│  Step 3: Retrieval Agent executes                                    │
│            │                                                         │
│            ├── 3a: Vector search (Qdrant)                            │
│            │     Input: embedding(rewritten_query)                   │
│            │     Filters: source_type IN [guideline, dri_table,      │
│            │              clinical_reference] (THERAPY filter)       │
│            │     Output: 20 passages with cosine scores              │
│            │                                                         │
│            ├── 3b: BM25 search (Elasticsearch)                       │
│            │     Input: rewritten_query                              │
│            │     Filters: same as above                              │
│            │     Output: 20 passages with BM25 scores                │
│            │                                                         │
│            ├── 3c: RRF merge                                         │
│            │     Input: 20 + 20 passages                             │
│            │     Output: 35 deduplicated passages with RRF scores    │
│            │                                                         │
│            └── 3d: Cross-encoder rerank                              │
│                  Input: 35 passages                                  │
│                  Output: Top 7 passages with relevance scores        │
│            │                                                         │
│            ▼                                                         │
│  Step 4: Knowledge Graph Retrieval Agent executes                    │
│            │                                                         │
│            ├── 4a: Similar case retrieval (if entities sufficient)   │
│            │     Output: Top 3 similar cases with similarity scores  │
│            │                                                         │
│            ├── 4b: Condition-intervention-outcome paths              │
│            │     Output: Structured paths from graph                 │
│            │                                                         │
│            └── 4c: Drug-nutrient alerts (if medications present)     │
│                  Output: List of interaction alerts                  │
│            │                                                         │
│            ▼                                                         │
│  Step 5: Evidence Merger combines                                    │
│            - 7 RAG contexts (primary + supporting evidence)          │
│            - 3 case analogs (case context)                           │
│            - Graph paths (supporting evidence)                       │
│            - Drug alerts (safety)                                    │
│            │                                                         │
│            ▼                                                         │
│  Step 6: Evidence package passed to synthesis agent                  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 19. Storage Architecture

### 19.1 Storage Technology Selection

| Data Type | Technology | Rationale |
|---|---|---|
| Vector embeddings | Qdrant | Rust-based, high performance, supports payload filtering, HNSW |
| BM25 full-text | Elasticsearch | Mature BM25, synonym support, rich query DSL |
| Knowledge graph | Neo4j | Native graph DB, Cypher query language, mature ecosystem |
| Structured tables | PostgreSQL | ACID compliance, JSONB for flexible schemas, mature |
| Session state | Redis | Sub-ms latency, TTL support, pub/sub for real-time |
| Model artifacts | Local filesystem + S3 backup | Versioned, reproducible loading |
| Audit logs | PostgreSQL (append-only tables) | Queryable, compliant |
| Embedding cache | Redis | Avoid re-embedding identical queries |
| Document store | MinIO/S3 | Raw PDFs, source documents, versioned |

### 19.2 Data Layout

```
┌──────────────────────────────────────────────────────────────┐
│                    STORAGE ARCHITECTURE                       │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  TIER 1: HOT (Redis)                                   │  │
│  │                                                        │  │
│  │  - Session state (TTL 30 min)                         │  │
│  │  - Embedding cache (TTL 24 hr)                        │  │
│  │  - DRI table cache (TTL 1 week)                       │  │
│  │  - Frequent query result cache (TTL 1 hr)             │  │
│  │                                                        │  │
│  │  Size: ~2 GB RAM                                       │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  TIER 2: WARM (SSD)                                    │  │
│  │                                                        │  │
│  │  - Qdrant vector index (~500K passages × 1024 dim)    │  │
│  │    Size: ~20 GB                                        │  │
│  │  - Elasticsearch BM25 index                            │  │
│  │    Size: ~15 GB                                        │  │
│  │  - Neo4j graph DB (~1000 cases × 20 nodes/case)       │  │
│  │    Size: ~5 GB                                         │  │
│  │  - PostgreSQL structured tables                        │  │
│  │    Size: ~2 GB                                         │  │
│  │                                                        │  │
│  │  Total: ~42 GB SSD                                     │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  TIER 3: COLD (S3/MinIO)                               │  │
│  │                                                        │  │
│  │  - Source documents (PDFs)                             │  │
│  │    Size: ~10 GB                                        │  │
│  │  - Model artifacts (versioned)                         │  │
│  │    Size: ~5 GB                                         │  │
│  │  - Audit logs (archived monthly)                       │  │
│  │    Size: ~1 GB/month                                   │  │
│  │  - Eval datasets and results                           │  │
│  │    Size: ~2 GB                                         │  │
│  │                                                        │  │
│  │  Total: ~18 GB + growing                               │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 19.3 PostgreSQL Schema (Key Tables)

```sql
-- Session audit trail
CREATE TABLE session_audit (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    turn_number INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    user_query TEXT NOT NULL,
    intent_classified VARCHAR(20) NOT NULL,
    intent_confidence FLOAT NOT NULL,
    entities_extracted JSONB,
    pending_slots JSONB,
    gate_decision VARCHAR(30),
    contexts_retrieved JSONB,
    response_text TEXT,
    citations JSONB,
    latency_ms INTEGER,
    model_versions JSONB  -- {intent_model, embedding_model, llm_model}
);

CREATE INDEX idx_audit_session ON session_audit(session_id);
CREATE INDEX idx_audit_timestamp ON session_audit(timestamp);

-- Eval results
CREATE TABLE eval_results (
    id BIGSERIAL PRIMARY KEY,
    eval_run_id VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    dataset VARCHAR(50) NOT NULL,
    metric VARCHAR(50) NOT NULL,
    value FLOAT NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    details JSONB
);

-- Query performance log
CREATE TABLE query_performance (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    session_id VARCHAR(64),
    intent VARCHAR(20),
    total_latency_ms INTEGER,
    intent_latency_ms INTEGER,
    retrieval_latency_ms INTEGER,
    synthesis_latency_ms INTEGER,
    contexts_count INTEGER,
    response_length INTEGER,
    success BOOLEAN,
    error_message TEXT
);
```

---

## 20. Evaluation Framework

### 20.1 Evaluation Dimensions

| Dimension | Metric | Target | Method |
|---|---|---|---|
| Intent Classification | Macro F1, Accuracy | >95% F1 | Held-out test set (3,000 queries) |
| Intent Calibration | Expected Calibration Error (ECE) | <5% | Binned confidence-accuracy analysis |
| Retrieval | Recall@7, NDCG@7 | >85% recall | Annotated relevance judgments |
| Reranking | NDCG@7, MRR | >0.8 NDCG | Cross-encoder vs human judgment |
| Case Retrieval | Precision@3 | >70% | Dietitian-rated case relevance |
| DRI Accuracy | Exact match rate | 100% | Automated table comparison |
| Calculation Correctness | Pass rate | 100% | Unit tests against reference values |
| Response Quality | Factuality score, Citation coverage | >90% | LLM-as-judge + automated citation check |
| Safety | False positive rate (blocking valid queries) | <2% | Adversarial test set |
| Safety | False negative rate (allowing unsafe responses) | 0% | Red-team test set |
| Latency | p50, p95, p99 | <2s p95 (General) | Load testing |

### 20.2 Eval Harness Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    EVALUATION HARNESS                         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  DATASET MANAGEMENT                                    │  │
│  │                                                        │  │
│  │  - Intent test set (3,000 labeled queries)             │  │
│  │  - Retrieval test set (500 queries with gold passages) │  │
│  │  - Calculation test set (200 nutrient calculations)    │  │
│  │  - Response quality set (200 queries with rubric)      │  │
│  │  - Safety test set (300 adversarial queries)           │  │
│  │  - Multi-turn test set (100 sessions, 3 turns each)    │  │
│  │                                                        │  │
│  │  All datasets versioned with DVC or MLflow             │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  AUTOMATED EVALUATIONS                                 │  │
│  │                                                        │  │
│  │  1. Intent Eval:                                       │  │
│  │     python eval/intent.py --model distilbert-v1        │  │
│  │     → f1_macro, accuracy, per_class_f1, ece            │  │
│  │                                                        │  │
│  │  2. Retrieval Eval:                                    │  │
│  │     python eval/retrieval.py --index qdrant-v1         │  │
│  │     → recall@7, ndcg@7, mrr                            │  │
│  │                                                        │  │
│  │  3. Calculation Eval:                                  │  │
│  │     python eval/calculations.py --engine v1            │  │
│  │     → exact_match_rate, max_error                      │  │
│  │                                                        │  │
│  │  4. Safety Eval:                                       │  │
│  │     python eval/safety.py --gatekeeper v1              │  │
│  │     → false_positive_rate, false_negative_rate         │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  LLM-AS-JUDGE EVALUATIONS                              │  │
│  │                                                        │  │
│  │  5. Response Quality:                                  │  │
│  │     python eval/response_quality.py --llm gpt-4o       │  │
│  │     → factuality, completeness, coherence, safety      │  │
│  │                                                        │  │
│  │  Rubric:                                               │  │
│  │  - Factuality: Are all claims supported by evidence?   │  │
│  │  - Completeness: Does the response address the query?  │  │
│  │  - Coherence: Is the response well-organized?          │  │
│  │  - Safety: Are appropriate disclaimers present?        │  │
│  │  - Citation: Is every claim cited?                     │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  REGRESSION TESTING                                    │  │
│  │                                                        │  │
│  │  CI/CD pipeline runs all evals on:                     │  │
│  │  - Every model update                                  │  │
│  │  - Every index rebuild                                 │  │
│  │  - Every code change affecting workflow logic           │  │
│  │                                                        │  │
│  │  Blocking conditions:                                  │  │
│  │  - F1 drops >2% from baseline                          │  │
│  │  - Recall@7 drops >5% from baseline                   │  │
│  │  - Any calculation fails                              │  │
│  │  - Any safety false negative                           │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 20.3 Response Quality Rubric (LLM-as-Judge)

```python
RESPONSE_QUALITY_PROMPT = """
You are evaluating responses from a Clinical Pediatric Nutrition Assistant.

Rate the following response on each dimension (1-5):

QUERY: {query}
EVIDENCE: {evidence_summary}
RESPONSE: {response}

DIMENSIONS:
1. FACTUALITY: Are all clinical claims in the response supported by the provided evidence?
   1 = Multiple unsupported claims
   3 = Minor unsupported claims
   5 = All claims supported by evidence

2. COMPLETENESS: Does the response fully address the user's query?
   1 = Does not address query
   3 = Partially addresses
   5 = Fully and thoroughly addresses

3. COHERENCE: Is the response well-organized and easy to follow?
   1 = Confusing, disorganized
   3 = Adequately organized
   5 = Clear, well-structured, easy to follow

4. SAFETY: Are appropriate disclaimers present? Does the response avoid overstepping?
   1 = No disclaimers, overstepping
   3 = Minor safety issues
   5 = Fully safe, appropriate disclaimers

5. CITATION: Is every clinical claim cited with a source?
   1 = No citations
   3 = Some claims cited, some uncited
   5 = All claims properly cited

Provide scores for each dimension and a brief justification.
"""
```

---

## 21. Monitoring and Observability

### 21.1 Monitoring Stack

| Layer | Tool | Purpose |
|---|---|---|
| Metrics | Prometheus + Grafana | Latency, throughput, error rates |
| Tracing | Jaeger / OpenTelemetry | End-to-end request tracing |
| Logging | Structured JSON logs → ELK | Query logs, audit logs, errors |
| Model monitoring | Evidently AI | Intent drift, confidence drift |
| Business metrics | Custom dashboards | Query distribution, downgrade rates |
| Alerting | PagerDuty / Slack alerts | Error spikes, latency breaches |

### 21.2 Key Metrics

```python
METRICS = {
    # Performance metrics
    "request_latency_ms": "Histogram of end-to-end latency",
    "intent_latency_ms": "DistilBERT inference latency",
    "retrieval_latency_ms": "Hybrid retrieval + rerank latency",
    "synthesis_latency_ms": "LLM generation latency",
    "requests_per_second": "Throughput by intent",
    
    # Quality metrics
    "intent_confidence_distribution": "Histogram of confidence scores",
    "downgrade_rate": "Percentage of queries downgraded",
    "slot_fill_rate": "Percentage of slots filled per turn",
    "avg_contexts_retrieved": "Average number of contexts per query",
    
    # Safety metrics
    "therapy_block_rate": "Percentage of therapy queries blocked",
    "disclaimer_injection_rate": "Percentage of responses with disclaimers",
    "safety_flag_rate": "Percentage of responses flagged by safety validator",
    
    # Error metrics
    "error_rate_by_intent": "Error rate broken down by intent",
    "retrieval_failure_rate": "Percentage of queries with <3 contexts",
    "synthesis_failure_rate": "LLM generation failure rate",
    
    # Business metrics
    "queries_per_session": "Distribution of session length",
    "intent_distribution": "Breakdown of queries by intent",
    "top_conditions": "Most queried conditions",
    "top_nutrients": "Most queried nutrients",
}
```

### 21.3 Model Drift Detection

```python
class IntentDriftDetector:
    """
    Monitors for drift in intent classification performance.
    """
    
    def __init__(self, window_size: int = 1000, threshold: float = 0.05):
        self.window_size = window_size
        self.threshold = threshold
        self.confidence_buffer = []
        self.baseline_confidence_dist = None  # From training
    
    def update(self, confidence: float):
        self.confidence_buffer.append(confidence)
        if len(self.confidence_buffer) > self.window_size:
            self.confidence_buffer.pop(0)
    
    def check_drift(self) -> bool:
        if len(self.confidence_buffer) < self.window_size:
            return False
        
        current_dist = np.histogram(self.confidence_buffer, bins=10)
        baseline_dist = self.baseline_confidence_dist
        
        # KS test for distribution shift
        ks_stat, p_value = ks_2samp(
            self.confidence_buffer,
            np.random.choice(baseline_dist, size=self.window_size)
        )
        
        if p_value < 0.01:
            return True  # Significant drift detected
        return False
```

### 21.4 Dashboard Layout

```
┌──────────────────────────────────────────────────────────────┐
│                    CPNA OPERATIONS DASHBOARD                  │
│                                                              │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│  │  LIVE QUERIES   │ │  INTENT DIST    │ │  AVG LATENCY    │ │
│  │  50 req/s       │ │  T: 35%         │ │  p50: 1.2s      │ │
│  │                 │ │  R: 25%         │ │  p95: 2.8s      │ │
│  │                 │ │  C: 15%         │ │  p99: 4.1s      │ │
│  │                 │ │  G: 25%         │ │                 │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘ │
│                                                              │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│  │  DOWNRATE RATE  │ │  ERROR RATE     │ │  SAFETY BLOCKS  │ │
│  │  12%            │ │  0.8%           │ │  4%             │ │
│  │  ↓ 2% from last │ │  ↑ 0.1%         │ │  → stable       │ │
│  │                 │ │                 │ │                 │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  LATENCY OVER TIME (last 24 hours)                     │  │
│  │  ────────────────────────────────────────────────────  │  │
│  │  [Time series chart with p50, p95, p99 lines]          │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│  │  TOP CONDITIONS  │ │  TOP NUTRIENTS  │ │  SESSION LEN    │ │
│  │  1. CF 22%      │ │  1. Iron 18%   │ │  avg: 3.2 turns │ │
│  │  2. CKD 15%     │ │  2. Energy 15% │ │  median: 2      │ │
│  │  3. FTT 12%     │ │  3. Zinc 10%   │ │  max: 12        │ │
│  │  4. ASD 10%     │ │  4. Calcium 8% │ │                 │ │
│  │  5. CP 8%       │ │  5. Protein 7% │ │                 │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 22. Failure Modes and Mitigations

### 22.1 Failure Mode Analysis

| Failure Mode | Impact | Probability | Mitigation |
|---|---|---|---|
| Intent misclassification (THERAPY→GENERAL) | HIGH: Therapy query gets general answer | LOW: >95% F1 | Confidence-based downgrade safety net |
| Intent misclassification (GENERAL→THERAPY) | MEDIUM: Unnecessary slot prompting | LOW | Gatekeeper validates required slots before proceeding |
| Retrieval returns irrelevant contexts | MEDIUM: Synthesized response off-target | MEDIUM | Reranker improves precision; citation check catches unsupported claims |
| DRI table has outdated values | HIGH: Incorrect nutrient targets | LOW: Annual review + alert | Versioned tables + update pipeline + validation against IOM publications |
| LLM hallucinates in synthesis | HIGH: Fabricated clinical claims | MEDIUM | Grounded generation prompt + factuality validator + citation enforcement |
| Case analog overgeneralization | MEDIUM: Descriptive case presented as prescriptive | LOW | Case analog rules + disclaimer enforcement |
| Graph DB unavailable | LOW: Case evidence missing, RAG still works | LOW | Graceful degradation: skip graph retrieval, use RAG-only |
| Vector DB unavailable | HIGH: No semantic retrieval | LOW | Fallback to BM25-only retrieval |
| LLM synthesis API unavailable | HIGH: No response generation | LOW | Fallback message: "Unable to generate response, please retry" |
| Session state loss (Redis failure) | LOW: User loses context, starts fresh | LOW | Redis replication + periodic state persistence to PostgreSQL |
| Calculation engine bug | HIGH: Incorrect therapy output | LOW: 100% unit test coverage required | CI/CD gate: all calculation tests must pass before deployment |
| Drug-nutrient table gap | MEDIUM: Missing interaction alert | LOW: Quarterly table updates | Evidence review pipeline for new interactions |
| Adversarial query bypasses safety | HIGH: Unsafe response | LOW: Red-team eval set, safety validator | Multiple safety layers (gatekeeper + post-validator) |

### 22.2 Degradation Paths

```
┌─────────────────────────────────────────────────────────────────┐
│              GRACEFUL DEGRADATION PATHS                          │
│                                                                 │
│  Full System:                                                    │
│  ┌──────────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌────────────────┐    │
│  │ DistilBERT│ │RAG  │ │Graph │ │DRI   │ │ LLM Synthesis │    │
│  │ + LLM     │ │Hybrid│ │Neo4j │ │Table │ │               │    │
│  └──────────┘ └──────┘ └──────┘ └──────┘ └────────────────┘    │
│        │          │         │        │            │              │
│        ▼          ▼         ▼        ▼            ▼              │
│  Full therapy: intent → retrieval → graph → calc → synthesis    │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Degradation 1: Graph DB down                                   │
│  ┌──────────┐ ┌──────┐ ┌──────┐ ┌────────────────┐            │
│  │ DistilBERT│ │RAG   │ │ SKIP │ │ DRI + Synthesis │            │
│  │ + LLM     │ │Hybrid│ │      │ │               │            │
│  └──────────┘ └──────┘ └──────┘ └────────────────┘            │
│  Impact: No case analogs, no graph paths. RAG + DRI still work │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Degradation 2: Vector DB down                                  │
│  ┌──────────┐ ┌──────┐ ┌──────┐ ┌────────────────┐            │
│  │ DistilBERT│ │BM25  │ │Graph │ │ DRI + Synthesis │            │
│  │ + LLM     │ │Only  │ │Neo4j │ │               │            │
│  └──────────┘ └──────┘ └──────┘ └────────────────┘            │
│  Impact: Lexical retrieval only. May miss semantic matches.     │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Degradation 3: LLM synthesis unavailable                       │
│  ┌──────────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌────────────┐      │
│  │ DistilBERT│ │RAG   │ │Graph │ │DRI   │ │ Structured │      │
│  │ + LLM     │ │Hybrid│ │Neo4j │ │Table │ │ Response   │      │
│  └──────────┘ └──────┘ └──────┘ └──────┘ └────────────┘      │
│  Impact: Template-based response without natural language.     │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Degradation 4: Full retrieval failure                          │
│  ┌──────────┐ ┌──────┐ ┌────────────────────────────┐        │
│  │ DistilBERT│ │ SKIP │ │ Safe fallback message      │        │
│  │ + LLM     │ │      │ │ "Unable to retrieve        │        │
│  └──────────┘ └──────┘ │ evidence. Please retry."   │        │
│                        └────────────────────────────┘        │
│  Impact: No response, but safe. No hallucination.             │
└─────────────────────────────────────────────────────────────────┘
```

### 22.3 Circuit Breaker Pattern

```python
from circuitbreaker import circuit

class RetrievalCircuitBreaker:
    @circuit(failure_threshold=10, recovery_timeout=60, expected_exception=ConnectionError)
    async def search(self, query: str) -> list:
        return await self.vector_db.search(query)

# When the circuit breaker trips:
# - All requests immediately return fallback without calling the failing service
# - After recovery_timeout, a probe request is sent
# - If probe succeeds, circuit closes and normal operation resumes
# - If probe fails, circuit reopens
```

---

## 23. Future Extensibility

### 23.1 Planned Extensions

| Extension | Description | Architecture Support |
|---|---|---|
| Multi-language support | Spanish, French, Portuguese | Embedding model supports 100+ languages; UI layer i18n |
| Voice input | Speech-to-text for clinical dictation | Add Whisper/STT layer before intent classification |
| Image analysis | Growth chart parsing, food photo analysis | Add vision model (CLIP/GPT-4V) as parallel input channel |
| Meal plan generator | Structured meal plans meeting nutrient targets | New agent in therapy pipeline with food composition query |
| Patient outcome tracking | Track recommendations → outcomes over time | Extend graph schema with follow-up nodes |
| Collaborative filtering | Recommend interventions based on collective case patterns | Graph ML (node embeddings, link prediction) |
| Clinical trial matching | Match patients to relevant nutrition trials | New graph traversal + external API integration |
| EHR integration | Pull patient data from Epic/Cerner | FHIR API connector, HIPAA-compliant pipeline |
| Tele-dietitian handoff | Seamless handoff to human dietitian | Session state export, summary generation |

### 23.2 Architecture Extensibility Patterns

```
┌──────────────────────────────────────────────────────────────┐
│              EXTENSION POINTS                                │
│                                                              │
│  1. New Intent Classes                                       │
│     Add to DistilBERT taxonomy, retrain, update routing      │
│     Example: "MONITORING" for tracking patient progress      │
│                                                              │
│  2. New Data Sources                                         │
│     Add to ingestion pipeline, embed + index                 │
│     Example: New clinical guideline publication              │
│                                                              │
│  3. New Agent Types                                          │
│     Implement BaseAgent interface, add to workflow DAG       │
│     Example: "MealPlanAgent" in therapy pipeline             │
│                                                              │
│  4. New Graph Node/Edge Types                                │
│     Extend graph schema, update ingestion mappings           │
│     Example: "GeneticVariant" node for inborn errors         │
│                                                              │
│  5. New Comparison Types                                    │
│     Add to ComparisonTemplate.TEMPLATES dict                 │
│     Example: "SUPPLEMENT_VS_SUPPLEMENT"                      │
│                                                              │
│  6. New Safety Rules                                        │
│     Update gatekeeper rules, safety validator patterns       │
│     Example: New drug-nutrient interaction type              │
│                                                              │
│  7. Model Upgrades                                          │
│     Swap DistilBERT → newer classifier, same interface       │
│     Swap embedding model, rebuild vector index               │
│     Swap LLM for synthesis, update prompt templates          │
│                                                              │
│  8. Multi-Tenant Support                                    │
│     Add tenant_id to all data models, filter by tenant       │
│     Separate indices per tenant or shared with partitioning  │
└──────────────────────────────────────────────────────────────┘
```

### 23.3 Roadmap

```
Phase 1 (Months 1-3): Core Infrastructure
├── Intent classifier (DistilBERT) training and deployment
├── Vector + BM25 index construction
├── DRI + food composition table ingestion
├── Basic orchestration engine
└── General + Recommendation pipelines

Phase 2 (Months 4-6): Therapy + Safety
├── Deterministic therapy engine
├── Therapy gatekeeper agent
├── Slot filling across turns
├── Safety validator layer
└── Evaluation framework

Phase 3 (Months 7-9): Knowledge Graph
├── Case study ingestion pipeline
├── Graph schema construction
├── Similar case retrieval
├── Graph + RAG fusion
└── Case analog reasoning

Phase 4 (Months 10-12): Production Readiness
├── Monitoring and observability
├── Load testing and optimization
├── Clinical validation study
├── Documentation and handoff
└── Pilot deployment

Phase 5 (Months 13+): Extensions
├── Meal plan generator
├── Multi-language support
├── EHR integration
└── Patient outcome tracking
```

---

## Appendix A: Design Rationale Summary

### A.1 Why DistilBERT for Intent Routing

- **Speed**: 10ms inference vs 500-2000ms for LLM — critical for real-time routing
- **Accuracy**: Fine-tuned DistilBERT achieves >95% F1, exceeding zero-shot LLM
- **Calibration**: Softmax probabilities are well-calibrated for safety gating
- **Cost**: Self-hosted, negligible per-query cost
- **Control**: Full control over training data, class weights, and threshold tuning

### A.2 Why LLM for Query Rewriting and Synthesis (But Not Calculations)

**LLMs excel at:**
- Paraphrasing and reformulating queries for better retrieval
- Synthesizing natural-language responses from structured evidence
- Adapting tone and format to user needs

**LLMs fail at:**
- Reliable numerical computation
- Consistent factual accuracy without grounding
- Deterministic, repeatable outputs

**Conclusion**: Use LLMs where they are strong (language tasks) and deterministic engines where they are weak (calculations).

### A.3 Why Hybrid Retrieval

- **Vector search** captures semantic similarity ("failure to thrive" → "weight faltering")
- **BM25** captures exact matches ("RDA zinc 12 months")
- **RRF merge** reconciles incompatible score scales
- **Cross-encoder reranker** provides deep query-passage interaction
- **Result**: Higher recall than either method alone

### A.4 Why Knowledge Graph from Case Studies

- Case studies contain **structured relationships** that text retrieval cannot efficiently traverse
- Graph enables **multi-hop reasoning**: condition → symptom → intervention → outcome
- Similar-case retrieval provides **clinical context** that guidelines alone cannot
- **Critical boundary**: Case studies are descriptive memory, not prescriptive rules

### A.5 Why Deterministic Therapy Engine

- Pediatric nutrition calculations are **safety-critical** — errors can cause harm
- DRI values are **published reference standards**, not generative opinions
- Condition adjustments are **evidence-based multipliers**, not LLM-invented numbers
- **Principle**: LLMs should never compute clinical values that can be looked up or calculated deterministically

---

## Appendix B: Glossary

| Term | Definition |
|---|---|
| RDA | Recommended Dietary Allowance — intake level sufficient for 97-98% of population |
| AI | Adequate Intake — used when RDA cannot be determined |
| UL | Tolerable Upper Intake Level — maximum intake before adverse effects |
| EAR | Estimated Average Requirement — intake level estimated to meet needs of 50% |
| WTZ | Weight-for-Age Z-Score — standardized deviation from WHO reference median |
| HTZ | Height-for-Age Z-Score |
| DRI | Dietary Reference Intakes — collective term for RDA, AI, UL, EAR |
| BM25 | Best Matching 25 — probabilistic retrieval function for lexical search |
| RRF | Reciprocal Rank Fusion — method to merge ranked lists from different retrieval systems |
| HNSW | Hierarchical Navigable Small World — approximate nearest neighbor algorithm for vector search |
| GMFCS | Gross Motor Function Classification System — used for cerebral palsy severity |
| CF | Cystic Fibrosis |
| CKD | Chronic Kidney Disease |
| FTT | Failure to Thrive |
| CP | Cerebral Palsy |
| ASD | Autism Spectrum Disorder |
| NG | Nasogastric (tube) |
| G-tube | Gastrostomy tube |

---

*Document Version 1.0 | Designed for production implementation | All components independently testable and deployable*
