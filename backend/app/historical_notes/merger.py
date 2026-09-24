import logging
from typing import Dict, Any
from app.style.schema import StyleProfileSchema
from app.style.features import NUMERIC_FEATURES
from app.style.learning import observe_numeric, observe_categorical

logger = logging.getLogger(__name__)


def merge_historical_analysis(
    profile: StyleProfileSchema, aggregated_data: Dict[str, Any], note_count: int
) -> StyleProfileSchema:
    """Merge aggregated historical features into the profile.

    Uses the same evidence-based update as every other path. A bulk import of
    ``note_count`` notes counts as that many observations, so confidence grows
    with the amount of real evidence rather than a fixed bump.
    """
    agg = aggregated_data.get("aggregated_features", {})
    subj = aggregated_data.get("subjective_traits", [])
    count = max(1, note_count)

    # 1. Provenance weighting (separate from feature confidence).
    contribs = profile.source_contributions
    total = sum(contribs.values())
    added = note_count * 0.1
    new_hist = contribs.get("historical_notes", 0.0) + added
    new_total = total + added
    if new_total > 0:
        profile.source_contributions = {
            "historical_notes": round(new_hist / new_total, 2),
            "edited_notes": round(contribs.get("edited_notes", 0.0) / new_total, 2),
            "generated_feedback": round(
                contribs.get("generated_feedback", 0.0) / new_total, 2
            ),
        }

    # 2. Numeric features — one unified rule, unit-consistent with the aggregator.
    reason = f"Averaged across {note_count} imported historical note(s)."
    for field, (metric_key, _per_1000) in NUMERIC_FEATURES.items():
        if metric_key in agg:
            current = getattr(profile, field)
            setattr(profile, field, observe_numeric(current, agg[metric_key], reason, count=count))

    # 3. Categorical / boolean features detected across the corpus.
    if agg.get("has_examples", 0) > 0.5:
        profile.example_density = observe_categorical(
            profile.example_density,
            "High",
            f"Examples detected in >50% of {note_count} imported notes.",
            count=count,
        )
    if agg.get("has_summary", 0) > 0.5:
        profile.summary_position = observe_categorical(
            profile.summary_position,
            "End",
            f"Summary sections detected in >50% of {note_count} imported notes.",
            count=count,
        )

    # 4. Subjective tone from the LLM pass.
    tones = [s for s in subj if s.get("feature") == "tone"]
    if tones:
        profile.tone = observe_categorical(
            profile.tone,
            tones[0].get("new", "Academic"),
            tones[0].get("reason", "Inferred from historical notes."),
            count=count,
        )

    return profile
