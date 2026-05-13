"""Unit tests for app/config/routing_config.py — Prompt 7."""

import pytest

from app.config.routing_config import (
    _ALL_ROUTING_KEYS,
    get_allowed_sources,
    get_condition_tags_for_chunk,
    get_priority_source,
    normalize_condition,
)


# ---------------------------------------------------------------------------
# normalize_condition
# ---------------------------------------------------------------------------

class TestNormalizeCondition:
    def test_type_1_diabetes(self):
        assert normalize_condition("type 1 diabetes") == "t1d"

    def test_t1d_alias(self):
        assert normalize_condition("t1d") == "t1d"

    def test_ibd_maps_to_gi_disorders(self):
        assert normalize_condition("ibd") == "gi_disorders"

    def test_gerd_maps_to_gi_disorders(self):
        assert normalize_condition("gerd") == "gi_disorders"

    def test_pku_maps_to_imd(self):
        assert normalize_condition("pku") == "imd"

    def test_msud_maps_to_imd(self):
        assert normalize_condition("msud") == "imd"

    def test_galactosemia_maps_to_imd(self):
        assert normalize_condition("galactosemia") == "imd"

    def test_preterm_nutrition(self):
        assert normalize_condition("preterm nutrition") == "preterm"

    def test_chronic_kidney_disease(self):
        assert normalize_condition("chronic kidney disease") == "ckd"

    def test_epilepsy_ketogenic_therapy(self):
        assert normalize_condition("epilepsy/ketogenic therapy") == "epilepsy_keto"

    def test_epilepsy_alias(self):
        assert normalize_condition("epilepsy") == "epilepsy_keto"

    def test_cystic_fibrosis(self):
        assert normalize_condition("cystic fibrosis") == "cystic_fibrosis"

    def test_food_allergy(self):
        assert normalize_condition("food allergy") == "food_allergy"

    def test_unknown_returns_none(self):
        assert normalize_condition("something unknown") is None

    def test_empty_string_returns_none(self):
        assert normalize_condition("") is None

    def test_case_insensitive(self):
        assert normalize_condition("TYPE 1 DIABETES") == "t1d"

    def test_strips_whitespace(self):
        assert normalize_condition("  pku  ") == "imd"


# ---------------------------------------------------------------------------
# get_allowed_sources
# ---------------------------------------------------------------------------

class TestGetAllowedSources:
    def test_ckd_includes_shaw2020(self):
        sources = get_allowed_sources("ckd")
        assert "Shaw2020" in sources

    def test_ckd_includes_west_africa(self):
        sources = get_allowed_sources("ckd")
        assert "WestAfricaFCT2019" in sources

    def test_ckd_includes_integrative_biochem(self):
        # IntegrativeBiochem2022 is a cross-condition source — always included
        sources = get_allowed_sources("ckd")
        assert "IntegrativeBiochem2022" in sources

    def test_t1d_includes_integrative_biochem(self):
        sources = get_allowed_sources("t1d")
        assert "IntegrativeBiochem2022" in sources

    def test_preterm_priority_source_present(self):
        sources = get_allowed_sources("preterm")
        assert "PretermNeonate2013" in sources

    def test_unknown_condition_returns_empty_list(self):
        assert get_allowed_sources("unknown_condition") == []

    def test_unknown_condition_does_not_raise(self):
        # Must never raise — documented contract
        result = get_allowed_sources("nonexistent_key_xyz")
        assert isinstance(result, list)

    def test_no_duplicates(self):
        sources = get_allowed_sources("cystic_fibrosis")
        assert len(sources) == len(set(sources))

    def test_empty_string_returns_empty_list(self):
        assert get_allowed_sources("") == []


# ---------------------------------------------------------------------------
# get_priority_source
# ---------------------------------------------------------------------------

class TestGetPrioritySource:
    def test_preterm_priority_is_preterm_neonate(self):
        assert get_priority_source("preterm") == "PretermNeonate2013"

    def test_t1d_priority_is_shaw2020(self):
        assert get_priority_source("t1d") == "Shaw2020"

    def test_ckd_priority_is_shaw2020(self):
        assert get_priority_source("ckd") == "Shaw2020"

    def test_cystic_fibrosis_priority_is_shaw2020(self):
        assert get_priority_source("cystic_fibrosis") == "Shaw2020"

    def test_unknown_returns_none(self):
        assert get_priority_source("unknown") is None

    def test_empty_string_returns_none(self):
        assert get_priority_source("") is None

    def test_does_not_raise_for_unknown(self):
        result = get_priority_source("definitely_not_a_real_key")
        assert result is None


# ---------------------------------------------------------------------------
# get_condition_tags_for_chunk
# ---------------------------------------------------------------------------

class TestGetConditionTagsForChunk:
    def test_shaw2020_chapter_13_includes_ckd(self):
        tags = get_condition_tags_for_chunk("Shaw2020", 13)
        assert "ckd" in tags

    def test_shaw2020_chapter_11_includes_t1d(self):
        tags = get_condition_tags_for_chunk("Shaw2020", 11)
        assert "t1d" in tags

    def test_shaw2020_chapter_12_includes_cystic_fibrosis(self):
        tags = get_condition_tags_for_chunk("Shaw2020", 12)
        assert "cystic_fibrosis" in tags

    def test_shaw2020_chapter_17_includes_epilepsy_keto(self):
        tags = get_condition_tags_for_chunk("Shaw2020", 17)
        assert "epilepsy_keto" in tags

    def test_west_africa_fct_returns_all_routing_keys(self):
        # WestAfricaFCT2019 is listed as "all" in every condition
        tags = get_condition_tags_for_chunk("WestAfricaFCT2019", 1)
        for key in _ALL_ROUTING_KEYS:
            assert key in tags, f"Expected '{key}' in tags for WestAfricaFCT2019"

    def test_integrative_biochem_returns_all_routing_keys(self):
        # IntegrativeBiochem2022 is in CROSS_CONDITION_SOURCES
        tags = get_condition_tags_for_chunk("IntegrativeBiochem2022", "7.4")
        for key in _ALL_ROUTING_KEYS:
            assert key in tags, f"Expected '{key}' in tags for IntegrativeBiochem2022"

    def test_integrative_biochem_any_chapter_returns_all(self):
        tags = get_condition_tags_for_chunk("IntegrativeBiochem2022", "3.1")
        assert len(tags) == len(_ALL_ROUTING_KEYS)

    def test_nonexistent_source_returns_empty(self):
        assert get_condition_tags_for_chunk("nonexistent_source", 1) == []

    def test_chapter_key_as_string_int(self):
        # chapter_key normalised: "13" and 13 must give same result
        tags_int = get_condition_tags_for_chunk("Shaw2020", 13)
        tags_str = get_condition_tags_for_chunk("Shaw2020", "13")
        assert set(tags_int) == set(tags_str)

    def test_does_not_raise_on_bad_input(self):
        result = get_condition_tags_for_chunk(None, None)
        assert isinstance(result, list)

    def test_preterm_neonate_source_includes_preterm(self):
        # PretermNeonate2013 is listed as "all" for preterm
        tags = get_condition_tags_for_chunk("PretermNeonate2013", 1)
        assert "preterm" in tags

    def test_drug_nutrient_chapter_18_in_multiple_conditions(self):
        # DrugNutrient2024 ch18 appears in preterm, t1d, food_allergy, imd, etc.
        tags = get_condition_tags_for_chunk("DrugNutrient2024", 18)
        assert len(tags) >= 2
