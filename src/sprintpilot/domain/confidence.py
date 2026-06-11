"""Engineering confidence assessment domain models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sprintpilot.domain.artifacts import MissingInformation, Reasoning, Recommendation, Risk


def _strip_required(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must not be empty")
    return stripped


class ConfidenceFactorScore(BaseModel):
    """Score and explanation for one confidence factor."""

    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    score: int = Field(ge=0, le=100)
    weight: int = Field(gt=0, le=100)
    reason_code: str
    reasoning: str
    evidence: list[str] = Field(default_factory=list)

    @field_validator("key", "label", "reason_code", "reasoning")
    @classmethod
    def fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "confidence factor field")


class ScoreCap(BaseModel):
    """A cap applied to the weighted score."""

    model_config = ConfigDict(extra="forbid")

    reason: str
    cap: int = Field(ge=0, le=100)
    explanation: str

    @field_validator("reason", "explanation")
    @classmethod
    def fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "score cap field")


class EngineeringConfidenceAssessment(BaseModel):
    """Structured Engineering Confidence Score output."""

    model_config = ConfigDict(extra="forbid")

    overall_score: int = Field(ge=0, le=100)
    factor_scores: list[ConfidenceFactorScore]
    score_caps: list[ScoreCap] = Field(default_factory=list)
    reasoning: Reasoning
    risks: list[Risk] = Field(default_factory=list)
    missing_information: list[MissingInformation] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    review_required: bool = True

    @model_validator(mode="after")
    def assessment_must_be_reviewable(self) -> "EngineeringConfidenceAssessment":
        if not self.factor_scores:
            raise ValueError("confidence assessment must include factor scores")
        if self.overall_score < 90 and not self.recommendations:
            raise ValueError("confidence scores below 90 must include recommendations")
        return self
