"""Single source of truth for style-feature units and extractor mapping.

Every producer (feedback diff, historical aggregate, analyzer) and the learning
updater reference this so numeric features are always in a consistent unit.
Frequencies are normalized **per 1000 words**; the rest are raw averages.
"""

# feature name -> (feature_extractor metric key, normalized per-1000-words?)
NUMERIC_FEATURES = {
    "average_sentence_length": ("avg_sentence_length", False),
    "average_paragraph_length": ("avg_paragraph_length", False),
    "heading_depth": ("avg_heading_depth", False),
    "bullet_frequency": ("bullets", True),
    "code_block_frequency": ("code_blocks", True),
    "table_frequency": ("tables", True),
    "diagram_frequency": ("diagrams", True),
}

# categorical features updated from feedback/historical (others are LLM-only)
CATEGORICAL_FEATURES = ("example_density", "summary_position", "tone")


def per_1000(count: float, word_count: int) -> float:
    """Normalize a raw count to a per-1000-word rate."""
    if word_count <= 0:
        return 0.0
    return (count / word_count) * 1000.0
