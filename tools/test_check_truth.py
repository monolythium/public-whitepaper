#!/usr/bin/env python3
"""Regression tests for the public Stele deployment-truth gate."""

from __future__ import annotations

import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import check_truth


class SteleDeploymentTruthTests(unittest.TestCase):
    def assert_stale(self, text: str) -> None:
        self.assertTrue(
            any(
                pattern.search(text)
                for pattern in check_truth.STALE_STELE_DEPLOYMENT.values()
            ),
            msg=f"expected stale deployment copy to be rejected: {text!r}",
        )

    def test_reserved_hostname_forms_are_rejected(self) -> None:
        stale_samples = (
            "The reserved Stele production hostname will be released later.",
            "The canonical production hostname is reserved as `stele.monolythium.com`.",
            "Publication of the reserved Stele hostname remains gated.",
        )
        for sample in stale_samples:
            with self.subTest(sample=sample):
                self.assert_stale(sample)

    def test_unavailable_deployment_forms_are_rejected(self) -> None:
        stale_samples = (
            "This paper does not publish it as a live link.",
            "The hostname is intentionally not linked until deployment.",
            "The hostname is not published as a live link.",
            "Publication of the hostname as a live destination remains gated.",
        )
        for sample in stale_samples:
            with self.subTest(sample=sample):
                self.assert_stale(sample)

    def test_current_snapshot_satisfies_every_required_anchor(self) -> None:
        current = """
> The public preview is live at
> [stele.monolythium.com](https://stele.monolythium.com) with zero published services.
> Browser Wallet
> v0.4.5 is a prerelease. The public web authenticates users through Browser Wallet and can
> inspect an existing valid non-economic approval preview; it does not create drafts.
> Hosted Stele MCP exposes exactly two OAuth-protected tools. Draft preparation is unavailable
> without a published listing.
> The isolated local Stele MCP exposes exactly three read/status tools and no transaction tool.
> Economic writes, transaction
> signing, and mainnet remain off.
"""
        searchable = check_truth.folded_prose(current)
        missing = [
            phrase
            for phrase in check_truth.STELE_STATUS_REQUIRED
            if phrase.casefold() not in searchable
        ]
        self.assertEqual([], missing)
        self.assertFalse(
            any(
                pattern.search(current)
                for pattern in check_truth.STALE_STELE_DEPLOYMENT.values()
            )
        )


class SteleTruthMainBlackBoxTests(unittest.TestCase):
    """Mutate copies of real public documents and exercise the CLI entry point."""

    def run_mutation(
        self,
        relative: str,
        old: str,
        new: str,
        expected_error: str,
    ) -> None:
        source_root = check_truth.ROOT
        document_relatives = tuple(
            path.relative_to(source_root) for path in check_truth.DOCUMENTS
        )
        status_relatives = tuple(
            path.relative_to(source_root) for path in check_truth.STELE_STATUS_DOCUMENTS
        )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for source_relative in set(document_relatives + status_relatives):
                source = source_root / source_relative
                destination = root / source_relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)

            target = root / relative
            original = target.read_text(encoding="utf-8")
            self.assertIn(old, original)
            target.write_text(original.replace(old, new, 1), encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.multiple(
                check_truth,
                ROOT=root,
                DOCUMENTS=tuple(root / path for path in document_relatives),
                STELE_STATUS_DOCUMENTS=tuple(root / path for path in status_relatives),
            ), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = check_truth.main()

            self.assertEqual(1, result, msg=stdout.getvalue())
            self.assertIn(expected_error, stderr.getvalue())

    def test_main_rejects_wrong_hosted_tool_count_when_correct_anchor_remains(self) -> None:
        self.run_mutation(
            "2026/may/monolythium-whitepaper-v5.0.md",
            "| Hosted Stele MCP | Exactly two keyless, OAuth-protected tools",
            "| Hosted Stele MCP | Exactly four keyless, OAuth-protected tools",
            "hosted Stele MCP claims exactly 4 tools; expected exactly 2",
        )

    def test_main_rejects_wrong_local_tool_count_when_correct_anchor_remains(self) -> None:
        self.run_mutation(
            "2026/may/monolythium-whitepaper-v5.0.md",
            "local Stele MCP exposes exactly three read/status tools",
            "local Stele MCP exposes exactly four read/status tools",
            "local Stele MCP claims exactly 4 tools; expected exactly 3",
        )

    def test_main_rejects_transaction_capable_local_mcp(self) -> None:
        self.run_mutation(
            "README.md",
            "no transaction tool. Draft preparation",
            "no transaction tool, but it supports transaction signing. Draft preparation",
            "local Stele MCP claims transaction capability",
        )

    def test_main_rejects_nonzero_catalog_when_zero_anchor_remains(self) -> None:
        self.run_mutation(
            "2026/may/monolythium-whitepaper-v5.0.md",
            "with zero published services",
            "with four published services",
            "Stele catalog claims 4 published services; expected zero",
        )

    def test_main_rejects_enabled_economic_writes(self) -> None:
        self.run_mutation(
            "README.md",
            "Economic writes, transaction signing, and mainnet remain off.",
            "Economic writes, transaction signing, and mainnet remain off. Economic writes are enabled.",
            "Stele economic writes incorrectly presented as enabled",
        )

    def test_main_rejects_enabled_transaction_signing(self) -> None:
        self.run_mutation(
            "README.md",
            "Economic writes, transaction signing, and mainnet remain off.",
            "Economic writes, transaction signing, and mainnet remain off. Transaction signing is enabled.",
            "Stele transaction signing incorrectly presented as enabled",
        )

    def test_main_rejects_live_mainnet(self) -> None:
        self.run_mutation(
            "README.md",
            "Economic writes, transaction signing, and mainnet remain off.",
            "Economic writes, transaction signing, and mainnet remain off. Mainnet is live.",
            "Stele mainnet incorrectly presented as enabled",
        )

    def test_main_rejects_public_web_draft_creation(self) -> None:
        self.run_mutation(
            "README.md",
            "it does not create drafts.",
            "it does not create drafts. The public web can create booking drafts.",
            "public web claims draft creation",
        )

    def test_main_rejects_draft_preparation_without_a_listing(self) -> None:
        self.run_mutation(
            "README.md",
            "Draft preparation is unavailable without a published listing.",
            "Draft preparation is unavailable without a published listing. Draft preparation is available without a published listing.",
            "draft preparation claims no listing prerequisite",
        )


if __name__ == "__main__":
    unittest.main()
