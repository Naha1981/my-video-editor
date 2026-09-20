from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class NahaLLMError(RuntimeError):
    pass


class NahaLLMClient:
    """Small dependency-free client for the internal NahaLLM gateway."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("NAHALLM_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("NAHALLM_API_KEY", "")
        self.timeout = float(timeout or os.getenv("NAHALLM_TIMEOUT_SECONDS", "45"))

    @property
    def enabled(self) -> bool:
        return os.getenv("NAHALLM_ENABLED", "0").lower() in {"1", "true", "yes", "on"}

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def health(self) -> dict[str, Any]:
        if not self.configured:
            return {"enabled": self.enabled, "configured": False, "status": "not_configured"}
        try:
            request = Request(self.base_url + "/health", headers={"Accept": "application/json"})
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return {"enabled": self.enabled, "configured": True, "status": "ok", "data": payload}
        except Exception as exc:
            return {
                "enabled": self.enabled,
                "configured": True,
                "status": "unavailable",
                "error": f"{type(exc).__name__}: {exc}",
            }

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str = "fast",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        if not self.configured:
            raise NahaLLMError("NahaLLM is not configured")
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        request = Request(
            self.base_url + "/v1/chat/completions",
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
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            raise NahaLLMError(f"NahaLLM HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise NahaLLMError(f"NahaLLM connection failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise NahaLLMError("NahaLLM returned invalid JSON") from exc

        return body

    def text(
        self,
        system: str,
        user: str,
        *,
        model: str = "fast",
        max_tokens: int = 1200,
    ) -> tuple[str, dict[str, Any]]:
        response = self.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            model=model,
            max_tokens=max_tokens,
        )
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise NahaLLMError("NahaLLM response did not contain assistant content") from exc
        return str(content), response.get("nahallm") or {}
