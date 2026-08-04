from typing import Dict, Any
from app.evaluation.metrics import evaluate_all_metrics


def compute_overall_score(metrics: Dict[str, float]) -> float:
    """Combine individual metrics into a single weighted score."""
    weights = {
        "structural_similarity": 0.15,
        "section_order_similarity": 0.15,
        "formatting_similarity": 0.15,
        "sentence_style_similarity": 0.15,
        "example_density_similarity": 0.10,
        "edit_distance_similarity": 0.30,
    }

    score = 0.0
    for key, weight in weights.items():
        score += metrics.get(key, 0.0) * weight

    return round(score, 2)


def evaluate_generation(original_md: str, edited_md: str) -> Dict[str, Any]:
    """
    Orchestrates the evaluation of a single note generation.
    Returns the composite score and the individual metrics.
    """
    metrics = evaluate_all_metrics(original_md, edited_md)
    overall_score = compute_overall_score(metrics)

    return {
        "personalization_score": overall_score,
        **{k: round(v, 2) for k, v in metrics.items()},
    }
