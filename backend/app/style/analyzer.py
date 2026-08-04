import json
import logging
import google.generativeai as genai
from app.core.config import settings
from app.style.schema import StyleProfileSchema, FeatureValue
from app.services.document_parser import ParsedDocument

logger = logging.getLogger(__name__)

# Configure Gemini for Analysis
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

analysis_model = genai.GenerativeModel("gemini-2.5-flash")


def _fv(value, reason: str = "Inferred from uploaded note."):
    """Wrap a raw analyzed value into a FeatureValue for the style schema."""
    return FeatureValue(value=value, confidence=0.6, reason=reason)


def _profile_from_flat(data: dict) -> StyleProfileSchema:
    """Build a StyleProfileSchema (nested FeatureValue fields) from flat LLM output."""

    def _num(key, default):
        try:
            return float(data.get(key, default))
        except (TypeError, ValueError):
            return float(default)

    return StyleProfileSchema(
        heading_style=_fv(data.get("heading_style", "Standard markdown headers")),
        section_order=_fv(list(data.get("section_order", []) or [])),
        bullet_style=_fv(data.get("bullet_style", "Standard bullets")),
        average_sentence_length=_fv(_num("average_sentence_length", 15)),
        average_paragraph_length=_fv(_num("average_paragraph_length", 0)),
        heading_depth=_fv(_num("heading_depth", 0)),
        bullet_frequency=_fv(_num("bullet_frequency", 0)),
        diagram_frequency=_fv(_num("diagram_frequency", 0)),
        table_frequency=_fv(_num("table_frequency", 0)),
        code_block_frequency=_fv(_num("code_block_frequency", 0)),
        example_density=_fv(data.get("example_density", "Medium")),
        summary_position=_fv(data.get("summary_position", "None")),
        keyword_highlighting=_fv(bool(data.get("keyword_highlighting", True))),
        tone=_fv(data.get("tone", "Academic")),
        preferred_sections=_fv(list(data.get("preferred_sections", []) or [])),
        formatting_preferences=_fv(dict(data.get("formatting_preferences", {}) or {})),
    )


def analyze_style_from_document(doc: ParsedDocument) -> StyleProfileSchema:
    """Analyze a parsed document to extract a structured style profile."""

    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured.")

    # We construct a prompt highlighting both raw text and structure
    prompt = f"""
You are an expert style analyzer. I will provide you with a user's uploaded note. 
Your job is to analyze the formatting, structure, tone, and stylistic quirks of this document.

DOCUMENT METADATA:
Headings Found: {len(doc.headings)}
Paragraphs Found: {len(doc.paragraphs)}
Total Lines: {doc.metadata.get('total_lines', 0)}

DOCUMENT CONTENT:
{doc.text[:15000]}  # limit text length to avoid context bloat if it's huge

Based on the content above, infer the user's note-taking style and return a FLAT JSON object
with exactly these keys (primitive values only, no nested objects):
  "heading_style" (string), "section_order" (list of strings), "bullet_style" (string),
  "average_sentence_length" (number), "average_paragraph_length" (number), "heading_depth" (number),
  "bullet_frequency" (number), "diagram_frequency" (number), "table_frequency" (number),
  "code_block_frequency" (number), "example_density" (string), "summary_position" (string),
  "keyword_highlighting" (boolean), "tone" (string), "preferred_sections" (list of strings),
  "formatting_preferences" (object of string->string).
"""

    try:
        response = analysis_model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            ),
        )

        # Parse the flat JSON response and wrap each value into the nested
        # FeatureValue schema the rest of the system expects.
        data = json.loads(response.text)
        return _profile_from_flat(data)

    except Exception as e:
        logger.error(f"Error analyzing style: {e}")
        # Return a fallback default profile (schema defaults are valid FeatureValues).
        return StyleProfileSchema()
