"""
app/api/router.py — FastAPI application entrypoint for CPNA v1.

Endpoints:
  POST /api/chat          — main chat orchestration
  POST /api/session/reset — clear active task state
  GET  /api/health        — liveness check
  GET  /metrics           — Prometheus metrics (wired in Prompt 12)

Middleware:
  - Request-ID (UUID per request, echoed as X-Request-ID header)
  - Structured per-request logging (session_id, intent, latency_ms — NO PII)
  - Global exception handler (safe error surface, no stack traces)
"""

from __future__ import annotations

import contextlib
import logging
import time
import uuid
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ResetRequest,
    ResetResponse,
    StateSnapshot,
)
from app.classification.intent_classifier import ClassificationResult, IntentClassifier, MockIntentClassifier
from app.classification.intent_labels import CONFIDENCE_THRESHOLD, IntentLabel
from app.contracts.display_adapter import DisplayAdapter, DisplayAdapterError
from app.contracts.response_contracts import EvidenceSummary, GeneralResponse
from app.observability.logger import log_error, log_pipeline_event, log_request_summary
from app.observability.metrics import (
    cpna_downgrade_total,
    cpna_latency_seconds,
    cpna_requests_total,
)
from app.state.conversation_state import ConversationPhase, ConversationState
from app.state.state_manager import ResolutionType, StateManager
from app.workflows.comparison_workflow import WorkflowError
from app.workflows.workflow_router import WorkflowRouter

logger = logging.getLogger(__name__)
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)
slog = structlog.get_logger()

_VERSION = "1.0.0"
_SAFE_ERROR_RESPONSE = "Something went wrong. Please try again."
_SAFE_ADAPTER_ANSWER = "I wasn't able to format a complete response for that query."


