"""Taiga backlog sync orchestration."""

from __future__ import annotations

from sprintpilot.domain import SprintPlan
from sprintpilot.integrations.taiga.auth import resolve_taiga_auth
from sprintpilot.integrations.taiga.client import MatchResult, TaigaClientProtocol
from sprintpilot.integrations.taiga.mapper import MappingValidationError, map_sprint_plan_to_taiga
from sprintpilot.integrations.taiga.models import (
    SprintPilotSourceRef,
    TaigaItemRef,
    TaigaProjectRef,
    TaigaSettings,
    TaigaSyncAction,
    TaigaSyncPlan,
    TaigaSyncResult,
)


def sync_sprint_plan_to_taiga(
    sprint_plan: SprintPlan,
    *,
    settings: TaigaSettings | None,
    client: TaigaClientProtocol,
    dry_run: bool | None = None,
) -> TaigaSyncResult:
    """Export a SprintPlan into Taiga backlog items or preview the export."""

    is_dry_run = settings.dry_run if settings is not None and dry_run is None else bool(dry_run)
    if settings is None:
        return _failed_result(
            dry_run=is_dry_run,
            reasoning="Taiga settings are required before export.",
        )

    try:
        auth = resolve_taiga_auth(settings)
    except ValueError as exc:
        return _failed_result(dry_run=is_dry_run, reasoning=str(exc))

    project = TaigaProjectRef(
        identifier=settings.project_identifier,
        project_id=0,
    )
    try:
        mapped = map_sprint_plan_to_taiga(sprint_plan, project=project)
    except MappingValidationError as exc:
        return _failed_result(dry_run=is_dry_run, reasoning=str(exc))

    if is_dry_run:
        previewed = _preview_actions(mapped.epics, mapped.user_stories, mapped.tasks)
        return TaigaSyncResult(
            dry_run=True,
            previewed=previewed,
            reasoning="Dry run completed without Taiga mutations.",
        )

    try:
        resolved_project = client.resolve_project(settings, auth)
    except Exception as exc:  # noqa: BLE001 - convert integration errors into safe result
        return _failed_result(
            dry_run=False,
            reasoning=f"Taiga project resolution failed: {_safe_error(exc)}",
        )

    try:
        mapped = map_sprint_plan_to_taiga(sprint_plan, project=resolved_project)
    except MappingValidationError as exc:
        return _failed_result(dry_run=False, reasoning=str(exc))

    return _write_sync(mapped, client)


def _write_sync(mapped, client: TaigaClientProtocol) -> TaigaSyncResult:
    created: list[TaigaItemRef] = []
    matched: list[TaigaItemRef] = []
    skipped: list[TaigaSyncAction] = []
    failed: list[TaigaSyncAction] = []
    story_refs_by_source: dict[str, TaigaItemRef] = {}

    for epic in mapped.epics:
        match = client.find_existing_epic(mapped.project, epic.source_ref, epic.subject)
        if _append_match_or_skip(match, epic.source_ref, "epic", matched, skipped):
            continue
        try:
            created.append(client.create_epic(epic))
        except Exception as exc:  # noqa: BLE001
            failed.append(_failed_action("epic", epic.source_ref, _safe_error(exc)))

    for story in mapped.user_stories:
        match = client.find_existing_user_story(mapped.project, story.source_ref, story.subject)
        if match.is_ambiguous:
            skipped.append(
                _skip_action("user_story", story.source_ref, match.ambiguous_reason or "Ambiguous match")
            )
            continue
        if match.is_match and match.matched_item is not None:
            matched.append(match.matched_item.ref)
            story_refs_by_source[story.source_ref.source_id] = match.matched_item.ref
            continue
        try:
            ref = client.create_user_story(story)
            created.append(ref)
            story_refs_by_source[story.source_ref.source_id] = ref
        except Exception as exc:  # noqa: BLE001
            failed.append(_failed_action("user_story", story.source_ref, _safe_error(exc)))

    for task in mapped.tasks:
        story_ref = story_refs_by_source.get(task.user_story_source_id)
        if story_ref is None:
            skipped.append(
                _skip_action(
                    "task",
                    task.source_ref,
                    f"Parent user story {task.user_story_source_id} was not created or matched.",
                )
            )
            continue
        task_with_story = task.with_user_story_ref(story_ref.item_id)
        match = client.find_existing_task(
            mapped.project,
            story_ref,
            task.source_ref,
            task.subject,
        )
        if _append_match_or_skip(match, task.source_ref, "task", matched, skipped):
            continue
        try:
            created.append(client.create_task(task_with_story))
        except Exception as exc:  # noqa: BLE001
            failed.append(_failed_action("task", task.source_ref, _safe_error(exc)))

    return TaigaSyncResult(
        dry_run=False,
        created=created,
        matched=matched,
        skipped=skipped,
        failed=failed,
        reasoning="Taiga backlog sync completed with reviewable item results.",
    )


def _append_match_or_skip(
    match: MatchResult,
    source_ref: SprintPilotSourceRef,
    item_type,
    matched: list[TaigaItemRef],
    skipped: list[TaigaSyncAction],
) -> bool:
    if match.is_ambiguous:
        skipped.append(_skip_action(item_type, source_ref, match.ambiguous_reason or "Ambiguous match"))
        return True
    if match.is_match and match.matched_item is not None:
        matched.append(match.matched_item.ref)
        return True
    return False


def _preview_actions(epics, stories, tasks) -> list[TaigaSyncAction]:
    actions: list[TaigaSyncAction] = []
    for payload, item_type in (
        *[(epic, "epic") for epic in epics],
        *[(story, "user_story") for story in stories],
        *[(task, "task") for task in tasks],
    ):
        actions.append(
            TaigaSyncAction(
                action_type="preview",
                item_type=item_type,
                source_ref=payload.source_ref,
                payload=payload.to_create_payload()
                if item_type != "task"
                else {
                    "project": payload.project_id,
                    "subject": payload.subject,
                    "description": payload.description,
                    "user_story_source_id": payload.user_story_source_id,
                },
                reasoning="Dry-run preview; no Taiga mutation was made.",
            )
        )
    return actions


def _failed_result(*, dry_run: bool, reasoning: str) -> TaigaSyncResult:
    return TaigaSyncResult(
        dry_run=dry_run,
        failed=[
            TaigaSyncAction(
                action_type="fail",
                item_type="epic",
                reasoning=reasoning,
            )
        ],
        reasoning=reasoning,
    )


def _failed_action(item_type, source_ref: SprintPilotSourceRef, error: str) -> TaigaSyncAction:
    return TaigaSyncAction(
        action_type="fail",
        item_type=item_type,
        source_ref=source_ref,
        reasoning=error,
        error=error,
    )


def _skip_action(item_type, source_ref: SprintPilotSourceRef, reasoning: str) -> TaigaSyncAction:
    return TaigaSyncAction(
        action_type="skip",
        item_type=item_type,
        source_ref=source_ref,
        reasoning=reasoning,
    )


def _safe_error(exc: Exception) -> str:
    return str(exc)
