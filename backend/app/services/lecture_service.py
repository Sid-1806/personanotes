import os
import shutil
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lecture import Lecture
from app.models.user import User

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def save_lecture(db: AsyncSession, file: UploadFile, user: User) -> Lecture:
    """
    Saves an uploaded lecture file to the local disk and creates a database record.

    Args:
        db (AsyncSession): The database session.
        file (UploadFile): The uploaded file object from FastAPI.
        user (User): The user who uploaded the file.

    Returns:
        Lecture: The created Lecture database model instance.
    """
    # Save file locally
    file_extension = Path(file.filename).suffix
    file_id = os.urandom(8).hex()
    new_filename = f"{user.id}_{file_id}{file_extension}"
    file_path = UPLOAD_DIR / new_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Save to database
    lecture = Lecture(
        user_id=user.id,
        filename=file.filename,
        filepath=str(file_path),
        filetype=file.content_type,
    )
    db.add(lecture)
    await db.commit()
    await db.refresh(lecture)
    return lecture
