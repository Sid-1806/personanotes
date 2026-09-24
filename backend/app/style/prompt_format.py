import json
from typing import Any, Dict


def summarize_style_for_prompt(style_profile: Dict[str, Any]) -> str:
    """
    Reduce a StyleProfile (nested ``FeatureValue`` dict) to a compact
    ``{field: value}`` JSON containing only the *learned* preferences.

    The stored profile carries per-field ``confidence`` / ``reason`` /
    ``last_updated`` metadata plus ``source_contributions``. That metadata is
    useful for the dashboard but is noise for the generation model, which only
    needs the values. This helper:

    - flattens each ``FeatureValue`` to its ``value``,
    - drops ``source_contributions`` and empty/default values,
    - omits fields still at their default (unlearned) confidence (<= 0.5), so the
      model is only told about style the system has actually learned.

    Returns a JSON string, or a neutral instruction when nothing has been learned.
    """
    neutral = "No specific style preferred. Use standard, well-structured notes."
    if not style_profile:
        return neutral

    learned: Dict[str, Any] = {}
    for key, feat in style_profile.items():
        if key == "source_contributions":
            continue

        if isinstance(feat, dict) and "value" in feat:
            confidence = feat.get("confidence")
            observations = feat.get("observations", 0) or 0
            # A feature is "learned" if we have observed it at least once, or (for
            # legacy profiles without an observation count) if confidence rose
            # above the default. Otherwise it is still an unlearned default.
            is_learned = observations >= 1 or (
                confidence is not None and confidence > 0.5
            )
            if not is_learned:
                continue
            value = feat.get("value")
        else:
            # Tolerate an already-flat / legacy shape.
            value = feat

        if value in (None, "", [], {}):
            continue
        if isinstance(value, float):
            value = round(value, 1)
        learned[key] = value

    if not learned:
        return neutral
    return json.dumps(learned, indent=2)