@contextlib.asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Run ingestion once at startup, then yield to serve requests."""
    try:
        from app.retrieval.startup_ingestion import get_retrieval_agent
        agent = get_retrieval_agent()
        fastapi_app.state.retrieval_agent = agent
    except Exception as exc:
        logger.error("lifespan: startup ingestion failed — retrieval will be unavailable: %s", exc)
        fastapi_app.state.retrieval_agent = None
    yield
    # shutdown — nothing to tear down for in-memory stores


# ---------------------------------------------------------------------------
# Application-level singletons
# All heavy components are created once at startup.
# Tests replace these via dependency injection / monkeypatching on app.state.
# ---------------------------------------------------------------------------

app = FastAPI(title="CPNA v1", version=_VERSION, lifespan=lifespan)

# These are overrideable in tests via app.state.*
app.state.intent_classifier = None   # set lazily or by tests
app.state.state_manager = None       # set lazily or by tests
app.state.workflow_router = None     # set lazily or by tests
app.state.display_adapter = DisplayAdapter()


def _get_classifier():
    if app.state.intent_classifier is None:
        try:
            app.state.intent_classifier = IntentClassifier()
            logger.info("_get_classifier: real IntentClassifier loaded successfully")
        except Exception as exc:
            logger.warning(
                "_get_classifier: failed to load IntentClassifier (%s) — falling back to MockIntentClassifier",
                exc,
            )
            app.state.intent_classifier = MockIntentClassifier()
    return app.state.intent_classifier


def _get_state_manager() -> StateManager:
    if app.state.state_manager is None:
        app.state.state_manager = StateManager()
    return app.state.state_manager


def _get_router() -> WorkflowRouter:
    # Re-attempt retrieval init if a previous attempt failed (retrieval_agent stays None).
    # Only cache the router once retrieval is successfully initialised.
    retrieval_agent = getattr(app.state, "retrieval_agent", None)
    if retrieval_agent is None:
        try:
            from app.retrieval.startup_ingestion import get_retrieval_agent
            retrieval_agent = get_retrieval_agent()
            app.state.retrieval_agent = retrieval_agent
            # Invalidate any cached router built without retrieval so it gets rebuilt below.
            app.state.workflow_router = None
            logger.info("_get_router: retrieval agent initialised lazily")
        except Exception as exc:
            import traceback as _tb
            logger.warning(
                "_get_router: retrieval agent init failed (%s) — retrieval will be unavailable\n%s",
                str(exc).encode("ascii", "replace").decode("ascii"),
                _tb.format_exc()[:800],
            )
    if app.state.workflow_router is None:
        app.state.workflow_router = WorkflowRouter(retrieval_agent=retrieval_agent)
    return app.state.workflow_router


# ---------------------------------------------------------------------------
# Middleware — Request ID
# ---------------------------------------------------------------------------

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    session_id = getattr(request.state, "session_id", "unknown")
    request_id = getattr(request.state, "request_id", "unknown")
    log_error(
        "unhandled_exception",
        exc,
        session_id=session_id,
        request_id=request_id,
        extra={"path": str(request.url.path), "method": request.method},
    )
    return JSONResponse(
        status_code=500,
        content={"error": _SAFE_ERROR_RESPONSE, "session_id": session_id},
    )


# ---------------------------------------------------------------------------
# Safe clarification response builder
# ---------------------------------------------------------------------------

def _clarification_response(message: str) -> GeneralResponse:
    return GeneralResponse(
        title="Clarification Needed",
        summary=message,
        direct_answer=message,
        explanation="",
        follow_up_hint="",
        evidence_summary=EvidenceSummary(used_sources=[], retrieval_note=""),
    )


def _safe_adapter_fallback() -> GeneralResponse:
    return GeneralResponse(
        title="Response Unavailable",
        summary=_SAFE_ADAPTER_ANSWER,
        direct_answer=_SAFE_ADAPTER_ANSWER,
        explanation="",
        follow_up_hint="Please rephrase your question.",
        evidence_summary=EvidenceSummary(used_sources=[], retrieval_note=""),
    )


# ---------------------------------------------------------------------------
# POST /api/chat
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=None)
async def chat(request: Request, body: ChatRequest) -> JSONResponse:
    t_start = time.monotonic()
    request.state.session_id = body.session_id
    request_id = getattr(request.state, "request_id", "")
    classifier = _get_classifier()
    sm = _get_state_manager()
    router = _get_router()
    adapter = app.state.display_adapter

    # Observability accumulators — mutated as the request progresses
    _workflow_routed_to = "none"
    _retrieval_passage_count = 0
    _downgrade_occurred = False
    _error: str | None = None

    # Step 1 — load / create state
    state: ConversationState = sm.get_state(body.session_id)

    # Phase 4 — mid slot-fill: skip re-classification, route directly to therapy workflow
    # This prevents "10 year old", "30kg", etc. from being misclassified as GENERAL.
    if state.phase == ConversationPhase.SLOT_FILLING:
        _workflow_routed_to = "slot_fill_continue"
        preserved_label = state.active_task_context.current_intent or IntentLabel.THERAPY
        clf_result = ClassificationResult(
            label=preserved_label,
            confidence=0.95,
            all_scores={preserved_label.value: 0.95},
            needs_clarification=False,
        )
        intent_label = clf_result.label
        confidence = clf_result.confidence
        # Fall through to step 3 (pending slots check) with the preserved intent.
        goto_step3 = True
    else:
        goto_step3 = False

    # Phase 5 — all slots confirmed: force therapy dispatch regardless of last classified intent
    if state.phase == ConversationPhase.DISPATCHING:
        _workflow_routed_to = "therapy_dispatch"
        state.phase = ConversationPhase.RESPONDING
        sm.save_state(state)
        try:
            workflow_result = router.route(
                _force_therapy_state(state), body.message, sm
            )
        except Exception as exc:
            log_error("therapy_dispatch", exc, session_id=body.session_id, request_id=request_id)
            workflow_result = None
        if workflow_result is not None:
            # Jump straight to adapter step
            goto_step3 = False
            goto_dispatch = True
        else:
            goto_dispatch = False
    else:
        goto_dispatch = False

    # Phase 7 — RECOMMENDATION → THERAPY handoff: user is following a CTA to provide patient data
    if (
        not goto_step3
        and not goto_dispatch
        and state.pending_intent == "therapy"
        and state.phase == ConversationPhase.IDLE
    ):
        state.pending_intent = None
        state.phase = ConversationPhase.SLOT_FILLING
        if state.active_task_context.current_intent is None:
            state.active_task_context.current_intent = IntentLabel.THERAPY
        sm.save_state(state)
        # Re-enter as a THERAPY intent so TherapyWorkflow handles the turn
        clf_result = ClassificationResult(
            label=IntentLabel.THERAPY,
            confidence=0.95,
            all_scores={IntentLabel.THERAPY.value: 0.95},
            needs_clarification=False,
        )
        intent_label = clf_result.label
        confidence = clf_result.confidence
        goto_step3 = True

    if goto_dispatch:
        # Therapy dispatch path — skip all classification and slot logic, jump to adapter
        intent_label = IntentLabel.THERAPY
        confidence = 0.95
    else:
        if not goto_step3:
            # Step 2 — classify intent (normal path)
            clf_result = classifier.classify(body.message)
        intent_label = clf_result.label
        confidence = clf_result.confidence

    if not goto_dispatch:
        # Step 3 — check pending slots FIRST (loose reply takes priority over clarification)
        # This ensures bare values like "10" are treated as slot fills, not ambiguous queries.
        pending_slots = state.active_task_context.pending_slots
        if pending_slots:
            resolution = sm.resolve_loose_reply(body.session_id, body.message)
            if resolution.resolution_type == ResolutionType.SLOT_FILL and resolution.resolved_slot:
                state = sm.confirm_slot(
                    body.session_id,
                    resolution.resolved_slot,
                    resolution.resolved_value or body.message,
                )
                # Re-load with preserved intent from prior turn
                if state.active_task_context.current_intent is None:
                    state.active_task_context.current_intent = IntentLabel.THERAPY
                    sm.save_state(state)
                intent_label = state.active_task_context.current_intent
                confidence = 0.90

                # If no slots remain and phase is SLOT_FILLING, advance to DISPATCHING
                if (
                    state.phase == ConversationPhase.SLOT_FILLING
                    and not state.active_task_context.pending_slots
                ):
                    state.phase = ConversationPhase.DISPATCHING
                    sm.save_state(state)

        # Step 4 — needs clarification → return safe GeneralResponse (never HTTP 400)
        # Skip if we just resolved a slot (intent_label set above).
        if clf_result.needs_clarification and intent_label is None:
            clarification_text = (
                "I want to make sure I help you correctly — are you looking for personalized "
                "nutrition planning, dietary guidance, a food comparison, or general nutrition "
                "information?"
            )
            cpna_resp = _clarification_response(clarification_text)
            state.clarification_needed = True
            state.clarification_prompt = clarification_text
            sm.save_state(state)

            latency_ms = (time.monotonic() - t_start) * 1000
            _workflow_routed_to = "clarification"
            cpna_requests_total.labels(query_type="unclear", status="clarification").inc()
            log_request_summary(
                session_id=body.session_id,
                request_id=request_id,
                intent="unclear",
                intent_confidence=confidence,
                workflow_routed_to=_workflow_routed_to,
                retrieval_passage_count=0,
                latency_ms=latency_ms,
                downgrade_occurred=False,
                error=None,
            )
            slog.info(
                "chat",
                session_id=body.session_id,
                intent="unclear",
                confidence=round(confidence, 3),
                latency_ms=int(latency_ms),
                outcome="clarification",
            )
            snapshot = _build_snapshot(state)
            return JSONResponse(
                content=ChatResponse(
                    session_id=body.session_id,
                    response=cpna_resp.model_dump(),
                    state_snapshot=snapshot,
                ).model_dump()
            )

        # Step 5 — update intent in state
        assert intent_label is not None  # guaranteed: either classified or inherited from slot resolution
        state = sm.update_intent(body.session_id, intent_label, confidence)
        _workflow_routed_to = intent_label.value

        # Step 6 — route
        log_pipeline_event(
            "intent_classified",
            session_id=body.session_id,
            request_id=request_id,
            intent=intent_label.value,
            confidence=round(confidence, 4),
        )

        try:
            workflow_result = router.route(state, body.message, sm)
        except WorkflowError as exc:
            log_error(
                "workflow_routing",
                exc,
                session_id=body.session_id,
                request_id=request_id,
                intent=intent_label.value,
            )
            cpna_resp = _clarification_response(
                "I couldn't identify the items you'd like to compare. "
                "Please try: 'Compare X vs Y' or 'Compare X to Y'."
            )
            sm.save_state(state)
            latency_ms = (time.monotonic() - t_start) * 1000
            _error = "WorkflowError"
            cpna_requests_total.labels(query_type=intent_label.value, status="error").inc()
            log_request_summary(
                session_id=body.session_id,
                request_id=request_id,
                intent=intent_label.value,
                intent_confidence=confidence,
                workflow_routed_to=_workflow_routed_to,
                retrieval_passage_count=0,
                latency_ms=latency_ms,
                downgrade_occurred=False,
                error=_error,
            )
            snapshot = _build_snapshot(state)
            return JSONResponse(
                content=ChatResponse(
                    session_id=body.session_id,
                    response=cpna_resp.model_dump(),
                    state_snapshot=snapshot,
                ).model_dump()
            )

    # Track passage count and downgrade from workflow result
    evidence = workflow_result.response_data.get("evidence", [])
    _retrieval_passage_count = len(evidence) if isinstance(evidence, list) else 0
    if workflow_result.response_data.get("downgrade_note") or (
        workflow_result.response_data.get("query_type") == "recommendation"
        and intent_label == IntentLabel.THERAPY
    ):
        _downgrade_occurred = True
        cpna_downgrade_total.labels(downgrade_reason="unsupported_condition").inc()

    # Step 7 — adapt to display contract
    # Slot-fill results bypass the DisplayAdapter and return the prompt directly.
    if workflow_result.requires_slot_fill and workflow_result.slot_prompt:
        cpna_resp = _clarification_response(workflow_result.slot_prompt)
        _workflow_routed_to = "slot_fill"
    else:
        try:
            cpna_resp = adapter.adapt(workflow_result)
        except DisplayAdapterError as exc:
            log_error(
                "display_adapter",
                exc,
                session_id=body.session_id,
                request_id=request_id,
                intent=intent_label.value,
            )
            cpna_resp = _safe_adapter_fallback()
            _error = "DisplayAdapterError"

    # Step 8 — save state
    updated = workflow_result.updated_state
    final_for_save = updated if updated is not None else state

    # After a full therapy response, reset phase so the next unrelated turn starts clean
    if (
        intent_label == IntentLabel.THERAPY
        and not (workflow_result.requires_slot_fill)
        and _workflow_routed_to in ("therapy", "therapy_dispatch")
        and not _error
    ):
        final_for_save.phase = ConversationPhase.IDLE
        final_for_save.pending_intent = None

    sm.save_state(final_for_save)

    # Step 9 — emit metrics + structured log + return
    latency_ms = (time.monotonic() - t_start) * 1000
    latency_s = latency_ms / 1000.0
    status = "error" if _error else "ok"

    cpna_requests_total.labels(query_type=intent_label.value, status=status).inc()
    cpna_latency_seconds.labels(query_type=intent_label.value).observe(latency_s)

    log_request_summary(
        session_id=body.session_id,
        request_id=request_id,
        intent=intent_label.value,
        intent_confidence=confidence,
        workflow_routed_to=_workflow_routed_to,
        retrieval_passage_count=_retrieval_passage_count,
        latency_ms=latency_ms,
        downgrade_occurred=_downgrade_occurred,
        error=_error,
    )
    slog.info(
        "chat",
        session_id=body.session_id,
        intent=intent_label.value,
        confidence=round(confidence, 3),
        latency_ms=int(latency_ms),
        outcome=status,
    )

    snapshot = _build_snapshot(final_for_save)
    return JSONResponse(
        content=ChatResponse(
            session_id=body.session_id,
            response=cpna_resp.model_dump(),
            state_snapshot=snapshot,
        ).model_dump()
    )


# ---------------------------------------------------------------------------
# POST /api/session/reset
# ---------------------------------------------------------------------------

@app.post("/api/session/reset")
async def session_reset(body: ResetRequest) -> ResetResponse:
    sm = _get_state_manager()
    sm.reset_task(body.session_id)
    return ResetResponse(status="ok", session_id=body.session_id)


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=_VERSION)


# ---------------------------------------------------------------------------
# POST /api/eval — Eval platform integration endpoint
# ---------------------------------------------------------------------------

from app.api.eval_endpoint import EvalRequest, eval_endpoint as _eval_handler

@app.post("/api/eval", response_model=None)
async def eval_chat(request: Request, body: EvalRequest):
    return await _eval_handler(request, body)


# ---------------------------------------------------------------------------
# GET /metrics (Prometheus — wired in Prompt 12)
# ---------------------------------------------------------------------------

@app.get("/metrics")
async def metrics():
    from fastapi.responses import Response
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _force_therapy_state(state: ConversationState) -> ConversationState:
    """Return a copy of state with current_intent forced to THERAPY and high confidence."""
    copy = state.model_copy(deep=True)
    copy.active_task_context.current_intent = IntentLabel.THERAPY
    copy.intent_confidence = 0.95
    return copy


def _build_snapshot(state: ConversationState) -> StateSnapshot:
    ctx = state.active_task_context
    return StateSnapshot(
        current_intent=ctx.current_intent.value if ctx.current_intent else None,
        workflow_stage=ctx.workflow_stage,
        pending_slots=list(ctx.pending_slots),
        clarification_needed=state.clarification_needed,
    )
