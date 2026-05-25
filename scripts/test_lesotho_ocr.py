"""
Test OCR quality on the Lesotho FCT before committing to full ingestion.

Samples pages 1, 20, 50, 80, and 110 (spread across the 127-page document)
and prints the extracted text so you can judge whether it's usable.

Usage:
    python scripts/test_lesotho_ocr.py

Requires: pymupdf (fitz), pytesseract, Pillow — all should be present in rag_env.
If tesseract is not on PATH, set TESSERACT_CMD below.
"""

import io
import sys
import os

# Auto-configure tesseract path on Windows if not on PATH
import sys as _sys
if _sys.platform == "win32":
    import pytesseract as _pt
    import shutil
    if not shutil.which("tesseract"):
        _pt.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

PDF_PATH = os.path.join(
    os.path.dirname(__file__), "..", "app", "common", "data", "LESOTHO Food Composition Table.pdf"
)
SAMPLE_PAGES = [1, 20, 50, 80, 110]
ZOOM = 2.0          # 2x render resolution — same as production OCR fallback
SEPARATOR = "\n" + "=" * 72 + "\n"


def ocr_page(doc, page_num: int) -> str:
    """OCR a single 1-based page number. Returns extracted text."""
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as e:
        print(f"Missing dependency: {e}")
        sys.exit(1)

    idx = page_num - 1
    if idx < 0 or idx >= doc.page_count:
        return f"[page {page_num} out of range — document has {doc.page_count} pages]"

    page = doc[idx]
    mat = fitz.Matrix(ZOOM, ZOOM)
    pix = page.get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    text = pytesseract.image_to_string(img, config="--psm 6")
    return text.strip()


def main():
    try:
        import fitz
    except ImportError:
        print("pymupdf (fitz) not installed. Run: python -m pip install pymupdf")
        sys.exit(1)

    path = os.path.abspath(PDF_PATH)
    if not os.path.exists(path):
        print(f"File not found: {path}")
        sys.exit(1)

    doc = fitz.open(path)
    print(f"Lesotho FCT — {doc.page_count} pages total")
    print(f"Sampling pages: {SAMPLE_PAGES}")
    print(f"Zoom: {ZOOM}x")

    results = {}
    for pg in SAMPLE_PAGES:
        print(f"\nOCR page {pg}...", end=" ", flush=True)
        text = ocr_page(doc, pg)
        results[pg] = text
        word_count = len(text.split())
        print(f"{word_count} words extracted")

    doc.close()

    # Print full output for inspection
    for pg, text in results.items():
        print(SEPARATOR)
        print(f"PAGE {pg}")
        print(SEPARATOR)
        if text:
            print(text[:1500])   # cap at 1500 chars per page so output stays readable
            if len(text) > 1500:
                print(f"\n... [{len(text) - 1500} more chars]")
        else:
            print("[empty — OCR returned nothing]")

    print(SEPARATOR)
    print("VERDICT GUIDE")
    print(SEPARATOR)
    print("Good  (>80 words/page, readable food names + numbers) -> safe to ingest")
    print("OK    (40-80 words/page, some garbling)               -> ingest with caution")
    print("Poor  (<40 words/page, mostly garbage)                -> skip Lesotho")


if __name__ == "__main__":
    main()
