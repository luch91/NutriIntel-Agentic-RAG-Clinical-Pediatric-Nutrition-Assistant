"""
app/observability/logger.py — Structured JSON request logger.

Emits one log event per /api/chat request with derived metadata only.
NEVER logs: user message text, biomarker values, medication names, weight, height.
"""

from __future__ import annotations

import logging
from typing import Optional

import structlog

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(),
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)

_slog = structlog.get_logger("cpna.request")


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
    """Emit one structured log line at the end of each /api/chat request."""
    _slog.info(
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
    )
