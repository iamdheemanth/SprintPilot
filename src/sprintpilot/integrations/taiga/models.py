"""Models for SprintPilot's Taiga backlog export foundation."""

from __future__ import annotations

import os
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_validator


PROHIBITED_SCHEDULING_FIELDS = {
    "sprint",
    "sprint_id",
    "sprint_order",
    "milestone",
    "milestone_id",
    "capacity",
    "velocity",
    "kanban_order",
    "assigned_to_sprint",
    "scheduled_container",
}


def _strip_required(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must not be empty")
    return stripped


def assert_no_scheduling_fields(payload: dict[str, Any]) -> None:
    prohibited = PROHIBITED_SCHEDULING_FIELDS.intersection(payload.keys())
    if prohibited:
        fields = ", ".join(sorted(prohibited))
        raise ValueError(f"Taiga backlog payload must not include scheduling fields: {fields}")


class TaigaAuthMode(StrEnum):
    """Supported Taiga token authentication modes."""

    BEARER = "bearer"
    APPLICATION_TOKEN = "application-token"


class TaigaSettings(BaseModel):
    """Runtime settings for Taiga backlog export."""

    model_config = ConfigDict(extra="forbid")

    base_url: str
    project_identifier: str
    auth_mode: TaigaAuthMode
    token_environment_key: str | None = None
    token_reference: str | None = None
    username_or_email: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0)
    max_retries: int = Field(default=0, ge=0)
    dry_run: bool = True

    @field_validator("base_url")
    @classmethod
    def base_url_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "Taiga base URL").rstrip("/")

    @field_validator("project_identifier")
    @classmethod
    def project_identifier_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "Taiga project identifier")

    @field_validator("token_environment_key", "token_reference")
    @classmethod
    def token_pointer_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _strip_required(value, "Taiga token reference")

    @field_validator("username_or_email")
    @classmethod
    def optional_username_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _strip_required(value, "Taiga username or email")

    @model_validator(mode="after")
    def token_pointer_must_be_configured(self) -> "TaigaSettings":
        if self.token_environment_key is None and self.token_reference is None:
            raise ValueError("Taiga token environment key or token reference is required")
        return self

    @classmethod
    def from_env(
        cls,
        env: dict[str, str] | None = None,
        *,
        require: bool = False,
    ) -> "TaigaSettings | None":
        source = env if env is not None else os.environ
        keys = {
            "base_url": "SPRINTPILOT_TAIGA_BASE_URL",
            "project_identifier": "SPRINTPILOT_TAIGA_PROJECT",
            "auth_mode": "SPRINTPILOT_TAIGA_AUTH_MODE",
            "token_environment_key": "SPRINTPILOT_TAIGA_TOKEN_ENV_KEY",
        }
        optional_keys = {
            "username_or_email": "SPRINTPILOT_TAIGA_USERNAME_OR_EMAIL",
            "timeout_seconds": "SPRINTPILOT_TAIGA_TIMEOUT_SECONDS",
            "max_retries": "SPRINTPILOT_TAIGA_MAX_RETRIES",
            "dry_run": "SPRINTPILOT_TAIGA_DRY_RUN",
        }

        has_any = any(source.get(name) for name in (*keys.values(), *optional_keys.values()))
        if not has_any and not require:
            return None

        missing = [name for name in keys.values() if not source.get(name, "").strip()]
        if missing:
            raise ValueError(f"Missing required Taiga configuration: {', '.join(missing)}")

        values: dict[str, Any] = {
            field: source[env_key].strip() for field, env_key in keys.items()
        }
        username = source.get(optional_keys["username_or_email"], "").strip()
        if username:
            values["username_or_email"] = username
        timeout = source.get(optional_keys["timeout_seconds"], "").strip()
        if timeout:
            values["timeout_seconds"] = _parse_positive_float(
                timeout,
                setting_name=optional_keys["timeout_seconds"],
            )
        retries = source.get(optional_keys["max_retries"], "").strip()
        if retries:
            values["max_retries"] = _parse_non_negative_int(
                retries,
                setting_name=optional_keys["max_retries"],
            )
        dry_run = source.get(optional_keys["dry_run"], "").strip()
        if dry_run:
            values["dry_run"] = _parse_bool(dry_run, setting_name=optional_keys["dry_run"])
        return cls(**values)


class TaigaAuth(BaseModel):
    """Resolved Taiga authentication headers with secret-safe serialization."""

    model_config = ConfigDict(extra="forbid")

    mode: TaigaAuthMode
    identity: str | None = None
    _headers: dict[str, str] = PrivateAttr(default_factory=dict)

    def __init__(self, *, headers: dict[str, str], **data: Any) -> None:
        super().__init__(**data)
        self._headers = dict(headers)

    @property
    def headers(self) -> dict[str, str]:
        return dict(self._headers)


class TaigaProjectRef(BaseModel):
    """Resolved Taiga project target."""

    model_config = ConfigDict(extra="forbid")

    identifier: str
    project_id: int
    name: str | None = None
    slug: str | None = None

    @field_validator("identifier")
    @classmethod
    def identifier_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "Taiga project identifier")


ArtifactType = Literal["epic", "story", "task"]
TaigaItemType = Literal["epic", "user_story", "task"]
SyncActionType = Literal["create", "match", "skip", "fail", "preview"]


