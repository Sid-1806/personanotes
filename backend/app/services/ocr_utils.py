"""Small, dependency-free helpers for the OCR fallback decision (unit-testable)."""

OCR_MIN_TEXT_LEN = 40


def needs_ocr(text: str) -> bool:
    """True when extracted text is too sparse to be real content.

    A scanned / image-only PDF yields little or no extractable text, which is
    the signal to fall back to OCR.
    """
    return len((text or "").strip()) < OCR_MIN_TEXT_LEN
