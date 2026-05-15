"""
Unit tests for the retrieval source-filter fix.

Covers:
1. _source_matches() — correct matching, case/separator normalisation, non-matches
2. RetrievalAgent source filter — allowed_sources eliminates wrong-source passages,
   passes correct-source passages, and is skipped when allowed_sources is empty
3. Priority boosting — priority-source passages are promoted to the front
4. startup_ingestion._collect_pdf_paths() — finds PDFs in the data directory
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.agents.retrieval_agent import RetrievalAgent, RetrievalResult, _source_matches
from app.retrieval import RetrievedPassage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _passage(passage_id: str, source_title: str, text: str = "sample text") -> RetrievedPassage:
    return RetrievedPassage(
        passage_id=passage_id,
        text=text,
        source_title=source_title,
        source_type="test",
        score=0.8,
    )


def _make_agent(vec_results: list, bm25_results: list) -> RetrievalAgent:
    """
    Build a RetrievalAgent with fully mocked sub-components so no ML runs.
    vec_results and bm25_results are returned verbatim from the mock retrievers.
    """
    mock_vector = MagicMock()
    mock_vector.embed_query.return_value = [0.0] * 384
    mock_vector.search.return_value = vec_results

    mock_bm25 = MagicMock()
    mock_bm25.search.return_value = bm25_results

    mock_reranker = MagicMock()
    # Reranker passes passages through unchanged, preserving order
    mock_reranker.rerank.side_effect = lambda query, passages, top_k: passages[:top_k]

    mock_rewriter = MagicMock()
    mock_rewriter.rewrite.side_effect = lambda query, ctx="": query

    return RetrievalAgent(
        vector_retriever=mock_vector,
        bm25_retriever=mock_bm25,
        reranker=mock_reranker,
        query_rewrite_agent=mock_rewriter,
    )


# ---------------------------------------------------------------------------
# Tests: _source_matches
# ---------------------------------------------------------------------------

class TestSourceMatches:

    def test_exact_match(self):
        p = _passage("abc123", "Shaw2020")
        assert _source_matches(p, "Shaw2020")

    def test_case_insensitive(self):
        p = _passage("abc123", "shaw2020")
        assert _source_matches(p, "Shaw2020")

    def test_underscores_ignored(self):
        p = _passage("abc123", "West_Africa_FCT_2019")
        assert _source_matches(p, "WestAfricaFCT2019")

    def test_spaces_ignored(self):
        p = _passage("abc123", "West Africa FCT 2019")
        assert _source_matches(p, "WestAfricaFCT2019")

    def test_hyphens_ignored(self):
        p = _passage("abc123", "Drug-Nutrient2024")
        assert _source_matches(p, "DrugNutrient2024")

    def test_source_title_is_prefix_match(self):
        # source_title may contain the full book name; source_id is a short key
        p = _passage("abc123", "WestAfricaFCT2019 — Legumes Chapter")
        assert _source_matches(p, "WestAfricaFCT2019")

    def test_no_match_different_source(self):
        p = _passage("abc123", "Shaw2020")
        assert not _source_matches(p, "WestAfricaFCT2019")

    def test_no_match_partial_overlap(self):
        p = _passage("abc123", "PretermNeonate2013")
        assert not _source_matches(p, "Preterm2013")  # different key

    def test_md5_passage_id_ignored(self):
        """passage_id is an MD5 hex — should have no effect on matching."""
        p = _passage("a1b2c3d4e5f6a7b8", "DrugNutrient2024")
        assert _source_matches(p, "DrugNutrient2024")
        assert not _source_matches(p, "Shaw2020")


# ---------------------------------------------------------------------------
# Tests: RetrievalAgent source filter
# ---------------------------------------------------------------------------

class TestRetrievalAgentSourceFilter:

    # Shared test passages
    _shaw_p = _passage("md5abc001", "Shaw2020", "cystic fibrosis management")
    _fct_p  = _passage("md5abc002", "WestAfricaFCT2019", "bambara nut zinc 3.2mg")
    _dri_p  = _passage("md5abc003", "DRI2006", "vitamin D 600 IU children")

    def test_filter_keeps_allowed_sources(self):
        """Passages whose source_title matches an allowed source are kept."""
        agent = _make_agent(
            vec_results=[self._shaw_p, self._fct_p, self._dri_p],
            bm25_results=[],
        )
        with patch(
            "app.agents.retrieval_agent.get_allowed_sources",
            return_value=["Shaw2020"],
        ):
            result = agent.retrieve("cystic fibrosis nutrition", diagnosis="cystic fibrosis")

        ids = [p.passage_id for p in result.passages]
        assert "md5abc001" in ids, "Shaw2020 passage should pass the filter"
        assert "md5abc002" not in ids, "FCT passage should be filtered out"
        assert "md5abc003" not in ids, "DRI passage should be filtered out"

    def test_filter_removed_when_allowed_sources_empty(self):
        """When no routing key resolves (e.g. COMPARISON), all passages pass."""
        agent = _make_agent(
            vec_results=[self._shaw_p, self._fct_p, self._dri_p],
            bm25_results=[],
        )
        # diagnosis=None → allowed_sources=[] → filter skipped
        result = agent.retrieve("compare bambara nut vs groundnut")
        ids = [p.passage_id for p in result.passages]
        assert "md5abc001" in ids
        assert "md5abc002" in ids
        assert "md5abc003" in ids

    def test_bm25_filter_also_applied(self):
        """BM25 results are filtered by the same allowed_sources list."""
        agent = _make_agent(
            vec_results=[],
            bm25_results=[self._shaw_p, self._fct_p],
        )
        with patch(
            "app.agents.retrieval_agent.get_allowed_sources",
            return_value=["WestAfricaFCT2019"],
        ):
            result = agent.retrieve("zinc iron legumes", diagnosis="preterm")

        ids = [p.passage_id for p in result.passages]
        assert "md5abc002" in ids
        assert "md5abc001" not in ids

    def test_empty_store_returns_empty_result(self):
        """When both vector and BM25 return nothing, result is an empty list."""
        agent = _make_agent(vec_results=[], bm25_results=[])
        result = agent.retrieve("cystic fibrosis fat malabsorption")
        assert isinstance(result, RetrievalResult)
        assert result.passages == []

    def test_md5_passage_ids_do_not_break_filter(self):
        """
        passage_id is a 16-char MD5 hex. The old startswith filter would return
        False for every passage. The new source_title filter must work correctly.
        """
        shaw_md5 = _passage("a3f9d81c2e74b056", "Shaw2020", "cystic fibrosis")
        fct_md5  = _passage("b1e4c92f3a5d7080", "WestAfricaFCT2019", "bambara nut")

        agent = _make_agent(
            vec_results=[shaw_md5, fct_md5],
            bm25_results=[],
        )
        # normalize_condition must return a non-None key so get_allowed_sources is called
        with (
            patch("app.agents.retrieval_agent.normalize_condition", return_value="cystic_fibrosis"),
            patch("app.agents.retrieval_agent.get_allowed_sources", return_value=["Shaw2020"]),
        ):
            result = agent.retrieve("cystic fibrosis", diagnosis="cystic_fibrosis")

        ids = [p.passage_id for p in result.passages]
        assert "a3f9d81c2e74b056" in ids, "Shaw2020 passage with MD5 id should pass"
        assert "b1e4c92f3a5d7080" not in ids, "FCT passage with MD5 id should be filtered"


# ---------------------------------------------------------------------------
# Tests: priority source boosting
# ---------------------------------------------------------------------------

class TestPrioritySourceBoosting:

    def test_priority_source_passages_ranked_first(self):
        """Priority source passages must appear before non-priority ones."""
        shaw_p1 = _passage("md5s01", "Shaw2020", "cystic fibrosis chapter 12")
        shaw_p2 = _passage("md5s02", "Shaw2020", "cystic fibrosis enzymes")
        other_p = _passage("md5o01", "DrugNutrient2024", "drug interactions CF")

        agent = _make_agent(
            vec_results=[other_p, shaw_p1, shaw_p2],
            bm25_results=[],
        )
        with (
            patch("app.agents.retrieval_agent.normalize_condition", return_value="cystic_fibrosis"),
            patch("app.agents.retrieval_agent.get_allowed_sources", return_value=["Shaw2020", "DrugNutrient2024"]),
            patch("app.agents.retrieval_agent.get_priority_source", return_value="Shaw2020"),
        ):
            result = agent.retrieve("cystic fibrosis fat malabsorption", diagnosis="cystic_fibrosis")

        ids = [p.passage_id for p in result.passages]
        shaw_positions = [i for i, pid in enumerate(ids) if pid.startswith("md5s")]
        other_positions = [i for i, pid in enumerate(ids) if pid.startswith("md5o")]
        if shaw_positions and other_positions:
            assert max(shaw_positions) < min(other_positions), (
                f"Shaw2020 passages should all precede non-priority passages. "
                f"Got order: {ids}"
            )

    def test_no_priority_source_does_not_crash(self):
        """When get_priority_source returns None, the pipeline continues normally."""
        p = _passage("md5abc", "Shaw2020", "PKU phenylalanine")
        agent = _make_agent(vec_results=[p], bm25_results=[])
        with patch("app.agents.retrieval_agent.get_priority_source", return_value=None):
            result = agent.retrieve("PKU low protein diet")
        assert isinstance(result, RetrievalResult)


# ---------------------------------------------------------------------------
# Tests: startup_ingestion._collect_pdf_paths
# ---------------------------------------------------------------------------

class TestCollectPdfPaths:

    def test_finds_pdfs_in_data_dir(self):
        """_collect_pdf_paths returns at least the known West Africa FCT PDF."""
        from app.retrieval.startup_ingestion import _collect_pdf_paths, _DATA_DIR

        paths = _collect_pdf_paths()
        assert len(paths) > 0, "Expected PDFs in app/common/data/"
        names = [Path(p).name.lower() for p in paths]
        assert any("west africa" in n or "food composition table for west africa" in n for n in names), (
            "West Africa FCT PDF not found in data dir"
        )

    def test_all_paths_are_absolute(self):
        from app.retrieval.startup_ingestion import _collect_pdf_paths
        for path in _collect_pdf_paths():
            assert Path(path).is_absolute(), f"Expected absolute path, got: {path}"

    def test_all_paths_exist(self):
        from app.retrieval.startup_ingestion import _collect_pdf_paths
        for path in _collect_pdf_paths():
            assert Path(path).exists(), f"Path returned but does not exist: {path}"

    def test_returns_empty_for_missing_dir(self, tmp_path):
        """When the data dir doesn't exist, returns [] without raising."""
        from app.retrieval import startup_ingestion

        nonexistent = tmp_path / "no_such_dir"
        with patch.object(startup_ingestion, "_DATA_DIR", nonexistent):
            paths = startup_ingestion._collect_pdf_paths()
        assert paths == []

    def test_only_pdfs_returned(self):
        """Non-PDF files in the data directory are excluded."""
        from app.retrieval.startup_ingestion import _collect_pdf_paths
        for path in _collect_pdf_paths():
            assert Path(path).suffix.lower() == ".pdf", (
                f"Non-PDF file in results: {path}"
            )
