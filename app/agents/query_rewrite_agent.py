"""
QueryRewriteAgent — rewrites the user query into retrieval-optimised form.

Uses Groq API (llama-3.1-8b-instant) via the groq SDK.
Falls back to the original query if the API call fails.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_MODEL = "llama-3.1-8b-instant"
_MAX_TOKENS = 128

_SYSTEM_PROMPT = (
    "You are a medical retrieval query optimiser for a pediatric nutrition RAG system. "
    "Rewrite the user query into a concise, keyword-rich retrieval query that will maximise "
    "relevant passage recall from a clinical nutrition knowledge base. "
    "Return ONLY the rewritten query — no explanation, no preamble."
)


class QueryRewriteAgent:
    """
    Wraps Groq SDK to rewrite queries for better retrieval recall.

    Pass a groq.Groq client for testing / dependency injection.
    If no client is supplied, one is created using the GROQ_API_KEY env var.
    """

    def __init__(self, client: Optional[object] = None) -> None:
        self._client = client

    def _get_client(self) -> object:
        if self._client is not None:
            return self._client
        import groq  # lazy import
        return groq.Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

    def rewrite(self, query: str, patient_context: str = "") -> str:
        """
        Return a retrieval-optimised version of query.

        patient_context is an optional free-text summary of known patient data
        (e.g. "8yo female, cystic fibrosis, weight 25 kg") that helps the model
        produce more targeted rewrites.  May be empty.

        Falls back to the original query on any API error.
        """
        if not query.strip():
            return query

        user_content = query
        if patient_context.strip():
            user_content = f"Patient context: {patient_context}\n\nQuery: {query}"

        try:
            client = self._get_client()
            response = client.chat.completions.create(  # type: ignore[union-attr]
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            )
            rewritten = response.choices[0].message.content.strip()
            logger.debug("QueryRewriteAgent: '%s' → '%s'", query, rewritten)
            return rewritten or query
        except Exception as exc:
            logger.warning("QueryRewriteAgent: API error (%s) — using original query", exc)
            return query
