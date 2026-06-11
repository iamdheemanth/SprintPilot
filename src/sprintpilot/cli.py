"""Local CLI entrypoint for SprintPilot Core v1 report generation."""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from sprintpilot.config import RuntimeSettings
from sprintpilot.llm import LLMProvider, LLMProviderError
from sprintpilot.llm.factory import create_provider
from sprintpilot.reporting import ReportWriteError, assemble_report, write_markdown_report
from sprintpilot.workflow import (
    normalize_product_idea,
    run_architecture_planning_workflow,
    run_confidence_assessment_workflow,
    run_product_definition_workflow,
    run_sprint_planning_workflow,
)

try:  # pragma: no cover - exercised when optional CLI dependency is installed.
    import typer
except ModuleNotFoundError:  # pragma: no cover - keeps unit tests provider-free/dependency-light.
    typer = None

try:  # pragma: no cover - exercised when optional CLI dependency is installed.
    from rich.console import Console
except ModuleNotFoundError:  # pragma: no cover
    Console = None


PLAN_EXIT_OK = 0
PLAN_EXIT_INPUT = 2
PLAN_EXIT_CONFIG = 3
PLAN_EXIT_AGENT_VALIDATION = 4
PLAN_EXIT_REPORT_WRITE = 5

app = typer.Typer(help="SprintPilot Core v1 local planning CLI.") if typer else None


@dataclass(frozen=True)
class PlanCommandResult:
    """Result returned by the testable Core v1 plan command boundary."""

    exit_code: int
    message: str
    report_path: Path | None = None
    confidence_score: int | None = None
    risk_count: int = 0
    missing_information_count: int = 0


@dataclass(frozen=True)
class DiagnosticsCommandResult:
    """Result returned by the testable provider diagnostics command boundary."""

    exit_code: int
    message: str


def run_plan_command(
    *,
    idea: str | None = None,
    idea_file: str | Path | None = None,
    output: str | Path | None = None,
    report_format: str = "markdown",
    title: str | None = None,
    dry_run: bool = False,
    provider: LLMProvider | None = None,
    on_start: Callable[[str], None] | None = None,
) -> PlanCommandResult:
    """Generate a local SprintPilot Core v1 report from exactly one idea source."""

    input_error = _validate_idea_sources(idea=idea, idea_file=idea_file)
    if input_error is not None:
        return PlanCommandResult(exit_code=PLAN_EXIT_INPUT, message=input_error)

    if report_format != "markdown":
        return PlanCommandResult(
            exit_code=PLAN_EXIT_INPUT,
            message="Core v1 supports only markdown report output.",
        )

    try:
        product_idea = normalize_product_idea(idea or "", idea_file=idea_file)
    except OSError as exc:
        return PlanCommandResult(
            exit_code=PLAN_EXIT_INPUT,
            message=f"Unable to read product idea file: {exc}",
        )
    except ValueError as exc:
        return PlanCommandResult(exit_code=PLAN_EXIT_INPUT, message=str(exc))

    if dry_run:
        return PlanCommandResult(
            exit_code=PLAN_EXIT_OK,
            message="SprintPilot plan inputs validated. Dry run did not generate artifacts.",
        )

    if provider is None:
        try:
            provider = create_provider(RuntimeSettings.from_env().llm)
        except Exception as exc:
            return PlanCommandResult(
                exit_code=PLAN_EXIT_CONFIG,
                message=f"Missing or unsupported model provider configuration: {exc}",
            )

    if on_start is not None:
        on_start(_provider_startup_message(provider))

    report_title = title or product_idea.title or "Core v1 Planning Report"
    try:
        product_definition = run_product_definition_workflow(
            product_idea=product_idea,
            provider=provider,
        )
        architecture_plan = run_architecture_planning_workflow(
            product_definition=product_definition,
            provider=provider,
        )
        sprint_plan = run_sprint_planning_workflow(
            product_definition=product_definition,
            architecture_plan=architecture_plan,
            provider=provider,
        )
        confidence_assessment = run_confidence_assessment_workflow(
            product_definition=product_definition,
            architecture_plan=architecture_plan,
            sprint_plan=sprint_plan,
        )
        report = assemble_report(
            title=report_title,
            product_idea=product_idea,
            product_definition=product_definition,
            architecture_plan=architecture_plan,
            sprint_plan=sprint_plan,
            confidence_assessment=confidence_assessment,
        )
    except LLMProviderError as exc:
        return PlanCommandResult(
            exit_code=PLAN_EXIT_CONFIG,
            message=f"LLM provider error: {exc}",
        )
    except Exception as exc:
        return PlanCommandResult(
            exit_code=PLAN_EXIT_AGENT_VALIDATION,
            message=f"Core v1 workflow validation failed: {exc}",
        )

    try:
        report_path = write_markdown_report(report, output)
    except ReportWriteError as exc:
        return PlanCommandResult(
            exit_code=PLAN_EXIT_REPORT_WRITE,
            message=str(exc),
        )

    risk_count = (
        len(product_definition.risks)
        + len(architecture_plan.risks)
        + len(sprint_plan.risks)
        + len(confidence_assessment.risks)
    )
    missing_information_count = (
        len(product_definition.missing_information)
        + len(architecture_plan.open_questions)
        + len(confidence_assessment.missing_information)
    )
    return PlanCommandResult(
        exit_code=PLAN_EXIT_OK,
        message=(
            f"Report written to {report_path}. "
            f"Engineering Confidence Score: {confidence_assessment.overall_score}/100. "
            f"Risks: {risk_count}. Missing information: {missing_information_count}. "
            "Generated artifacts require human review."
        ),
        report_path=report_path,
        confidence_score=confidence_assessment.overall_score,
        risk_count=risk_count,
        missing_information_count=missing_information_count,
    )


