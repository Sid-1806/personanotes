from typing import Any, Dict
from app.style.schema import StyleProfileSchema
from app.style.features import NUMERIC_FEATURES
from app.style.learning import observe_numeric, observe_categorical
import logging

logger = logging.getLogger(__name__)


def merge_profiles(
    existing: Dict[str, Any], new_profile: StyleProfileSchema
) -> Dict[str, Any]:
    """
    Merge a new StyleProfile into an existing profile dictionary.
    This allows the system to slowly adapt rather than abruptly overwrite everything.

    Both profiles use the nested FeatureValue schema, so all merging happens on the
    ``.value`` of each field while confidence/reason metadata is preserved.
    """
    if not existing:
        return new_profile.model_dump()

    # Parse the stored profile back into the schema. Fall back to defaults if the
    # stored JSON is malformed or from an older shape.
    try:
        current = StyleProfileSchema(**existing)
    except Exception:
        logger.warning("Existing style profile could not be parsed; using defaults.")
        current = StyleProfileSchema()

    # 1. Categorical / string fields: treat the new inference as an observation
    #    (repeated agreement builds confidence; a change re-opens the belief).
    for field in (
        "heading_style",
        "bullet_style",
        "example_density",
        "summary_position",
        "tone",
    ):
        cur = getattr(current, field)
        new = getattr(new_profile, field)
        setattr(current, field, observe_categorical(cur, new.value, new.reason))

    # 2. Numeric metrics: evidence-based running mean toward the new value.
    #    Covers every numeric feature via the single source of truth.
    for field in NUMERIC_FEATURES:
        cur = getattr(current, field)
        new = getattr(new_profile, field)
        setattr(current, field, observe_numeric(cur, new.value, new.reason))

    # 3. List fields: union of unique items, preserving order.
    for field in ("section_order", "preferred_sections"):
        cur = getattr(current, field)
        new = getattr(new_profile, field)
        merged_items = list(cur.value)
        for item in new.value:
            if item not in merged_items:
                merged_items.append(item)
        cur.value = merged_items

    # 4. Boolean: take the newest.
    current.keyword_highlighting.value = new_profile.keyword_highlighting.value

    # 5. Dict field: shallow-merge the new keys on top of existing.
    merged_fmt = dict(current.formatting_preferences.value)
    merged_fmt.update(new_profile.formatting_preferences.value)
    current.formatting_preferences.value = merged_fmt

    return current.model_dump()
