"""
routing_config.py — single source of truth for condition-to-source routing.

Source IDs match exactly what chapter_extractor.py produces in metadata["source"]:
  Shaw2020, OxfordHandbook2012, ClinicalNutrition2013, VitMinRequirements,
  PretermNeonate2013, DrugNutrient2024, IntegrativeBiochem2022,
  WestAfricaFCT2019, DRI2006
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Condition alias map — CLAUDE.md diagnosis strings → routing keys
# ---------------------------------------------------------------------------

CONDITION_ALIAS_MAP: Dict[str, str] = {
    "type 1 diabetes": "t1d",
    "t1d": "t1d",
    "cystic fibrosis": "cystic_fibrosis",
    "food allergy": "food_allergy",
    "preterm nutrition": "preterm",
    "preterm": "preterm",
    "chronic kidney disease": "ckd",
    "ckd": "ckd",
    "pku": "imd",
    "msud": "imd",
    "galactosemia": "imd",
    "inherited metabolic disorder": "imd",
    "epilepsy/ketogenic therapy": "epilepsy_keto",
    "epilepsy": "epilepsy_keto",
    "ketogenic": "epilepsy_keto",
    "ibd": "gi_disorders",
    "gerd": "gi_disorders",
    "gi disorders": "gi_disorders",
}

# All 8 routing keys (used by cross-condition logic)
_ALL_ROUTING_KEYS: List[str] = [
    "t1d", "cystic_fibrosis", "food_allergy", "preterm",
    "ckd", "imd", "epilepsy_keto", "gi_disorders",
]

# ---------------------------------------------------------------------------
# Cross-condition sources — included in every THERAPY retrieval pass
# ---------------------------------------------------------------------------

CROSS_CONDITION_SOURCES: Dict[str, Any] = {
    "IntegrativeBiochem2022": "all",
}

# ---------------------------------------------------------------------------
# Condition routing table
# ---------------------------------------------------------------------------

CONDITION_ROUTING: Dict[str, Dict] = {
    "preterm": {
        "sources": {
            "PretermNeonate2013": "all",
            "Shaw2020": [7, 5, 4],
            "IntegrativeBiochem2022": ["6.2", "7.4", "8.4", "9.3"],
            "DrugNutrient2024": [18, 10, 26],
            "WestAfricaFCT2019": "all",
        },
        "priority_source": "PretermNeonate2013",
        "always_include": ["dri_structured", "DrugNutrient2024__ch18"],
    },
    "t1d": {
        "sources": {
            "Shaw2020": [11, 2],
            "IntegrativeBiochem2022": ["8.4", "8.4.2", "9.2", "9.3",
                                       "9.4", "8.2", "8.3"],
            "OxfordHandbook2012": [22],
            "WestAfricaFCT2019": "all",
            "DrugNutrient2024": [18],
        },
        "priority_source": "Shaw2020",
        "always_include": ["dri_structured"],
    },
    "food_allergy": {
        "sources": {
            "Shaw2020": [15, 16, 26],
            "OxfordHandbook2012": [37],
            "DrugNutrient2024": [18, 23],
            "WestAfricaFCT2019": "all",
        },
        "priority_source": "Shaw2020",
        "always_include": ["dri_structured"],
    },
    "cystic_fibrosis": {
        "sources": {
            "Shaw2020": [12, 4, 5],
            "ClinicalNutrition2013": [24],
            "OxfordHandbook2012": [30],
            "IntegrativeBiochem2022": ["7.4", "3.1", "4", "5"],
            "DrugNutrient2024": [18, 17],
            "VitMinRequirements": [5, 6, 3, 2],
            "WestAfricaFCT2019": "all",
        },
        "priority_source": "Shaw2020",
        "always_include": ["dri_structured", "DrugNutrient2024__ch18"],
    },
    "imd": {
        "sources": {
            "Shaw2020": [27, 28, 29, 30, 31],
            "IntegrativeBiochem2022": ["7.5", "7.5.2", "7.3", "3.3",
                                       "3.3.2", "9.3", "9.3.1", "5", "5.2"],
            "ClinicalNutrition2013": [6],
            "OxfordHandbook2012": [36],
            "DrugNutrient2024": [18],
            "WestAfricaFCT2019": "all",
        },
        "priority_source": "Shaw2020",
        "always_include": ["dri_structured"],
    },
    "epilepsy_keto": {
        "sources": {
            "Shaw2020": [17],
            "IntegrativeBiochem2022": ["7.4.6", "7.4", "7.4.1",
                                       "9.4", "9.4.2", "6.2"],
            "OxfordHandbook2012": [33],
            "DrugNutrient2024": [16, 18],
            "WestAfricaFCT2019": "all",
        },
        "priority_source": "Shaw2020",
        "always_include": ["dri_structured", "DrugNutrient2024__ch16"],
    },
    "ckd": {
        "sources": {
            "Shaw2020": [13],
            "ClinicalNutrition2013": [14],
            "OxfordHandbook2012": [29],
            "IntegrativeBiochem2022": ["8.3", "9.3", "5", "5.2"],
            "DrugNutrient2024": [17, 18],
            "VitMinRequirements": [4, 11, 12, 13],
            "DRI2006": ["water"],
            "WestAfricaFCT2019": "all",
        },
        "priority_source": "Shaw2020",
        "always_include": ["dri_structured", "DrugNutrient2024__ch17"],
    },
    "gi_disorders": {
        "sources": {
            "Shaw2020": [8, 9, 10],
            "ClinicalNutrition2013": [11, 12, 13],
            "OxfordHandbook2012": [26],
            "IntegrativeBiochem2022": ["7.3", "7.4", "3.1", "4", "5"],
            "DrugNutrient2024": [18, 26],
            "WestAfricaFCT2019": "all",
        },
        "priority_source": "Shaw2020",
        "always_include": ["dri_structured"],
    },
}


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def normalize_condition(diagnosis: str) -> Optional[str]:
    """Map a CLAUDE.md diagnosis string to a routing key. Returns None if unknown."""
    if not diagnosis:
        return None
    return CONDITION_ALIAS_MAP.get(diagnosis.lower().strip())


def get_allowed_sources(routing_key: str) -> List[str]:
    """
    Return all source_id strings for a routing key, including cross-condition sources.
    Returns [] for unknown keys — never raises.
    """
    if not routing_key or routing_key not in CONDITION_ROUTING:
        if routing_key:
            logger.warning("get_allowed_sources: unknown routing_key '%s'", routing_key)
        return []

    condition_sources = list(CONDITION_ROUTING[routing_key]["sources"].keys())
    cross_sources = list(CROSS_CONDITION_SOURCES.keys())

    # Merge, preserving order, no duplicates
    merged: List[str] = []
    seen = set()
    for src in condition_sources + cross_sources:
        if src not in seen:
            merged.append(src)
            seen.add(src)
    return merged


def get_priority_source(routing_key: str) -> Optional[str]:
    """Return the priority source for a routing key. Returns None if unknown — never raises."""
    if not routing_key or routing_key not in CONDITION_ROUTING:
        return None
    return CONDITION_ROUTING[routing_key].get("priority_source")


def get_condition_tags_for_chunk(source_id: str, chapter_key: Any) -> List[str]:
    """
    Inverse lookup: returns list of routing keys (conditions) that reference
    this source_id + chapter_key combination.

    chapter_key may be int, str, or float — all are normalised for comparison.
    If source appears with "all", includes that condition regardless of chapter_key.
    If source_id is in CROSS_CONDITION_SOURCES, returns all 8 condition keys.
    Returns [] if source_id not referenced anywhere — never raises.
    """
    try:
        # Cross-condition source → all 8 conditions
        if source_id in CROSS_CONDITION_SOURCES:
            return list(_ALL_ROUTING_KEYS)

        tags: List[str] = []
        chapter_key_str = str(chapter_key)

        for routing_key, config in CONDITION_ROUTING.items():
            sources = config.get("sources", {})
            if source_id not in sources:
                continue

            chapters = sources[source_id]

            if chapters == "all":
                tags.append(routing_key)
                continue

            # chapters is a list — normalise each element to str for comparison
            if any(str(ch) == chapter_key_str for ch in chapters):
                tags.append(routing_key)

        return tags
    except Exception as exc:
        logger.warning("get_condition_tags_for_chunk error: %s", exc)
        return []
