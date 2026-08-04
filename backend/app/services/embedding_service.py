import logging
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize model globally so it is loaded once
logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    length_function=len,
    is_separator_regex=False,
)


def get_text_chunks(text: str) -> list[str]:
    """Split text into overlapping chunks."""
    return text_splitter.split_text(text)


def generate_embeddings(chunks: list[str]) -> list[list[float]]:
    """Generate dense vector embeddings for a list of text chunks."""
    if not chunks:
        return []

    # model.encode returns a numpy array, convert to list of floats for Qdrant
    embeddings = model.encode(chunks, convert_to_numpy=True).tolist()
    return embeddings
