"""OCR via Gemini's multimodal model. No system dependency (no Tesseract)."""

import logging
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

_ocr_model = genai.GenerativeModel(settings.GEMINI_MODEL)

_OCR_PROMPT = (
    "Extract all readable text from this image. Preserve structure as markdown "
    "(headings, lists, tables). Return ONLY the extracted text, with no commentary."
)


def ocr_image_bytes(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """Extract text from image bytes using Gemini. Returns '' on failure."""
    if not settings.GEMINI_API_KEY:
        logger.warning("OCR requested but GEMINI_API_KEY is not configured.")
        return ""
    try:
        response = _ocr_model.generate_content(
            [_OCR_PROMPT, {"mime_type": mime_type, "data": image_bytes}]
        )
        return response.text or ""
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return ""
