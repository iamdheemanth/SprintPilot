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
from sprintpilot.domain import SprintPlan
from sprintpilot.integrations.taiga.client import TaigaClient, TaigaClientProtocol
from sprintpilot.integrations.taiga.config import TaigaConfigOverrides, resolve_taiga_settings
from sprintpilot.integrations.taiga.models import TaigaSettings, TaigaSyncResult
from sprintpilot.integrations.taiga.profile_store import (
    RepoTaigaBindingStore,
    TaigaConnectionProfile,
    TaigaProfileStore,
    default_taiga_config_dir,
)
from sprintpilot.integrations.taiga.sync import sync_sprint_plan_to_taiga
from sprintpilot.llm import LLMProvider, LLMProviderError
from sprintpilot.llm.factory import create_provider
from sprintpilot.reporting import (
    ReportWriteError,
    assemble_report,
    write_markdown_report,
    write_sprint_plan_artifact,
)
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
    sprint_plan_artifact_path: Path | None = None
    confidence_score: int | None = None
    risk_count: int = 0
    missing_information_count: int = 0


@dataclass(frozen=True)
class DiagnosticsCommandResult:
    """Result returned by the testable provider diagnostics command boundary."""

    exit_code: int
    message: str


@dataclass(frozen=True)
class TaigaExportCommandResult:
    """Result returned by the testable Taiga export command boundary."""

    exit_code: int
    message: str
    sync_result: TaigaSyncResult | None = None


@dataclass(frozen=True)
class TaigaConnectCommandResult:
    """Result returned by the testable Taiga connection setup command boundary."""

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
        sprint_plan_artifact_path = write_sprint_plan_artifact(sprint_plan, report_path)
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
            f"SprintPlan artifact written to {sprint_plan_artifact_path}. "
            f"Engineering Confidence Score: {confidence_assessment.overall_score}/100. "
            f"Risks: {risk_count}. Missing information: {missing_information_count}. "
            "Generated artifacts require human review."
        ),
        report_path=report_path,
        sprint_plan_artifact_path=sprint_plan_artifact_path,
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


def run_taiga_export_command(
    *,
    sprint_plan_file: str | Path,
    dry_run: bool = False,
    live: bool = False,
    profile_name: str | None = None,
    taiga_base_url: str | None = None,
    taiga_project: str | None = None,
    taiga_auth_mode: str | None = None,
    taiga_token_env_key: str | None = None,
    taiga_token_reference: str | None = None,
    settings: RuntimeSettings | None = None,
    client_factory: Callable[[], TaigaClientProtocol] | None = None,
) -> TaigaExportCommandResult:
    """Export a structured SprintPlan JSON artifact to Taiga backlog items."""

    if dry_run and live:
        return TaigaExportCommandResult(
            exit_code=PLAN_EXIT_INPUT,
            message="Choose either dry-run or live Taiga export mode, not both.",
        )
    export_dry_run = not live if not dry_run else True

    try:
        runtime_settings = settings or RuntimeSettings.from_env()
    except Exception as exc:
        return TaigaExportCommandResult(
            exit_code=PLAN_EXIT_CONFIG,
            message=f"Missing or unsupported runtime configuration: {exc}",
        )

    try:
        if settings is not None:
            taiga_settings = runtime_settings.taiga
        else:
            taiga_settings = resolve_taiga_settings(
                overrides=TaigaConfigOverrides(
                    profile_name=profile_name,
                    base_url=taiga_base_url,
                    project_identifier=taiga_project,
                    auth_mode=taiga_auth_mode,
                    token_environment_key=taiga_token_env_key,
                    token_reference=taiga_token_reference,
                )
            )
            if taiga_settings is None:
                taiga_settings = runtime_settings.taiga
    except Exception as exc:
        return TaigaExportCommandResult(
            exit_code=PLAN_EXIT_CONFIG,
            message=f"Missing or unsupported Taiga configuration: {exc}",
        )
    if taiga_settings is None:
        return TaigaExportCommandResult(
            exit_code=PLAN_EXIT_CONFIG,
            message="Missing Taiga configuration. Run `sprintpilot taiga-connect` or use legacy SPRINTPILOT_TAIGA_* environment variables.",
        )

    try:
        sprint_plan = _load_sprint_plan_json(sprint_plan_file)
    except OSError as exc:
        return TaigaExportCommandResult(
            exit_code=PLAN_EXIT_INPUT,
            message=f"Unable to read SprintPlan file: {exc}",
        )
    except ValueError as exc:
        return TaigaExportCommandResult(exit_code=PLAN_EXIT_INPUT, message=str(exc))

    client = client_factory() if client_factory is not None else TaigaClient()
    sync_result = sync_sprint_plan_to_taiga(
        sprint_plan,
        settings=taiga_settings,
        client=client,
        dry_run=export_dry_run,
    )
    exit_code = PLAN_EXIT_OK if not sync_result.failed else PLAN_EXIT_CONFIG
    return TaigaExportCommandResult(
        exit_code=exit_code,
        message=_taiga_export_message(
            settings=runtime_settings,
            taiga_settings=taiga_settings,
            sync_result=sync_result,
        ),
        sync_result=sync_result,
    )


