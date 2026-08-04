import pytest
from app.evaluation.engine import compute_overall_score


def test_compute_overall_score():
    metrics = {
        "structural_similarity": 90.0,
        "section_order_similarity": 100.0,
        "formatting_similarity": 80.0,
        "sentence_style_similarity": 85.0,
        "example_density_similarity": 100.0,
        "edit_distance_similarity": 95.0,
    }

    # Weights:
    # struct: 0.15 * 90 = 13.5
    # order: 0.15 * 100 = 15.0
    # fmt: 0.15 * 80 = 12.0
    # style: 0.15 * 85 = 12.75
    # ex: 0.10 * 100 = 10.0
    # edit: 0.30 * 95 = 28.5
    # Total = 13.5 + 15 + 12 + 12.75 + 10 + 28.5 = 91.75

    score = compute_overall_score(metrics)
    assert score == 91.75


def test_compute_overall_score_missing_keys():
    metrics = {"structural_similarity": 100.0}
    score = compute_overall_score(metrics)
    assert score == 15.0  # 100 * 0.15
