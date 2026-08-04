from typing import Dict, Any, List


def compute_benchmark(metrics_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare Generation 1 vs Generation N."""
    if len(metrics_history) < 2:
        return {
            "overall_improvement": 0,
            "largest_improvements": [],
            "largest_regressions": [],
            "first_generation": {},
            "latest_generation": {},
        }

    first = metrics_history[0]
    latest = metrics_history[-1]

    keys = [
        "structural_similarity",
        "formatting_similarity",
        "section_order_similarity",
        "sentence_style_similarity",
        "example_density_similarity",
        "edit_distance_similarity",
    ]

    deltas = []
    for k in keys:
        if k in first and k in latest:
            diff = latest[k] - first[k]
            deltas.append(
                {
                    "feature": k.replace("_similarity", "").replace("_", " ").title(),
                    "delta": round(diff, 2),
                }
            )

    deltas.sort(key=lambda x: x["delta"], reverse=True)

    improvements = [d for d in deltas if d["delta"] > 0]
    regressions = [d for d in reversed(deltas) if d["delta"] < 0]

    overall_improvement = (
        latest["personalization_score"] - first["personalization_score"]
    )

    return {
        "overall_improvement": round(overall_improvement, 2),
        "largest_improvements": improvements[:3],
        "largest_regressions": regressions[:3],
        "first_generation": {k: first.get(k, 0) for k in keys},
        "latest_generation": {k: latest.get(k, 0) for k in keys},
    }
