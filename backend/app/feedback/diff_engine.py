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
                    "original": round(orig[metric_name], 2),
                    "edited": round(edited[metric_name], 2),
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
            }
        )

    bullet_orig = normalize_per_1000_words(orig["bullets"], orig_wc)
    bullet_edit = normalize_per_1000_words(edited["bullets"], edited_wc)
    if abs(bullet_edit - bullet_orig) > 1.0:
        changes.append(
            {
                "feature": "bullet_frequency",
                "delta": round(bullet_edit - bullet_orig, 2),
            }
        )

    table_orig = normalize_per_1000_words(orig["tables"], orig_wc)
    table_edit = normalize_per_1000_words(edited["tables"], edited_wc)
    if abs(table_edit - table_orig) > 0.5:
        changes.append(
            {
                "feature": "table_frequency",
                "delta": round(table_edit - table_orig, 2),
            }
        )

    diagram_orig = normalize_per_1000_words(orig["diagrams"], orig_wc)
    diagram_edit = normalize_per_1000_words(edited["diagrams"], edited_wc)
    if abs(diagram_edit - diagram_orig) > 0.5:
        changes.append(
            {
                "feature": "diagram_frequency",
                "delta": round(diagram_edit - diagram_orig, 2),
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


def compute_evaluation_metrics(original_md: str, edited_md: str) -> Dict[str, float]:
    """
    Compute detailed structural similarity metrics (0-100 scale).
    """
    import difflib

    orig = extract_features(original_md)
    edited = extract_features(edited_md)

    if not orig or not edited:
        return {
            "personalization_score": 0.0,
            "structural_similarity": 0.0,
            "formatting_similarity": 0.0,
            "section_order_similarity": 0.0,
            "sentence_style_similarity": 0.0,
            "example_density_similarity": 0.0,
            "edit_distance_similarity": 0.0,
        }

    # Edit distance (SequenceMatcher ratio)
    matcher = difflib.SequenceMatcher(None, original_md, edited_md)
    edit_dist = matcher.ratio() * 100.0

    # Structural similarity (headings and depth)
    orig_hd = orig.get("avg_heading_depth", 0)
    edit_hd = edited.get("avg_heading_depth", 0)
    struct_sim = max(0, 100 - abs(orig_hd - edit_hd) * 20)

    # Section order (rough proxy via word count difference for now)
    wc_diff = abs(orig.get("word_count", 0) - edited.get("word_count", 0))
    sec_order_sim = max(0, 100 - (wc_diff / max(1, orig.get("word_count", 1))) * 100)

    # Formatting (code blocks and tables)
    orig_fmt = orig.get("code_blocks", 0) + orig.get("tables", 0)
    edit_fmt = edited.get("code_blocks", 0) + edited.get("tables", 0)
    fmt_sim = max(0, 100 - abs(orig_fmt - edit_fmt) * 10)

    # Sentence style (average sentence length)
    sl_diff = abs(
        orig.get("avg_sentence_length", 0) - edited.get("avg_sentence_length", 0)
    )
    sent_sim = max(0, 100 - sl_diff * 5)

    # Example density
    ex_diff = abs(orig.get("has_examples", 0) - edited.get("has_examples", 0))
    ex_sim = 100 if ex_diff == 0 else 50

    # Composite Personalization Score
    # The higher the edit distance, the lower the personalization score (meaning it WAS personalized well if it didn't need edits)
    # Wait, the user said: "This should represent how closely the generated notes matched the user's preferred style before manual editing."
    # Therefore, fewer edits = higher score.
    pers_score = (
        struct_sim * 0.15
        + sec_order_sim * 0.15
        + fmt_sim * 0.15
        + sent_sim * 0.15
        + ex_sim * 0.10
        + edit_dist * 0.30
    )

    return {
        "personalization_score": round(pers_score, 2),
        "structural_similarity": round(struct_sim, 2),
        "formatting_similarity": round(fmt_sim, 2),
        "section_order_similarity": round(sec_order_sim, 2),
        "sentence_style_similarity": round(sent_sim, 2),
        "example_density_similarity": round(ex_sim, 2),
        "edit_distance_similarity": round(edit_dist, 2),
    }
