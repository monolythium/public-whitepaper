#!/usr/bin/env python3
"""Fail closed when internal material enters the public artifact set."""

from __future__ import annotations

import io
import re
import stat
import subprocess
import sys
import unicodedata
import zipfile
import zlib
from dataclasses import dataclass
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

PRIVATE_PATH_TOKENS = frozenset({"draft", "drafts", "internal", "private"})
PRIVATE_COMPOUND_ENDING = re.compile(
    r"(?:drafts?|internal|private)"
    r"(?:docs?|notes?|plans?|files?|materials?|work(?:ing)?)?$"
)
PRIVATE_HIDDEN_PATH_PARTS = frozenset(
    {".claude", ".codex", ".cursor", ".idea", ".local"}
)

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
REGULAR_GIT_MODES = frozenset({"100644", "100755"})


@dataclass(frozen=True)
class Candidate:
    path: Path
    git_mode: str | None
    stage: int = 0


def is_private_path_part(part: str) -> bool:
    """Reject normalized private-work variants without rejecting words like privacy."""
    compatible = unicodedata.normalize("NFKC", part)
    decomposed = unicodedata.normalize("NFKD", compatible)
    normalized = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
        and unicodedata.category(character) != "Cf"
    )
    if normalized.casefold() in PRIVATE_HIDDEN_PATH_PARTS:
        return True

    # Preserve lower-to-upper and acronym-to-title boundaries before folding so
    # ``SteleInternal`` and ``SteleINTERNALDocs`` receive the same treatment as
    # ``stele-internal``.
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", normalized)
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "-", separated)
    folded = separated.casefold().lstrip(".")
    tokens = set(re.findall(r"[a-z0-9]+", folded))
    if tokens & PRIVATE_PATH_TOKENS:
        return True

    # All-cap and all-lower compound names have no recoverable camel boundary.
    # Match only known private markers with a narrow terminal work-product
    # suffix so words such as ``internalization`` and ``privateer`` stay public.
    compact = re.sub(r"[^a-z0-9]+", "", folded)
    if PRIVATE_COMPOUND_ENDING.search(compact):
        return True

    return bool(
        re.match(r"^(?:drafts?|internal|private)(?:$|[^a-z]|[0-9])", folded)
    )


def filesystem_git_mode(path: Path) -> str | None:
    """Return a Git-like mode for an archive-fallback filesystem entry."""
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode):
        return "120000"
    if stat.S_ISREG(mode):
        return "100755" if mode & stat.S_IXUSR else "100644"
    return None


def candidate_files(root: Path = ROOT) -> list[Candidate]:
    """Return index entries Git would publish, with an archive-friendly fallback."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--stage"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return sorted(
            (
                Candidate(path=path, git_mode=filesystem_git_mode(path))
                for path in root.rglob("*")
                if (path.is_symlink() or not path.is_dir())
                and not any(part in FALLBACK_IGNORED_DIRS for part in path.parts)
            ),
            key=lambda candidate: candidate.path.as_posix(),
        )

    candidates: list[Candidate] = []
    for encoded in result.stdout.split(b"\0"):
        if not encoded:
            continue
        metadata, encoded_path = encoded.split(b"\t", 1)
        encoded_mode, _object_id, encoded_stage = metadata.split(b" ", 2)
        candidates.append(
            Candidate(
                path=root / encoded_path.decode("utf-8", errors="strict"),
                git_mode=encoded_mode.decode("ascii", errors="strict"),
                stage=int(encoded_stage),
            )
        )
    return sorted(
        candidates,
        key=lambda candidate: (candidate.path.as_posix(), candidate.stage),
    )


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
    candidates = candidate_files(root)
    for candidate in candidates:
        path = candidate.path
        relative = path.relative_to(root).as_posix()
        pure_path = PurePosixPath(relative)
        suffix = pure_path.suffix.casefold()

        if any(is_private_path_part(part) for part in pure_path.parts):
            failures.append(f"private path is tracked: {relative}")

        if candidate.stage != 0:
            failures.append(
                f"unmerged tracked entry is not allowed: {relative} "
                f"(index stage {candidate.stage})"
            )
            continue

        # Inspect the index mode before the filesystem. This rejects links and
        # gitlinks even when their worktree target is absent or uninitialized.
        if candidate.git_mode == "120000":
            failures.append(f"symlink is not allowed: {relative}")
            continue
        if candidate.git_mode not in REGULAR_GIT_MODES:
            mode = candidate.git_mode or "non-regular filesystem type"
            failures.append(
                f"non-regular tracked entry is not allowed: {relative} ({mode})"
            )
            continue

        # A regular index entry must also be a present regular worktree file;
        # otherwise scanning worktree bytes would silently skip or dereference
        # a different object than the reviewed candidate.
        if path.is_symlink():
            failures.append(f"symlink is not allowed: {relative}")
            continue
        if not path.exists():
            failures.append(f"tracked regular file is missing: {relative}")
            continue
        if not path.is_file():
            failures.append(
                f"tracked regular entry is not a regular worktree file: {relative}"
            )
            continue

        contents = path.read_bytes()

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

    builder_path = root / "tools/build.py"
    if builder_path.is_symlink():
        failures.append("tools/build.py must not be a symlink")
    elif not builder_path.is_file():
        failures.append("tools/build.py is missing")
    else:
        builder = builder_path.read_bytes()
        if re.search(rb"presentational_hints\s*=\s*True\b", builder):
            failures.append("tools/build.py enables unsafe HTML presentational hints")

    return sorted(set(failures)), len(candidates)


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
