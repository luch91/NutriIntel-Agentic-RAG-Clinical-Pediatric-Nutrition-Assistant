"""
semantic_chunker.py — post-processor for chapter_extractor output.

Splits chapter-level Documents into sub-chunks for denser retrieval.
Does NOT replace chapter_extractor — it is called immediately after it.
"""

from __future__ import annotations

from typing import List

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


def chunk_chapter(
    chapter_doc: Document,
    chunk_size: int = 500,
    chunk_overlap: int = 75,
) -> List[Document]:
    """
    Split a single chapter Document into sub-chunk Documents.

    Each output chunk:
    - Inherits ALL metadata from chapter_doc unchanged
    - Adds chunk_index (0-based), total_chunks, chunk_id to metadata
    - chunk_id format: "{source}__{chapter_num}__chunk{i}"

    Returns [] if page_content is empty or whitespace-only.
    Does not modify chapter_doc in place.
    """
    if not chapter_doc.page_content or not chapter_doc.page_content.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " "],
    )

    texts = splitter.split_text(chapter_doc.page_content)
    if not texts:
        return []

    source = chapter_doc.metadata.get("source", "unknown")
    chapter_num = chapter_doc.metadata.get("chapter_num", "0")
    total = len(texts)

    chunks: List[Document] = []
    for i, text in enumerate(texts):
        meta = dict(chapter_doc.metadata)  # shallow copy — all original fields preserved
        meta["chunk_index"] = i
        meta["total_chunks"] = total
        meta["chunk_id"] = f"{source}__{chapter_num}__chunk{i}"
        chunks.append(Document(page_content=text, metadata=meta))

    return chunks


def chunk_all_chapters(
    chapter_docs: List[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 75,
) -> List[Document]:
    """
    Apply chunk_chapter to every document and return the flattened list.
    Preserves the original document order.
    """
    result: List[Document] = []
    for doc in chapter_docs:
        result.extend(chunk_chapter(doc, chunk_size=chunk_size, chunk_overlap=chunk_overlap))
    return result
