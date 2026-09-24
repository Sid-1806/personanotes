from typing import Dict, Any, List
from app.feedback.feature_extractor import extract_features


def normalize_per_1000_words(count: int, word_count: int) -> float:
    if word_count == 0:
        return 0.0
    return (count / word_count) * 1000


def compare_features(original_md: str, edited_md: str) -> List[Dict[str, Any]]:
    """
    Compare original and edited markdown to produce deterministic feature deltas.
    """
    orig = extract_features(original_md)
    edited = extract_features(edited_md)

    if not orig or not edited:
        return []

    changes = []

    # Helper to calculate delta and threshold
    def add_delta(feature_name: str, metric_name: str, threshold: float = 0.1):
        delta = edited[metric_name] - orig[metric_name]
        if abs(delta) >= threshold:
            changes.append(
                {
                    "feature": feature_name,
                    "delta": round(delta, 2),
                    "observed": round(edited[metric_name], 2),  # absolute edited value
                }
            )

    # Continuous metrics
    add_delta("average_sentence_length", "avg_sentence_length", threshold=2.0)
    add_delta("average_paragraph_length", "avg_paragraph_length", threshold=5.0)
    add_delta("heading_depth", "avg_heading_depth", threshold=0.3)

    # Frequency metrics (normalized per 1000 words)
    orig_wc = orig["word_count"]
    edited_wc = edited["word_count"]

    code_orig = normalize_per_1000_words(orig["code_blocks"], orig_wc)
    code_edit = normalize_per_1000_words(edited["code_blocks"], edited_wc)
    if abs(code_edit - code_orig) > 0.5:
        changes.append(
            {
                "feature": "code_block_frequency",
                "delta": round(code_edit - code_orig, 2),
                "observed": round(code_edit, 2),
            }
        )

    bullet_orig = normalize_per_1000_words(orig["bullets"], orig_wc)
    bullet_edit = normalize_per_1000_words(edited["bullets"], edited_wc)
    if abs(bullet_edit - bullet_orig) > 1.0:
        changes.append(
            {
                "feature": "bullet_frequency",
                "delta": round(bullet_edit - bullet_orig, 2),
                "observed": round(bullet_edit, 2),
            }
        )

    table_orig = normalize_per_1000_words(orig["tables"], orig_wc)
    table_edit = normalize_per_1000_words(edited["tables"], edited_wc)
    if abs(table_edit - table_orig) > 0.5:
        changes.append(
            {
                "feature": "table_frequency",
                "delta": round(table_edit - table_orig, 2),
                "observed": round(table_edit, 2),
            }
        )

    diagram_orig = normalize_per_1000_words(orig["diagrams"], orig_wc)
    diagram_edit = normalize_per_1000_words(edited["diagrams"], edited_wc)
    if abs(diagram_edit - diagram_orig) > 0.5:
        changes.append(
            {
                "feature": "diagram_frequency",
                "delta": round(diagram_edit - diagram_orig, 2),
                "observed": round(diagram_edit, 2),
            }
        )

    # Boolean/Categorical shifts
    if not orig["has_summary"] and edited["has_summary"]:
        changes.append(
            {
                "feature": "summary_position",
                "new": "End",
                "reason": "User explicitly added a summary.",
            }
        )

    if not orig["has_examples"] and edited["has_examples"]:
        changes.append(
            {
                "feature": "example_density",
                "new": "High",
                "reason": "User explicitly added examples.",
            }
        )

    return changes
