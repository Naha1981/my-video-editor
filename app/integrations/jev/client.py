from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import JevMission, JevMissionResult
from .safety import allowed_domain, validate_target_url


class JevBrowserError(RuntimeError):
    pass


class JevBrowserAgent:
    """Stable application-facing adapter for the remote Jev browser worker."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("JEV_WORKER_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("JEV_WORKER_API_KEY", "")
        self.timeout = float(timeout or os.getenv("JEV_TIMEOUT_SECONDS", "240"))
        self._result: JevMissionResult | None = None

    @property
    def enabled(self) -> bool:
        return os.getenv("JEV_ENABLED", "0").lower() in {"1", "true", "yes", "on"}

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def start(self) -> dict:
        if not self.enabled:
            return {"enabled": False, "status": "disabled"}
        if not self.configured:
            return {"enabled": True, "status": "not_configured"}
        try:
            request = Request(
                self.base_url + "/health",
                headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
            )
            with urlopen(request, timeout=min(self.timeout, 15)) as response:
                return {"enabled": True, "status": "ok", "data": json.loads(response.read().decode("utf-8"))}
        except Exception as exc:
            return {"enabled": True, "status": "unavailable", "error": f"{type(exc).__name__}: {exc}"}

    def execute(self, mission: JevMission) -> JevMissionResult:
        if not self.enabled:
            raise JevBrowserError("Jev is disabled")
        if not self.configured:
            raise JevBrowserError("Jev worker is not configured")
        target = validate_target_url(mission.source_url)
        allowlist = os.getenv("JEV_ALLOWED_DOMAINS", "")
        if not allowed_domain(target, allowlist):
            raise JevBrowserError("Target domain is not allowed by JEV_ALLOWED_DOMAINS")

        payload = {
            "mission_id": mission.mission_id,
            "url": target,
            "goal": mission.goal,
            "requirements": mission.requirements,
            "metadata": mission.metadata,
        }
        request = Request(
            self.base_url + "/run",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2500]
            raise JevBrowserError(f"Jev worker HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise JevBrowserError(f"Jev worker connection failed: {exc}") from exc
        if not body.get("mission_id"):
            raise JevBrowserError("Jev worker returned no mission_id")
        self._result = JevMissionResult(**{
            key: body.get(key)
            for key in (
                "mission_id", "source_url", "completed", "observations", "assets",
                "trace", "errors", "final_url", "observed_at",
            )
            if key in body
        })
        return self._result

    def run_mission(self, mission: JevMission) -> JevMissionResult:
        return self.execute(mission)

    def get_observation(self) -> dict:
        return (self._result.as_dict() if self._result else {}).get("observations", {})  # type: ignore[return-value]

    def get_result(self) -> JevMissionResult | None:
        return self._result

    def stop(self) -> dict:
        self._result = None
        return {"status": "stopped"}