def run_diagnostics_command(
    *,
    provider: LLMProvider | None = None,
    verbose: bool = False,
) -> DiagnosticsCommandResult:
    """Run provider diagnostics without executing the product planning workflow."""

    if provider is None:
        try:
            provider = create_provider(RuntimeSettings.from_env().llm)
        except Exception as exc:
            return DiagnosticsCommandResult(
                exit_code=PLAN_EXIT_CONFIG,
                message=f"Missing or unsupported model provider configuration: {exc}",
            )

    config = provider.config
    api_key_present = _has_configured_api_key(config.environment_keys)
    health = provider.check_health()
    lines = [
        f"Provider: {config.provider_name}",
        f"Model: {config.model_name}",
        f"Fallbacks: {len(config.fallback_models)}",
        f"Retries: {config.max_retries}",
        "",
        f"API Key: {'Present' if api_key_present else 'Missing'}",
        "",
        "Provider Health:",
        _status_line(health.request_sent, "Request sent"),
        _status_line(health.response_received, "Response received"),
        _status_line(health.structured_output_supported, "Structured output supported"),
    ]

    if verbose:
        lines.extend(_verbose_diagnostics_lines(health))

    exit_code = PLAN_EXIT_OK if (
        api_key_present
        and health.request_sent
        and health.response_received
        and health.structured_output_supported
    ) else PLAN_EXIT_CONFIG
    return DiagnosticsCommandResult(
        exit_code=exit_code,
        message=_redact_secret_values("\n".join(lines)),
    )


