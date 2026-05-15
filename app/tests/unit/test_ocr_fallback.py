"""
Unit tests for the OCR fallback path in chapter_extractor.

Strategy:
- Tests run without real PDFs and without a live Tesseract binary.
- PyPDFLoader, fitz, and pytesseract are monkey-patched to control what
  "empty" vs "text" page content looks like.
- Verifies that _extract_text_with_ocr_fallback() is called when PyPDFLoader
  returns blank pages, that its output is used as chapter_text, and that
  chapters are still skipped when OCR also returns empty.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from langchain.docstore.document import Document

from app.common.chapter_extractor import extract_chapters_from_pdf


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pages(texts: list[str]) -> list[Document]:
    """Build a list of LangChain Documents simulating loaded PDF pages."""
    return [Document(page_content=t) for t in texts]


def _west_africa_blank_pages(n: int = 500) -> list[Document]:
    """500 blank pages — simulates a fully scanned FCT PDF."""
    return _make_pages([""] * n)


def _west_africa_text_pages(n: int = 500) -> list[Document]:
    """500 pages where FCT chapter 3 (pages 152-191) has legume data."""
    pages = [""] * n
    for i in range(151, 191):   # 0-indexed pages 152-191
        pages[i] = f"Legumes page {i + 1}: bambara nut protein 18g zinc 3.2mg"
    return _make_pages(pages)


# ---------------------------------------------------------------------------
# Tests for _extract_text_with_ocr_fallback
# ---------------------------------------------------------------------------

class TestExtractTextWithOcrFallback:
    """Direct unit tests for the OCR helper function."""

    def test_returns_string_on_success(self):
        """When fitz + pytesseract succeed, returns non-empty string."""
        from app.common.chapter_extractor import _extract_text_with_ocr_fallback  # type: ignore[attr-defined]

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value.tobytes.return_value = b"\x89PNG\r\n"

        mock_doc = MagicMock()
        mock_doc.page_count = 5
        mock_doc.__getitem__ = lambda self, i: mock_page
        mock_doc.close = MagicMock()

        with (
            patch("fitz.open", return_value=mock_doc),
            patch("pytesseract.image_to_string", return_value="bambara nut zinc 3.2mg"),
            patch("PIL.Image.open", return_value=MagicMock()),
        ):
            result = _extract_text_with_ocr_fallback("dummy.pdf", 1, 3)

        assert "bambara nut" in result
        assert "zinc" in result

    def test_returns_empty_on_fitz_failure(self):
        """When fitz.open raises, returns empty string without propagating."""
        from app.common.chapter_extractor import _extract_text_with_ocr_fallback  # type: ignore[attr-defined]

        with patch("fitz.open", side_effect=RuntimeError("fitz failure")):
            result = _extract_text_with_ocr_fallback("bad.pdf", 1, 3)

        assert result == ""

    def test_returns_empty_when_ocr_produces_blank(self):
        """When pytesseract returns only whitespace, result is effectively empty."""
        from app.common.chapter_extractor import _extract_text_with_ocr_fallback  # type: ignore[attr-defined]

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value.tobytes.return_value = b"\x89PNG\r\n"

        mock_doc = MagicMock()
        mock_doc.page_count = 2
        mock_doc.__getitem__ = lambda self, i: mock_page
        mock_doc.close = MagicMock()

        with (
            patch("fitz.open", return_value=mock_doc),
            patch("pytesseract.image_to_string", return_value="   \n\t  "),
            patch("PIL.Image.open", return_value=MagicMock()),
        ):
            result = _extract_text_with_ocr_fallback("dummy.pdf", 1, 2)

        assert result.strip() == ""

    def test_concatenates_multiple_pages(self):
        """Text from multiple pages is joined with double newlines."""
        from app.common.chapter_extractor import _extract_text_with_ocr_fallback  # type: ignore[attr-defined]

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value.tobytes.return_value = b"\x89PNG\r\n"

        mock_doc = MagicMock()
        mock_doc.page_count = 3
        mock_doc.__getitem__ = lambda self, i: mock_page
        mock_doc.close = MagicMock()

        page_texts = ["Page one content", "Page two content", "Page three content"]

        with (
            patch("fitz.open", return_value=mock_doc),
            patch("pytesseract.image_to_string", side_effect=page_texts),
            patch("PIL.Image.open", return_value=MagicMock()),
        ):
            result = _extract_text_with_ocr_fallback("dummy.pdf", 1, 3)

        assert "Page one content" in result
        assert "Page two content" in result
        assert "Page three content" in result


# ---------------------------------------------------------------------------
# Tests for extract_chapters_from_pdf — OCR integration path
# ---------------------------------------------------------------------------

class TestExtractChaptersOcrPath:
    """
    Tests that extract_chapters_from_pdf invokes OCR when PyPDFLoader
    returns empty chapters, and uses OCR output as the chapter text.
    """

    def _patch_loader(self, pages: list[Document]):
        """Return a patch context that makes PyPDFLoader yield `pages`."""
        mock_loader_instance = MagicMock()
        mock_loader_instance.load.return_value = pages
        return patch(
            "app.common.chapter_extractor.PyPDFLoader",
            return_value=mock_loader_instance,
        )

    def test_ocr_fallback_called_for_blank_chapters(self):
        """
        When all pages are blank, _extract_text_with_ocr_fallback must be
        called at least once (for the first blank chapter encountered).
        """
        pages = _west_africa_blank_pages(500)

        ocr_mock = MagicMock(return_value="OCR text: bambara nut zinc 3.2mg")

        with (
            self._patch_loader(pages),
            patch(
                "app.common.chapter_extractor._extract_text_with_ocr_fallback",
                ocr_mock,
            ),
        ):
            docs = extract_chapters_from_pdf("dummy.pdf", "west_africa_fct_2019")

        assert ocr_mock.called, "OCR fallback was not called for blank chapters"

    def test_ocr_text_used_as_chapter_content(self):
        """
        When PyPDFLoader returns blank pages but OCR succeeds, the returned
        Document should contain the OCR-extracted text.
        """
        pages = _west_africa_blank_pages(500)
        ocr_text = "Legumes chapter: bambara nut protein 18g zinc 3.2mg iron 3mg"

        with (
            self._patch_loader(pages),
            patch(
                "app.common.chapter_extractor._extract_text_with_ocr_fallback",
                return_value=ocr_text,
            ),
        ):
            docs = extract_chapters_from_pdf("dummy.pdf", "west_africa_fct_2019")

        assert len(docs) > 0, "Expected at least one document from OCR output"
        all_text = " ".join(d.page_content for d in docs)
        assert "bambara nut" in all_text

    def test_chapter_skipped_when_ocr_also_empty(self):
        """
        When both PyPDFLoader and OCR return empty, the chapter must be
        skipped — not added as a blank Document.
        """
        pages = _west_africa_blank_pages(500)

        with (
            self._patch_loader(pages),
            patch(
                "app.common.chapter_extractor._extract_text_with_ocr_fallback",
                return_value="",
            ),
        ):
            docs = extract_chapters_from_pdf("dummy.pdf", "west_africa_fct_2019")

        assert len(docs) == 0, "Blank OCR output should produce no documents"
        for doc in docs:
            assert doc.page_content.strip() != "", "Found a blank Document in output"

    def test_text_pdf_does_not_invoke_ocr(self):
        """
        When ALL chapters in a PDF have text content, OCR must NOT be called.
        We seed every page in the West Africa FCT range with text so no chapter
        falls through to the OCR path.
        """
        from app.common.chapter_extractor import WEST_AFRICA_FCT_TOC

        # Build pages where every page covered by the FCT TOC has content
        max_page = max(info["pages"][1] for info in WEST_AFRICA_FCT_TOC.values())
        page_texts = [f"Food data page {i}" for i in range(max_page + 10)]
        pages = _make_pages(page_texts)

        ocr_mock = MagicMock(return_value="should not be called")

        with (
            self._patch_loader(pages),
            patch(
                "app.common.chapter_extractor._extract_text_with_ocr_fallback",
                ocr_mock,
            ),
        ):
            docs = extract_chapters_from_pdf("dummy.pdf", "west_africa_fct_2019")

        assert not ocr_mock.called, "OCR was invoked unnecessarily for a text PDF"
        assert len(docs) > 0

    def test_metadata_preserved_after_ocr(self):
        """
        Documents produced from OCR content must carry the correct source_id
        and book_title metadata — same as text-extracted chapters.
        """
        pages = _west_africa_blank_pages(500)
        ocr_text = "West Africa FCT chapter text from OCR"

        with (
            self._patch_loader(pages),
            patch(
                "app.common.chapter_extractor._extract_text_with_ocr_fallback",
                return_value=ocr_text,
            ),
        ):
            docs = extract_chapters_from_pdf("dummy.pdf", "west_africa_fct_2019")

        assert len(docs) > 0
        for doc in docs:
            assert doc.metadata["source"] == "WestAfricaFCT2019"
            assert "West Africa" in doc.metadata["book_title"]
