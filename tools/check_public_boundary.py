#!/usr/bin/env python3
"""Fail closed when internal material enters the public artifact set."""

from __future__ import annotations

import io
import re
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from typing import Iterable, Iterator


ROOT = Path(__file__).resolve().parents[1]

ALLOWED_PDFS = frozenset(
    {
        "2026/may/monolythium-lightpaper-v5.0.pdf",
        "2026/may/monolythium-whitepaper-v5.0.pdf",
    }
)

OFFICE_SUFFIXES = frozenset(
    {
        ".doc",
        ".docm",
        ".docx",
        ".dot",
        ".dotx",
        ".key",
        ".numbers",
        ".odp",
        ".ods",
        ".odt",
        ".pages",
        ".ppt",
        ".pptm",
        ".pptx",
        ".rtf",
        ".xls",
        ".xlsm",
        ".xlsx",
    }
)

PRIVATE_PATH_PARTS = frozenset({"draft", "drafts", "internal", "private"})

# Build signatures in pieces so the gate does not trigger on its own source.
UNPUBLISHED_MARKER = re.compile(
    rb"\bdo[ \t\r\n]+not[ \t\r\n]+publish\b", re.IGNORECASE
)
INTERNAL_PATH_MARKERS = (
    re.compile((b"file" + rb":[/\\]+"), re.IGNORECASE),
    re.compile((rb"/(?:" + b"home" + rb"|Users|private/tmp|tmp)/")),
    re.compile((rb"[A-Za-z]:[/\\]+" + b"Users" + rb"[/\\]+")),
    re.compile((rb"/(?:workspace|workspaces|builds|runner/_work)/")),
    re.compile((b"monolythium" + rb"-ecosystem[/\\]")),
)

OLE_COMPOUND_MAGIC = bytes.fromhex("d0cf11e0a1b11ae1")
PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = b"PK\x03\x04"

FALLBACK_IGNORED_DIRS = frozenset(
    {".git", ".venv", "__pycache__", "node_modules"}
)


def candidate_files(root: Path = ROOT) -> list[Path]:
    """Return files Git would publish, with an archive-friendly fallback."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return sorted(
            path
            for path in root.rglob("*")
            if path.is_file()
            and not any(part in FALLBACK_IGNORED_DIRS for part in path.parts)
        )

    files: list[Path] = []
    for encoded in result.stdout.split(b"\0"):
        if not encoded:
            continue
        path = root / encoded.decode("utf-8", errors="strict")
        # A staged deletion is not part of the candidate tree.
        if path.is_file():
            files.append(path)
    return sorted(files)


def decoded_pdf_payloads(contents: bytes) -> Iterator[bytes]:
    """Yield raw and Flate-decoded PDF payloads for boundary inspection."""
    yield contents
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", contents, re.DOTALL):
        stream = match.group(1)
        try:
            yield zlib.decompress(stream)
        except zlib.error:
            continue


def looks_like_office_container(contents: bytes) -> bool:
    if contents.startswith(OLE_COMPOUND_MAGIC):
        return True
    if not contents.startswith(ZIP_MAGIC):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as archive:
            names = {name.casefold() for name in archive.namelist()}
    except (OSError, zipfile.BadZipFile):
        return False
    return any(
        name == "[content_types].xml"
        or name.startswith(("word/", "ppt/", "xl/"))
        for name in names
    ) and any(name.startswith(("word/", "ppt/", "xl/")) for name in names)


def content_failures(relative: str, contents: bytes) -> Iterable[str]:
    payloads = (
        decoded_pdf_payloads(contents)
        if contents.startswith(PDF_MAGIC)
        else (contents,)
    )
    for payload in payloads:
        if UNPUBLISHED_MARKER.search(payload):
            yield f"unpublished marker found: {relative}"
            return

    payloads = (
        decoded_pdf_payloads(contents)
        if contents.startswith(PDF_MAGIC)
        else (contents,)
    )
    for payload in payloads:
        if any(pattern.search(payload) for pattern in INTERNAL_PATH_MARKERS):
            yield f"local filesystem path found: {relative}"
            return


def scan(root: Path = ROOT) -> tuple[list[str], int]:
    failures: list[str] = []
    files = candidate_files(root)
    for path in files:
        relative = path.relative_to(root).as_posix()
        pure_path = PurePosixPath(relative)
        suffix = pure_path.suffix.casefold()
        contents = path.read_bytes()

        if any(part.casefold() in PRIVATE_PATH_PARTS for part in pure_path.parts):
            failures.append(f"private path is tracked: {relative}")

        if suffix in OFFICE_SUFFIXES or looks_like_office_container(contents):
            failures.append(f"office artifact is not allowed: {relative}")

        is_pdf = contents.startswith(PDF_MAGIC)
        if (suffix == ".pdf" or is_pdf) and relative not in ALLOWED_PDFS:
            failures.append(f"PDF is not in the release allowlist: {relative}")
        if relative in ALLOWED_PDFS and not is_pdf:
            failures.append(f"allowlisted PDF has invalid content: {relative}")

        failures.extend(content_failures(relative, contents))

    for relative in sorted(ALLOWED_PDFS):
        if not (root / relative).is_file():
            failures.append(f"allowlisted PDF is missing: {relative}")

    return sorted(set(failures)), len(files)


def main() -> int:
    failures, file_count = scan()
    if failures:
        print("public repository boundary failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print(f"public repository boundary passed ({file_count} candidate files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
