"""Qdrant-backed vector store.

Payload shape (every point):
    user_id     int    tenant isolation -- always filtered on
    kind        str    "lecture_chunk" | "note_chunk"
    lecture_id  int?   source lecture (lecture chunks)
    note_id     int?   source note (note chunks)
    course_id   int?   course scope, so course-wide retrieval is a filter
    page        int?   1-based page for provenance in citations
    text        str    the chunk itself

Deletes matter: a lecture removed from Postgres whose points stay in Qdrant
would keep being retrieved into future generations, so every delete path here
removes the matching points.
"""

import logging
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import settings
from app.services.embedding_service import model as embedding_model

logger = logging.getLogger(__name__)

KIND_LECTURE = "lecture_chunk"
KIND_NOTE = "note_chunk"

client = QdrantClient(url=settings.QDRANT_URL)

# Derive the vector size from the embedding model instead of hardcoding it, so
# swapping EMBEDDING_MODEL_NAME can't silently mismatch the collection dimension.
VECTOR_SIZE = embedding_model.get_sentence_embedding_dimension()


def init_collection():
    """Create collection if it doesn't exist."""
    collection_name = settings.QDRANT_COLLECTION_NAME
    collections = client.get_collections().collections
    if not any(c.name == collection_name for c in collections):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


# Ensure collection exists on startup.
# Guarded so the app can still import/boot if Qdrant is temporarily unavailable;
# the collection will be (re)checked lazily on first write instead of crashing import.
try:
    init_collection()
except Exception as _e:  # pragma: no cover - depends on external service availability
    logger.warning(f"Could not initialize Qdrant collection at startup: {_e}")


def build_filter(
    user_id: int,
    lecture_id: int | None = None,
    course_id: int | None = None,
    note_id: int | None = None,
    kind: str | None = None,
) -> Filter:
    """Compose a retrieval filter. `user_id` is always required."""
    conditions = [FieldCondition(key="user_id", match=MatchValue(value=user_id))]
    if lecture_id is not None:
        conditions.append(
            FieldCondition(key="lecture_id", match=MatchValue(value=lecture_id))
        )
    if course_id is not None:
        conditions.append(
            FieldCondition(key="course_id", match=MatchValue(value=course_id))
        )
    if note_id is not None:
        conditions.append(
            FieldCondition(key="note_id", match=MatchValue(value=note_id))
        )
    if kind is not None:
        conditions.append(FieldCondition(key="kind", match=MatchValue(value=kind)))
    return Filter(must=conditions)


def store_lecture_chunks(
    lecture_id: int,
    user_id: int,
    chunks: list[str],
    embeddings: list[list[float]],
    course_id: int | None = None,
    pages: list[int] | None = None,
):
    """Store lecture chunks and their embeddings into Qdrant.

    Args:
        lecture_id: ID of the lecture.
        user_id: Owner, used for tenant isolation on every query.
        chunks: Text chunks.
        embeddings: Corresponding embedding vectors.
        course_id: Course scope, so course-wide retrieval is a single filter.
        pages: 1-based page number per chunk, for citation provenance.
    """
    if not chunks or not embeddings:
        return

    init_collection()

    points = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        payload = {
            "kind": KIND_LECTURE,
            "lecture_id": lecture_id,
            "user_id": user_id,
            "text": chunk,
        }
        if course_id is not None:
            payload["course_id"] = course_id
        if pages and i < len(pages):
            payload["page"] = pages[i]
        points.append(
            PointStruct(id=str(uuid.uuid4()), vector=embedding, payload=payload)
        )

    client.upsert(collection_name=settings.QDRANT_COLLECTION_NAME, points=points)


def store_note_chunks(
    note_id: int,
    user_id: int,
    chunks: list[str],
    embeddings: list[list[float]],
    course_id: int | None = None,
    lecture_id: int | None = None,
):
    """Index a generated note so the user can search and cite their own notes."""
    if not chunks or not embeddings:
        return

    init_collection()
    delete_note_points(note_id, user_id)  # re-index cleanly on edit

    points = []
    for chunk, embedding in zip(chunks, embeddings):
        payload = {
            "kind": KIND_NOTE,
            "note_id": note_id,
            "user_id": user_id,
            "text": chunk,
        }
        if course_id is not None:
            payload["course_id"] = course_id
        if lecture_id is not None:
            payload["lecture_id"] = lecture_id
        points.append(
            PointStruct(id=str(uuid.uuid4()), vector=embedding, payload=payload)
        )

    client.upsert(collection_name=settings.QDRANT_COLLECTION_NAME, points=points)


def _delete_by_filter(flt: Filter) -> None:
    try:
        client.delete(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points_selector=FilterSelector(filter=flt),
        )
    except Exception as exc:  # pragma: no cover - external service
        logger.error(f"Failed to delete points from Qdrant: {exc}")


def delete_lecture_points(lecture_id: int, user_id: int) -> None:
    """Remove every point belonging to a lecture (both its chunks and notes')."""
    _delete_by_filter(build_filter(user_id=user_id, lecture_id=lecture_id))


def delete_note_points(note_id: int, user_id: int) -> None:
    """Remove every indexed chunk of one generated note."""
    _delete_by_filter(build_filter(user_id=user_id, note_id=note_id, kind=KIND_NOTE))


def delete_user_points(user_id: int) -> None:
    """Remove everything belonging to a user (account deletion)."""
    _delete_by_filter(build_filter(user_id=user_id))
