import os
import aiofiles
from typing import List, Tuple
from fastapi import UploadFile
from app.services.document_parser import parse_document

UPLOAD_DIR = "uploads/historical"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def import_files(files: List[UploadFile]) -> List[Tuple[str, str, str]]:
    """
    Reads and parses multiple uploaded files.
    Returns a list of (filename, filepath, parsed_markdown)
    """
    imported_data = []

    for file in files:
        if not file.filename:
            continue

        filepath = os.path.join(UPLOAD_DIR, file.filename)

        # Save to disk
        async with aiofiles.open(filepath, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)

        # Extract text using our existing document_parser
        # parse_document takes filepath as the first argument and is synchronous
        parsed = parse_document(filepath)

        imported_data.append((file.filename, filepath, parsed.text))

    return imported_data
