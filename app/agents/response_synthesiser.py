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
_MAX_TOKENS_STRUCTURED = 900  # higher budget for JSON extraction

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


import json as _json
import re as _re
_LABEL_PREFIX = _re.compile(r"^\d+\.\s*")
_CODE_FENCE = _re.compile(r"^```[a-z]*\n?|\n?```$")

def _clean_part(text: str) -> str:
    """Strip leading numbered labels the model echoes back (e.g. '1. ')."""
    return _LABEL_PREFIX.sub("", text).strip() or None


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
        api_key = (os.environ.get("GROQ_API_KEY") or "").strip().lstrip("﻿")
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
            f"Write exactly three parts, each on its own line, separated by '|||'.\n"
            f"Part 1: one sentence summarising the dietary recommendation.\n"
            f"Part 2: one sentence stating what this recommendation covers.\n"
            f"Part 3: two to three sentences of practical guidance from the evidence.\n"
            f"Output format: <Part 1> ||| <Part 2> ||| <Part 3>"
        )
        raw = self._call(_SYSTEM_RECOMMENDATION, user_prompt)

        summary = context_out = guidance = None
        if raw:
            parts = [_clean_part(p) for p in raw.split("|||")]
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
            f"Write exactly three parts, each on its own line, separated by '|||'.\n"
            f"Part 1: one sentence summarising the comparison.\n"
            f"Part 2: one to two sentences on the most clinically relevant difference.\n"
            f"Part 3: one to two sentences guiding clinical application.\n"
            f"Output format: <Part 1> ||| <Part 2> ||| <Part 3>"
        )
        raw = self._call(_SYSTEM_COMPARISON, user_prompt)

        summary = takeaway = interpretation = None
        if raw:
            parts = [_clean_part(p) for p in raw.split("|||")]
            summary = parts[0] if len(parts) > 0 else None
            takeaway = parts[1] if len(parts) > 1 else None
            interpretation = parts[2] if len(parts) > 2 else None

        return {
            "summary": summary,
            "executive_takeaway": takeaway,
            "interpretation": interpretation,
        }

    def _synthesise_comparison_structured_legacy(
        self,
        entity_a: str,
        entity_b: str,
        evidence: list,
        dimension: Optional[str] = None,
        extra_entities: Optional[list] = None,
    ) -> dict:
        """Legacy two-entity extractor — kept for reference."""
        return self.synthesise_comparison_structured(
            entities=[entity_a, entity_b] + (extra_entities or []),
            evidence=evidence,
            dimension=dimension,
        )

    def synthesise_comparison_structured(
        self,
        entities: Optional[List[str]] = None,
        evidence: Optional[list] = None,
        dimension: Optional[str] = None,
        # Legacy keyword args kept for callers that pass entity_a/entity_b directly
        entity_a: Optional[str] = None,
        entity_b: Optional[str] = None,
        extra_entities: Optional[list] = None,
    ) -> dict:
        """
        Extracts structured nutrient comparison data from FCT passages for 2–5 entities.

        Returns a dict with keys:
          matrix_rows   — list of {nutrient, unit, value_a, value_b[, value_c, ...]}
                          column keys match entity order: value_a=entities[0], value_b=entities[1], etc.
          points_a      — list of str (qualitative fallback, entity[0])
          points_b      — list of str (qualitative fallback, entity[1])
          serving_basis — str
          data_quality  — "good" | "partial" | "not_found"
          key_insight   — str | None
        Falls back to empty lists on any failure so the caller can degrade gracefully.
        """
        # Resolve entities — support both new (entities=[...]) and legacy (entity_a/entity_b) call styles
        if entities is None:
            entities = [e for e in [entity_a, entity_b] + (extra_entities or []) if e]
        if not entities or len(entities) < 2:
            return {"matrix_rows": [], "points_a": [], "points_b": [], "data_quality": "not_found"}
        if evidence is None:
            evidence = []
        if not evidence:
            return {"matrix_rows": [], "points_a": [], "points_b": [], "data_quality": "not_found"}

        # Build context blocks — one per entity using passages tagged with 'entity' field
        # (per-entity retrieval tags each passage). Fall back to a shared pool if not tagged.
        tagged = any(item.get("entity") for item in evidence)
        if tagged:
            raw_context_parts = []
            for entity in entities:
                entity_items = [e for e in evidence if e.get("entity") == entity]
                if not entity_items:
                    raw_context_parts.append(f"[{entity.upper()}]\nNo passages retrieved.")
                    continue
                block = "\n".join(
                    _truncate(item.get("excerpt", ""), 600) for item in entity_items[:4]
                )
                raw_context_parts.append(f"[{entity.upper()}]\n{block}")
            raw_context = "\n\n---\n\n".join(raw_context_parts)
        else:
            # Shared pool fallback (legacy path)
            raw_context = "\n\n---\n\n".join(
                f"[Source: {item.get('source_title', 'FCT')}]\n"
                f"{_truncate(item.get('excerpt', ''), 600)}"
                for item in evidence[:7]
            )

        target_nutrients = dimension if dimension else (
            "energy (kcal), protein (g), fat (g), carbohydrate (g), "
            "iron (mg), zinc (mg), calcium (mg), vitamin A (µg)"
        )

        # Build dynamic entity label lines and column key map
        col_keys = [f"value_{chr(97 + i)}" for i in range(len(entities))]  # value_a, value_b, value_c …
        entity_lines = "\n".join(
            f"  Food {chr(65 + i)} ({col_keys[i]}): {entity}"
            for i, entity in enumerate(entities)
        )

        example_row = _json.dumps(
            {"nutrient": "Protein", "unit": "g", **{k: 0.0 for k in col_keys}}
        )

        col_rules = "\n".join(
            f"- {col_keys[i]} is for {entities[i]}"
            for i in range(len(entities))
        )

        user_prompt = (
            f"You are a clinical nutrition data extraction assistant.\n\n"
            f"Below are raw excerpts from Food Composition Tables (FCT). "
            f"Data may appear in columnar format without headers.\n\n"
            f"Extract {target_nutrients} for:\n{entity_lines}\n\n"
            f"FCT Data:\n{raw_context}\n\n"
            f"Return ONLY valid JSON — no markdown, no code fences, no explanation.\n"
            f"Structure:\n"
            f'{{"matrix_rows": [{example_row}, ...], '
            f'"serving_basis": "per 100g", "data_quality": "good", "key_insight": "..."}}\n\n'
            f"Rules:\n"
            f"- Each food has its own context block labelled [FOOD NAME IN CAPS]. "
            f"Only read data for a food from its OWN labelled block — do NOT use another food's numbers as a proxy.\n"
            f"- Include only nutrients found in the source data. Omit rows where no food has data.\n"
            f"{col_rules}\n"
            f"- data_quality: 'good' (all foods found), 'partial' (some found), 'not_found' (none).\n"
            f"- key_insight: one sentence on the most clinically relevant finding, or null.\n"
            f"- Omit a column key entirely from a row if that food has no data for that nutrient."
        )

        client = self._get_client()
        if client is None:
            return {"matrix_rows": [], "points_a": [], "points_b": [], "data_quality": "not_found"}

        try:
            response = client.chat.completions.create(  # type: ignore[union-attr]
                model=_MODEL,
                temperature=0,
                max_tokens=_MAX_TOKENS_STRUCTURED,
                messages=[
                    {"role": "system", "content": (
                        "You extract structured nutritional data from Food Composition Table text. "
                        "Return only valid JSON as instructed. No prose."
                    )},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = response.choices[0].message.content.strip()
            raw = _CODE_FENCE.sub("", raw).strip()
            parsed = _json.loads(raw)
            matrix_rows = parsed.get("matrix_rows", [])
            # Validate row shape — must have nutrient + at least one value column
            clean_rows = [
                r for r in matrix_rows
                if isinstance(r, dict)
                and "nutrient" in r
                and any(k in r for k in col_keys)
            ]
            return {
                "matrix_rows": clean_rows,
                "points_a": [],
                "points_b": [],
                "serving_basis": parsed.get("serving_basis", "per 100g"),
                "data_quality": parsed.get("data_quality", "partial" if clean_rows else "not_found"),
                "key_insight": parsed.get("key_insight"),
            }
        except _json.JSONDecodeError as exc:
            logger.warning("synthesise_comparison_structured: JSON parse failed — %s", exc)
        except Exception as exc:
            logger.warning(
                "synthesise_comparison_structured: error — %s",
                str(exc).encode("ascii", "replace").decode("ascii"),
            )
        return {"matrix_rows": [], "points_a": [], "points_b": [], "data_quality": "not_found"}

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
            f"Write exactly three parts, each on its own line, separated by '|||'.\n"
            f"Part 1: one sentence summarising the topic.\n"
            f"Part 2: one to two sentences directly answering the question.\n"
            f"Part 3: two to three sentences of explanation with supporting detail.\n"
            f"Output format: <Part 1> ||| <Part 2> ||| <Part 3>"
        )
        raw = self._call(_SYSTEM_GENERAL, user_prompt)

        summary = direct_answer = explanation = None
        if raw:
            parts = [_clean_part(p) for p in raw.split("|||")]
            summary = parts[0] if len(parts) > 0 else None
            direct_answer = parts[1] if len(parts) > 1 else None
            explanation = parts[2] if len(parts) > 2 else None

        return {
            "summary": summary,
            "direct_answer": direct_answer,
            "explanation": explanation,
        }
