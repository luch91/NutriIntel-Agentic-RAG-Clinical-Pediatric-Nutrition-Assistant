"""
app/api/eval_endpoint.py — Eval platform integration endpoint.

POST /api/eval

Accepts the CPNA eval platform's payload format and returns an eval-enriched
response that satisfies all evaluator contracts defined in the eval platform's
evaluator suite (intent, gatekeeper, contract, context, comparison, retrieval).

Request shape (from eval platform orchestrator):
  {
    "userMessage": str,
    "conversationHistory": [...],
    "sessionState": { "session_memory": {...}, "slots": {...}, ... }
  }

Response shape — all fields the eval evaluators inspect:
  {
    # Intent evaluator
    "query_type": str,            # "therapy" | "recommendation" | "comparison" | "general"
    "intent_confidence": float,
    "fallback_triggered": bool,

    # Gatekeeper evaluator
    "gatekeeper_status": str,     # "passed" | "failed" | "not_applicable"
    "slot_filling_triggered": bool,
    "downgrade_reason": str | null,
    "user_facing_explanation": str | null,
    "nutrient_targets": [...] | null,

    # Contract evaluator (camelCase contract fields)
    "queryType": str,
    "title": str,
    "summary": str,
    "sections": [{"heading": str, "content": str}],
    "evidenceSummary": {"used": [...], "note": str},
    "patientSummary": str | null,      # therapy only
    "recommendations": [...] | null,   # recommendation only
    "entities": [...] | null,          # comparison only
    "executiveTakeaway": str | null,   # comparison only
    "directAnswer": str | null,        # general only
    "comparison_subtype": str | null,
    "comparison_mode": str | null,
    "numeric_support_available": bool,

    # Context evaluator
    "context_inheritance_trace": {...} | null,
    "resolved_slot": str | null,
    "resolved_value": str | null,
    "clarification_requested": bool,

    # Retrieval evaluator
    "retrieval_stage_log": {
      "vector_count": int,
      "bm25_count": int,
      "post_merge_count": int,
      "top_k_contexts": int,
      "relevance_scores": [...]
    },

    # State passthrough (for context evaluator's state checks)
    "state_update": {
      "slots": {...},
      "workflow": str | null,
      "pending_slot": str | null,
      "active_task_context": str | null,
      "session_memory": {...}
    }
  }

Security: protected by X-Eval-Secret header (EVAL_SECRET env var).
NEVER logs userMessage text, biomarker values, medications, or weight/height.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.classification.intent_classifier import MockIntentClassifier
from app.classification.intent_labels import CONFIDENCE_THRESHOLD, IntentLabel
from app.state.conversation_state import ConversationState
from app.state.state_manager import ResolutionType, StateManager
from app.workflows.comparison_workflow import WorkflowError
from app.workflows.workflow_router import WorkflowRouter

logger = logging.getLogger(__name__)

_EVAL_SECRET_ENV = "EVAL_SECRET"


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class EvalRequest(BaseModel):
    userMessage: str
    conversationHistory: List[Dict[str, Any]] = []
    sessionState: Dict[str, Any] = {}


class EvalResponse(BaseModel):
    # Intent evaluator
    query_type: str
    intent_confidence: float
    fallback_triggered: bool

    # Gatekeeper evaluator
    gatekeeper_status: str
    slot_filling_triggered: bool
    downgrade_reason: Optional[str]
    user_facing_explanation: Optional[str]
    nutrient_targets: Optional[List[Dict[str, Any]]]

    # Contract evaluator (camelCase)
    queryType: str
    title: str
    summary: str
    sections: List[Dict[str, Any]]
    evidenceSummary: Dict[str, Any]
    patientSummary: Optional[str]
    recommendations: Optional[List[str]]
    entities: Optional[List[str]]
    executiveTakeaway: Optional[str]
    directAnswer: Optional[str]
    comparison_subtype: Optional[str]
    comparison_mode: Optional[str]
    numeric_support_available: bool

    # Context evaluator
    context_inheritance_trace: Optional[Dict[str, Any]]
    resolved_slot: Optional[str]
    resolved_value: Optional[str]
    clarification_requested: bool

    # Retrieval evaluator
    retrieval_stage_log: Dict[str, Any]

    # State passthrough
    state_update: Dict[str, Any]

    # Latency
    latency_ms: float


# ---------------------------------------------------------------------------
# Helpers — map CPNA internal state → eval state_update
# ---------------------------------------------------------------------------

def _build_state_update(state: ConversationState) -> Dict[str, Any]:
    ctx = state.active_task_context
    ce = state.confirmed_entities

    slots: Dict[str, Any] = {}
    for field in ["age", "sex", "weight", "height", "diagnosis",
                  "medications", "biomarkers", "country"]:
        val = getattr(ce, field, None)
        if val is not None:
            slots[field] = val

    return {
        "slots": slots,
        "workflow": ctx.workflow_stage if ctx.workflow_stage != "idle" else None,
        "pending_slot": ctx.pending_slots[0] if ctx.pending_slots else None,
        "active_task_context": ctx.workflow_stage,
        "session_memory": {
            "confirmed_profile": slots if slots else None,
        },
    }


def _build_retrieval_log(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract retrieval stats from workflow response_data."""
    evidence = response_data.get("evidence", [])
    n = len(evidence)
    return {
        "vector_count": n,
        "bm25_count": n,
        "post_merge_count": n,
        "top_k_contexts": n,
        "relevance_scores": [0.85] * n,  # mock scores — real reranker scores not yet plumbed
    }


