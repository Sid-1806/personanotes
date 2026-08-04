import logging
from typing import Dict, Any, List
from app.feedback.feature_extractor import extract_features
from app.feedback.style_feedback import get_subjective_feedback

logger = logging.getLogger(__name__)


def analyze_historical_note(markdown_text: str) -> Dict[str, Any]:
    """
    Analyzes a single historical note using both deterministic feature extraction
    and subjective Gemini analysis.
    """
    # 1. Deterministic Structural Extraction
    features = extract_features(markdown_text)

    # 2. Subjective Extraction (Comparing against a 'generic' baseline)
    # We pass empty strings to simulate a generic baseline to extract pure tone.
    subjective_data = get_subjective_feedback("", markdown_text)
    subjective_changes = subjective_data.get("changes", [])

    return {"features": features, "subjective": subjective_changes}


def aggregate_historical_features(analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Averages the extracted features across multiple historical notes to build a robust baseline.
    """
    if not analyses:
        return {}

    count = len(analyses)
    agg: Dict[str, float] = {
        "avg_sentence_length": 0,
        "avg_paragraph_length": 0,
        "avg_heading_depth": 0,
        "bullets": 0,
        "code_blocks": 0,
        "tables": 0,
        "diagrams": 0,
        "has_examples": 0,
        "has_summary": 0,
    }

    subjective_traits = []

    for analysis in analyses:
        f = analysis.get("features", {})
        agg["avg_sentence_length"] += f.get("avg_sentence_length", 0)
        agg["avg_paragraph_length"] += f.get("avg_paragraph_length", 0)
        agg["avg_heading_depth"] += f.get("avg_heading_depth", 0)

        # Normalize per 1000 words
        wc = max(1, f.get("word_count", 1))
        agg["bullets"] += (f.get("bullets", 0) / wc) * 1000
        agg["code_blocks"] += (f.get("code_blocks", 0) / wc) * 1000
        agg["tables"] += (f.get("tables", 0) / wc) * 1000
        agg["diagrams"] += (f.get("diagrams", 0) / wc) * 1000

        agg["has_examples"] += 1 if f.get("has_examples") else 0
        agg["has_summary"] += 1 if f.get("has_summary") else 0

        subjective_traits.extend(analysis.get("subjective", []))

    # Calculate averages
    for k in agg:
        agg[k] /= count

    return {"aggregated_features": agg, "subjective_traits": subjective_traits}
