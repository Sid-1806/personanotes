from typing import Dict, Any
from app.style.schema import StyleProfileSchema, FeatureValue
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

LEARNING_RATE = 0.2


def update_numeric_feature(
    feature: FeatureValue[float], delta: float, reason: str
) -> FeatureValue[float]:
    # Weighted average: high confidence means slower change. Low confidence means faster change.
    weight = LEARNING_RATE * (
        1.0 - feature.confidence + 0.1
    )  # +0.1 to always have some learning
    new_val = feature.value + (delta * weight)

    # Confidence increases slightly when updated, as we're learning more about the user
    new_conf = min(1.0, feature.confidence + 0.05)

    return FeatureValue(
        value=new_val,
        confidence=new_conf,
        reason=reason,
        last_updated=datetime.utcnow().isoformat(),
    )


def update_categorical_feature(
    feature: FeatureValue[str], new_val: str, reason: str
) -> FeatureValue[str]:
    # For categorical, we switch to the new value but lower confidence initially, unless it was already low
    return FeatureValue(
        value=new_val,
        confidence=0.6,
        reason=reason,
        last_updated=datetime.utcnow().isoformat(),
    )


def apply_feedback_to_profile(
    profile: StyleProfileSchema, feedback_json: Dict[str, Any]
) -> StyleProfileSchema:
    """
    Apply structured feedback to the StyleProfileSchema using confidence-weighted updates.
    """
    changes = feedback_json.get("changes", [])
    if not changes:
        return profile

    for change in changes:
        feat_name = change.get("feature")
        if not hasattr(profile, feat_name):
            continue

        current_feature = getattr(profile, feat_name)

        # Handle Numeric deltas
        if "delta" in change:
            reason = f"Adjusted by {change['delta']} based on recent edit."
            if isinstance(current_feature.value, (int, float)):
                new_feature = update_numeric_feature(
                    current_feature, float(change["delta"]), reason
                )
                setattr(profile, feat_name, new_feature)

        # Handle Categorical shifts (e.g. tone)
        elif "new" in change:
            reason = change.get(
                "reason", "User explicitly changed this formatting style."
            )
            if isinstance(current_feature.value, str):
                new_feature = update_categorical_feature(
                    current_feature, change["new"], reason
                )
                setattr(profile, feat_name, new_feature)

    return profile
