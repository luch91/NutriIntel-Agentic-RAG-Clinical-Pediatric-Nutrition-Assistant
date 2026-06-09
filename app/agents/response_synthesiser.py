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
_MAX_TOKENS_STRUCTURED = 2048  # full 30-row nutrient table with up to 5 entity columns

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

# ---------------------------------------------------------------------------
# Full nutrient definitions — display name → FCT aliases + unit
# Used by synthesise_comparison_structured to always emit all rows.
# ---------------------------------------------------------------------------
NUTRIENT_DEFINITIONS: List[dict] = [
    {"display": "Energy",         "unit": "kcal", "aliases": ["ENERC_KCAL", "ENERGY_KC", "ENERC", "Kcal", "kcal", "kJ"]},
    {"display": "Water",          "unit": "g",    "aliases": ["WATER", "H2O"]},
    {"display": "Protein",        "unit": "g",    "aliases": ["PROCNT", "PROTEIN", "A_PROTEI", "PROTCNT"]},
    {"display": "Fat",            "unit": "g",    "aliases": ["FAT", "FATCE"]},
    {"display": "Carbohydrate",   "unit": "g",    "aliases": ["CHOCDF", "CHO", "CHOAVLDF", "CHO AVAIL"]},
    {"display": "Fibre",          "unit": "g",    "aliases": ["FIBTG", "FIBRE", "FIB", "FIBRE. TOTAL DIETARY", "FIBRE TOTAL"]},
    {"display": "Ash",            "unit": "g",    "aliases": ["ASH"]},
    {"display": "Calcium",        "unit": "mg",   "aliases": ["CA", "Ca", "CALCIUM"]},
    {"display": "Iron",           "unit": "mg",   "aliases": ["FE", "Fe", "IRON"]},
    {"display": "Magnesium",      "unit": "mg",   "aliases": ["MG", "Mg", "MAGNESIUM"]},
    {"display": "Phosphorus",     "unit": "mg",   "aliases": ["P", "PHOSPHORUS", "PHOS"]},
    {"display": "Potassium",      "unit": "mg",   "aliases": ["K", "POTASSIUM"]},
    {"display": "Sodium",         "unit": "mg",   "aliases": ["NA", "Na", "SODIUM"]},
    {"display": "Zinc",           "unit": "mg",   "aliases": ["ZN", "Zn", "ZINC"]},
    {"display": "Copper",         "unit": "mg",   "aliases": ["CU", "Cu", "COPPER"]},
    {"display": "Vit A RE",       "unit": "µg",   "aliases": ["VITA_RE", "VITA", "VIT_A_RE", "VITA(RE)"]},
    {"display": "Vit A RAE",      "unit": "µg",   "aliases": ["VITA_RAE", "RAE"]},
    {"display": "Retinol",        "unit": "µg",   "aliases": ["RETOL", "RETINOL"]},
    {"display": "Beta-carotene",  "unit": "µg",   "aliases": ["CARTB", "BCAROT"]},
    {"display": "Vit D",          "unit": "µg",   "aliases": ["VITD", "VIT_D"]},
    {"display": "Vit E",          "unit": "mg",   "aliases": ["VITE", "TOCPHA"]},
    {"display": "Thiamine",       "unit": "mg",   "aliases": ["THIA", "THIAMINE", "VIT_B1"]},
    {"display": "Riboflavin",     "unit": "mg",   "aliases": ["RIBF", "RIBOFLAVIN", "VIT_B2"]},
    {"display": "Niacin equiv",   "unit": "mg",   "aliases": ["NE", "NIACIN_EQUIV"]},
    {"display": "Niacin",         "unit": "mg",   "aliases": ["NIA", "NIACIN"]},
    {"display": "Tryptophan",     "unit": "mg",   "aliases": ["TRP", "TRYPTOPHAN"]},
    {"display": "Vit B6",         "unit": "mg",   "aliases": ["VITB6A", "VIT_B6"]},
    {"display": "Folate",         "unit": "µg",   "aliases": ["FOL", "FOLATE"]},
    {"display": "Folate equiv",   "unit": "µg",   "aliases": ["FOLAC", "DFE"]},
    {"display": "Vit B12",        "unit": "µg",   "aliases": ["VITB12", "VIT_B12"]},
    {"display": "Vit C",          "unit": "mg",   "aliases": ["VITC", "VIT_C", "ASCORBIC"]},
]

