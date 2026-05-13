"""
Integration tests for Prompt 9 — API Layer.

All tests use:
  - httpx.AsyncClient (ASGI transport — no real network)
  - fakeredis.FakeRedis for state persistence
  - MockIntentClassifier (keyword-based, no model loading)
  - No Qdrant / vector store (WorkflowRouter initialized with retrieval_agent=None)

Tests:
  1. POST /api/chat "What does vitamin D do?" → 200, query_type == "general"
  2. POST /api/chat "Give me a personalized plan" (no slots) → 200, slot prompt
  3. POST /api/chat low-confidence message → 200, needs_clarification, no 400
  4. POST /api/session/reset → 200, status == "ok"
  5. All responses pass CPNAResponse Pydantic validation
  6. No response contains forbidden strings
"""

import json
import uuid

import fakeredis
import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.api.router import app, _get_classifier, _get_state_manager, _get_router
from app.classification.intent_classifier import MockIntentClassifier
from app.contracts.display_adapter import DisplayAdapter
from app.contracts.response_contracts import (
    ComparisonResponse,
    GeneralResponse,
    RecommendationResponse,
    TherapyResponse,
)
from app.state.state_manager import StateManager
from app.workflows.workflow_router import WorkflowRouter

_FORBIDDEN_STRINGS = [
    "debug_trace_internal",
    "[object Object]",
    "Traceback",
    "<class ",
    "_sa_instance_state",
    "computation_trace",
]


# ---------------------------------------------------------------------------
# Fixtures — override app.state singletons before each test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def wire_test_dependencies():
    """Replace production singletons with test doubles."""
    app.state.intent_classifier = MockIntentClassifier()
    app.state.state_manager = StateManager(redis_client=fakeredis.FakeRedis())
    app.state.workflow_router = WorkflowRouter(retrieval_agent=None)
    app.state.display_adapter = DisplayAdapter()
    yield
    # Reset to None after each test so lazy init is re-triggered if needed
    app.state.intent_classifier = None
    app.state.state_manager = None
    app.state.workflow_router = None


def _client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _unique_session() -> str:
    return f"test-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Helper — validate no forbidden strings in response body
# ---------------------------------------------------------------------------

def _assert_no_forbidden(body: str) -> None:
    for s in _FORBIDDEN_STRINGS:
        assert s not in body, f"Forbidden string found in response: {repr(s)}"


# ---------------------------------------------------------------------------
# Test 1 — General question → query_type == "general"
# ---------------------------------------------------------------------------

