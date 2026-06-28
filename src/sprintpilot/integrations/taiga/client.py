"""Taiga client abstraction for backlog export."""

from __future__ import annotations

import json
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

from sprintpilot.integrations.taiga.models import (
    SprintPilotSourceRef,
    TaigaAuth,
    TaigaEpicPayload,
    TaigaItemRef,
    TaigaProjectRef,
    TaigaSettings,
    TaigaTaskPayload,
    TaigaUserStoryPayload,
)


class TaigaClientError(RuntimeError):
    """Safe Taiga client error that must not include credentials."""


class ExistingTaigaItem(BaseModel):
    """Existing Taiga item found during idempotent matching."""

    model_config = ConfigDict(extra="forbid")

    ref: TaigaItemRef
    reason: str


class MatchResult(BaseModel):
    """Result of looking up a potential existing Taiga item."""

    model_config = ConfigDict(extra="forbid")

    matched_item: ExistingTaigaItem | None = None
    ambiguous_reason: str | None = None

    @classmethod
    def no_match(cls) -> "MatchResult":
        return cls()

    @classmethod
    def matched(cls, item: ExistingTaigaItem) -> "MatchResult":
        return cls(matched_item=item)

    @classmethod
    def ambiguous(cls, reason: str) -> "MatchResult":
        return cls(ambiguous_reason=reason)

    @property
    def is_match(self) -> bool:
        return self.matched_item is not None

    @property
    def is_ambiguous(self) -> bool:
        return self.ambiguous_reason is not None


class TaigaClientProtocol(Protocol):
    """Protocol implemented by real and mocked Taiga clients."""

    def resolve_project(self, settings: TaigaSettings, auth: TaigaAuth) -> TaigaProjectRef:
        ...

    def find_existing_epic(
        self,
        project: TaigaProjectRef,
        source_ref: SprintPilotSourceRef,
        title: str | None = None,
    ) -> MatchResult:
        ...

    def find_existing_user_story(
        self,
        project: TaigaProjectRef,
        source_ref: SprintPilotSourceRef,
        title: str | None = None,
    ) -> MatchResult:
        ...

    def find_existing_task(
        self,
        project: TaigaProjectRef,
        user_story_ref: TaigaItemRef,
        source_ref: SprintPilotSourceRef,
        subject: str | None = None,
    ) -> MatchResult:
        ...

    def create_epic(self, payload: TaigaEpicPayload) -> TaigaItemRef:
        ...

    def create_user_story(self, payload: TaigaUserStoryPayload) -> TaigaItemRef:
        ...

    def create_task(self, payload: TaigaTaskPayload) -> TaigaItemRef:
        ...


