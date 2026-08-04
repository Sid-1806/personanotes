import re
from typing import Dict, Any


def count_matches(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, re.MULTILINE))


def extract_features(markdown_text: str) -> Dict[str, Any]:
    """
    Deterministically extract structural and formatting features from a markdown document.
    """
    if not markdown_text:
        return {}

    lines = markdown_text.split("\n")
    word_count = len(markdown_text.split())

    # 1. Heading Depth and Count
    headings = re.findall(r"^(#{1,6})\s+(.*)", markdown_text, re.MULTILINE)
    heading_count = len(headings)
    avg_heading_depth = sum(len(h[0]) for h in headings) / max(1, heading_count)

    # 2. Sentences and Paragraphs
    sentences = re.split(r"[.!?]+", markdown_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    avg_sentence_length = sum(len(s.split()) for s in sentences) / max(
        1, len(sentences)
    )

    paragraphs = [p for p in markdown_text.split("\n\n") if p.strip()]
    avg_paragraph_length = sum(len(p.split()) for p in paragraphs) / max(
        1, len(paragraphs)
    )

    # 3. Lists and Bullets
    bullets = count_matches(r"^\s*[-*+]\s+", markdown_text)
    numbered_lists = count_matches(r"^\s*\d+\.\s+", markdown_text)

    # 4. Elements (per 1000 words logic will be applied in diff engine or normalized here)
    code_blocks = count_matches(r"^```[\s\S]*?^```", markdown_text)
    tables = count_matches(r"^\|.*\|$", markdown_text)
    equations = count_matches(r"\$\$.*?\$\$", markdown_text) + count_matches(
        r"(?<!\$)\$[^\$]+\$(?!\$)", markdown_text
    )
    diagrams = count_matches(r"^```mermaid[\s\S]*?^```", markdown_text)

    # 5. Formatting
    bold_count = count_matches(r"\*\*.*?\*\*", markdown_text)
    italic_count = (
        count_matches(r"\*.*?\*", markdown_text) - bold_count
    )  # rough approximation

    # 6. Sections (Keywords)
    text_lower = markdown_text.lower()
    has_summary = "summary" in text_lower or "conclusion" in text_lower
    has_examples = "example" in text_lower
    has_definitions = "definition" in text_lower

    return {
        "word_count": word_count,
        "heading_count": heading_count,
        "avg_heading_depth": avg_heading_depth,
        "avg_sentence_length": avg_sentence_length,
        "avg_paragraph_length": avg_paragraph_length,
        "bullets": bullets,
        "numbered_lists": numbered_lists,
        "code_blocks": code_blocks,
        "tables": tables,
        "equations": equations,
        "diagrams": diagrams,
        "bold_count": bold_count,
        "italic_count": italic_count,
        "has_summary": has_summary,
        "has_examples": has_examples,
        "has_definitions": has_definitions,
    }
