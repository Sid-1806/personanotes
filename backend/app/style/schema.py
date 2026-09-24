from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Generic, TypeVar
from datetime import datetime

T = TypeVar("T")


class FeatureValue(BaseModel, Generic[T]):
    value: T
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: str = Field(default="Initial inference.")
    last_updated: Optional[str] = None
    observations: int = 0  # evidence count; drives confidence + convergence
    # When true the user has fixed this value by hand; the learning rule
    # leaves it alone so their explicit choice is never silently overwritten.
    pinned: bool = False


class StyleProfileSchema(BaseModel):
    heading_style: FeatureValue[str] = Field(
        default_factory=lambda: FeatureValue(value="Standard markdown headers")
    )
    section_order: FeatureValue[List[str]] = Field(
        default_factory=lambda: FeatureValue(value=[])
    )
    bullet_style: FeatureValue[str] = Field(
        default_factory=lambda: FeatureValue(value="Standard bullets")
    )
    average_sentence_length: FeatureValue[float] = Field(
        default_factory=lambda: FeatureValue(value=15.0)
    )
    diagram_frequency: FeatureValue[float] = Field(
        default_factory=lambda: FeatureValue(value=0.0)
    )
    table_frequency: FeatureValue[float] = Field(
        default_factory=lambda: FeatureValue(value=0.0)
    )
    code_block_frequency: FeatureValue[float] = Field(
        default_factory=lambda: FeatureValue(value=0.0)
    )
    # Additional numeric structural features (kept in sync with feature_extractor /
    # diff_engine so no deterministically-computed signal is silently dropped).
    average_paragraph_length: FeatureValue[float] = Field(
        default_factory=lambda: FeatureValue(value=0.0)
    )
    heading_depth: FeatureValue[float] = Field(
        default_factory=lambda: FeatureValue(value=0.0)
    )
    bullet_frequency: FeatureValue[float] = Field(
        default_factory=lambda: FeatureValue(value=0.0)
    )
    example_density: FeatureValue[str] = Field(
        default_factory=lambda: FeatureValue(value="Medium")
    )
    summary_position: FeatureValue[str] = Field(
        default_factory=lambda: FeatureValue(value="None")
    )
    keyword_highlighting: FeatureValue[bool] = Field(
        default_factory=lambda: FeatureValue(value=False)
    )
    tone: FeatureValue[str] = Field(
        default_factory=lambda: FeatureValue(value="Academic")
    )
    preferred_sections: FeatureValue[List[str]] = Field(
        default_factory=lambda: FeatureValue(value=[])
    )
    formatting_preferences: FeatureValue[Dict[str, Any]] = Field(
        default_factory=lambda: FeatureValue(value={})
    )

    source_contributions: Dict[str, float] = Field(
        default_factory=lambda: {
            "historical_notes": 0.0,
            "edited_notes": 0.0,
            "generated_feedback": 0.0,
        }
    )


class AnalyzeStyleRequest(BaseModel):
    pass


class UpdateStyleRequest(BaseModel):
    profile: StyleProfileSchema


class AttributeOverrideRequest(BaseModel):
    """Set one attribute by hand from the Style page."""

    value: Any
    pinned: bool = True


class AttributeResetRequest(BaseModel):
    """Clear a hand-set attribute (or the whole profile when feature is None)."""

    feature: Optional[str] = None


class StyleResponse(BaseModel):
    profile: StyleProfileSchema
    version: int
