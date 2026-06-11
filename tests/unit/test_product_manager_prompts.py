from __future__ import annotations

from sprintpilot.agents.prompts import build_product_manager_messages
from sprintpilot.domain import ProductIdea


def test_product_manager_prompt_uses_core_v1_scope_and_agile_terms() -> None:
    messages = build_product_manager_messages(ProductIdea(raw_text="Build a planning assistant"))
    prompt_text = "\n".join(message.content for message in messages)

    assert "Product Manager Agent" in prompt_text
    assert "functional requirements" in prompt_text
    assert "non-functional requirements" in prompt_text
    assert "user stories" in prompt_text
    assert "acceptance criteria" in prompt_text
    assert "Do not generate source code" in prompt_text
    assert messages[-1].content.endswith("Build a planning assistant")
