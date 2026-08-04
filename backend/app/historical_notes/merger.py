import logging
from typing import Dict, Any
from app.style.schema import StyleProfileSchema
from app.feedback.updater import update_numeric_feature, update_categorical_feature
from datetime import datetime

logger = logging.getLogger(__name__)


def merge_historical_analysis(
    profile: StyleProfileSchema, aggregated_data: Dict[str, Any], note_count: int
) -> StyleProfileSchema:
    """
    Merges aggregated historical data into the current style profile.
    Applies a heavy weight based on the number of notes provided.
    """
    agg = aggregated_data.get("aggregated_features", {})
    subj = aggregated_data.get("subjective_traits", [])

    # 1. Update source contributions
    # Calculate new normalized weights
    current_contribs = profile.source_contributions
    total_existing_weight = sum(current_contribs.values())

    # Each historical note adds a significant base weight (e.g., 0.1 per note)
    historical_weight_added = note_count * 0.1

    new_historical = (
        current_contribs.get("historical_notes", 0.0) + historical_weight_added
    )

    new_total = total_existing_weight + historical_weight_added
    if new_total > 0:
        profile.source_contributions = {
            "historical_notes": round(new_historical / new_total, 2),
            "edited_notes": round(
                current_contribs.get("edited_notes", 0.0) / new_total, 2
            ),
            "generated_feedback": round(
                current_contribs.get("generated_feedback", 0.0) / new_total, 2
            ),
        }

    # 2. Merge Numeric Features
    reason_prefix = f"Averaged across {note_count} imported historical notes."

    # Mapping our internal aggregated metrics to schema properties
    if "avg_sentence_length" in agg:
        delta = agg["avg_sentence_length"] - profile.average_sentence_length.value
        profile.average_sentence_length = update_numeric_feature(
            profile.average_sentence_length, delta, reason_prefix
        )
        # Force high confidence for historical imports
        profile.average_sentence_length.confidence = min(
            1.0, profile.average_sentence_length.confidence + 0.3
        )

    if "code_blocks" in agg and agg["code_blocks"] > 1:
        delta = agg["code_blocks"] - profile.code_block_frequency.value
        profile.code_block_frequency = update_numeric_feature(
            profile.code_block_frequency, delta, reason_prefix
        )
        profile.code_block_frequency.confidence = min(
            1.0, profile.code_block_frequency.confidence + 0.3
        )

    # Map the remaining aggregated numeric features onto their schema fields so
    # historical import learns them too (previously computed and then dropped).
    numeric_map = {
        "avg_paragraph_length": "average_paragraph_length",
        "avg_heading_depth": "heading_depth",
        "bullets": "bullet_frequency",
        "tables": "table_frequency",
        "diagrams": "diagram_frequency",
    }
    for agg_key, field_name in numeric_map.items():
        if agg_key in agg:
            feature = getattr(profile, field_name)
            delta = agg[agg_key] - feature.value
            updated = update_numeric_feature(feature, delta, reason_prefix)
            updated.confidence = min(1.0, updated.confidence + 0.3)
            setattr(profile, field_name, updated)

    # 3. Merge Categorical / Boolean Features
    if agg.get("has_examples", 0) > 0.5:  # If more than 50% of notes have examples
        profile.example_density = update_categorical_feature(
            profile.example_density,
            "High",
            f"Examples detected in >50% of {note_count} imported notes.",
        )
        profile.example_density.confidence = 0.9

    if agg.get("has_summary", 0) > 0.5:
        profile.summary_position = update_categorical_feature(
            profile.summary_position,
            "End",
            f"Summary sections detected in >50% of {note_count} imported notes.",
        )
        profile.summary_position.confidence = 0.9

    # 4. Merge Subjective Features
    # If the LLM noticed a consistent tone shift
    if subj:
        # Just grab the first tone suggestion for simplicity
        tones = [s for s in subj if s.get("feature") == "tone"]
        if tones:
            best_tone = tones[0]
            profile.tone = update_categorical_feature(
                profile.tone,
                best_tone.get("new", "Academic"),
                best_tone.get("reason", "Inferred from historical notes."),
            )
            profile.tone.confidence = 0.85

    return profile
