from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Profile = Literal["A", "B"]

ALLOWED_ARTIFACT_KEYS = frozenset({"schema_version", "profile", "source", "metadata"})
SUPPORTED_SCHEMA_VERSIONS = frozenset({"v1"})


@dataclass(slots=True)
class LeanCheckerArtifact:
    schema_version: str
    profile: Profile
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


def validate_artifact_schema(data: dict[str, Any], strict: bool = True) -> tuple[bool, list[str]]:
    if not isinstance(data, dict):
        return False, ["Artifact must be a dictionary."]
    errors: list[str] = []
    keys = set(data.keys())
    if strict:
        unknown = sorted(keys - ALLOWED_ARTIFACT_KEYS)
        if unknown:
            errors.append(f"Unknown artifact fields in strict mode: {', '.join(unknown)}")

    missing = sorted({"schema_version", "profile", "source"} - keys)
    if missing:
        errors.append(f"Missing required artifact fields: {', '.join(missing)}")

    schema_version = data.get("schema_version")
    if not isinstance(schema_version, str) or schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"Unsupported schema_version: {schema_version}")

    profile = data.get("profile")
    if not isinstance(profile, str) or profile not in {"A", "B"}:
        errors.append(f"Unsupported profile: {profile}")

    source = data.get("source")
    if not isinstance(source, str):
        errors.append("Artifact field `source` must be a string.")
    if "metadata" in data and not isinstance(data["metadata"], dict):
        errors.append("Artifact field `metadata` must be a dictionary.")

    return len(errors) == 0, errors
