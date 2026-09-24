"""Unified, evidence-based style-profile updates.

One update rule used by every path (feedback, historical import, analyze,
merge). Numeric features are a recency-weighted running mean toward observed
values: the step is 1/n (converges as evidence grows) but capped at 1/N_MAX so
the profile never fully freezes and can re-open if the user's style shifts.
Confidence is derived from the evidence count, not ad-hoc bumps.

A feature the user has **pinned** is never moved by observation. Pinning is how
someone says "I always want tables" and has it stick; silently learning over an
explicit choice would make the Style page's controls a lie.
"""

from datetime import datetime, timezone
from app.style.schema import FeatureValue

N_MAX = 20        # cap on effective evidence -> step floors at 1/N_MAX (stays adaptive)
N_CONFIDENT = 6   # observations at which confidence approaches 1.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confidence(observations: int) -> float:
    return round(min(1.0, observations / N_CONFIDENT), 3)


def observe_numeric(
    feature: FeatureValue, observed: float, reason: str, count: int = 1
) -> FeatureValue:
    """Update a numeric feature toward an observed value.

    `count` lets bulk evidence (e.g. a historical import of N notes) advance the
    running mean more decisively than a single edit.
    """
    if getattr(feature, "pinned", False):
        return feature

    observations = feature.observations + count
    n_eff = min(observations, N_MAX)
    step = min(1.0, count / n_eff)  # first/bulk evidence adopts more of the observation
    new_value = feature.value + step * (observed - feature.value)
    return FeatureValue(
        value=round(new_value, 3),
        confidence=_confidence(n_eff),
        reason=reason,
        last_updated=_now(),
        observations=observations,
    )


def observe_categorical(
    feature: FeatureValue, observed: str, reason: str, count: int = 1
) -> FeatureValue:
    """Update a categorical feature. Agreement builds confidence; a change resets it.

    `count` lets bulk evidence (a historical import) build confidence in one step.
    """
    if getattr(feature, "pinned", False):
        return feature

    if feature.value == observed:
        observations = feature.observations + count
    else:
        observations = count  # new belief, supported by `count` observations
    return FeatureValue(
        value=observed,
        confidence=_confidence(observations),
        reason=reason,
        last_updated=_now(),
        observations=observations,
    )


def pin_value(feature: FeatureValue, value, reason: str = "") -> FeatureValue:
    """Set a feature by hand and hold it there.

    Confidence goes to 1.0 because the value is no longer an inference — the
    user stated it.
    """
    return FeatureValue(
        value=value,
        confidence=1.0,
        reason=reason or "You set this yourself.",
        last_updated=_now(),
        observations=max(feature.observations, N_CONFIDENT),
        pinned=True,
    )


def unpin(feature: FeatureValue) -> FeatureValue:
    """Release a hand-set feature so learning can move it again.

    Evidence is reset to zero: the pinned value was asserted, not observed, so
    it should not count as accumulated evidence once the user steps back.
    """
    return FeatureValue(
        value=feature.value,
        confidence=0.5,
        reason="Learning again from your notes and edits.",
        last_updated=_now(),
        observations=0,
        pinned=False,
    )