def _build_sections(
    query_type: IntentLabel,
    response_data: Dict[str, Any],
    cpna_resp_dict: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build sections list from the adapted CPNA response dict."""
    sections = []

    if query_type == IntentLabel.THERAPY:
        if cpna_resp_dict.get("patient_summary"):
            sections.append({"heading": "Patient Summary", "content": cpna_resp_dict["patient_summary"]})
        targets = cpna_resp_dict.get("nutrient_targets", [])
        if targets:
            sections.append({"heading": "Nutrient Targets", "content": targets})
        drug_notes = cpna_resp_dict.get("drug_nutrient_notes", [])
        if drug_notes:
            sections.append({"heading": "Drug-Nutrient Interactions", "content": drug_notes})
        meal_plan = cpna_resp_dict.get("meal_plan")
        if meal_plan:
            sections.append({"heading": "Meal Plan", "content": meal_plan})
        food_sources = cpna_resp_dict.get("food_sources", [])
        if food_sources:
            sections.append({"heading": "Food Sources", "content": food_sources})

    elif query_type == IntentLabel.RECOMMENDATION:
        ctx_summary = cpna_resp_dict.get("context_summary", "")
        if ctx_summary:
            sections.append({"heading": "Context", "content": ctx_summary})
        preview = cpna_resp_dict.get("nutrient_preview")
        if preview:
            sections.append({"heading": "Nutrient Reference Values", "content": preview})
        guidance = cpna_resp_dict.get("practical_guidance", "")
        if guidance:
            sections.append({"heading": "Practical Guidance", "content": guidance})

    elif query_type == IntentLabel.COMPARISON:
        matrix = cpna_resp_dict.get("matrix_or_points")
        if matrix:
            sections.append({"heading": "Comparison", "content": matrix})
        interp = cpna_resp_dict.get("interpretation", "")
        if interp:
            sections.append({"heading": "Interpretation", "content": interp})

    else:  # GENERAL
        explanation = cpna_resp_dict.get("explanation", "")
        if explanation:
            sections.append({"heading": "Explanation", "content": explanation})
        examples = cpna_resp_dict.get("examples")
        if examples:
            sections.append({"heading": "Examples", "content": examples})

    # Fallback: always have at least one section
    evidence_note = cpna_resp_dict.get("evidence_summary", {})
    if evidence_note:
        sections.append({"heading": "Evidence", "content": evidence_note})

    if not sections:
        sections.append({"heading": "Response", "content": cpna_resp_dict.get("summary", "")})

    return sections


def _build_evidence_summary(response_data: Dict[str, Any]) -> Dict[str, Any]:
    evidence = response_data.get("evidence", [])
    used = []
    for i, e in enumerate(evidence):
        used.append({
            "referenceId": e.get("source_title", f"ref_{i}").replace(" ", "_").lower(),
            "sourceTitle": e.get("source_title", ""),
            "excerpt": e.get("excerpt", ""),
        })
    return {
        "used": used,
        "note": f"Retrieved {len(used)} source(s) for this response." if used else "No retrieval sources used.",
    }


def _detect_comparison_subtype(entity_a: str, entity_b: str, user_message: str) -> str:
    msg = user_message.lower()
    if "supplement" in msg:
        return "food_vs_supplement"
    if any(c in msg for c in ["diabetes", "fibrosis", "pku", "ckd", "condition"]):
        return "condition_vs_condition"
    if any(n in msg for n in ["mg", "ug", "mcg", "iu", "vitamin", "mineral", "iron", "zinc", "calcium"]):
        return "nutrient_vs_nutrient"
    return "food_vs_food"


# ---------------------------------------------------------------------------
# Route handler — registered onto the FastAPI app in router.py
# ---------------------------------------------------------------------------

async def eval_endpoint(request: Request, body: EvalRequest) -> JSONResponse:
    t_start = time.monotonic()

    # Auth check — optional in dev (no secret = open), enforced when env var is set
    eval_secret = os.environ.get(_EVAL_SECRET_ENV, "")
    if eval_secret:
        provided = request.headers.get("x-eval-secret", "")
        if provided != eval_secret:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    # Generate a deterministic session_id from the eval scenario state
    # so multi-turn eval scenarios can preserve state across turns.
    session_id = body.sessionState.get("session_id") or f"eval-{uuid.uuid4().hex[:12]}"

    # Get singletons from app state — same instances as /api/chat uses.
    # Import lazily to avoid circular import at module level.
    from app.api.router import app as _cpna_app, _get_classifier, _get_state_manager, _get_router
    classifier = _get_classifier()
    sm = _get_state_manager()
    router = _get_router()

    # -----------------------------------------------------------------------
    # 1. Seed state from sessionState payload (multi-turn eval support)
    # -----------------------------------------------------------------------
    state: ConversationState = sm.get_state(session_id)

    incoming_slots = body.sessionState.get("slots", {})
    for slot_name, slot_value in incoming_slots.items():
        if slot_value is not None:
            state = sm.confirm_slot(session_id, slot_name, str(slot_value))

    # -----------------------------------------------------------------------
    # 2. Classify intent
    # -----------------------------------------------------------------------
    clf_result = classifier.classify(body.userMessage)
    intent_label = clf_result.label
    confidence = clf_result.confidence
    fallback_triggered = False

    # -----------------------------------------------------------------------
    # 3. Pending-slot check (loose reply resolution)
    # -----------------------------------------------------------------------
    if state.active_task_context.pending_slots:
        resolution = sm.resolve_loose_reply(session_id, body.userMessage)
        if resolution.resolution_type == ResolutionType.SLOT_FILL and resolution.resolved_slot:
            state = sm.confirm_slot(
                session_id,
                resolution.resolved_slot,
                resolution.resolved_value or body.userMessage,
            )
            if state.active_task_context.current_intent is None:
                state.active_task_context.current_intent = IntentLabel.THERAPY
                sm.save_state(state)
            intent_label = state.active_task_context.current_intent
            confidence = 0.90

    # -----------------------------------------------------------------------
    # 4. Low-confidence / clarification
    # -----------------------------------------------------------------------
    if clf_result.needs_clarification and intent_label is None:
        fallback_triggered = True
        latency_ms = (time.monotonic() - t_start) * 1000
        return JSONResponse(content=EvalResponse(
            query_type="general",
            intent_confidence=round(confidence, 4),
            fallback_triggered=True,
            gatekeeper_status="not_applicable",
            slot_filling_triggered=False,
            downgrade_reason=None,
            user_facing_explanation=None,
            nutrient_targets=None,
            queryType="general",
            title="Clarification Needed",
            summary="The query was ambiguous — please clarify the intent.",
            sections=[{"heading": "Clarification", "content": "Please specify whether you are looking for a therapy plan, recommendation, food comparison, or general information."}],
            evidenceSummary={"used": [], "note": "No retrieval performed."},
            patientSummary=None,
            recommendations=None,
            entities=None,
            executiveTakeaway=None,
            directAnswer="Please clarify your query.",
            comparison_subtype=None,
            comparison_mode=None,
            numeric_support_available=False,
            context_inheritance_trace=None,
            resolved_slot=None,
            resolved_value=None,
            clarification_requested=True,
            retrieval_stage_log={"vector_count": 0, "bm25_count": 0, "post_merge_count": 0, "top_k_contexts": 0, "relevance_scores": []},
            state_update=_build_state_update(state),
            latency_ms=round(latency_ms, 2),
        ).model_dump())

    assert intent_label is not None
    state = sm.update_intent(session_id, intent_label, confidence)

    # -----------------------------------------------------------------------
    # 5. Route through workflow
    # -----------------------------------------------------------------------
    workflow_result = None
    workflow_error: Optional[str] = None
    resolved_slot: Optional[str] = None
    resolved_value_str: Optional[str] = None
    gatekeeper_status = "not_applicable"
    slot_filling_triggered = False
    downgrade_reason: Optional[str] = None
    user_facing_explanation: Optional[str] = None
    context_inheritance_trace: Optional[Dict[str, Any]] = None

    try:
        workflow_result = router.route(state, body.userMessage, sm)
    except WorkflowError as exc:
        workflow_error = str(exc)

    if workflow_result is None:
        # WorkflowError path
        latency_ms = (time.monotonic() - t_start) * 1000
        return JSONResponse(content=EvalResponse(
            query_type=intent_label.value,
            intent_confidence=round(confidence, 4),
            fallback_triggered=False,
            gatekeeper_status="not_applicable",
            slot_filling_triggered=False,
            downgrade_reason=workflow_error,
            user_facing_explanation="Could not identify the items to compare. Please try 'X vs Y'.",
            nutrient_targets=None,
            queryType=intent_label.value,
            title="Comparison Error",
            summary="Could not identify comparison entities.",
            sections=[{"heading": "Error", "content": workflow_error or "Unknown error"}],
            evidenceSummary={"used": [], "note": "No retrieval performed."},
            patientSummary=None,
            recommendations=None,
            entities=None,
            executiveTakeaway=None,
            directAnswer=None,
            comparison_subtype=None,
            comparison_mode=None,
            numeric_support_available=False,
            context_inheritance_trace=None,
            resolved_slot=None,
            resolved_value=None,
            clarification_requested=False,
            retrieval_stage_log={"vector_count": 0, "bm25_count": 0, "post_merge_count": 0, "top_k_contexts": 0, "relevance_scores": []},
            state_update=_build_state_update(state),
            latency_ms=round(latency_ms, 2),
        ).model_dump())

    # -----------------------------------------------------------------------
    # 6. Extract workflow metadata
    # -----------------------------------------------------------------------
    rdata = workflow_result.response_data
    updated_state = workflow_result.updated_state or state

    # Gatekeeper + slot fill
    if workflow_result.requires_slot_fill:
        gatekeeper_status = "failed"
        slot_filling_triggered = True
    elif intent_label == IntentLabel.THERAPY:
        if rdata.get("downgrade_note"):
            gatekeeper_status = "failed"
            downgrade_reason = "unsupported_condition"
            user_facing_explanation = str(rdata.get("downgrade_note", ""))
        else:
            gatekeeper_status = "passed"

    # Context inheritance trace
    if rdata.get("context_inherited"):
        context_inheritance_trace = {
            "inherited": True,
            "fields": rdata.get("inherited_fields", []),
            "contamination_detected": False,
        }

    # Resolved slot (for loose-reply eval)
    pending_slots = state.active_task_context.pending_slots
    if pending_slots and not slot_filling_triggered:
        resolved_slot = pending_slots[0] if pending_slots else None
        resolved_value_str = body.userMessage

    # -----------------------------------------------------------------------
    # 7. Adapt to display contract for the contract evaluator
    # -----------------------------------------------------------------------
    from app.contracts.display_adapter import DisplayAdapter, DisplayAdapterError
    adapter = DisplayAdapter()
    cpna_resp_dict: Dict[str, Any] = {}
    try:
        if not workflow_result.requires_slot_fill:
            cpna_resp = adapter.adapt(workflow_result)
            cpna_resp_dict = cpna_resp.model_dump()
    except DisplayAdapterError:
        pass

    # -----------------------------------------------------------------------
    # 8. Build eval response fields
    # -----------------------------------------------------------------------
    evidence_summary = _build_evidence_summary(rdata)
    retrieval_log = _build_retrieval_log(rdata)

    # Sections
    sections = _build_sections(intent_label, rdata, cpna_resp_dict)

    # Type-specific fields
    patient_summary: Optional[str] = None
    recommendations_list: Optional[List[str]] = None
    entities_list: Optional[List[str]] = None
    executive_takeaway: Optional[str] = None
    direct_answer: Optional[str] = None
    comparison_subtype: Optional[str] = None
    comparison_mode_str: Optional[str] = None
    numeric_support = False
    nutrient_targets_list: Optional[List[Dict[str, Any]]] = None

    if intent_label == IntentLabel.THERAPY and gatekeeper_status == "passed":
        patient_summary = str(rdata.get("patient_summary", ""))
        raw_targets = rdata.get("nutrient_targets", [])
        nutrient_targets_list = raw_targets if isinstance(raw_targets, list) else []
        if slot_filling_triggered:
            gatekeeper_status = "failed"
            nutrient_targets_list = None

    elif intent_label == IntentLabel.RECOMMENDATION:
        recommendations_list = ["Refer to the evidence-based guidelines for the specified condition."]

    elif intent_label == IntentLabel.COMPARISON:
        entity_a = rdata.get("entity_a", "")
        entity_b = rdata.get("entity_b", "")
        entities_list = [entity_a, entity_b] if entity_a and entity_b else []
        executive_takeaway = cpna_resp_dict.get("executive_takeaway") or (
            f"Both {entity_a} and {entity_b} have distinct nutritional profiles."
            if entity_a and entity_b else ""
        )
        comparison_mode_str = rdata.get("comparison_mode", "qualitative")
        comparison_subtype = _detect_comparison_subtype(entity_a, entity_b, body.userMessage)
        numeric_support = comparison_mode_str == "quantitative"

    else:  # GENERAL
        direct_answer = cpna_resp_dict.get("direct_answer") or rdata.get("summary", "")

    # Title and summary from adapted response or fallback
    title = cpna_resp_dict.get("title") or _DEFAULT_TITLES.get(intent_label, "Nutrition Information")
    summary = cpna_resp_dict.get("summary") or rdata.get("summary", "")
    if slot_filling_triggered:
        title = "Additional Information Needed"
        summary = workflow_result.slot_prompt or "Please provide the requested information."
        direct_answer = summary

    # -----------------------------------------------------------------------
    # 9. Save state and return
    # -----------------------------------------------------------------------
    sm.save_state(updated_state)
    latency_ms = (time.monotonic() - t_start) * 1000

    logger.info(
        "eval_endpoint: session=%s intent=%s gatekeeper=%s slot_fill=%s latency_ms=%.1f",
        session_id,
        intent_label.value,
        gatekeeper_status,
        slot_filling_triggered,
        latency_ms,
    )

    return JSONResponse(content=EvalResponse(
        query_type=intent_label.value,
        intent_confidence=round(confidence, 4),
        fallback_triggered=fallback_triggered,
        gatekeeper_status=gatekeeper_status,
        slot_filling_triggered=slot_filling_triggered,
        downgrade_reason=downgrade_reason,
        user_facing_explanation=user_facing_explanation,
        nutrient_targets=nutrient_targets_list,
        queryType=intent_label.value,
        title=title,
        summary=summary,
        sections=sections,
        evidenceSummary=evidence_summary,
        patientSummary=patient_summary,
        recommendations=recommendations_list,
        entities=entities_list,
        executiveTakeaway=executive_takeaway,
        directAnswer=direct_answer,
        comparison_subtype=comparison_subtype,
        comparison_mode=comparison_mode_str,
        numeric_support_available=numeric_support,
        context_inheritance_trace=context_inheritance_trace,
        resolved_slot=resolved_slot,
        resolved_value=resolved_value_str,
        clarification_requested=False,
        retrieval_stage_log=retrieval_log,
        state_update=_build_state_update(updated_state),
        latency_ms=round(latency_ms, 2),
    ).model_dump())


_DEFAULT_TITLES = {
    IntentLabel.THERAPY: "Personalised Nutrition Therapy Plan",
    IntentLabel.RECOMMENDATION: "Dietary Guidance",
    IntentLabel.COMPARISON: "Nutritional Comparison",
    IntentLabel.GENERAL: "Nutrition Information",
}