class SprintPilotSourceRef(BaseModel):
    """Stable source metadata embedded in Taiga backlog descriptions."""

    model_config = ConfigDict(extra="forbid")

    artifact_type: ArtifactType
    source_id: str
    source_title: str
    sprint_plan_id: str | None = None

    @field_validator("source_id", "source_title")
    @classmethod
    def source_fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "SprintPilot source field")

    def marker(self) -> str:
        return f"SprintPilot-Source: {self.artifact_type}:{self.source_id}"


class TaigaItemRef(BaseModel):
    """Reference to a Taiga item returned by lookup or create calls."""

    model_config = ConfigDict(extra="forbid")

    item_type: TaigaItemType
    item_id: int
    subject: str

    @field_validator("subject")
    @classmethod
    def subject_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "Taiga item subject")


class _BacklogPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str
    description: str
    project_id: int
    source_ref: SprintPilotSourceRef

    @field_validator("subject", "description")
    @classmethod
    def text_fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "Taiga backlog payload field")

    @model_validator(mode="before")
    @classmethod
    def reject_scheduling_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            assert_no_scheduling_fields(data)
        return data

    def contains_scheduling_fields(self) -> bool:
        return bool(PROHIBITED_SCHEDULING_FIELDS.intersection(self.model_dump().keys()))


class TaigaEpicPayload(_BacklogPayload):
    """Taiga epic payload derived from a SprintPlan epic."""

    def to_create_payload(self) -> dict[str, Any]:
        payload = {
            "project": self.project_id,
            "subject": self.subject,
            "description": self.description,
        }
        assert_no_scheduling_fields(payload)
        return payload


class TaigaUserStoryPayload(_BacklogPayload):
    """Taiga user story payload derived from a SprintPlan story."""

    epic_ref: int | None = None

    def to_create_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "project": self.project_id,
            "subject": self.subject,
            "description": self.description,
        }
        if self.epic_ref is not None:
            payload["epic"] = self.epic_ref
        assert_no_scheduling_fields(payload)
        return payload


class TaigaTaskPayload(_BacklogPayload):
    """Taiga task payload derived from a SprintPlan story task."""

    user_story_source_id: str
    user_story_ref: int | None = None

    @field_validator("user_story_source_id")
    @classmethod
    def user_story_source_id_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "Taiga task user story source id")

    def with_user_story_ref(self, user_story_ref: int) -> "TaigaTaskPayload":
        return self.model_copy(update={"user_story_ref": user_story_ref})

    def to_create_payload(self) -> dict[str, Any]:
        if self.user_story_ref is None:
            raise ValueError("Taiga task payload must link to one user story before creation")
        payload = {
            "project": self.project_id,
            "user_story": self.user_story_ref,
            "subject": self.subject,
            "description": self.description,
        }
        assert_no_scheduling_fields(payload)
        return payload


class TaigaMappedPayloads(BaseModel):
    """All Taiga backlog payloads generated from one SprintPlan."""

    model_config = ConfigDict(extra="forbid")

    project: TaigaProjectRef
    epics: list[TaigaEpicPayload]
    user_stories: list[TaigaUserStoryPayload]
    tasks: list[TaigaTaskPayload]
    unsupported_mappings: list[str] = Field(default_factory=list)


class TaigaSyncAction(BaseModel):
    """A planned or executed sync action."""

    model_config = ConfigDict(extra="forbid")

    action_type: SyncActionType
    item_type: TaigaItemType
    source_ref: SprintPilotSourceRef | None = None
    payload: dict[str, Any] | None = None
    taiga_ref: TaigaItemRef | None = None
    reasoning: str
    error: str | None = None

    @field_validator("reasoning")
    @classmethod
    def reasoning_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "sync action reasoning")


class TaigaSyncPlan(BaseModel):
    """Reviewable sync plan built before Taiga mutation."""

    model_config = ConfigDict(extra="forbid")

    project: TaigaProjectRef | None = None
    dry_run: bool
    epic_actions: list[TaigaSyncAction] = Field(default_factory=list)
    story_actions: list[TaigaSyncAction] = Field(default_factory=list)
    task_actions: list[TaigaSyncAction] = Field(default_factory=list)
    unsupported_mappings: list[str] = Field(default_factory=list)


class TaigaSyncResult(BaseModel):
    """Final outcome of dry-run or write-mode sync."""

    model_config = ConfigDict(extra="forbid")

    dry_run: bool
    created: list[TaigaItemRef] = Field(default_factory=list)
    matched: list[TaigaItemRef] = Field(default_factory=list)
    skipped: list[TaigaSyncAction] = Field(default_factory=list)
    failed: list[TaigaSyncAction] = Field(default_factory=list)
    previewed: list[TaigaSyncAction] = Field(default_factory=list)
    reasoning: str

    @field_validator("reasoning")
    @classmethod
    def result_reasoning_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "sync result reasoning")


def _parse_positive_float(value: str, *, setting_name: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{setting_name} must be a positive number") from exc
    if parsed <= 0:
        raise ValueError(f"{setting_name} must be a positive number")
    return parsed


def _parse_non_negative_int(value: str, *, setting_name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{setting_name} must be a non-negative integer") from exc
    if parsed < 0:
        raise ValueError(f"{setting_name} must be a non-negative integer")
    return parsed


def _parse_bool(value: str, *, setting_name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{setting_name} must be a boolean value")
