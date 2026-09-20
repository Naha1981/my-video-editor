from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class JevMission:
    mission_id: str
    source_url: str
    goal: str
    requirements: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class JevMissionResult:
    mission_id: str
    source_url: str
    completed: bool
    observations: list[dict[str, Any]] = field(default_factory=list)
    assets: list[dict[str, Any]] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    final_url: str | None = None
    observed_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "source_url": self.source_url,
            "completed": self.completed,
            "observations": self.observations,
            "assets": self.assets,
            "trace": self.trace,
            "errors": self.errors,
            "final_url": self.final_url,
            "observed_at": self.observed_at,
        }
