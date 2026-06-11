from __future__ import annotations

import pytest
from pydantic import ValidationError

from sprintpilot.domain import Assumption, MissingInformation, Recommendation, Risk


def test_shared_artifact_values_reject_blank_text() -> None:
    with pytest.raises(ValidationError):
        Assumption(text=" ")

    with pytest.raises(ValidationError):
        Risk(description="")


def test_recommendation_requires_action_and_rationale() -> None:
    recommendation = Recommendation(action="Clarify target users", rationale="User roles affect scope.")

    assert recommendation.action == "Clarify target users"
    assert recommendation.rationale == "User roles affect scope."


def test_missing_information_tracks_impact() -> None:
    missing = MissingInformation(question="Who approves the plan?", impact="Defines review gate.")

    assert missing.question == "Who approves the plan?"
    assert missing.impact == "Defines review gate."
