"""Unit tests for app/retrieval/semantic_chunker.py — Prompt 7."""

from langchain.docstore.document import Document

from app.retrieval.semantic_chunker import chunk_all_chapters, chunk_chapter


def _make_doc(text: str, source: str = "Shaw2020", chapter_num: str = "5",
              book_title: str = "Clinical Paediatric Dietetics") -> Document:
    return Document(
        page_content=text,
        metadata={"source": source, "chapter_num": chapter_num, "book_title": book_title},
    )


# ---------------------------------------------------------------------------
# chunk_chapter — core behaviour
# ---------------------------------------------------------------------------

class TestChunkChapter:
    def test_long_doc_produces_multiple_chunks(self):
        text = "Nutrition is important for pediatric health. " * 60  # ~2700 chars
        doc = _make_doc(text)
        chunks = chunk_chapter(doc, chunk_size=500, chunk_overlap=75)
        assert len(chunks) > 1

    def test_chunks_are_documents(self):
        doc = _make_doc("A" * 1000)
        chunks = chunk_chapter(doc)
        assert all(isinstance(c, Document) for c in chunks)

    def test_chunks_inherit_source_metadata(self):
        doc = _make_doc("Content " * 200, source="PretermNeonate2013", chapter_num="3")
        chunks = chunk_chapter(doc)
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.metadata["source"] == "PretermNeonate2013"
            assert chunk.metadata["chapter_num"] == "3"
            assert chunk.metadata["book_title"] == "Clinical Paediatric Dietetics"

    def test_chunks_have_chunk_index(self):
        doc = _make_doc("Word " * 300)
        chunks = chunk_chapter(doc)
        assert len(chunks) > 1
        for i, chunk in enumerate(chunks):
            assert chunk.metadata["chunk_index"] == i

    def test_chunks_have_total_chunks(self):
        doc = _make_doc("Word " * 300)
        chunks = chunk_chapter(doc)
        expected_total = len(chunks)
        for chunk in chunks:
            assert chunk.metadata["total_chunks"] == expected_total

    def test_chunk_id_format(self):
        doc = _make_doc("Content " * 200, source="Shaw2020", chapter_num="11")
        chunks = chunk_chapter(doc)
        for i, chunk in enumerate(chunks):
            expected_id = f"Shaw2020__11__chunk{i}"
            assert chunk.metadata["chunk_id"] == expected_id

    def test_empty_content_returns_empty_list(self):
        doc = _make_doc("")
        assert chunk_chapter(doc) == []

    def test_whitespace_only_returns_empty_list(self):
        doc = _make_doc("   \n\t  ")
        assert chunk_chapter(doc) == []

    def test_short_doc_produces_single_chunk(self):
        doc = _make_doc("Short text.")
        chunks = chunk_chapter(doc)
        assert len(chunks) == 1
        assert chunks[0].metadata["chunk_index"] == 0
        assert chunks[0].metadata["total_chunks"] == 1

    def test_does_not_modify_original_doc(self):
        original_meta = {"source": "Shaw2020", "chapter_num": "5", "book_title": "CPD"}
        doc = Document(page_content="Some content " * 100, metadata=dict(original_meta))
        chunk_chapter(doc)
        assert doc.metadata == original_meta

    def test_chunk_index_is_int(self):
        doc = _make_doc("Content " * 200)
        chunks = chunk_chapter(doc)
        assert len(chunks) > 1
        assert isinstance(chunks[0].metadata["chunk_index"], int)
        assert isinstance(chunks[0].metadata["total_chunks"], int)


# ---------------------------------------------------------------------------
# chunk_all_chapters — flattening
# ---------------------------------------------------------------------------

class TestChunkAllChapters:
    def test_flattens_multiple_docs(self):
        docs = [
            _make_doc("Chapter one content. " * 60, chapter_num="1"),
            _make_doc("Chapter two content. " * 60, chapter_num="2"),
        ]
        result = chunk_all_chapters(docs)
        assert len(result) > 2  # at least one chunk per doc

    def test_preserves_source_across_docs(self):
        docs = [
            _make_doc("Content A " * 60, source="Shaw2020", chapter_num="1"),
            _make_doc("Content B " * 60, source="PretermNeonate2013", chapter_num="2"),
        ]
        result = chunk_all_chapters(docs)
        sources = {c.metadata["source"] for c in result}
        assert "Shaw2020" in sources
        assert "PretermNeonate2013" in sources

    def test_empty_input_returns_empty_list(self):
        assert chunk_all_chapters([]) == []

    def test_skips_empty_docs(self):
        docs = [
            _make_doc("", chapter_num="1"),
            _make_doc("Real content here. " * 60, chapter_num="2"),
        ]
        result = chunk_all_chapters(docs)
        # All chunks should belong to chapter 2
        for chunk in result:
            assert chunk.metadata["chapter_num"] == "2"

    def test_order_preserved(self):
        docs = [
            _make_doc("Alpha " * 60, source="Shaw2020", chapter_num="1"),
            _make_doc("Beta " * 60, source="Shaw2020", chapter_num="2"),
        ]
        result = chunk_all_chapters(docs)
        chapter_nums = [c.metadata["chapter_num"] for c in result]
        # All chapter 1 chunks must precede all chapter 2 chunks
        ch1_indices = [i for i, n in enumerate(chapter_nums) if n == "1"]
        ch2_indices = [i for i, n in enumerate(chapter_nums) if n == "2"]
        assert max(ch1_indices) < min(ch2_indices)
