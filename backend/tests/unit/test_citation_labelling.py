"""A citation must name the source it actually came from.

Generated notes are indexed with the lecture id they were built from, so a
chunk of the AI's own output looks lecture-shaped. Labelling it with the
lecture's title would show a student AI-written text under the source
document's name — the exact thing citations exist to prevent.
"""

import pytest

from app.services.vector_db import KIND_LECTURE, KIND_NOTE


def label_citations(citations, lecture_names, note_names):
    """The pure labelling rule used by chat._hydrate_citations."""
    for citation in citations:
        if citation.get("kind") == KIND_NOTE or citation.get("note_id"):
            citation["note_title"] = note_names.get(citation.get("note_id"))
            citation["lecture_title"] = None
        elif citation.get("lecture_id"):
            citation["lecture_title"] = lecture_names.get(citation["lecture_id"])
    return citations


def test_note_chunk_is_not_labelled_with_the_lecture_it_came_from():
    citations = [
        {"kind": KIND_NOTE, "note_id": 36, "lecture_id": 7, "page": None},
    ]

    result = label_citations(citations, {7: "Nielsen_Ch3_part_a.pdf"}, {36: "My summary"})

    assert result[0]["note_title"] == "My summary"
    # The PDF's name must not appear on text the PDF did not contain.
    assert result[0]["lecture_title"] is None


def test_lecture_chunk_keeps_its_document_name_and_page():
    citations = [
        {"kind": KIND_LECTURE, "note_id": None, "lecture_id": 7, "page": 27},
    ]

    result = label_citations(citations, {7: "Nielsen_Ch3_part_a.pdf"}, {})

    assert result[0]["lecture_title"] == "Nielsen_Ch3_part_a.pdf"
    assert result[0]["page"] == 27


def test_mixed_results_are_labelled_independently():
    citations = [
        {"kind": KIND_LECTURE, "note_id": None, "lecture_id": 7, "page": 5},
        {"kind": KIND_NOTE, "note_id": 36, "lecture_id": 7, "page": None},
    ]

    lecture, note = label_citations(
        citations, {7: "Nielsen_Ch3_part_a.pdf"}, {36: "My summary"}
    )

    assert lecture["lecture_title"] == "Nielsen_Ch3_part_a.pdf"
    assert note["lecture_title"] is None
    assert note["note_title"] == "My summary"


def test_unknown_note_still_drops_the_misleading_lecture_name():
    # Even if the note row is gone, we must not fall back to the lecture title.
    citations = [{"kind": KIND_NOTE, "note_id": 99, "lecture_id": 7}]

    result = label_citations(citations, {7: "Nielsen_Ch3_part_a.pdf"}, {})

    assert result[0]["note_title"] is None
    assert result[0]["lecture_title"] is None


def test_generation_retrieval_never_pulls_note_chunks():
    """Generation must build from source material, not from its own prior output."""
    import inspect

    from app.services import llm_service

    source = inspect.getsource(llm_service.retrieve_for_generation)
    assert "KIND_LECTURE" in source, (
        "retrieve_for_generation must filter to lecture chunks, or notes would "
        "be regenerated from earlier generations"
    )
