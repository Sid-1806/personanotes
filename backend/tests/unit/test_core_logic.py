"""Unit tests for the pure business logic: style schema, profile merging,
confidence-weighted feedback, feature extraction, diffing, and evaluation.

These cover the deterministic core without needing Postgres, Qdrant, or Gemini.
"""

from app.style.schema import StyleProfileSchema, FeatureValue
from app.style.updater import merge_profiles
from app.style.prompt_format import summarize_style_for_prompt
from app.feedback.updater import apply_feedback_to_profile, LEARNING_RATE
from app.feedback.feature_extractor import extract_features
from app.feedback.diff_engine import compare_features
from app.evaluation.engine import evaluate_generation
from app.historical_notes.merger import merge_historical_analysis


# --- Schema ---------------------------------------------------------------

def test_default_profile_has_16_feature_fields():
    profile = StyleProfileSchema()
    feature_fields = [
        name for name, val in profile.model_dump().items()
        if isinstance(val, dict) and "confidence" in val
    ]
    assert len(feature_fields) == 16


def test_profile_round_trips_through_json():
    profile = StyleProfileSchema()
    restored = StyleProfileSchema(**profile.model_dump())
    assert restored.model_dump() == profile.model_dump()


# --- merge_profiles -------------------------------------------------------

def test_merge_averages_numeric_prefers_new_categorical_unions_lists():
    existing = StyleProfileSchema()
    existing.average_sentence_length.value = 10.0
    existing.tone.value = "Academic"
    existing.section_order.value = ["Intro"]

    incoming = StyleProfileSchema()
    incoming.average_sentence_length.value = 20.0
    incoming.tone.value = "Casual"
    incoming.section_order.value = ["Summary"]

    merged = merge_profiles(existing.model_dump(), incoming)

    assert merged["average_sentence_length"]["value"] == 15.0     # moving average
    assert merged["tone"]["value"] == "Casual"                     # prefer newest
    assert set(merged["section_order"]["value"]) == {"Intro", "Summary"}  # union
    # result must still parse back into the schema
    assert StyleProfileSchema(**merged) is not None


# --- apply_feedback_to_profile -------------------------------------------

def test_numeric_feedback_is_confidence_weighted():
    profile = StyleProfileSchema()  # average_sentence_length starts at 15.0, confidence 0.5
    result = apply_feedback_to_profile(
        profile, {"changes": [{"feature": "average_sentence_length", "delta": 4.0}]}
    )
    weight = LEARNING_RATE * (1 - 0.5 + 0.1)  # 0.2 * 0.6 = 0.12
    assert result.average_sentence_length.value == 15.0 + 4.0 * weight  # 15.48


def test_categorical_feedback_switches_value():
    profile = StyleProfileSchema()
    result = apply_feedback_to_profile(
        profile, {"changes": [{"feature": "tone", "new": "Casual"}]}
    )
    assert result.tone.value == "Casual"


def test_unknown_feature_is_ignored_gracefully():
    profile = StyleProfileSchema()
    before = profile.model_dump()
    result = apply_feedback_to_profile(
        profile, {"changes": [{"feature": "not_a_real_field", "delta": 5.0}]}
    )
    assert result.model_dump() == before


# --- feature extraction + diff -------------------------------------------

def test_feature_extractor_counts_structure():
    md = "# Heading\n\n- one\n- two\n\n```\ncode\n```\n\nHello world."
    features = extract_features(md)
    assert features["heading_count"] == 1
    assert features["bullets"] == 2
    assert features["code_blocks"] == 1


def test_compare_features_returns_a_list_of_changes():
    changes = compare_features(
        "Short.",
        "This is a considerably longer sentence with many more words than before.",
    )
    assert isinstance(changes, list)


# --- evaluation -----------------------------------------------------------

def test_identical_documents_score_near_100():
    doc = "# Topic\n\n## Overview\n\nSome content here. And more content."
    result = evaluate_generation(doc, doc)
    assert 0 <= result["personalization_score"] <= 100
    assert result["personalization_score"] > 90


def test_more_edits_lower_the_score():
    draft = "# A\n\nShort note."
    small_edit = "# A\n\nShort note!"
    big_edit = "# A\n\n## B\n\nCompletely rewritten and much longer note with tables and lists."
    assert (
        evaluate_generation(draft, small_edit)["personalization_score"]
        > evaluate_generation(draft, big_edit)["personalization_score"]
    )


# --- prompt compaction ----------------------------------------------------

def test_summarize_drops_metadata_and_unlearned_defaults():
    profile = StyleProfileSchema()
    profile.tone.value = "Casual"
    profile.tone.confidence = 0.9  # learned
    # heading_style stays at default confidence 0.5 -> should be dropped

    out = summarize_style_for_prompt(profile.model_dump())
    assert "Casual" in out
    assert "confidence" not in out        # no metadata leaks
    assert "reason" not in out
    assert "heading_style" not in out     # unlearned default omitted


def test_summarize_empty_profile_is_neutral():
    assert summarize_style_for_prompt({}).startswith("No specific style")


# --- historical merge -----------------------------------------------------

def test_historical_merge_learns_numeric_features_with_high_confidence():
    aggregated = {
        "aggregated_features": {
            "avg_sentence_length": 18.0,
            "avg_paragraph_length": 40.0,
            "avg_heading_depth": 2.0,
            "bullets": 5.0,
            "code_blocks": 2.0,
            "tables": 1.0,
            "diagrams": 1.0,
            "has_examples": 1.0,
            "has_summary": 1.0,
        },
        "subjective_traits": [],
    }
    profile = merge_historical_analysis(StyleProfileSchema(), aggregated, note_count=3)
    assert profile.average_sentence_length.value != 15.0        # moved from default
    assert profile.average_sentence_length.confidence >= 0.8    # anchored high
    assert profile.example_density.value == "High"              # >50% had examples
