import logging

import fitz  # PyMuPDF
from pathlib import Path
from pydantic import BaseModel
from typing import List, Dict, Any
import re

from app.core.config import settings
from app.services.ocr_utils import needs_ocr

logger = logging.getLogger(__name__)


class ParsedDocument(BaseModel):
    """
    Data model representing a parsed document's structure.

    Attributes:
        text (str): The full raw text of the document.
        headings (List[str]): Extracted headings.
        paragraphs (List[str]): Extracted paragraphs.
        pages (List[str]): Per-page text, so chunks can carry a page number and
            citations can say "Lecture 4, p.7" instead of showing an opaque excerpt.
        metadata (Dict[str, Any]): Additional extracted metadata (e.g., line count).
    """
    text: str
    headings: List[str] = []
    paragraphs: List[str] = []
    pages: List[str] = []
    metadata: Dict[str, Any] = {}


def extract_structure_from_text(text: str) -> ParsedDocument:
    """
    Heuristically extract headings and paragraphs from raw text/markdown.

    Args:
        text (str): The raw text to parse.

    Returns:
        ParsedDocument: The structured document data.
    """
    lines = text.split("\n")
    headings = []
    paragraphs = []
    current_paragraph = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_paragraph:
                paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
            continue

        # Simple heuristic for markdown headings or all-caps lines
        if stripped.startswith("#") or (stripped.isupper() and len(stripped) > 3):
            headings.append(stripped)
            if current_paragraph:
                paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
        else:
            current_paragraph.append(stripped)

    if current_paragraph:
        paragraphs.append(" ".join(current_paragraph))

    return ParsedDocument(
        text=text,
        headings=headings,
        paragraphs=paragraphs,
        metadata={"total_lines": len(lines)},
    )


def extract_from_pdf(filepath: str) -> ParsedDocument:
    """
    Extract text and structure from a PDF file.

    Args:
        filepath (str): The local path to the PDF file.

    Returns:
        ParsedDocument: The parsed structure containing the text and metadata.
    """
    pages: List[str] = []
    try:
        doc = fitz.open(filepath)
        for page in doc:
            pages.append(page.get_text("text"))
        text = "\n\n".join(pages)

        # Scanned / image-only PDFs yield little extractable text -> OCR each page.
        if settings.OCR_ENABLED and needs_ocr(text):
            from app.services.ocr_service import ocr_image_bytes

            ocr_pages = []
            for page in doc:
                pix = page.get_pixmap(dpi=150)
                ocr_pages.append(ocr_image_bytes(pix.tobytes("png")))
            if any(p.strip() for p in ocr_pages):
                pages = ocr_pages
                text = "\n\n".join(pages)

        doc.close()
    except Exception as e:
        logger.error(f"Error parsing PDF {filepath}: {e}")
        text = "\n\n".join(pages)

    parsed = extract_structure_from_text(text)
    # Keeping per-page text lets the chunker attach a page number to each chunk,
    # so a citation can say "p.7" instead of showing an anonymous excerpt.
    parsed.pages = pages
    parsed.metadata["page_count"] = len(pages)
    return parsed


def extract_from_image(filepath: str) -> ParsedDocument:
    """Extract text from an image file via OCR (Gemini multimodal)."""
    text = ""
    if settings.OCR_ENABLED:
        from app.services.ocr_service import ocr_image_bytes

        mime = "image/jpeg" if filepath.lower().endswith((".jpg", ".jpeg")) else "image/png"
        try:
            with open(filepath, "rb") as f:
                text = ocr_image_bytes(f.read(), mime_type=mime)
        except Exception as e:
            logger.error(f"Error OCR-ing image {filepath}: {e}")
    parsed = extract_structure_from_text(text)
    parsed.pages = [text]
    parsed.metadata["page_count"] = 1
    return parsed


def extract_from_text_file(filepath: str) -> ParsedDocument:
    """
    Extract text and structure from a plain text or markdown file.

    Args:
        filepath (str): The local path to the text file.

    Returns:
        ParsedDocument: The parsed structure of the text document.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        logger.error(f"Error parsing text file {filepath}: {e}")
        text = ""

    parsed = extract_structure_from_text(text)
    parsed.pages = [text]
    parsed.metadata["page_count"] = 1
    return parsed


def parse_document(filepath: str, filetype: str = "") -> ParsedDocument:
    """
    Parse a document and return its structured content based on its extension or MIME type.

    Args:
        filepath (str): The path to the file.
        filetype (str, optional): The MIME type or generic file type identifier. Defaults to "".

    Returns:
        ParsedDocument: The structured document data.
    """
    extension = Path(filepath).suffix.lower()

    if extension == ".pdf" or "pdf" in filetype:
        return extract_from_pdf(filepath)
    elif extension in [".png", ".jpg", ".jpeg"] or "image" in filetype:
        return extract_from_image(filepath)
    elif extension in [".txt", ".md"] or "text" in filetype or "markdown" in filetype:
        return extract_from_text_file(filepath)
    else:
        # Fallback to attempt plain text
        return extract_from_text_file(filepath)
