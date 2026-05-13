"""
DrugNutrientInteractionChecker — checks medications against known nutrient interactions.

nutrient_calculator.py has no drug-nutrient logic; all rules are new here.
"""

from __future__ import annotations

from enum import Enum
from typing import List
from pydantic import BaseModel


class InteractionType(str, Enum):
    DEPLETION = "DEPLETION"
    COMPETITION = "COMPETITION"
    ABSORPTION_EFFECT = "ABSORPTION_EFFECT"


class Severity(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class DrugNutrientInteraction(BaseModel):
    drug: str
    nutrient: str
    interaction_type: InteractionType
    severity: Severity
    clinical_note: str
    source: str


# ---------------------------------------------------------------------------
# Interaction rule table
# Each entry: (drug_keywords, nutrient, interaction_type, severity, clinical_note, source)
# drug_keywords: list of lowercase strings; any match triggers the rule
# ---------------------------------------------------------------------------

_RULES: list[tuple] = [
    (
        ["metformin"],
        "Vitamin B12",
        InteractionType.DEPLETION,
        Severity.HIGH,
        "Metformin reduces ileal absorption of Vitamin B12 via calcium-dependent mechanism; monitor B12 levels annually and supplement if deficient.",
        "Ting 2014, JAMA",
    ),
    (
        ["carbamazepine", "valproate", "phenytoin", "anticonvulsant"],
        "Vitamin D",
        InteractionType.DEPLETION,
        Severity.MODERATE,
        "Anticonvulsants induce hepatic CYP450 enzymes, accelerating catabolism of Vitamin D; consider supplementation and monitor 25-OH-D levels.",
        "Holick 2007, NEJM; Pittschieler 2010, Epilepsy Research",
    ),
    (
        ["cholestyramine"],
        "Vitamin A",
        InteractionType.COMPETITION,
        Severity.MODERATE,
        "Cholestyramine binds bile acids and fat-soluble vitamins in the gut; administer fat-soluble vitamins (A, D, E, K) at least 4 hours apart.",
        "Compendium of Pharmaceuticals and Specialties",
    ),
    (
        ["cholestyramine"],
        "Vitamin D",
        InteractionType.COMPETITION,
        Severity.MODERATE,
        "Cholestyramine reduces absorption of Vitamin D; administer separately by ≥4 hours.",
        "Compendium of Pharmaceuticals and Specialties",
    ),
    (
        ["cholestyramine"],
        "Vitamin E",
        InteractionType.COMPETITION,
        Severity.MODERATE,
        "Cholestyramine reduces absorption of Vitamin E; administer separately.",
        "Compendium of Pharmaceuticals and Specialties",
    ),
    (
        ["cholestyramine"],
        "Vitamin K",
        InteractionType.COMPETITION,
        Severity.MODERATE,
        "Cholestyramine reduces absorption of Vitamin K; monitor coagulation and administer separately.",
        "Compendium of Pharmaceuticals and Specialties",
    ),
    (
        ["corticosteroid", "prednisolone", "prednisone", "dexamethasone", "hydrocortisone"],
        "Calcium",
        InteractionType.DEPLETION,
        Severity.MODERATE,
        "Corticosteroids reduce intestinal calcium absorption and increase renal excretion; supplement calcium and Vitamin D with long-term use.",
        "Rizzoli 2013, Bone",
    ),
    (
        ["corticosteroid", "prednisolone", "prednisone", "dexamethasone", "hydrocortisone"],
        "Vitamin D",
        InteractionType.DEPLETION,
        Severity.MODERATE,
        "Corticosteroids impair Vitamin D metabolism; supplement and monitor 25-OH-D levels.",
        "Rizzoli 2013, Bone",
    ),
    (
        ["creon", "pancrelipase", "pancreatin"],
        "Fat absorption",
        InteractionType.ABSORPTION_EFFECT,
        Severity.LOW,
        "Creon (pancrelipase) is an enzyme replacement — not a depletion risk. Must be administered with all meals and snacks to optimise fat absorption in cystic fibrosis. Dose adjustment per fat content of meal.",
        "ESPGHAN 2016 CF Nutrition Consensus",
    ),
]


class DrugNutrientInteractionChecker:
    """Check a medication list against known drug-nutrient interaction rules."""

    def check(
        self,
        medications: List[str],
        nutrients: List[str],
    ) -> List[DrugNutrientInteraction]:
        """
        Return all interactions for the given medication and nutrient lists.

        medications: list of medication names (case-insensitive matching).
        nutrients: list of nutrient names to filter against.
                   Pass an empty list to return all interactions for the medications.
        """
        meds_lower = [m.strip().lower() for m in medications]
        nutrients_lower = {n.strip().lower() for n in nutrients} if nutrients else None

        results: List[DrugNutrientInteraction] = []
        seen: set = set()

        for (keywords, nutrient, itype, severity, note, source) in _RULES:
            # Check if any medication matches any keyword for this rule
            matched_drug: str | None = None
            for med in meds_lower:
                for kw in keywords:
                    if kw in med:
                        matched_drug = med
                        break
                if matched_drug:
                    break

            if matched_drug is None:
                continue

            # Filter by requested nutrients if specified
            if nutrients_lower is not None and nutrient.lower() not in nutrients_lower:
                continue

            dedup_key = (matched_drug, nutrient)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            results.append(DrugNutrientInteraction(
                drug=matched_drug,
                nutrient=nutrient,
                interaction_type=itype,
                severity=severity,
                clinical_note=note,
                source=source,
            ))

        return results
