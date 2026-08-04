import fitz  # PyMuPDF
from pathlib import Path
from pydantic import BaseModel
from typing import List, Dict, Any
import re


class ParsedDocument(BaseModel):
    """
    Data model representing a parsed document's structure.

    Attributes:
        text (str): The full raw text of the document.
        headings (List[str]): Extracted headings.
        paragraphs (List[str]): Extracted paragraphs.
        metadata (Dict[str, Any]): Additional extracted metadata (e.g., line count).
    """
    text: str
    headings: List[str] = []
    paragraphs: List[str] = []
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
    text = ""
    try:
        doc = fitz.open(filepath)
        for page in doc:
            text += page.get_text("text") + "\n\n"
        doc.close()
    except Exception as e:
        print(f"Error parsing PDF {filepath}: {e}")

    return extract_structure_from_text(text)


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
        print(f"Error parsing text file {filepath}: {e}")
        text = ""

    return extract_structure_from_text(text)


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
    elif extension in [".txt", ".md"] or "text" in filetype or "markdown" in filetype:
        return extract_from_text_file(filepath)
    else:
        # Fallback to attempt plain text
        return extract_from_text_file(filepath)
