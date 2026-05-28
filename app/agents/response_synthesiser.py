"""
ResponseSynthesiser — rewrites display-adapter prose fields using an LLM.

Uses Groq API (llama-3.1-8b-instant) to turn structured workflow data into
natural, readable clinical language. All numeric and structured fields
(nutrient_targets, drug_nutrient_notes, evidence_summary, etc.) are left
strictly untouched — only prose strings are rewritten.

Falls back silently to the original response on any API error, so the system
degrades gracefully if the Groq key is absent or the API is down.

Safety rules enforced via system prompt:
  - Ground strictly in the provided context — no invented values, dosages,
    or clinical claims not present in the source data.
  - Never add recommendations not supported by the supplied evidence.
  - Return only the requested field — no preamble, no markdown formatting.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

_MODEL = "llama-3.1-8b-instant"
_TEMPERATURE = 0.3
_MAX_TOKENS = 300

_SAFETY_RULE = (
    "IMPORTANT: Ground every sentence strictly in the provided data. "
    "Do NOT add clinical values, dosages, or recommendations not explicitly "
    "present in the supplied context. Do NOT use markdown formatting. "
    "Write in plain, professional clinical English suitable for a dietitian."
)

# ---------------------------------------------------------------------------
# Per-intent system prompts
# ---------------------------------------------------------------------------

_SYSTEM_THERAPY = (
    "You are a clinical dietitian assistant summarising a paediatric nutrition therapy plan. "
    "You will be given structured patient data and nutrient targets computed by a deterministic engine. "
    "Rewrite the provided text into clear, warm, professional clinical prose a dietitian would use "
    "when presenting a plan to a clinical team. "
    + _SAFETY_RULE
)

_SYSTEM_RECOMMENDATION = (
    "You are a paediatric nutrition advisor. "
    "You will be given evidence excerpts from clinical nutrition references. "
    "Write a concise, practical dietary recommendation grounded strictly in the provided evidence. "
    "Use plain language suitable for a healthcare professional. "
    + _SAFETY_RULE
)

_SYSTEM_COMPARISON = (
    "You are a clinical nutrition analyst. "
    "You will be given evidence excerpts comparing two foods or nutrients. "
    "Write a clear, balanced interpretive summary of the comparison. "
    "State key differences and clinical relevance based only on the provided evidence. "
    + _SAFETY_RULE
)

_SYSTEM_GENERAL = (
    "You are a paediatric nutrition information specialist. "
    "You will be given evidence excerpts from clinical nutrition references. "
    "Write a clear, accessible explanation that directly answers the user's question "
    "using only the provided evidence. Use plain language. "
    + _SAFETY_RULE
)


def _truncate(text: str, max_chars: int = 1200) -> str:
    """Truncate long text to stay within token limits."""
    return text[:max_chars] + "…" if len(text) > max_chars else text


def _format_evidence(evidence_items: list) -> str:
    """Format evidence excerpts into a concise context block."""
    if not evidence_items:
        return "No retrieved evidence available."
    parts = []
    for i, item in enumerate(evidence_items[:5], 1):  # cap at 5 sources
        title = item.get("source_title", "Unknown source")
        excerpt = _truncate(item.get("excerpt", item.get("excerpt_safe", "")), 300)
        if excerpt:
            parts.append(f"[{i}] {title}: {excerpt}")
    return "\n".join(parts) if parts else "No retrieved evidence available."


class ResponseSynthesiser:
    """
    LLM-backed prose synthesiser for CPNA display responses.

    All structured fields (nutrient targets, drug notes, evidence items, etc.)
    are preserved exactly — only human-readable prose fields are rewritten.

    Pass a groq.Groq client for testing / dependency injection.
    If no client is supplied, one is created lazily using GROQ_API_KEY env var.
    If GROQ_API_KEY is not set, synthesis is skipped and originals are returned.
    """

    def __init__(self, client: Optional[object] = None) -> None:
        self._client = client

    def _get_client(self) -> Optional[object]:
        if self._client is not None:
            return self._client
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            return None
        try:
            import groq  # lazy import
            return groq.Groq(api_key=api_key)
        except Exception as exc:
            logger.warning("ResponseSynthesiser: could not create Groq client: %s", exc)
            return None

    def _call(self, system: str, user: str) -> Optional[str]:
        """Make one Groq completion call. Returns None on any failure."""
        client = self._get_client()
        if client is None:
            return None
        try:
            response = client.chat.completions.create(  # type: ignore[union-attr]
                model=_MODEL,
                temperature=_TEMPERATURE,
                max_tokens=_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            text = response.choices[0].message.content.strip()
            return text or None
        except Exception as exc:
            logger.warning("ResponseSynthesiser: API error — %s", str(exc).encode("ascii", "replace").decode("ascii"))
            return None

    # ------------------------------------------------------------------
    # Public entry points — one per intent type
    # ------------------------------------------------------------------

    def synthesise_therapy(
        self,
        patient_summary: str,
        nutrient_targets: list,
        drug_notes: list,
        evidence: list,
    ) -> dict:
        """
        Returns dict with keys: summary, patient_summary
        Numeric/structured fields are passed through unchanged.
        """
        targets_text = "; ".join(
            f"{t.get('nutrient','')}: {t.get('final_value', t.get('value',''))} {t.get('unit','')}"
            for t in nutrient_targets[:10]
        )
        drugs_text = "; ".join(
            f"{d.get('drug','')} affects {d.get('nutrient','')}"
            for d in drug_notes[:5]
        ) or "None documented."
        evidence_text = _format_evidence(evidence)

        user_prompt = (
            f"Patient summary from deterministic engine:\n{_truncate(patient_summary, 400)}\n\n"
            f"Nutrient targets (DO NOT change these values):\n{targets_text}\n\n"
            f"Drug-nutrient interactions:\n{drugs_text}\n\n"
            f"Retrieved evidence:\n{evidence_text}\n\n"
            f"Task: Write a 2–3 sentence clinical summary introducing this therapy plan. "
            f"Reference the condition and key nutritional priorities only. "
            f"Do not repeat the numeric targets — they appear separately."
        )
        summary = self._call(_SYSTEM_THERAPY, user_prompt)

        patient_prompt = (
            f"Original patient summary:\n{_truncate(patient_summary, 600)}\n\n"
            f"Task: Rewrite this as a clear, concise 2–3 sentence patient profile "
            f"a dietitian would present in a clinical handover. Keep all clinical facts exactly."
        )
        new_patient_summary = self._call(_SYSTEM_THERAPY, patient_prompt)

        return {
            "summary": summary,
            "patient_summary": new_patient_summary,
        }

    def synthesise_recommendation(
        self,
        evidence: list,
        context_summary: str,
        condition_hint: str = "",
    ) -> dict:
        """
        Returns dict with keys: summary, context_summary, practical_guidance
        """
        evidence_text = _format_evidence(evidence)
        condition_str = f" for {condition_hint}" if condition_hint else ""

        user_prompt = (
            f"Context: {_truncate(context_summary, 300)}\n\n"
            f"Retrieved evidence{condition_str}:\n{evidence_text}\n\n"
            f"Task: Write:\n"
            f"1. A 1-sentence summary of the dietary recommendation.\n"
            f"2. A 1-sentence context summary explaining what this recommendation covers.\n"
            f"3. 2–3 sentences of practical guidance grounded in the evidence.\n"
            f"Separate each with '|||'."
        )
        raw = self._call(_SYSTEM_RECOMMENDATION, user_prompt)

        summary = context_out = guidance = None
        if raw:
            parts = [p.strip() for p in raw.split("|||")]
            summary = parts[0] if len(parts) > 0 else None
            context_out = parts[1] if len(parts) > 1 else None
            guidance = parts[2] if len(parts) > 2 else None

        return {
            "summary": summary,
            "context_summary": context_out,
            "practical_guidance": guidance,
        }

    def synthesise_comparison(
        self,
        entity_a: str,
        entity_b: str,
        evidence: list,
        comparison_mode: str,
    ) -> dict:
        """
        Returns dict with keys: summary, executive_takeaway, interpretation
        """
        evidence_text = _format_evidence(evidence)

        user_prompt = (
            f"Comparing: {entity_a} vs {entity_b}\n"
            f"Mode: {comparison_mode}\n\n"
            f"Retrieved evidence:\n{evidence_text}\n\n"
            f"Task: Write:\n"
            f"1. A 1-sentence summary of the comparison.\n"
            f"2. A 1–2 sentence executive takeaway highlighting the most clinically relevant difference.\n"
            f"3. A 1–2 sentence interpretation guiding clinical application.\n"
            f"Separate each with '|||'."
        )
        raw = self._call(_SYSTEM_COMPARISON, user_prompt)

        summary = takeaway = interpretation = None
        if raw:
            parts = [p.strip() for p in raw.split("|||")]
            summary = parts[0] if len(parts) > 0 else None
            takeaway = parts[1] if len(parts) > 1 else None
            interpretation = parts[2] if len(parts) > 2 else None

        return {
            "summary": summary,
            "executive_takeaway": takeaway,
            "interpretation": interpretation,
        }

    def synthesise_general(
        self,
        query_hint: str,
        evidence: list,
    ) -> dict:
        """
        Returns dict with keys: summary, direct_answer, explanation
        """
        evidence_text = _format_evidence(evidence)

        user_prompt = (
            f"User question (paraphrased): {_truncate(query_hint, 200)}\n\n"
            f"Retrieved evidence:\n{evidence_text}\n\n"
            f"Task: Write:\n"
            f"1. A 1-sentence summary of the topic.\n"
            f"2. A direct answer to the question in 1–2 sentences.\n"
            f"3. A 2–3 sentence explanation with supporting detail from the evidence.\n"
            f"Separate each with '|||'."
        )
        raw = self._call(_SYSTEM_GENERAL, user_prompt)

        summary = direct_answer = explanation = None
        if raw:
            parts = [p.strip() for p in raw.split("|||")]
            summary = parts[0] if len(parts) > 0 else None
            direct_answer = parts[1] if len(parts) > 1 else None
            explanation = parts[2] if len(parts) > 2 else None

        return {
            "summary": summary,
            "direct_answer": direct_answer,
            "explanation": explanation,
        }
