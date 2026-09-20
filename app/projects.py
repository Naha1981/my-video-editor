from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SAFE_ID = re.compile(r"[^a-zA-Z0-9_-]+")


def normalize_project_id(value: str | None = None) -> str:
    raw = SAFE_ID.sub("-", str(value or "").strip()).strip("-")
    return raw[:48] or "project"


def project_path(root: Path, project_id: str) -> Path:
    return root / f"{normalize_project_id(project_id)}.json"


def save_project(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    project_id = normalize_project_id(payload.get("id"))
    now = datetime.now(timezone.utc).isoformat()
    document = {
        **payload,
        "id": project_id,
        "saved_at": now,
        "schema_version": "1.0",
    }
    root.mkdir(parents=True, exist_ok=True)
    project_path(root, project_id).write_text(
        json.dumps(document, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return document


def load_project(root: Path, project_id: str) -> dict[str, Any]:
    path = project_path(root, project_id)
    if not path.exists():
        raise FileNotFoundError(project_id)
    return json.loads(path.read_text(encoding="utf-8"))


def list_projects(root: Path) -> list[dict[str, Any]]:
    root.mkdir(parents=True, exist_ok=True)
    rows=[]
    for path in sorted(root.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            item=json.loads(path.read_text(encoding="utf-8"))
            rows.append({
                "id": item.get("id", path.stem),
                "name": item.get("name") or item.get("prompt") or path.stem,
                "saved_at": item.get("saved_at"),
                "version": item.get("version"),
            })
        except Exception:
            continue
    return rows[:100]