def run_taiga_connect_command(
    *,
    profile_name: str,
    base_url: str | None = None,
    project_identifier: str | None = None,
    auth_mode: str | None = None,
    token_environment_key: str | None = None,
    token_reference: str | None = None,
    username_or_email: str | None = None,
    make_default: bool = False,
    bind_repo: bool = True,
    config_dir: str | Path | None = None,
    repo_dir: str | Path | None = None,
) -> TaigaConnectCommandResult:
    """Create or update a user-local Taiga profile and optionally bind this repo."""

    profile_store = TaigaProfileStore(config_dir=config_dir)
    binding_store = RepoTaigaBindingStore(repo_dir=repo_dir)
    existing = profile_store.get_profile(profile_name)
    has_profile_updates = any(
        value is not None
        for value in (
            base_url,
            project_identifier,
            auth_mode,
            token_environment_key,
            token_reference,
            username_or_email,
        )
    )

    if existing is None and not has_profile_updates:
        return TaigaConnectCommandResult(
            exit_code=PLAN_EXIT_INPUT,
            message="New Taiga profiles require a base URL, project identifier, auth mode, and token environment key or token reference.",
        )

    try:
        if has_profile_updates or existing is None:
            profile = TaigaConnectionProfile(
                name=profile_name,
                base_url=base_url or (existing.base_url if existing else ""),
                project_identifier=project_identifier
                or (existing.project_identifier if existing else ""),
                auth_mode=auth_mode or (existing.auth_mode if existing else "bearer"),
                token_environment_key=token_environment_key
                if token_environment_key is not None
                else (existing.token_environment_key if existing else None),
                token_reference=token_reference
                if token_reference is not None
                else (existing.token_reference if existing else None),
                username_or_email=username_or_email
                if username_or_email is not None
                else (existing.username_or_email if existing else None),
            )
            profile_store.save_profile(profile, make_default=make_default)
        elif make_default and existing is not None:
            profile_store.save_profile(existing, make_default=True)
    except Exception as exc:
        return TaigaConnectCommandResult(exit_code=PLAN_EXIT_INPUT, message=str(exc))

    if bind_repo:
        binding_store.set_active_profile(profile_name)

    lines = [
        f"Taiga profile '{profile_name}' saved.",
        f"Profiles: {profile_store.path}",
    ]
    if bind_repo:
        lines.append(f"Repo active profile: {binding_store.path}")
    lines.append("Token values were not stored; keep them in your environment or OS keyring.")
    return TaigaConnectCommandResult(
        exit_code=PLAN_EXIT_OK,
        message=_redact_secret_values("\n".join(lines)),
    )


def main(argv: list[str] | None = None) -> int:
    """Console-script compatible CLI entrypoint."""

    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "taiga-connect":
        args = _build_taiga_connect_parser().parse_args(argv[1:])
        result = run_taiga_connect_command(
            profile_name=args.profile_name,
            base_url=args.base_url,
            project_identifier=args.project,
            auth_mode=args.auth_mode,
            token_environment_key=args.token_env_key,
            token_reference=args.token_reference,
            username_or_email=args.username_or_email,
            make_default=args.default,
            bind_repo=not args.no_bind,
        )
        _print_result(result)
        return result.exit_code
    if argv and argv[0] == "taiga-export":
        args = _build_taiga_export_parser().parse_args(argv[1:])
        result = run_taiga_export_command(
            sprint_plan_file=args.sprint_plan_file,
            dry_run=args.dry_run,
            live=args.live,
            profile_name=args.profile,
            taiga_base_url=args.taiga_base_url,
            taiga_project=args.taiga_project,
            taiga_auth_mode=args.taiga_auth_mode,
            taiga_token_env_key=args.taiga_token_env_key,
            taiga_token_reference=args.taiga_token_reference,
        )
        _print_result(result)
        return result.exit_code
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


