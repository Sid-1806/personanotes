"""Pinned style attributes must survive the learning loop.

Pinning is the user saying "I always want this". If an edit could quietly
average it away, the Style page's controls would be decorative.
"""

import pytest

from app.style.learning import (
    N_CONFIDENT,
    observe_categorical,
    observe_numeric,
    pin_value,
    unpin,
)
from app.style.schema import FeatureValue, StyleProfileSchema
from app.feedback.updater import apply_feedback_to_profile
from app.style.prompt_format import summarize_style_for_prompt


def test_pinned_numeric_is_not_moved_by_observation():
    feature = pin_value(FeatureValue(value=3.0), 12.0)
    updated = observe_numeric(feature, 99.0, "an edit")

    assert updated.value == 12.0
    assert updated.pinned is True


def test_pinned_categorical_is_not_moved_by_observation():
    feature = pin_value(FeatureValue(value="Academic"), "Conversational")
    updated = observe_categorical(feature, "Technical", "an edit")

    assert updated.value == "Conversational"
    assert updated.pinned is True


def test_unpinned_numeric_still_learns():
    feature = FeatureValue(value=10.0)
    updated = observe_numeric(feature, 20.0, "an edit")

    assert 10.0 < updated.value <= 20.0
    assert updated.pinned is False


def test_pin_value_asserts_full_confidence():
    pinned = pin_value(FeatureValue(value=1.0, confidence=0.2, observations=1), 7.0)

    assert pinned.value == 7.0
    assert pinned.confidence == 1.0
    assert pinned.observations >= N_CONFIDENT


def test_unpin_resets_evidence_so_learning_restarts():
    pinned = pin_value(FeatureValue(value=2.0), 9.0)
    released = unpin(pinned)

    assert released.pinned is False
    assert released.observations == 0
    assert released.value == 9.0  # the value stays; only the hold is released

    # And it is movable again.
    moved = observe_numeric(released, 19.0, "an edit")
    assert moved.value > 9.0


def test_feedback_pipeline_respects_a_pin():
    profile = StyleProfileSchema()
    profile.average_sentence_length = pin_value(profile.average_sentence_length, 11.0)
    profile.tone = pin_value(profile.tone, "Concise")

    feedback = {
        "changes": [
            {"feature": "average_sentence_length", "observed": 31.0},
            {"feature": "tone", "new": "Academic"},
            {"feature": "bullet_frequency", "observed": 14.0},
        ]
    }
    updated = apply_feedback_to_profile(profile, feedback)

    assert updated.average_sentence_length.value == 11.0
    assert updated.tone.value == "Concise"
    # An unpinned feature in the same payload still learns.
    assert updated.bullet_frequency.value > 0


def test_pinned_values_reach_the_generation_prompt():
    profile = StyleProfileSchema()
    profile.tone = pin_value(profile.tone, "Conversational")

    summary = summarize_style_for_prompt(profile.model_dump())

    assert "Conversational" in summary
