"""Pure helpers behind the notes API and the ingestion pipeline."""

import pytest

from app.api.routers.notes import _excerpt, _word_count
from app.services.embedding_service import get_chunks_with_pages
from app.services.llm_service import generate_title, suggested_questions


def test_excerpt_skips_headings_code_and_tables():
    markdown = """# Backpropagation

```python
x = 1
```

| a | b |
|---|---|

> a quote

Gradients flow backwards through the network."""

    assert _excerpt(markdown) == "Gradients flow backwards through the network."


def test_excerpt_strips_list_markers():
    assert _excerpt("- First bullet point") == "First bullet point"
    assert _excerpt("1. Numbered point") == "Numbered point"


def test_excerpt_handles_empty_input():
    assert _excerpt("") == ""
    assert _word_count("") == 0


def test_title_prefers_the_documents_own_heading():
    # Free, deterministic and usually exactly right -- no model call needed.
    assert generate_title("## Hash tables\n\nSome text") == "Hash tables"
    assert generate_title("# Gradient descent") == "Gradient descent"


def test_title_falls_back_when_there_is_no_heading_and_no_key(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "GEMINI_API_KEY", "", raising=False)
    assert generate_title("just prose, no heading", fallback="Untitled") == "Untitled"


def test_suggested_questions_come_from_headings():
    markdown = "# Lecture\n\n## Hashing\n\ntext\n\n## Collisions\n\ntext"
    questions = suggested_questions(markdown, limit=2)

    assert questions == [
        "Explain Hashing in more depth",
        "Explain Collisions in more depth",
    ]


def test_suggested_questions_dedupe_repeated_headings():
    markdown = "## Recap\n\na\n\n## Recap\n\nb\n\n## Proofs\n\nc"
    assert suggested_questions(markdown, limit=3) == [
        "Explain Recap in more depth",
        "Explain Proofs in more depth",
    ]


def test_chunks_carry_their_page_number():
    pages = ["page one text", "page two text", "page three text"]
    chunks, page_numbers = get_chunks_with_pages(pages)

    assert len(chunks) == len(page_numbers)
    # Pages are 1-based so a citation can say "p.1", matching what a reader sees.
    assert page_numbers == [1, 2, 3]


def test_blank_pages_are_skipped_without_shifting_numbering():
    pages = ["first", "   ", "", "fourth"]
    chunks, page_numbers = get_chunks_with_pages(pages)

    assert chunks == ["first", "fourth"]
    assert page_numbers == [1, 4]
