from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path.home() / ".claude" / "skills" / "ffmpeg-skill"


def find_skill_root() -> Path | None:
    """Locate an installed ffmpeg-skill without making it a hard dependency."""
    candidates = []
    configured = os.getenv("NAHAVIDEO_FFMPEG_SKILL_HOME")
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.extend([
        DEFAULT_ROOT,
        Path.cwd() / ".ffmpeg-skill",
        Path.cwd() / "ffmpeg-skill",
    ])
    for root in candidates:
        if (root / "scripts" / "probe.py").exists():
            return root
    return None


def available() -> bool:
    return find_skill_root() is not None and shutil.which(sys.executable) is not None


def _parse_json(stdout: str) -> Any:
    text = stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for line in reversed(text.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {"raw": text}


def run_tool(tool: str, args: list[str], timeout: int = 180) -> dict[str, Any]:
    """Run one ffmpeg-skill tool directly, never through a shell."""
    root = find_skill_root()
    if root is None:
        return {"available": False, "status": "unavailable", "tool": tool}
    script = root / "scripts" / tool
    if not script.exists():
        return {
            "available": True,
            "status": "missing_tool",
            "tool": tool,
            "script": str(script),
        }
    cmd = [sys.executable, str(script), *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:
        return {
            "available": True,
            "status": "error",
            "tool": tool,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "available": True,
        "status": "ok" if proc.returncode == 0 else "failed",
        "tool": tool,
        "returncode": proc.returncode,
        "data": _parse_json(proc.stdout),
        "stderr": proc.stderr[-4000:],
    }


def verify_output(path: Path, platform: str | None = None) -> dict[str, Any]:
    """Probe and optionally platform-check a rendered asset through ffmpeg-skill."""
    if not path.exists() or path.stat().st_size <= 0:
        return {
            "status": "failed",
            "available": available(),
            "reason": "render output is missing or empty",
        }
    if not available():
        return {
            "status": "fallback_only",
            "available": False,
            "reason": "ffmpeg-skill not installed; NahaVideo native FFmpeg verification remains active",
        }

    probe = run_tool("probe.py", [str(path), "--json"])
    if probe.get("status") != "ok":
        return {
            "status": "failed",
            "available": True,
            "probe": probe,
            "reason": "ffmpeg-skill probe failed",
        }

    check = None
    if platform:
        check = run_tool("check.py", [str(path), "--platform", platform, "--json"])

    return {
        "status": "verified" if check is None or check.get("status") == "ok" else "check_failed",
        "available": True,
        "platform": platform,
        "probe": probe.get("data"),
        "check": check.get("data") if check else None,
        "probe_tool": "ffmpeg-skill/probe.py",
        "check_tool": "ffmpeg-skill/check.py" if check else None,
    }
