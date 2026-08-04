import google.generativeai as genai
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from app.core.config import settings
from app.services.vector_db import client as qdrant_client
from app.services.embedding_service import model as embedding_model
from app.style.prompt_format import summarize_style_for_prompt
import logging

logger = logging.getLogger(__name__)

# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

generation_model = genai.GenerativeModel("gemini-2.5-flash")


def search_qdrant(query: str, user_id: int, limit: int = 5) -> list[str]:
    """Embed the query and search Qdrant for relevant chunks belonging to this user."""
    try:
        # Generate embedding for the query
        query_vector = embedding_model.encode([query], convert_to_numpy=True).tolist()[
            0
        ]

        # Search Qdrant, restricted to the current user's own lecture chunks.
        # Without this filter, retrieval would leak other users' content.
        results = qdrant_client.query_points(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(key="user_id", match=MatchValue(value=user_id))
                ]
            ),
            limit=limit,
        ).points

        # Extract text from payloads
        chunks = [hit.payload.get("text", "") for hit in results if hit.payload]
        return chunks
    except Exception as e:
        logger.error(f"Error searching Qdrant: {e}")
        return []


def generate_notes(prompt: str, style_profile: dict, user_id: int) -> str:
    """Generate notes using Gemini based on retrieved context and user style profile."""
    if not settings.GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY is not configured in the backend."

    # 1. Retrieve context
    context_chunks = search_qdrant(prompt, user_id)
    context_text = "\n\n---\n\n".join(context_chunks)

    # 2. Build the prompt
    system_instruction = (
        "You are an expert AI tutor and note-generator. "
        "Use the provided lecture excerpts to answer the user's prompt. "
        "You MUST strictly adhere to the user's Personalization Style Profile provided below. "
        "Format the output exactly according to their stylistic preferences (headings, bullet types, tone, etc.). "
        "If the lecture excerpts do not contain the answer, you may use your general knowledge, "
        "but prioritize the provided context."
    )

    # Compact the profile to just the learned values so the model focuses on
    # them rather than the confidence/reason/timestamp metadata.
    style_json = summarize_style_for_prompt(style_profile)

    full_prompt = f"""
{system_instruction}

USER STYLE PROFILE:
{style_json}

LECTURE EXCERPTS:
{context_text}

USER PROMPT:
{prompt}
"""

    # 3. Call Gemini
    try:
        response = generation_model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        logger.error(f"Error generating notes with Gemini: {e}")
        return f"An error occurred while generating notes: {str(e)}"
