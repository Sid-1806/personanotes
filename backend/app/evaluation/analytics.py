from typing import Dict, Any, List


def calculate_improvement_insights(metrics_history: List[Dict[str, Any]]) -> List[str]:
    """Generate textual insights based on historical metrics data."""
    if len(metrics_history) < 2:
        return ["Not enough data to generate insights yet. Keep editing notes!"]

    insights = []

    first = metrics_history[0]
    latest = metrics_history[-1]

    # Personalization score trend
    score_diff = latest["personalization_score"] - first["personalization_score"]
    if score_diff > 5:
        insights.append(
            f"Overall personalization has improved by {round(score_diff)}% since you started."
        )
    elif score_diff < -5:
        insights.append(
            f"Overall personalization has dropped by {round(abs(score_diff))}%."
        )

    # Structural trend
    struct_diff = latest["structural_similarity"] - first["structural_similarity"]
    if struct_diff > 10:
        insights.append(
            "The system has become significantly better at matching your preferred heading hierarchy."
        )

    # Example density
    if latest["example_density_similarity"] > 90:
        insights.append(
            f"Example density now matches your preferred style with {round(latest['example_density_similarity'])}% similarity."
        )

    # Edit distance
    edit_diff = latest["edit_distance_similarity"] - first["edit_distance_similarity"]
    if edit_diff > 10:
        insights.append(
            f"Your manual edits have decreased, increasing edit similarity by {round(edit_diff)}%."
        )

    if not insights:
        insights.append(
            "Your style profile is stabilizing. The AI is learning steadily."
        )

    return insights
