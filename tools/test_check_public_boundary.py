#!/usr/bin/env python3
"""Regression tests for the public-only repository boundary."""

from __future__ import annotations

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

    def test_scan_rejects_normalized_private_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(Path(temporary))
            candidate = root / "notes" / "SteleInternal" / "release.md"
            candidate.parent.mkdir(parents=True)
            candidate.write_text("public-looking text\n", encoding="utf-8")

            with mock.patch.object(
                check_public_boundary, "candidate_files", return_value=[candidate]
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
                check_public_boundary, "candidate_files", return_value=[candidate]
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
                check_public_boundary, "candidate_files", return_value=[candidate]
            ), mock.patch.object(
                check_public_boundary, "ALLOWED_PDFS", frozenset()
            ):
                failures, file_count = check_public_boundary.scan(root)

            self.assertEqual(1, file_count)
            self.assertEqual(
                ["non-regular tracked entry is not allowed: nested-repository"],
                failures,
            )


if __name__ == "__main__":
    unittest.main()
