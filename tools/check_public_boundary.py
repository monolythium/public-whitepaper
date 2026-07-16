#!/usr/bin/env python3
"""Fail when unpublished/internal material enters the public repository tree."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_PDFS = {
    "2026/may/monolythium-lightpaper-v5.0.pdf",
    "2026/may/monolythium-whitepaper-v5.0.pdf",
}
FORBIDDEN_SUFFIXES = {
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
}
FORBIDDEN_MARKERS = {
    b"DRAFT." + b" Do not publish",
    b"Do not" + b" publish.",
    b"file:" + b"///home/",
    b"/home/" + b"blackwell/",
    b"monolythium-ecosystem/" + b"worktrees/",
}


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [entry.decode("utf-8") for entry in result.stdout.split(b"\0") if entry]


def main() -> int:
    failures: list[str] = []
    for relative in tracked_files():
        path = PurePosixPath(relative)
        suffix = path.suffix.lower()

        if "drafts" in path.parts:
            failures.append(f"unpublished draft path is tracked: {relative}")
        if suffix in FORBIDDEN_SUFFIXES:
            failures.append(f"office document is not a public source artifact: {relative}")
        if suffix == ".pdf" and relative not in ALLOWED_PDFS:
            failures.append(f"PDF is not in the public release allowlist: {relative}")

        contents = (ROOT / relative).read_bytes()
        if any(marker in contents for marker in FORBIDDEN_MARKERS):
            failures.append(f"internal marker or local workspace path found: {relative}")

    if failures:
        print("Public repository boundary failed:", file=sys.stderr)
        for failure in sorted(set(failures)):
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(f"Public repository boundary passed ({len(tracked_files())} tracked files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
