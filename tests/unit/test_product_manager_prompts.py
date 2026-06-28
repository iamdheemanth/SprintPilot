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


def test_product_manager_prompt_excludes_collaboration_while_allowing_individual_analytics() -> None:
    messages = build_product_manager_messages(
        ProductIdea(
            raw_text=(
                "Build a student internship tracking platform with applications, "
                "recruiter contacts and application analytics."
            )
        )
    )
    prompt_text = "\n".join(message.content for message in messages)

    assert "individual student user" in prompt_text
    assert "separate end users" in prompt_text
    assert "not collaboration" in prompt_text
    assert "multi-user collaboration" in prompt_text
    assert "shared workspaces" in prompt_text
    assert "team accounts" in prompt_text
    assert "commenting" in prompt_text
    assert "co-editing" in prompt_text
    assert "sharing workflows" in prompt_text
    assert "advisor or group collaboration" in prompt_text
    assert "role-based teamwork features" in prompt_text
    assert "application analytics" in prompt_text
    assert "student's own application tracking insights" in prompt_text


def test_product_manager_prompt_defines_allowed_and_forbidden_analytics_boundary() -> None:
    messages = build_product_manager_messages(
        ProductIdea(
            raw_text=(
                "Build a student internship tracking platform that allows students to track "
                "applications, interview stages, offers, deadlines, recruiter contacts, "
                "and application analytics."
            )
        )
    )
    prompt_text = "\n".join(message.content for message in messages)

    assert "single-student product" in prompt_text
    assert "total applications" in prompt_text
    assert "applications by status" in prompt_text
    assert "interview/offer counts" in prompt_text
    assert "upcoming deadline summary" in prompt_text
    assert "standalone module" in prompt_text
    assert "dashboard" in prompt_text
    assert "reporting system" in prompt_text
