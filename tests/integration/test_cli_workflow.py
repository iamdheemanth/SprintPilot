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
