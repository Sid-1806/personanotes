"""Translate raw style-feedback changes into short, product-friendly sentences.

The feedback pipeline produces internal `changes` (feature deltas / categorical
switches). The UI should show something a person understands -- e.g. "You wrote
shorter sentences" -- not the raw internal features. This module does that
mapping. Pure function, no I/O.
"""

from typing import Any, Dict, List

_NUMERIC_UP = {
    "average_sentence_length": "You wrote longer sentences.",
    "average_paragraph_length": "You wrote longer paragraphs.",
    "heading_depth": "You used deeper heading nesting.",
    "bullet_frequency": "You added more bullet points.",
    "code_block_frequency": "You added more code blocks.",
    "table_frequency": "You added more tables.",
    "diagram_frequency": "You added more diagrams.",
}

_NUMERIC_DOWN = {
    "average_sentence_length": "You wrote shorter, more concise sentences.",
    "average_paragraph_length": "You broke content into shorter paragraphs.",
    "heading_depth": "You flattened the heading structure.",
    "bullet_frequency": "You used fewer bullet points.",
    "code_block_frequency": "You used fewer code blocks.",
    "table_frequency": "You used fewer tables.",
    "diagram_frequency": "You used fewer diagrams.",
}

_LABELS = {
    "average_sentence_length": "Sentence length",
    "average_paragraph_length": "Paragraph length",
    "heading_depth": "Heading structure",
    "bullet_frequency": "Bullet usage",
    "code_block_frequency": "Code examples",
    "table_frequency": "Tables",
    "diagram_frequency": "Diagrams",
    "example_density": "Examples",
    "summary_position": "Summaries",
    "tone": "Tone",
}


def humanize_changes(feedback_data: Dict[str, Any]) -> List[str]:
    """Return user-facing sentences describing what PersonaNotes learned."""
    lines: List[str] = []
    for change in feedback_data.get("changes", []):
        feature = change.get("feature")
        if "delta" in change:
            table = _NUMERIC_UP if change["delta"] > 0 else _NUMERIC_DOWN
            if feature in table:
                lines.append(table[feature])
        elif "new" in change:
            if feature == "summary_position":
                lines.append("You added a summary section.")
            elif feature == "example_density":
                lines.append("You included more examples.")
            elif feature == "tone":
                lines.append(f"You shifted the tone to be {change['new']}.")
            else:
                lines.append(f"{_LABELS.get(feature, feature)} preference updated.")

    # De-duplicate while preserving order.
    seen: set = set()
    unique = [x for x in lines if not (x in seen or seen.add(x))]

    # Append a single confidence note listing the reinforced categories.
    features = sorted(
        {
            c.get("feature")
            for c in feedback_data.get("changes", [])
            if c.get("feature") in _LABELS
        }
    )
    if features:
        labels = ", ".join(_LABELS[f] for f in features)
        unique.append(f"Confidence increased for: {labels}.")

    return unique
