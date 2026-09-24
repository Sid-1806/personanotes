import os
import shutil
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lecture import Lecture
from app.models.user import User

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Formats the parser can actually read. Rejecting at upload time is kinder than
# accepting the file and failing during ingestion.
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".png", ".jpg", ".jpeg"}


async def save_lecture(
    db: AsyncSession,
    file: UploadFile,
    user: User,
    course_id: int | None = None,
) -> Lecture:
    """
    Saves an uploaded lecture file to the local disk and creates a database record.

    Args:
        db (AsyncSession): The database session.
        file (UploadFile): The uploaded file object from FastAPI.
        user (User): The user who uploaded the file.
        course_id (int | None): Course the lecture belongs to.

    Returns:
        Lecture: The created Lecture database model instance.
    """
    file_extension = Path(file.filename or "").suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"'{file.filename}' isn't a supported format. "
                "Upload a PDF, image (PNG/JPG), TXT or MD file."
            ),
        )

    file_id = os.urandom(8).hex()
    new_filename = f"{user.id}_{file_id}{file_extension}"
    file_path = UPLOAD_DIR / new_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    lecture = Lecture(
        user_id=user.id,
        course_id=course_id,
        filename=file.filename,
        filepath=str(file_path),
        filetype=file.content_type or file_extension,
    )
    db.add(lecture)
    await db.commit()
    await db.refresh(lecture)
    return lecture