def main(argv: list[str] | None = None) -> int:
    """Console-script compatible CLI entrypoint."""

    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "plan":
        argv = argv[1:]
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.diagnostics or args.provider_check:
        result = run_diagnostics_command(verbose=args.verbose)
        _print_result(result)
        return result.exit_code
    result = run_plan_command(
        idea=args.idea,
        idea_file=args.idea_file,
        output=args.output,
        report_format=args.report_format,
        title=args.title,
        dry_run=args.dry_run,
        on_start=_print_startup,
    )
    _print_result(result)
    return result.exit_code


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sprintpilot plan")
    parser.add_argument("--diagnostics", action="store_true")
    parser.add_argument("--provider-check", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--idea")
    parser.add_argument("--idea-file", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--format", dest="report_format", default="markdown")
    parser.add_argument("--title")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _validate_idea_sources(*, idea: str | None, idea_file: str | Path | None) -> str | None:
    has_idea = bool(idea and idea.strip())
    has_file = idea_file is not None
    if has_idea and has_file:
        return "Provide either --idea or --idea-file, not both."
    if not has_idea and not has_file:
        return "Provide exactly one product idea source with --idea or --idea-file."
    return None


def _print_result(result: PlanCommandResult) -> None:
    stream = sys.stderr if result.exit_code else sys.stdout
    if Console is None:
        print(_console_safe_message(result.message, encoding=getattr(stream, "encoding", None)), file=stream)
        return
    console = Console(stderr=bool(result.exit_code))
    style = "red" if result.exit_code else "green"
    console.print(
        _console_safe_message(result.message, encoding=getattr(console.file, "encoding", None)),
        style=style,
    )


def _has_configured_api_key(environment_keys: list[str]) -> bool:
    return any(os.getenv(key, "").strip() for key in environment_keys)


def _status_line(is_ok: bool, label: str) -> str:
    return f"{'✓' if is_ok else '✗'} {label}"


def _console_safe_message(message: str, *, encoding: str | None) -> str:
    if not encoding:
        return message
    try:
        message.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return message.replace("✓", "OK").replace("✗", "FAIL")
    return message


def _verbose_diagnostics_lines(health: object) -> list[str]:
    lines = ["", "Verbose:"]
    http_status = getattr(health, "http_status", None)
    response_id = getattr(health, "response_id", None)
    provider_error = getattr(health, "provider_error", None)
    error_message = getattr(health, "error_message", None)
    elapsed_ms = getattr(health, "elapsed_ms", None)
    if http_status is not None:
        lines.append(f"HTTP Status: {http_status}")
    if response_id:
        lines.append(f"Response ID: {response_id}")
    if provider_error:
        lines.append(f"Provider Error: {provider_error}")
    if error_message:
        lines.append(f"Error Message: {error_message}")
    if elapsed_ms is not None:
        lines.append(f"Elapsed: {elapsed_ms} ms")
    return lines


def _redact_secret_values(value: str) -> str:
    redacted = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [filtered]", value)
    return re.sub(r"sk-[A-Za-z0-9._~+/=-]+", "sk-[filtered]", redacted)


def _provider_startup_message(provider: LLMProvider) -> str:
    config = provider.config
    return (
        f"Provider: {config.provider_name}\n"
        f"Model: {config.model_name}\n"
        f"Fallbacks: {len(config.fallback_models)}\n"
        f"Retries: {config.max_retries}"
    )


def _print_startup(message: str) -> None:
    if Console is None:
        print(message, file=sys.stdout)
        return
    Console().print(message, style="cyan")


if app is not None:  # pragma: no cover - depends on Typer runtime.

    @app.command("plan")
    def typer_plan(
        idea: str | None = typer.Option(None, "--idea", help="Product idea text."),
        idea_file: Path | None = typer.Option(
            None,
            "--idea-file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to a text file containing the product idea.",
        ),
        output: Path | None = typer.Option(None, "--output", help="Report directory or file path."),
        report_format: str = typer.Option("markdown", "--format", help="Report format."),
        title: str | None = typer.Option(None, "--title", help="Optional report title."),
        dry_run: bool = typer.Option(False, "--dry-run", help="Validate inputs without generation."),
    ) -> None:
        result = run_plan_command(
            idea=idea,
            idea_file=idea_file,
            output=output,
            report_format=report_format,
            title=title,
            dry_run=dry_run,
            on_start=_print_startup,
        )
        _print_result(result)
        raise typer.Exit(result.exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
