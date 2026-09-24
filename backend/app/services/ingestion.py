"""Lecture ingestion worker: parse -> chunk -> embed -> index.

Runs on FastAPI's ``BackgroundTasks`` against a *synchronous* session, and is
written to survive process restarts: each run records its state on the
``Lecture`` row, and :func:`requeue_stuck_lectures` re-runs anything left mid-
flight when the app boots. Hosts like Render and Railway restart containers
routinely, so without that sweep a restart would silently strand a lecture in
``processing`` forever.

Failures are recorded with a *typed, user-facing* reason. A bare red badge with
no explanation and no way forward is the thing this replaces.
"""

import logging
import os

from app.services.document_parser import parse_document
from app.services.embedding_service import (
    generate_embeddings,
    get_chunks_with_pages,
    get_text_chunks,
)
from app.services.vector_db import store_lecture_chunks

logger = logging.getLogger(__name__)

# Statuses
PENDING = "pending"
PROCESSING = "processing"
READY = "ready"
FAILED = "failed"


class IngestionError(Exception):
    """A failure with a message that is safe and useful to show the user."""


def _set_status(
    lecture_id: int,
    status: str,
    chunk_count: int | None = None,
    page_count: int | None = None,
    error_message: str | None = None,
):
    """Persist ingestion state from the sync background worker."""
    from app.db.database import SyncSessionLocal
    from app.models.lecture import Lecture

    with SyncSessionLocal() as session:
        lecture = session.get(Lecture, lecture_id)
        if lecture is None:
            return
        lecture.ingestion_status = status
        if chunk_count is not None:
            lecture.chunk_count = chunk_count
        if page_count is not None:
            lecture.page_count = page_count
        # Clear a previous failure whenever we move forward, so a successful
        # retry doesn't leave a stale error hanging around in the UI.
        lecture.error_message = error_message
        session.commit()


def process_lecture(
    lecture_id: int,
    user_id: int,
    filepath: str,
    filetype: str,
    course_id: int | None = None,
):
    """Parse, chunk, embed and index one lecture, updating its status as it goes."""
    logger.info("Ingestion started for lecture %s", lecture_id)
    try:
        _set_status(lecture_id, PROCESSING)

        if not os.path.exists(filepath):
            raise IngestionError(
                "The uploaded file is no longer available on the server. "
                "Re-upload it to try again."
            )

        parsed = parse_document(filepath, filetype)
        pages = parsed.pages or ([parsed.text] if parsed.text else [])

        if not parsed.text.strip():
            raise IngestionError(
                "No readable text was found in this file. If it is a scan or a "
                "photo, make sure OCR is enabled; otherwise try a text-based PDF."
            )

        if pages:
            chunks, page_numbers = get_chunks_with_pages(pages)
        else:
            chunks, page_numbers = get_text_chunks(parsed.text), []

        if not chunks:
            raise IngestionError(
                "This file produced no indexable content. It may be empty or "
                "contain only images."
            )

        logger.info("Lecture %s -> %s chunks", lecture_id, len(chunks))

        try:
            embeddings = generate_embeddings(chunks)
        except Exception as exc:
            logger.exception("Embedding failed for lecture %s", lecture_id)
            raise IngestionError(
                "The text could not be embedded. This is usually temporary — retry."
            ) from exc

        try:
            store_lecture_chunks(
                lecture_id=lecture_id,
                user_id=user_id,
                chunks=chunks,
                embeddings=embeddings,
                course_id=course_id,
                pages=page_numbers,
            )
        except Exception as exc:
            logger.exception("Indexing failed for lecture %s", lecture_id)
            raise IngestionError(
                "The search index is unavailable right now, so this lecture "
                "couldn't be indexed. Retry in a moment."
            ) from exc

        _set_status(
            lecture_id,
            READY,
            chunk_count=len(chunks),
            page_count=parsed.metadata.get("page_count", len(pages)),
        )
        logger.info("Lecture %s ready (%s chunks)", lecture_id, len(chunks))

    except IngestionError as exc:
        _set_status(lecture_id, FAILED, error_message=str(exc))
    except Exception as exc:  # unexpected -> generic message, full detail in logs
        logger.exception("Unexpected ingestion failure for lecture %s", lecture_id)
        _set_status(
            lecture_id,
            FAILED,
            error_message="Processing failed unexpectedly. Retry, or re-upload the file.",
        )


def requeue_stuck_lectures() -> int:
    """Mark lectures stranded mid-ingestion as failed-but-retryable, on boot.

    In-process background work does not survive a restart. Rather than leaving
    a spinner running forever, surface the interruption with a reason and a
    retry affordance. Returns how many rows were reset.
    """
    from app.db.database import SyncSessionLocal
    from app.models.lecture import Lecture

    try:
        with SyncSessionLocal() as session:
            stuck = (
                session.query(Lecture)
                .filter(Lecture.ingestion_status.in_([PENDING, PROCESSING]))
                .all()
            )
            for lecture in stuck:
                lecture.ingestion_status = FAILED
                lecture.error_message = (
                    "Processing was interrupted when the server restarted. "
                    "Retry to pick it back up."
                )
            session.commit()
            if stuck:
                logger.warning("Reset %s interrupted lecture ingestion(s)", len(stuck))
            return len(stuck)
    except Exception as exc:  # never block startup on this sweep
        logger.warning("Could not sweep interrupted ingestions: %s", exc)
        return 0


def index_note(
    note_id: int,
    user_id: int,
    markdown: str,
    course_id: int | None = None,
    lecture_id: int | None = None,
):
    """Index a generated note so it is searchable alongside lecture material."""
    from app.services.vector_db import store_note_chunks

    try:
        chunks = get_text_chunks(markdown)
        if not chunks:
            return
        embeddings = generate_embeddings(chunks)
        store_note_chunks(
            note_id=note_id,
            user_id=user_id,
            chunks=chunks,
            embeddings=embeddings,
            course_id=course_id,
            lecture_id=lecture_id,
        )
    except Exception as exc:  # best-effort: a note is still readable unindexed
        logger.warning("Could not index note %s: %s", note_id, exc)
