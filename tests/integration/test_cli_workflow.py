from __future__ import annotations

from pathlib import Path

from tests.unit.test_core_v1_mocked_pipeline import InternshipTrackerProvider

from sprintpilot.cli import PLAN_EXIT_OK, main, run_plan_command


def test_full_mocked_cli_workflow_accepts_idea_file(tmp_path: Path) -> None:
    idea_file = tmp_path / "idea.txt"
    idea_file.write_text("Build a student internship tracking platform.", encoding="utf-8")

    result = run_plan_command(
        idea_file=idea_file,
        output=tmp_path,
        title="Student Internship Tracker",
        provider=InternshipTrackerProvider(),
    )

    assert result.exit_code == PLAN_EXIT_OK
    assert result.report_path is not None
    markdown = result.report_path.read_text(encoding="utf-8")
    assert "## Product Definition" in markdown
    assert "## Architecture Plan" in markdown
    assert "## Sprint Plan" in markdown
    assert "## Engineering Confidence Assessment" in markdown


def test_argparse_entrypoint_supports_plan_subcommand_for_dry_run(capsys) -> None:
    exit_code = main(
        [
            "plan",
            "--idea",
            "Build a student internship tracking platform.",
            "--dry-run",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == PLAN_EXIT_OK
    assert "validated" in captured.out.lower()


def test_argparse_entrypoint_supports_taiga_export_dry_run(monkeypatch, tmp_path: Path, capsys) -> None:
    from tests.unit.fixtures.test_taiga_sprint_plan import make_taiga_sprint_plan

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SPRINTPILOT_CONFIG_HOME", str(tmp_path / "config"))
    sprint_plan_file = tmp_path / "sprint-plan.json"
    sprint_plan_file.write_text(make_taiga_sprint_plan().model_dump_json(), encoding="utf-8")
    monkeypatch.setenv("SPRINTPILOT_MODEL_PROVIDER", "stub")
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", "stub-model")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_BASE_URL", "https://taiga.example.com")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_PROJECT", "project-slug")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_AUTH_MODE", "bearer")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN_ENV_KEY", "SPRINTPILOT_TAIGA_TOKEN")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-taiga-token")

    exit_code = main(["taiga-export", "--sprint-plan-file", str(sprint_plan_file), "--dry-run"])

    captured = capsys.readouterr()
    assert exit_code == PLAN_EXIT_OK
    assert "Taiga project: project-slug" in captured.out
    assert "Mode: dry-run" in captured.out
    assert "Previewed: 4" in captured.out
    assert "secret-taiga-token" not in captured.out
