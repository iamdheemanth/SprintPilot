from __future__ import annotations

from tests.unit.test_architect_adapter import _valid_architecture_payload
from tests.unit.test_architect_prompts import _definition

from sprintpilot.agents.prompts import build_scrum_master_messages
from sprintpilot.domain import ArchitecturePlan


def test_scrum_master_prompt_uses_agile_terms_and_core_v1_scope() -> None:
    messages = build_scrum_master_messages(
        product_definition=_definition(),
        architecture_plan=ArchitecturePlan.model_validate(_valid_architecture_payload()),
    )
    prompt_text = "\n".join(message.content for message in messages)

    assert "Scrum Master Agent" in prompt_text
    assert "epics" in prompt_text
    assert "sprint-ready stories" in prompt_text
    assert "task breakdown" in prompt_text
    assert "story point estimates" in prompt_text
    assert "estimate reasoning" in prompt_text
    assert "Do not generate source code" in prompt_text
    assert "A planning assistant for founders." in messages[-1].content