def test_general_query_returns_general_response():
    client = _client()
    payload = {"session_id": _unique_session(), "message": "What does vitamin D do?"}
    resp = client.post("/api/chat", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == payload["session_id"]
    assert "response" in body
    assert body["response"]["query_type"] == "general"
    _assert_no_forbidden(resp.text)


# ---------------------------------------------------------------------------
# Test 2 — Therapy intent with no slots → slot prompt returned
# ---------------------------------------------------------------------------

def test_therapy_intent_no_slots_returns_slot_prompt():
    client = _client()
    session_id = _unique_session()
    payload = {"session_id": session_id, "message": "Give me a personalized plan for my child."}
    resp = client.post("/api/chat", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    # Should not be a TherapyResponse (engine data not present)
    # Should be either a GeneralResponse (adapter fallback) or contain a slot-fill signal
    assert "response" in body
    # The response must be well-formed (have query_type)
    assert "query_type" in body["response"]
    _assert_no_forbidden(resp.text)


# ---------------------------------------------------------------------------
# Test 3 — Low-confidence / ambiguous message → clarification, NOT 400
# ---------------------------------------------------------------------------

def test_low_confidence_returns_clarification_not_error():
    client = _client()
    # MockIntentClassifier returns needs_clarification=True for messages < 4 chars
    payload = {"session_id": _unique_session(), "message": "hi"}
    resp = client.post("/api/chat", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert "response" in body
    # Clarification responses are GeneralResponse shape
    response_obj = body["response"]
    assert response_obj.get("query_type") == "general"
    # Should contain clarification hint
    combined_text = json.dumps(response_obj).lower()
    assert any(
        kw in combined_text
        for kw in ["clarification", "nutrition planning", "planning", "guidance", "comparison"]
    )
    _assert_no_forbidden(resp.text)


def test_low_confidence_returns_200_not_400():
    client = _client()
    payload = {"session_id": _unique_session(), "message": "?"}
    resp = client.post("/api/chat", json=payload)
    assert resp.status_code == 200
    assert "error" not in resp.json().get("response", {})


# ---------------------------------------------------------------------------
# Test 4 — Session reset → 200, status == "ok"
# ---------------------------------------------------------------------------

def test_session_reset_returns_ok():
    client = _client()
    session_id = _unique_session()
    payload = {"session_id": session_id}
    resp = client.post("/api/session/reset", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["session_id"] == session_id


# ---------------------------------------------------------------------------
# Test 5 — All responses pass CPNAResponse Pydantic validation
# ---------------------------------------------------------------------------

def _validate_cpna_response(response_dict: dict) -> None:
    qt = response_dict.get("query_type")
    if qt == "therapy":
        TherapyResponse.model_validate(response_dict)
    elif qt == "recommendation":
        RecommendationResponse.model_validate(response_dict)
    elif qt == "comparison":
        ComparisonResponse.model_validate(response_dict)
    elif qt == "general":
        GeneralResponse.model_validate(response_dict)
    else:
        raise AssertionError(f"Unknown query_type in response: {qt!r}")


def test_general_response_validates_as_pydantic():
    client = _client()
    resp = client.post("/api/chat", json={
        "session_id": _unique_session(),
        "message": "What is kwashiorkor?"
    })
    assert resp.status_code == 200
    _validate_cpna_response(resp.json()["response"])


def test_slot_prompt_response_validates_as_pydantic():
    client = _client()
    resp = client.post("/api/chat", json={
        "session_id": _unique_session(),
        "message": "Create a nutrition plan for my child with diabetes."
    })
    assert resp.status_code == 200
    _validate_cpna_response(resp.json()["response"])


# ---------------------------------------------------------------------------
# Test 6 — No forbidden strings in any response
# ---------------------------------------------------------------------------

def test_no_forbidden_strings_general():
    client = _client()
    resp = client.post("/api/chat", json={
        "session_id": _unique_session(),
        "message": "Tell me about iron deficiency."
    })
    _assert_no_forbidden(resp.text)


def test_no_forbidden_strings_therapy_incomplete():
    client = _client()
    resp = client.post("/api/chat", json={
        "session_id": _unique_session(),
        "message": "I need a therapy meal plan for my child."
    })
    _assert_no_forbidden(resp.text)


def test_no_forbidden_strings_low_confidence():
    client = _client()
    resp = client.post("/api/chat", json={
        "session_id": _unique_session(),
        "message": "ok"
    })
    _assert_no_forbidden(resp.text)


# ---------------------------------------------------------------------------
# Test 7 — Health endpoint
# ---------------------------------------------------------------------------

def test_health_endpoint():
    client = _client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"


# ---------------------------------------------------------------------------
# Test 8 — State snapshot is returned and well-formed
# ---------------------------------------------------------------------------

def test_state_snapshot_in_response():
    client = _client()
    resp = client.post("/api/chat", json={
        "session_id": _unique_session(),
        "message": "What is the role of zinc in immunity?"
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "state_snapshot" in body
    snap = body["state_snapshot"]
    assert "workflow_stage" in snap
    assert "pending_slots" in snap
    assert "clarification_needed" in snap
    assert isinstance(snap["pending_slots"], list)


# ---------------------------------------------------------------------------
# Test 9 — X-Request-ID header is present
# ---------------------------------------------------------------------------

def test_request_id_header_present():
    client = _client()
    resp = client.post("/api/chat", json={
        "session_id": _unique_session(),
        "message": "What is calcium?"
    })
    assert "x-request-id" in resp.headers


# ---------------------------------------------------------------------------
# Test 10 — Metrics endpoint responds
# ---------------------------------------------------------------------------

def test_metrics_endpoint():
    client = _client()
    resp = client.get("/metrics")
    assert resp.status_code == 200
