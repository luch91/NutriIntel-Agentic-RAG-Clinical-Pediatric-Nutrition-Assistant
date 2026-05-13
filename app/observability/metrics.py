"""
app/observability/metrics.py — Prometheus metrics for CPNA v1.

All counters and histograms are module-level singletons.
The /metrics endpoint (app/api/router.py) calls generate_latest() to expose them.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

# Total requests, labelled by query type and terminal status (ok / error / clarification)
cpna_requests_total = Counter(
    "cpna_requests_total",
    "Total /api/chat requests processed",
    ["query_type", "status"],
)

# Intent confidence distribution — 0.1-width buckets from 0 to 1
cpna_intent_confidence = Histogram(
    "cpna_intent_confidence",
    "Distribution of intent classifier confidence scores",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

# End-to-end request latency, labelled by query type
cpna_latency_seconds = Histogram(
    "cpna_latency_seconds",
    "End-to-end latency per /api/chat request in seconds",
    ["query_type"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Therapy → recommendation downgrades, labelled by reason
cpna_downgrade_total = Counter(
    "cpna_downgrade_total",
    "Number of therapy→recommendation downgrades",
    ["downgrade_reason"],
)

# Requests where classifier confidence fell below CONFIDENCE_THRESHOLD
cpna_low_confidence_total = Counter(
    "cpna_low_confidence_total",
    "Number of requests with intent confidence below threshold",
)
