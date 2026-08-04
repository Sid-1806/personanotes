from typing import Dict
from app.feedback.feature_extractor import extract_features
import difflib


def calculate_edit_distance(text1: str, text2: str) -> float:
    matcher = difflib.SequenceMatcher(None, text1, text2)
    return matcher.ratio() * 100.0


def calculate_structural_similarity(f1: Dict, f2: Dict) -> float:
    orig_hd = f1.get("avg_heading_depth", 0)
    edit_hd = f2.get("avg_heading_depth", 0)
    return max(0, 100 - abs(orig_hd - edit_hd) * 20)


def calculate_section_order_similarity(f1: Dict, f2: Dict) -> float:
    wc_diff = abs(f1.get("word_count", 0) - f2.get("word_count", 0))
    return max(0, 100 - (wc_diff / max(1, f1.get("word_count", 1))) * 100)


def calculate_formatting_similarity(f1: Dict, f2: Dict) -> float:
    orig_fmt = f1.get("code_blocks", 0) + f1.get("tables", 0)
    edit_fmt = f2.get("code_blocks", 0) + f2.get("tables", 0)
    return max(0, 100 - abs(orig_fmt - edit_fmt) * 10)


def calculate_sentence_style_similarity(f1: Dict, f2: Dict) -> float:
    sl_diff = abs(f1.get("avg_sentence_length", 0) - f2.get("avg_sentence_length", 0))
    return max(0, 100 - sl_diff * 5)


def calculate_example_density_similarity(f1: Dict, f2: Dict) -> float:
    ex_diff = abs(f1.get("has_examples", 0) - f2.get("has_examples", 0))
    return 100.0 if ex_diff == 0 else 50.0


def evaluate_all_metrics(original_md: str, edited_md: str) -> Dict[str, float]:
    f1 = extract_features(original_md)
    f2 = extract_features(edited_md)

    if not f1 or not f2:
        return {
            "structural_similarity": 0.0,
            "formatting_similarity": 0.0,
            "section_order_similarity": 0.0,
            "sentence_style_similarity": 0.0,
            "example_density_similarity": 0.0,
            "edit_distance_similarity": 0.0,
        }

    return {
        "structural_similarity": calculate_structural_similarity(f1, f2),
        "formatting_similarity": calculate_formatting_similarity(f1, f2),
        "section_order_similarity": calculate_section_order_similarity(f1, f2),
        "sentence_style_similarity": calculate_sentence_style_similarity(f1, f2),
        "example_density_similarity": calculate_example_density_similarity(f1, f2),
        "edit_distance_similarity": calculate_edit_distance(original_md, edited_md),
    }