class TaigaClient:
    """Small Taiga HTTP client for backlog export operations."""

    def __init__(
        self,
        *,
        settings: TaigaSettings | None = None,
        auth: TaigaAuth | None = None,
        transport: Callable[..., Any] | None = None,
    ) -> None:
        self._settings = settings
        self._auth = auth
        self._transport = transport

    def resolve_project(self, settings: TaigaSettings, auth: TaigaAuth) -> TaigaProjectRef:
        self._settings = settings
        self._auth = auth
        if settings.project_identifier.isdigit():
            return TaigaProjectRef(
                identifier=settings.project_identifier,
                project_id=int(settings.project_identifier),
            )
        response = self._request(
            "GET",
            "/api/v1/projects/by_slug",
            params={"slug": settings.project_identifier},
            settings=settings,
            auth=auth,
        )
        if not isinstance(response, dict):
            raise TaigaClientError("Taiga project lookup returned an unexpected response")
        return TaigaProjectRef(
            identifier=settings.project_identifier,
            project_id=int(response["id"]),
            name=response.get("name"),
            slug=response.get("slug"),
        )

    def find_existing_epic(
        self,
        project: TaigaProjectRef,
        source_ref: SprintPilotSourceRef,
        title: str | None = None,
    ) -> MatchResult:
        response = self._request(
            "GET",
            "/api/v1/epics",
            params={"project": project.project_id},
        )
        return _match_items(response, "epic", source_ref, title)

    def find_existing_user_story(
        self,
        project: TaigaProjectRef,
        source_ref: SprintPilotSourceRef,
        title: str | None = None,
    ) -> MatchResult:
        response = self._request(
            "GET",
            "/api/v1/userstories",
            params={"project": project.project_id},
        )
        return _match_items(response, "user_story", source_ref, title)

    def find_existing_task(
        self,
        project: TaigaProjectRef,
        user_story_ref: TaigaItemRef,
        source_ref: SprintPilotSourceRef,
        subject: str | None = None,
    ) -> MatchResult:
        response = self._request(
            "GET",
            "/api/v1/tasks",
            params={"project": project.project_id, "user_story": user_story_ref.item_id},
        )
        return _match_items(response, "task", source_ref, subject)

    def create_epic(self, payload: TaigaEpicPayload) -> TaigaItemRef:
        response = self._request("POST", "/api/v1/epics", json_data=payload.to_create_payload())
        return _item_ref_from_response(response, "epic", fallback_subject=payload.subject)

    def create_user_story(self, payload: TaigaUserStoryPayload) -> TaigaItemRef:
        response = self._request(
            "POST",
            "/api/v1/userstories",
            json_data=payload.to_create_payload(),
        )
        return _item_ref_from_response(response, "user_story", fallback_subject=payload.subject)

    def create_task(self, payload: TaigaTaskPayload) -> TaigaItemRef:
        response = self._request("POST", "/api/v1/tasks", json_data=payload.to_create_payload())
        return _item_ref_from_response(response, "task", fallback_subject=payload.subject)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        json_data: dict[str, object] | None = None,
        settings: TaigaSettings | None = None,
        auth: TaigaAuth | None = None,
    ) -> Any:
        request_settings = settings or self._settings
        request_auth = auth or self._auth
        if request_settings is None or request_auth is None:
            raise TaigaClientError("Taiga client requires settings and auth for HTTP operations")
        headers = request_auth.headers
        if self._transport is not None:
            return self._transport(
                method,
                path,
                params=params,
                json_data=json_data,
                headers=headers,
            )
        return _urllib_request(
            request_settings,
            method,
            path,
            params=params,
            json_data=json_data,
            headers=headers,
        )


def _urllib_request(
    settings: TaigaSettings,
    method: str,
    path: str,
    *,
    params: dict[str, object] | None,
    json_data: dict[str, object] | None,
    headers: dict[str, str],
) -> Any:
    query = f"?{urlencode(params)}" if params else ""
    url = f"{settings.base_url}{path}{query}"
    body = None if json_data is None else json.dumps(json_data).encode("utf-8")
    request_headers = {"Accept": "application/json", **headers}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    request = Request(url, data=body, method=method, headers=request_headers)
    try:
        with urlopen(request, timeout=settings.timeout_seconds or 30) as response:  # noqa: S310
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        raise TaigaClientError(f"Taiga request failed with status {exc.code}") from exc
    except URLError as exc:
        raise TaigaClientError(f"Taiga request failed: {exc.reason}") from exc
    return json.loads(raw) if raw else {}


def _match_items(
    response: Any,
    item_type,
    source_ref: SprintPilotSourceRef,
    title: str | None,
) -> MatchResult:
    if not isinstance(response, list):
        raise TaigaClientError("Taiga lookup returned an unexpected response")
    marker = source_ref.marker()
    marker_matches = [item for item in response if marker in str(item.get("description", ""))]
    if len(marker_matches) == 1:
        return MatchResult.matched(
            ExistingTaigaItem(
                ref=_item_ref_from_response(
                    marker_matches[0],
                    item_type,
                    fallback_subject=title or source_ref.source_title,
                ),
                reason="Matched SprintPilot source marker.",
            )
        )
    if len(marker_matches) > 1:
        return MatchResult.ambiguous("Multiple Taiga items contain the same SprintPilot source marker.")
    if title:
        title_matches = [item for item in response if item.get("subject") == title]
        if len(title_matches) == 1:
            return MatchResult.matched(
                ExistingTaigaItem(
                    ref=_item_ref_from_response(title_matches[0], item_type, fallback_subject=title),
                    reason="Matched one Taiga item by title.",
                )
            )
        if len(title_matches) > 1:
            return MatchResult.ambiguous("Multiple Taiga items share this title.")
    return MatchResult.no_match()


def _item_ref_from_response(response: Any, item_type, *, fallback_subject: str) -> TaigaItemRef:
    if not isinstance(response, dict) or "id" not in response:
        raise TaigaClientError("Taiga item response did not include an id")
    return TaigaItemRef(
        item_type=item_type,
        item_id=int(response["id"]),
        subject=response.get("subject") or fallback_subject,
    )
