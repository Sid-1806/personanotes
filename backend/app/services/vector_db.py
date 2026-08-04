import uuid
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from app.core.config import settings
from app.services.embedding_service import model as embedding_model

# Initialize Qdrant Client
# If QDRANT_URL is not set, it could use an in-memory db or local path, but we assume it's running via docker.
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
    import logging

    logging.getLogger(__name__).warning(
        f"Could not initialize Qdrant collection at startup: {_e}"
    )


def store_lecture_chunks(
    lecture_id: int, user_id: int, chunks: list[str], embeddings: list[list[float]]
):
    """
    Store chunks and their embeddings into Qdrant.

    Args:
        lecture_id (int): ID of the lecture.
        user_id (int): ID of the user owning the lecture.
        chunks (list[str]): List of text chunks.
        embeddings (list[list[float]]): Corresponding embedding vectors for each chunk.

    Returns:
        None
    """
    if not chunks or not embeddings:
        return

    # Make sure the collection exists (in case startup init was skipped/failed).
    init_collection()

    points = []
    for chunk, embedding in zip(chunks, embeddings):
        point_id = str(uuid.uuid4())
        points.append(
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={"lecture_id": lecture_id, "user_id": user_id, "text": chunk},
            )
        )

    client.upsert(collection_name=settings.QDRANT_COLLECTION_NAME, points=points)
