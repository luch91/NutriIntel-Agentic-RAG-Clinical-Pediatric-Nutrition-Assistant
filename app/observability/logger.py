"""
app/observability/logger.py — Structured JSON logger for CPNA v1.

Emits one log event per request with full pipeline context.
NEVER logs: user message text, biomarker values, medication names, weight, height.

Usage:
    from app.observability.logger import get_logger, log_request_summary, log_error

    log = get_logger(__name__)
    log.info("workflow_started", intent="therapy", session_id="abc")
    log_error("slot_filling", exc, session_id="abc", request_id="xyz")
"""

from __future__ import annotations

import logging
import traceback
from typing import Optional

import structlog

# ── Configure once at import time ──────────────────────────────────────────

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(),
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.JSONRenderer(),
    ],
)


def get_logger(name: str = "cpna") -> structlog.BoundLogger:
    """Return a named bound logger. Use at module level: log = get_logger(__name__)"""
    return structlog.get_logger(name)


# ── Pre-built loggers ──────────────────────────────────────────────────────

_request_log = get_logger("cpna.request")
_error_log = get_logger("cpna.error")
_pipeline_log = get_logger("cpna.pipeline")


# ── Public helpers ─────────────────────────────────────────────────────────

def log_request_summary(
    *,
    session_id: str,
    request_id: str,
    intent: str,
    intent_confidence: float,
    workflow_routed_to: str,
    retrieval_passage_count: int,
    latency_ms: float,
    downgrade_occurred: bool,
    error: Optional[str] = None,
) -> None:
    """Emit one structured log line at the end of each /api/chat or /api/eval request."""
    _request_log.info(
        "request_summary",
        session_id=session_id,
        request_id=request_id,
        intent=intent,
        intent_confidence=round(intent_confidence, 4),
        workflow_routed_to=workflow_routed_to,
        retrieval_passage_count=retrieval_passage_count,
        latency_ms=round(latency_ms, 2),
        downgrade_occurred=downgrade_occurred,
        error=error,
        status="error" if error else "ok",
    )


def log_error(
    stage: str,
    exc: Exception,
    *,
    session_id: str = "unknown",
    request_id: str = "unknown",
    intent: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """
    Emit a structured error log with traceback.

    stage: the pipeline stage that failed — e.g. "intent_classification",
           "slot_filling", "workflow_routing", "display_adapter", "redis"
    """
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    _error_log.error(
        "pipeline_error",
        stage=stage,
        session_id=session_id,
        request_id=request_id,
        intent=intent,
        error_type=type(exc).__name__,
        error_msg=str(exc),
        traceback="".join(tb).strip(),
        **(extra or {}),
    )


def log_pipeline_event(
    event: str,
    *,
    session_id: str = "unknown",
    request_id: str = "unknown",
    **kwargs,
) -> None:
    """
    Emit a mid-pipeline diagnostic event.

    event examples: "intent_classified", "gatekeeper_failed", "slot_prompted",
                    "retrieval_complete", "workflow_result_built"
    """
    _pipeline_log.info(
        event,
        session_id=session_id,
        request_id=request_id,
        **kwargs,
    )
