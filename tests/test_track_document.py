"""Tests for skills/design-document/helpers/track_document.py.

Run with: python3 -m pytest tests/test_track_document.py -v
or directly: python3 tests/test_track_document.py

Tests redirect $HOME so the global state files don't pollute the user's real ~/.claude/.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parent.parent
TRACK = REPO_DIR / "skills" / "design-document" / "helpers" / "track_document.py"


def run(args, cwd, home, check=True):
    env = os.environ.copy()
    env["HOME"] = str(home)
    return subprocess.run(
        [sys.executable, str(TRACK), *args],
        cwd=str(cwd),
        env=env,
        check=check,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def sandbox(tmp_path):
    """Returns (project_dir, fake_home). Both are fresh tmp dirs."""
    project = tmp_path / "project"
    home = tmp_path / "home"
    project.mkdir()
    home.mkdir()
    return project, home


def test_allocate_starts_at_D0001(sandbox):
    project, home = sandbox
    r = run(["allocate"], cwd=project, home=home)
    assert r.stdout.strip() == "D0001"


def test_allocate_increments(sandbox):
    project, home = sandbox
    ids = [run(["allocate"], cwd=project, home=home).stdout.strip() for _ in range(3)]
    assert ids == ["D0001", "D0002", "D0003"]


def test_allocate_creates_global_state(sandbox):
    project, home = sandbox
    run(["allocate"], cwd=project, home=home)
    state = json.loads((home / ".claude" / "ostack" / "state.json").read_text())
    assert state["next_id"] == 2
    assert (home / ".claude" / "ostack" / "index.md").exists()


def test_record_writes_local_and_global(sandbox):
    project, home = sandbox
    run(["allocate"], cwd=project, home=home)
    run([
        "record",
        "--id", "D0001",
        "--path", "./report.pdf",
        "--keywords", "quarterly, finance, summary",
        "--summary", "Q2 financial summary.",
    ], cwd=project, home=home)

    local = (project / "documents.md").read_text()
    global_idx = (home / ".claude" / "ostack" / "index.md").read_text()

    assert "D0001 — report.pdf" in local
    assert "Q2 financial summary." in local
    assert "quarterly, finance, summary" in local

    assert "D0001 — report.pdf" in global_idx
    assert str(project) in global_idx  # project path recorded


def test_record_with_source(sandbox):
    project, home = sandbox
    run(["allocate"], cwd=project, home=home)
    run([
        "record",
        "--id", "D0001",
        "--path", "./r.pdf",
        "--keywords", "a,b,c",
        "--summary", "x.",
        "--source", "Internal dashboard 2026",
    ], cwd=project, home=home)
    local = (project / "documents.md").read_text()
    assert "Internal dashboard 2026" in local


def test_revise_appends_note(sandbox):
    project, home = sandbox
    run(["allocate"], cwd=project, home=home)
    run([
        "record",
        "--id", "D0001",
        "--path", "./r.pdf",
        "--keywords", "a,b",
        "--summary", "x.",
    ], cwd=project, home=home)
    run(["revise", "--id", "D0001", "--note", "tightened intro"], cwd=project, home=home)
    local = (project / "documents.md").read_text()
    assert "D0001 — revised" in local
    assert "tightened intro" in local


def test_list_empty(sandbox):
    project, home = sandbox
    r = run(["list"], cwd=project, home=home)
    assert "No documents.md" in r.stdout


def test_list_after_record(sandbox):
    project, home = sandbox
    run(["allocate"], cwd=project, home=home)
    run([
        "record",
        "--id", "D0001",
        "--path", "./r.pdf",
        "--keywords", "a,b",
        "--summary", "x.",
    ], cwd=project, home=home)
    r = run(["list"], cwd=project, home=home)
    assert "D0001" in r.stdout


def test_two_projects_share_global_id(sandbox, tmp_path):
    """IDs are global — allocating in one project advances the counter for another."""
    project1, home = sandbox
    project2 = tmp_path / "project2"
    project2.mkdir()

    r1 = run(["allocate"], cwd=project1, home=home).stdout.strip()
    r2 = run(["allocate"], cwd=project2, home=home).stdout.strip()
    r3 = run(["allocate"], cwd=project1, home=home).stdout.strip()

    assert r1 == "D0001"
    assert r2 == "D0002"
    assert r3 == "D0003"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
