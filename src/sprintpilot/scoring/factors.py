"""Engineering Confidence Score factor definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceFactor:
    """Static confidence factor definition."""

    key: str
    label: str
    weight: int


CONFIDENCE_FACTORS: tuple[ConfidenceFactor, ...] = (
    ConfidenceFactor("requirement_clarity", "Requirement clarity", 25),
    ConfidenceFactor("architecture_completeness", "Architecture completeness", 20),
    ConfidenceFactor("dependency_readiness", "Dependency readiness", 15),
    ConfidenceFactor("acceptance_criteria_quality", "Acceptance criteria quality", 15),
    ConfidenceFactor("technical_ambiguity", "Technical ambiguity", 15),
    ConfidenceFactor("delivery_risk", "Delivery risk", 10),
)
