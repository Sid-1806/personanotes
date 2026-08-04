from typing import Any, List
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.models.user import User
from app.models.lecture import Lecture
from app.schemas.lecture import LectureResponse
from app.services import lecture_service
from app.services.document_parser import parse_document
from app.services.embedding_service import get_text_chunks, generate_embeddings
from app.services.vector_db import store_lecture_chunks
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def process_lecture_background(
    lecture_id: int, user_id: int, filepath: str, filetype: str
):
    """
    Background task to parse a lecture document, chunk the text, generate embeddings,
    and store the vectors in the database.

    Args:
        lecture_id (int): ID of the uploaded lecture.
        user_id (int): ID of the uploading user.
        filepath (str): Local path to the saved document.
        filetype (str): Type of the file.

    Returns:
        None
    """
    logger.info(f"Background processing started for lecture {lecture_id}")
    try:
        # Extract text structure
        parsed_doc = parse_document(filepath, filetype)
        text = parsed_doc.text
        if not text.strip():
            logger.warning(f"No text extracted from lecture {lecture_id}")
            return

        # Chunk text
        chunks = get_text_chunks(text)
        logger.info(f"Generated {len(chunks)} chunks for lecture {lecture_id}")

        # Embed chunks
        embeddings = generate_embeddings(chunks)

        # Store in Qdrant
        store_lecture_chunks(lecture_id, user_id, chunks, embeddings)
        logger.info(
            f"Successfully processed and stored embeddings for lecture {lecture_id}"
        )
    except Exception as e:
        logger.error(f"Error processing lecture {lecture_id}: {e}")


@router.post("/upload", response_model=LectureResponse)
async def upload_lecture(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Upload a new lecture file, save it, and schedule background vector processing.

    Args:
        background_tasks (BackgroundTasks): FastAPI background tasks object.
        file (UploadFile): The uploaded file.
        db (AsyncSession): The database session.
        current_user (User): The currently authenticated user.

    Returns:
        Any: The saved Lecture record serialized by LectureResponse.
    """
    lecture = await lecture_service.save_lecture(db, file, current_user)

    # Schedule background processing
    background_tasks.add_task(
        process_lecture_background,
        lecture_id=lecture.id,
        user_id=current_user.id,
        filepath=lecture.filepath,
        filetype=lecture.filetype,
    )

    return lecture


@router.get("/", response_model=List[LectureResponse])
async def read_lectures(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve all lectures uploaded by the current user.

    Args:
        db (AsyncSession): The database session.
        current_user (User): The currently authenticated user.

    Returns:
        Any: A list of Lecture records serialized by LectureResponse.
    """
    result = await db.execute(select(Lecture).where(Lecture.user_id == current_user.id))
    lectures = result.scalars().all()
    return lectures