# Map a user-supplied dimension string to the matching subset of NUTRIENT_DEFINITIONS.
# Accepts a single term ("zinc") or a comma/and-separated list ("zinc and iron" / "zinc, iron").
# If None/empty or no matches → return all definitions.
def _resolve_nutrient_targets(dimension: Optional[str]) -> List[dict]:
    if not dimension:
        return NUTRIENT_DEFINITIONS
    # Split on "and", "or", commas so "zinc and iron" → ["zinc", "iron"]
    import re as _re2
    terms = [t.strip() for t in _re2.split(r'[,\s]+(?:and|or)[,\s]+|,', dimension, flags=_re2.IGNORECASE) if t.strip()]
    if not terms:
        terms = [dimension.strip()]
    matched = []
    seen = set()
    for term in terms:
        term_lower = term.lower()
        for nd in NUTRIENT_DEFINITIONS:
            if nd["display"] in seen:
                continue
            if term_lower in nd["display"].lower():
                matched.append(nd)
                seen.add(nd["display"])
                continue
            if any(term_lower in a.lower() for a in nd["aliases"]):
                matched.append(nd)
                seen.add(nd["display"])
    return matched if matched else NUTRIENT_DEFINITIONS

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

        Always emits one row per nutrient in the target list (NUTRIENT_DEFINITIONS or the
        dimension-filtered subset). Missing values are represented as "—" rather than being
        omitted, so the table always has the full shape.

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

        # Determine the nutrient target list
        nutrient_targets = _resolve_nutrient_targets(dimension)

        # Build context blocks — one per entity using passages tagged with 'entity' field
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
            raw_context = "\n\n---\n\n".join(
                f"[Source: {item.get('source_title', 'FCT')}]\n"
                f"{_truncate(item.get('excerpt', ''), 600)}"
                for item in evidence[:7]
            )

        # Build column key map
        col_keys = [f"value_{chr(97 + i)}" for i in range(len(entities))]
        entity_lines = "\n".join(
            f"  Food {chr(65 + i)} ({col_keys[i]}): {entity}"
            for i, entity in enumerate(entities)
        )
        col_rules = "\n".join(
            f"- {col_keys[i]} is ONLY for {entities[i]} — never copy another food's number here"
            for i in range(len(entities))
        )

        # Build the nutrient extraction target list with all aliases
        nutrient_lines = "\n".join(
            f'  {nd["display"]} ({nd["unit"]}): look for any of {", ".join(nd["aliases"])}'
            for nd in nutrient_targets
        )

        example_row = _json.dumps(
            {"nutrient": "Protein", "unit": "g", **{k: "—" for k in col_keys}}
        )

        # Full required rows list for the "always emit" rule
        required_rows = ", ".join(f'"{nd["display"]}"' for nd in nutrient_targets)

        # Increase token budget for full 30-row tables
        max_tokens = max(_MAX_TOKENS_STRUCTURED, 200 + len(nutrient_targets) * 60)

        user_prompt = (
            f"You are a clinical nutrition data extraction assistant.\n\n"
            f"Below are raw excerpts from Food Composition Tables (West African FCT / Kenyan FCT). "
            f"Each food's data is in its own labelled block. "
            f"Data may appear in columnar format — numbers follow fixed column positions defined by "
            f"the column header row at the top of each table section (e.g. EDIBLE ENERC WATER PROTCNT FAT CHOAVLDF FIBTG ASH ...).\n\n"
            f"Foods to extract:\n{entity_lines}\n\n"
            f"Nutrients to extract (search ALL listed aliases for each nutrient):\n{nutrient_lines}\n\n"
            f"FCT Data:\n{raw_context}\n\n"
            f"Return ONLY valid JSON — no markdown, no code fences, no explanation.\n"
            f"Structure:\n"
            f'{{"matrix_rows": [{example_row}, ...], '
            f'"serving_basis": "per 100g", "data_quality": "good|partial|not_found", "key_insight": "..."}}\n\n'
            f"STRICT RULES:\n"
            f"1. Each food has its own context block labelled [FOOD NAME IN CAPS]. "
            f"ONLY read data for a food from its OWN labelled block.\n"
            f"{col_rules}\n"
            f"2. ALWAYS emit one row for EVERY nutrient in this list: {required_rows}. "
            f"If a value is not found, use the string \"—\" (not null, not 0, not omit).\n"
            f"3. data_quality: 'good' = all foods have at least macronutrients; "
            f"'partial' = some foods found; 'not_found' = no food data found.\n"
            f"4. key_insight: one sentence on the most clinically relevant finding, or null."
        )

        client = self._get_client()
        if client is None:
            return {"matrix_rows": [], "points_a": [], "points_b": [], "data_quality": "not_found"}

        try:
            response = client.chat.completions.create(  # type: ignore[union-attr]
                model=_MODEL,
                temperature=0,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": (
                        "You extract structured nutritional data from Food Composition Table text. "
                        "Return only valid JSON as instructed. No prose. "
                        "Always emit a row for every requested nutrient; use \"—\" for missing values."
                    )},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = response.choices[0].message.content.strip()
            raw = _CODE_FENCE.sub("", raw).strip()
            parsed = _json.loads(raw)
            matrix_rows = parsed.get("matrix_rows", [])

            # Validate row shape — must have nutrient field
            llm_rows = {
                r["nutrient"]: r for r in matrix_rows
                if isinstance(r, dict) and "nutrient" in r
            }

            # Merge LLM output with full nutrient list — always emit every row
            clean_rows = []
            for nd in nutrient_targets:
                row = llm_rows.get(nd["display"], {})
                merged: dict = {"nutrient": nd["display"], "unit": nd["unit"]}
                for k in col_keys:
                    val = row.get(k)
                    merged[k] = str(val) if val is not None and val != "" else "—"
                clean_rows.append(merged)

            any_real = any(
                row.get(col_keys[0], "—") != "—" for row in clean_rows
            )
            return {
                "matrix_rows": clean_rows,
                "points_a": [],
                "points_b": [],
                "serving_basis": parsed.get("serving_basis", "per 100g"),
                "data_quality": parsed.get("data_quality", "partial" if any_real else "not_found"),
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
