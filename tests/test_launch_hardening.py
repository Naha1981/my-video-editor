from pathlib import Path

from app.projects import save_project, load_project, list_projects
from app.security import validate_public_url


def test_public_url_rejects_localhost():
    try:
        validate_public_url("http://127.0.0.1:8000")
    except ValueError:
        return
    raise AssertionError("private/local URLs must be rejected")


def test_public_url_accepts_https_host():
    value = validate_public_url("https://example.com")
    assert value == "https://example.com"


def test_project_round_trip(tmp_path):
    root = tmp_path / "projects"
    saved = save_project(root, {
        "id": "demo-project",
        "name": "Demo Project",
        "plan": {"timeline": []},
        "clip_ids": ["a"],
    })
    loaded = load_project(root, "demo-project")
    assert saved["schema_version"] == "1.0"
    assert loaded["name"] == "Demo Project"
    assert list_projects(root)[0]["id"] == "demo-project"
