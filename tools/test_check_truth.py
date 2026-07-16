#!/usr/bin/env python3
"""Regression tests for the public Stele deployment-truth gate."""

from __future__ import annotations

import unittest

from check_truth import (
    STALE_STELE_DEPLOYMENT,
    STELE_STATUS_REQUIRED,
    folded_prose,
)


class SteleDeploymentTruthTests(unittest.TestCase):
    def assert_stale(self, text: str) -> None:
        self.assertTrue(
            any(pattern.search(text) for pattern in STALE_STELE_DEPLOYMENT.values()),
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
> v0.4.5 is a prerelease. Hosted Stele MCP exposes exactly two OAuth-protected tools.
> The isolated local Stele MCP exposes exactly three read/status tools and no transaction tool.
> Economic writes, transaction
> signing, and mainnet remain off.
"""
        searchable = folded_prose(current)
        missing = [
            phrase
            for phrase in STELE_STATUS_REQUIRED
            if phrase.casefold() not in searchable
        ]
        self.assertEqual([], missing)
        self.assertFalse(
            any(pattern.search(current) for pattern in STALE_STELE_DEPLOYMENT.values())
        )


if __name__ == "__main__":
    unittest.main()
