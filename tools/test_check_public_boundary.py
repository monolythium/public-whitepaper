#!/usr/bin/env python3
"""Regression tests for the public-only repository boundary."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import check_public_boundary


class PrivatePathTests(unittest.TestCase):
    def test_normalized_private_path_variants_are_rejected(self) -> None:
        private_parts = (
            ".local",
            ".CODEX",
            "drafts",
            "Draft-v2",
            "internal_docs",
            "SteleInternal",
            "INTERNALDocs",
            "SteleINTERNALDocs",
            "İnternal",
            "Steleİnternal",
            "In\u200bternalDocs",
            "provider-private-notes",
            "Ｐｒｉｖａｔｅ",
        )
        for part in private_parts:
            with self.subTest(part=part):
                self.assertTrue(check_public_boundary.is_private_path_part(part))

    def test_public_path_words_are_not_overmatched(self) -> None:
        public_parts = (
            ".github",
            "2026",
            "draftsmanship",
            "internalization",
            "privacy",
            "privateer",
            "public-whitepaper",
        )
        for part in public_parts:
            with self.subTest(part=part):
                self.assertFalse(check_public_boundary.is_private_path_part(part))


class BoundaryScanTests(unittest.TestCase):
    def make_root(self, parent: Path) -> Path:
        root = parent / "candidate"
        (root / "tools").mkdir(parents=True)
        (root / "tools/build.py").write_text("# safe builder\n", encoding="utf-8")
        return root

    def git(self, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    def make_git_root(self, parent: Path) -> Path:
        root = self.make_root(parent)
        self.git(root, "init", "-q")
        self.git(root, "config", "user.email", "boundary-test@example.invalid")
        self.git(root, "config", "user.name", "Boundary Test")
        self.git(root, "add", "tools/build.py")
        self.git(root, "commit", "-qm", "fixture")
        return root

    def test_scan_rejects_normalized_private_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(Path(temporary))
            candidate = root / "notes" / "SteleInternal" / "release.md"
            candidate.parent.mkdir(parents=True)
            candidate.write_text("public-looking text\n", encoding="utf-8")

            with mock.patch.object(
                check_public_boundary,
                "candidate_files",
                return_value=[
                    check_public_boundary.Candidate(candidate, "100644")
                ],
            ), mock.patch.object(
                check_public_boundary, "ALLOWED_PDFS", frozenset()
            ):
                failures, file_count = check_public_boundary.scan(root)

            self.assertEqual(1, file_count)
            self.assertIn(
                "private path is tracked: notes/SteleInternal/release.md", failures
            )

    def test_scan_rejects_symlink_without_reading_its_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = self.make_root(parent)
            outside = parent / "outside.txt"
            outside.write_text(
                "do " + "not " + "publish this target\n", encoding="utf-8"
            )
            candidate = root / "release.md"
            candidate.symlink_to(outside)

            with mock.patch.object(
                check_public_boundary,
                "candidate_files",
                return_value=[
                    check_public_boundary.Candidate(candidate, "120000")
                ],
            ), mock.patch.object(
                check_public_boundary, "ALLOWED_PDFS", frozenset()
            ):
                failures, file_count = check_public_boundary.scan(root)

            self.assertEqual(1, file_count)
            self.assertEqual(["symlink is not allowed: release.md"], failures)

    def test_scan_rejects_non_regular_tracked_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(Path(temporary))
            candidate = root / "nested-repository"
            candidate.mkdir()

            with mock.patch.object(
                check_public_boundary,
                "candidate_files",
                return_value=[
                    check_public_boundary.Candidate(candidate, "160000")
                ],
            ), mock.patch.object(
                check_public_boundary, "ALLOWED_PDFS", frozenset()
            ):
                failures, file_count = check_public_boundary.scan(root)

            self.assertEqual(1, file_count)
            self.assertEqual(
                [
                    "non-regular tracked entry is not allowed: "
                    "nested-repository (160000)"
                ],
                failures,
            )

    def test_real_git_index_rejects_absent_uninitialized_gitlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_git_root(Path(temporary))
            head = self.git(root, "rev-parse", "HEAD").stdout.strip()
            self.git(
                root,
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{head},ghost-submodule",
            )

            with mock.patch.object(
                check_public_boundary, "ALLOWED_PDFS", frozenset()
            ):
                failures, file_count = check_public_boundary.scan(root)

            self.assertEqual(2, file_count)
            self.assertIn(
                "non-regular tracked entry is not allowed: ghost-submodule (160000)",
                failures,
            )

    def test_real_git_index_rejects_tracked_symlink_by_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_git_root(Path(temporary))
            candidate = root / "release-link.md"
            candidate.symlink_to("missing-target.md")
            self.git(root, "add", "release-link.md")

            with mock.patch.object(
                check_public_boundary, "ALLOWED_PDFS", frozenset()
            ):
                failures, file_count = check_public_boundary.scan(root)

            self.assertEqual(2, file_count)
            self.assertIn("symlink is not allowed: release-link.md", failures)

    def test_real_git_index_does_not_skip_missing_regular_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_git_root(Path(temporary))
            candidate = root / "tracked-release.md"
            candidate.write_text("public text\n", encoding="utf-8")
            self.git(root, "add", "tracked-release.md")
            self.git(root, "commit", "-qm", "track release")
            candidate.unlink()

            with mock.patch.object(
                check_public_boundary, "ALLOWED_PDFS", frozenset()
            ):
                failures, file_count = check_public_boundary.scan(root)

            self.assertEqual(2, file_count)
            self.assertIn(
                "tracked regular file is missing: tracked-release.md", failures
            )

    def test_real_git_index_rejects_acronym_private_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_git_root(Path(temporary))
            candidate = root / "notes" / "SteleINTERNALDocs" / "release.md"
            candidate.parent.mkdir(parents=True)
            candidate.write_text("public-looking text\n", encoding="utf-8")
            self.git(root, "add", "notes/SteleINTERNALDocs/release.md")

            with mock.patch.object(
                check_public_boundary, "ALLOWED_PDFS", frozenset()
            ):
                failures, file_count = check_public_boundary.scan(root)

            self.assertEqual(2, file_count)
            self.assertIn(
                "private path is tracked: notes/SteleINTERNALDocs/release.md",
                failures,
            )


if __name__ == "__main__":
    unittest.main()
