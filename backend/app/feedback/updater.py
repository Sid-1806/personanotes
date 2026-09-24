"""Apply structured edit-feedback to a style profile.

Thin wrapper over the unified, evidence-based learning rule in
``app.style.learning`` so the feedback path, historical import, and analyze merge
all converge the same way. Numeric changes carry an absolute ``observed`` value
(unit-consistent, from the diff engine); categorical changes carry ``new``.
"""

from typing import Dict, Any
from app.style.schema import StyleProfileSchema
from app.style.learning import observe_numeric, observe_categorical


def apply_feedback_to_profile(
    profile: StyleProfileSchema, feedback_json: Dict[str, Any]
) -> StyleProfileSchema:
    for change in feedback_json.get("changes", []):
        feat_name = change.get("feature")
        if not feat_name or not hasattr(profile, feat_name):
            continue

        current = getattr(profile, feat_name)

        # Numeric: move the running mean toward the observed edited value.
        if "observed" in change and isinstance(current.value, (int, float)) and not isinstance(
            current.value, bool
        ):
            setattr(
                profile,
                feat_name,
                observe_numeric(
                    current, float(change["observed"]), "Learned from your recent edit."
                ),
            )
        # Categorical: adopt the new value; agreement over time builds confidence.
        elif "new" in change and isinstance(current.value, str):
            reason = change.get("reason", "Learned from your recent edit.")
            setattr(
                profile, feat_name, observe_categorical(current, change["new"], reason)
            )

    return profile
