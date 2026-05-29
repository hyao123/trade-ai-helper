"""Smoke guard that fails when unresolved merge-conflict markers are committed."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke


def _tracked_files(repo_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=False,
    )
    return [repo_root / path.decode("utf-8") for path in result.stdout.split(b"\0") if path]


def test_tracked_files_do_not_contain_merge_conflict_markers():
    repo_root = Path(__file__).resolve().parent.parent
    marker_prefixes = tuple(prefix * 7 for prefix in ("<", "=", ">"))
    offenders: list[str] = []

    for path in _tracked_files(repo_root):
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(lines, start=1):
            if line.startswith(marker_prefixes):
                offenders.append(f"{path.relative_to(repo_root)}:{lineno}")

    assert offenders == []
