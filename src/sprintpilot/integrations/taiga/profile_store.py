"""User-local Taiga profiles and repo-local active profile binding."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sprintpilot.integrations.taiga.models import TaigaAuthMode


def _strip_required(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must not be empty")
    return stripped


class TaigaConnectionProfile(BaseModel):
    """Reusable non-secret Taiga connection profile stored on the user's machine."""

    model_config = ConfigDict(extra="forbid")

    name: str
    base_url: str
    project_identifier: str
    auth_mode: TaigaAuthMode
    token_environment_key: str | None = None
    token_reference: str | None = None
    username_or_email: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0)
    max_retries: int = Field(default=0, ge=0)
    dry_run: bool = True

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "Taiga profile name")

    @field_validator("base_url")
    @classmethod
    def base_url_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "Taiga base URL").rstrip("/")

    @field_validator("project_identifier")
    @classmethod
    def project_identifier_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "Taiga project identifier")

    @field_validator("token_environment_key", "token_reference", "username_or_email")
    @classmethod
    def optional_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _strip_required(value, "Taiga profile value")

    @model_validator(mode="after")
    def require_token_pointer(self) -> "TaigaConnectionProfile":
        if self.token_environment_key is None and self.token_reference is None:
            raise ValueError("Taiga profile requires a token environment key or token reference")
        return self


class TaigaProfileStore:
    """Persists user-local Taiga profiles in the platform config directory."""

    def __init__(self, *, config_dir: str | Path | None = None) -> None:
        self.config_dir = Path(config_dir) if config_dir is not None else default_taiga_config_dir()
        self.path = self.config_dir / "taiga-profiles.json"

    def list_profiles(self) -> list[TaigaConnectionProfile]:
        data = self._read()
        profiles = [
            TaigaConnectionProfile.model_validate(profile)
            for profile in data.get("profiles", {}).values()
        ]
        return sorted(profiles, key=lambda profile: profile.name)

    def get_profile(self, name: str) -> TaigaConnectionProfile | None:
        data = self._read()
        raw_profile = data.get("profiles", {}).get(name)
        if raw_profile is None:
            return None
        return TaigaConnectionProfile.model_validate(raw_profile)

    def save_profile(self, profile: TaigaConnectionProfile, *, make_default: bool = False) -> None:
        data = self._read()
        profiles = data.setdefault("profiles", {})
        profiles[profile.name] = profile.model_dump(mode="json", exclude_none=True)
        if make_default or not data.get("default_profile"):
            data["default_profile"] = profile.name
        self._write(data)

    def get_default_profile_name(self) -> str | None:
        name = self._read().get("default_profile")
        return name if isinstance(name, str) and name.strip() else None

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "default_profile": None, "profiles": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid Taiga profile store: {self.path}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"Invalid Taiga profile store: {self.path}")
        data.setdefault("version", 1)
        data.setdefault("default_profile", None)
        data.setdefault("profiles", {})
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


class RepoTaigaBindingStore:
    """Stores the active Taiga profile name for one repository."""

    def __init__(self, *, repo_dir: str | Path | None = None) -> None:
        self.repo_dir = Path(repo_dir) if repo_dir is not None else Path.cwd()
        self.path = self.repo_dir / ".sprintpilot" / "taiga.json"

    def get_active_profile_name(self) -> str | None:
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid repo Taiga binding: {self.path}") from exc
        name = data.get("active_profile") if isinstance(data, dict) else None
        return name if isinstance(name, str) and name.strip() else None

    def set_active_profile(self, profile_name: str) -> None:
        name = _strip_required(profile_name, "Taiga profile name")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"version": 1, "active_profile": name}
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def default_taiga_config_dir() -> Path:
    override = os.getenv("SPRINTPILOT_CONFIG_HOME", "").strip()
    if override:
        return Path(override)
    if os.name == "nt":
        root = os.getenv("APPDATA", "").strip()
        return Path(root) / "SprintPilot" if root else Path.home() / "AppData" / "Roaming" / "SprintPilot"
    root = os.getenv("XDG_CONFIG_HOME", "").strip()
    return (Path(root) if root else Path.home() / ".config") / "sprintpilot"
