import os
import re
import pymupdf  # PyMuPDF

MAX_PAGES = int(os.getenv("PDFSAGE_MAX_PAGES", "100"))


class PDFError(ValueError):
    """Safe-to-show error about the uploaded PDF."""


def _clean(text: str) -> str:
    text = re.sub(r"-\n(\w)", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_text(source, ocr_min_chars: int = 40):
    """Extract text with PyMuPDF; pages with no text layer are OCR'd (needs Tesseract).
    `source` is a file path or raw bytes. Returns (text, info)."""
    doc = pymupdf.open(stream=source, filetype="pdf") if isinstance(source, (bytes, bytearray)) \
        else pymupdf.open(source)
    if doc.needs_pass:
        raise PDFError("Encrypted PDFs are not supported.")
    if len(doc) > MAX_PAGES:
        raise PDFError(f"PDF has {len(doc)} pages; the limit is {MAX_PAGES}.")
    pages, ocr_pages, warning = [], 0, None
    for page in doc:
        t = page.get_text().strip()
        if len(t) < ocr_min_chars:  # scanned / image-only page
            try:
                tp = page.get_textpage_ocr(language="eng", dpi=200, full=True)
                t = page.get_text(textpage=tp).strip()
                ocr_pages += 1
            except Exception as e:  # Tesseract missing
                warning = f"OCR unavailable: install Tesseract-OCR ({str(e)[:80]})"
        pages.append(t)
    n_pages = len(doc)
    doc.close()
    return _clean("\n".join(pages)), {"pages": n_pages, "ocr_pages": ocr_pages, "warning": warning}