def _build_taiga_export_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sprintpilot taiga-export")
    parser.add_argument("--sprint-plan-file", type=Path, required=True)
    parser.add_argument("--profile", help="Taiga profile name to use for this export.")
    parser.add_argument("--taiga-base-url", help="Explicit Taiga base URL override.")
    parser.add_argument("--taiga-project", help="Explicit Taiga project identifier override.")
    parser.add_argument("--taiga-auth-mode", choices=["bearer", "application-token"])
    parser.add_argument("--taiga-token-env-key", help="Environment variable containing the Taiga token.")
    parser.add_argument("--taiga-token-reference", help="OS keyring or secret-store token reference.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preview Taiga backlog items without creating them.")
    mode.add_argument("--live", action="store_true", help="Create Taiga backlog items.")
    return parser


def _build_taiga_connect_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sprintpilot taiga-connect")
    parser.add_argument("--profile", dest="profile_name", required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--project")
    parser.add_argument("--auth-mode", choices=["bearer", "application-token"])
    parser.add_argument("--token-env-key")
    parser.add_argument("--token-reference")
    parser.add_argument("--username-or-email")
    parser.add_argument("--default", action="store_true", help="Make this the user-default Taiga profile.")
    parser.add_argument("--no-bind", action="store_true", help="Do not bind the current repo to this profile.")
    parser.epilog = f"Profiles are stored under {default_taiga_config_dir()}."
    return parser


def _load_sprint_plan_json(path: str | Path) -> SprintPlan:
    raw = Path(path).read_text(encoding="utf-8")
    try:
        return SprintPlan.model_validate_json(raw)
    except Exception as exc:
        raise ValueError(f"Invalid SprintPlan JSON: {exc}") from exc


def _taiga_export_message(
    *,
    settings: RuntimeSettings,
    taiga_settings: TaigaSettings,
    sync_result: TaigaSyncResult,
) -> str:
    mode = "dry-run" if sync_result.dry_run else "live"
    lines = [
        f"Provider: {settings.llm.provider_name}",
        f"Model: {settings.llm.model_name}",
        f"Taiga project: {taiga_settings.project_identifier}",
        f"Mode: {mode}",
        "",
        "Backlog export result:",
        f"Previewed: {len(sync_result.previewed)}",
        f"Created: {len(sync_result.created)}",
        f"Matched: {len(sync_result.matched)}",
        f"Skipped: {len(sync_result.skipped)}",
        f"Failed: {len(sync_result.failed)}",
        sync_result.reasoning,
    ]
    for action in sync_result.previewed[:10]:
        source = action.source_ref.source_id if action.source_ref else "unknown"
        lines.append(f"- preview {action.item_type}: {source}")
    for item in sync_result.created[:10]:
        lines.append(f"- created {item.item_type}: {item.subject}")
    for action in [*sync_result.skipped, *sync_result.failed]:
        source = action.source_ref.source_id if action.source_ref else "configuration"
        lines.append(f"- {action.action_type} {action.item_type}: {source} - {action.reasoning}")
    return _redact_secret_values("\n".join(lines))


def _validate_idea_sources(*, idea: str | None, idea_file: str | Path | None) -> str | None:
    has_idea = bool(idea and idea.strip())
    has_file = idea_file is not None
    if has_idea and has_file:
        return "Provide either --idea or --idea-file, not both."
    if not has_idea and not has_file:
        return "Provide exactly one product idea source with --idea or --idea-file."
    return None


def _print_result(
    result: PlanCommandResult | DiagnosticsCommandResult | TaigaExportCommandResult | TaigaConnectCommandResult,
) -> None:
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

    @app.command("taiga-export")
    def typer_taiga_export(
        sprint_plan_file: Path = typer.Option(
            ...,
            "--sprint-plan-file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to a structured SprintPlan JSON artifact.",
        ),
        dry_run: bool = typer.Option(False, "--dry-run", help="Preview Taiga backlog export."),
        live: bool = typer.Option(False, "--live", help="Create Taiga backlog items."),
    ) -> None:
        result = run_taiga_export_command(
            sprint_plan_file=sprint_plan_file,
            dry_run=dry_run,
            live=live,
        )
        _print_result(result)
        raise typer.Exit(result.exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
