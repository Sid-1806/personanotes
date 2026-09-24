"""Unit tests for the pure business logic: style schema, profile merging,
confidence-weighted feedback, feature extraction, diffing, and evaluation.

These cover the deterministic core without needing Postgres, Qdrant, or Gemini.
"""

from app.style.schema import StyleProfileSchema, FeatureValue
from app.style.updater import merge_profiles
from app.style.prompt_format import summarize_style_for_prompt
from app.style.learning import observe_numeric, observe_categorical, N_CONFIDENT
from app.feedback.updater import apply_feedback_to_profile
from app.feedback.feature_extractor import extract_features
from app.feedback.diff_engine import compare_features
from app.evaluation.engine import evaluate_generation
from app.historical_notes.merger import merge_historical_analysis
from app.feedback.summary import humanize_changes
from app.services.ocr_utils import needs_ocr


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

def test_merge_adopts_new_on_first_evidence_and_unions_lists():
    existing = StyleProfileSchema()
    existing.average_sentence_length.value = 10.0   # observations 0 (no evidence yet)
    existing.tone.value = "Academic"
    existing.section_order.value = ["Intro"]

    incoming = StyleProfileSchema()
    incoming.average_sentence_length.value = 20.0
    incoming.tone.value = "Casual"
    incoming.section_order.value = ["Summary"]

    merged = merge_profiles(existing.model_dump(), incoming)

    # First observation adopts the observed value (running mean, step = 1/1).
    assert merged["average_sentence_length"]["value"] == 20.0
    assert merged["average_sentence_length"]["observations"] == 1
    assert merged["tone"]["value"] == "Casual"                     # newest observation
    assert set(merged["section_order"]["value"]) == {"Intro", "Summary"}  # union
    assert StyleProfileSchema(**merged) is not None


def test_merge_converges_toward_a_mean_after_evidence():
    existing = StyleProfileSchema()
    existing.average_sentence_length.value = 10.0
    existing.average_sentence_length.observations = 1  # already one observation

    incoming = StyleProfileSchema()
    incoming.average_sentence_length.value = 20.0

    merged = merge_profiles(existing.model_dump(), incoming)

    # Second observation moves halfway (step = 1/2), not all the way to 20.
    assert merged["average_sentence_length"]["value"] == 15.0
    assert merged["average_sentence_length"]["observations"] == 2


# --- apply_feedback_to_profile -------------------------------------------

def test_numeric_feedback_adopts_observed_value_then_converges():
    profile = StyleProfileSchema()  # average_sentence_length starts at 15.0, no evidence

    # First edit: observed absolute value is adopted (running mean, step = 1/1).
    profile = apply_feedback_to_profile(
        profile, {"changes": [{"feature": "average_sentence_length", "observed": 25.0}]}
    )
    assert profile.average_sentence_length.value == 25.0
    assert profile.average_sentence_length.observations == 1

    # Second edit toward a lower value: moves halfway (step = 1/2), not fully.
    profile = apply_feedback_to_profile(
        profile, {"changes": [{"feature": "average_sentence_length", "observed": 15.0}]}
    )
    assert profile.average_sentence_length.value == 20.0
    assert profile.average_sentence_length.observations == 2


def test_confidence_grows_with_evidence():
    feat = FeatureValue(value=15.0)     # fresh feature, no evidence
    feat = observe_numeric(feat, 18.0, "obs")   # first real observation
    prev = feat.confidence
    for _ in range(N_CONFIDENT + 2):
        feat = observe_numeric(feat, 18.0, "obs")
        assert feat.confidence >= prev  # monotonically non-decreasing with evidence
        prev = feat.confidence
    assert feat.confidence == 1.0       # saturates once enough evidence accrues


def test_categorical_change_resets_then_reinforces_confidence():
    feat = StyleProfileSchema().tone
    changed = observe_categorical(feat, "Casual", "switched")
    reinforced = observe_categorical(changed, "Casual", "again")
    assert reinforced.value == "Casual"
    assert reinforced.confidence > changed.confidence  # agreement builds confidence


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
    assert profile.average_sentence_length.value == 18.0        # adopted the corpus mean
    assert profile.average_sentence_length.observations == 3    # counted 3 notes of evidence
    assert profile.average_sentence_length.confidence >= 0.4    # confidence reflects evidence
    assert profile.example_density.value == "High"              # >50% had examples


# --- humanized feedback summary ------------------------------------------

def test_humanize_translates_changes_to_sentences():
    feedback = {
        "changes": [
            {"feature": "average_sentence_length", "delta": -3.0},
            {"feature": "bullet_frequency", "delta": 2.0},
            {"feature": "summary_position", "new": "End"},
            {"feature": "tone", "new": "Casual"},
        ]
    }
    out = humanize_changes(feedback)
    assert any("shorter" in s for s in out)
    assert any("bullet points" in s for s in out)
    assert any("summary section" in s for s in out)
    assert any("Casual" in s for s in out)
    assert any(s.startswith("Confidence increased for:") for s in out)


def test_humanize_empty_changes_returns_empty_list():
    assert humanize_changes({"changes": []}) == []


# --- OCR fallback decision ------------------------------------------------

def test_needs_ocr_detects_sparse_text():
    assert needs_ocr("") is True
    assert needs_ocr("   \n  ") is True
    assert needs_ocr("only a handful of words") is True   # < 40 chars
    assert needs_ocr("x" * 100) is False
