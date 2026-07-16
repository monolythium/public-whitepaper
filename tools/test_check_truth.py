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
> v0.4.5 is a prerelease. The public web authenticates users through Browser Wallet.
> That authentication proves only current control of the selected wallet address; it does not prove
> a human or legal identity, durable ownership, credentials, or authority.
> Provider Studio at https://stele.monolythium.com/studio can create, edit, preview, and delete
> private wallet-owned provider-listing
> drafts. These durable provider-listing drafts are not published, discoverable, or transactable,
> and provider publication remains off.
> Booking-approval drafts are separate. The web can inspect an existing valid non-economic
> booking-approval draft, but it does not create booking-approval drafts.
> The public web exposes no booking, payment, settlement, or other economic controls.
> Hosted Stele MCP exposes exactly two OAuth-protected tools, including booking-draft preparation.
> It does not create or access provider-listing drafts. Hosted booking-draft preparation is unavailable
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
        self.assertEqual([], check_truth.stele_status_contradictions(current))

    def test_provider_studio_listing_draft_creation_is_allowed(self) -> None:
        current = (
            "The public web Provider Studio can create private wallet-owned provider-listing "
            "drafts. These durable provider-listing drafts are not published, discoverable, "
            "or transactable."
        )
        self.assertEqual([], check_truth.stele_status_contradictions(current))

    def assert_contradiction(self, text: str, expected: str) -> None:
        labels = {label for _, label in check_truth.stele_status_contradictions(text)}
        self.assertIn(expected, labels, msg=f"expected rejection for {text!r}")

    def test_hosted_transaction_capability_paraphrases_are_rejected(self) -> None:
        samples = (
            "Hosted Stele MCP can sign and broadcast transactions.",
            "Hosted MCP broadcasts signed transactions.",
            "Hosted Stele MCP supports transaction submission.",
            "Hosted MCP offers hosted signing.",
            "Hosted Stele MCP has wallet custody.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "hosted Stele MCP claims transaction capability"
                )

    def test_public_web_forbidden_capability_paraphrases_are_rejected(self) -> None:
        samples = (
            (
                "The public web can publish provider listings.",
                "public web claims provider-publication authority",
            ),
            (
                "The Stele web supports provider publication.",
                "public web claims provider-publication authority",
            ),
            (
                "Provider publication is available through the public web.",
                "provider publication assigned to public web",
            ),
            (
                "The public web includes booking, payment, and settlement controls.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "The web app can pay providers.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Settlement controls are live on the Stele web.",
                "booking, payment, settlement, or economic controls assigned to public web",
            ),
        )
        for sample, expected in samples:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_wallet_authentication_identity_overclaims_are_rejected(self) -> None:
        samples = (
            "Browser Wallet owns identity proof.",
            "Browser Wallet proves human identity.",
            "Wallet authentication verifies legal identity.",
            "That authentication establishes authority.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "wallet authentication presented as identity proof"
                )

    def test_historical_future_gated_and_negative_copy_is_allowed(self) -> None:
        samples = (
            "Hosted Stele MCP does not sign or broadcast transactions.",
            "A future Hosted Stele MCP could support transaction signing after a separate release.",
            "The public web exposes no booking, payment, settlement, or other economic controls.",
            "The public web will support payments only after protocol activation.",
            "The retired public web used to offer payment controls.",
            "Provider publication could be available through a future public web after release.",
            "Wallet authentication does not prove human identity or authority.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))


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
            "| Isolated local Stele MCP | Exactly three read/status tools",
            "| Isolated local Stele MCP | Exactly four read/status tools",
            "local Stele MCP claims exactly 4 tools; expected exactly 3",
        )

    def test_main_rejects_transaction_capable_local_mcp(self) -> None:
        self.run_mutation(
            "README.md",
            "no transaction tool. Economic writes",
            "no transaction tool, but it supports transaction signing. Economic writes",
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

    def test_main_rejects_public_web_booking_approval_draft_creation(self) -> None:
        self.run_mutation(
            "README.md",
            "it does not create booking-approval drafts.",
            "it does not create booking-approval drafts. "
            "The public web can create booking-approval drafts.",
            "public web claims booking-approval draft creation",
        )

    def test_main_rejects_booking_draft_preparation_without_a_listing(self) -> None:
        self.run_mutation(
            "README.md",
            "Hosted booking-draft preparation is unavailable without a published listing.",
            "Hosted booking-draft preparation is unavailable without a published listing. "
            "Booking-draft preparation is available without a published listing.",
            "booking-draft preparation claims no listing prerequisite",
        )

    def test_main_rejects_stale_generic_public_web_draft_denial(self) -> None:
        self.run_mutation(
            "README.md",
            "it does not create booking-approval drafts.",
            "it does not create booking-approval drafts. The public web does not create drafts.",
            "public web still denies every draft class",
        )

    def test_main_rejects_published_provider_listing_draft(self) -> None:
        self.run_mutation(
            "README.md",
            "these durable provider-listing drafts are not published, discoverable, or transactable",
            "these durable provider-listing drafts are not published, discoverable, or transactable. "
            "Private provider-listing drafts are published",
            "provider-listing draft presented as public or executable",
        )

    def test_main_rejects_provider_studio_publication(self) -> None:
        self.run_mutation(
            "README.md",
            "provider publication remains off.",
            "provider publication remains off. Provider Studio can publish provider listings.",
            "Provider Studio presented as a publication or transaction surface",
        )

    def test_main_rejects_hosted_mcp_provider_listing_drafts(self) -> None:
        self.run_mutation(
            "README.md",
            "does not create or access provider-listing drafts.",
            "does not create or access provider-listing drafts. "
            "Hosted Stele MCP creates provider-listing drafts.",
            "hosted MCP claims provider-listing draft authority",
        )

    def test_main_rejects_provider_and_booking_draft_conflation(self) -> None:
        self.run_mutation(
            "README.md",
            "Booking-approval drafts are separate:",
            "Provider-listing drafts are booking-approval drafts. "
            "Booking-approval drafts are separate:",
            "provider-listing and booking-approval drafts are conflated",
        )

    def test_main_rejects_enabled_provider_publication(self) -> None:
        self.run_mutation(
            "README.md",
            "provider publication remains off.",
            "provider publication remains off. Provider publication is enabled.",
            "Stele provider publication incorrectly presented as enabled",
        )

    def test_main_rejects_hosted_signing_and_broadcast_adversarial_copy(self) -> None:
        self.run_mutation(
            "README.md",
            "Economic writes, transaction signing, and mainnet remain off.",
            "Economic writes, transaction signing, and mainnet remain off. "
            "Hosted Stele MCP can sign and broadcast transactions.",
            "hosted Stele MCP claims transaction capability",
        )

    def test_main_rejects_public_web_economic_controls_adversarial_copy(self) -> None:
        self.run_mutation(
            "README.md",
            "Economic writes, transaction signing, and mainnet remain off.",
            "Economic writes, transaction signing, and mainnet remain off. "
            "The public web includes booking, payment, and settlement controls.",
            "public web claims booking, payment, settlement, or economic controls",
        )

    def test_main_rejects_public_web_publication_adversarial_copy(self) -> None:
        self.run_mutation(
            "README.md",
            "Economic writes, transaction signing, and mainnet remain off.",
            "Economic writes, transaction signing, and mainnet remain off. "
            "The public web can publish provider listings.",
            "public web claims provider-publication authority",
        )

    def test_main_rejects_identity_overclaim_when_correct_anchor_remains(self) -> None:
        self.run_mutation(
            "README.md",
            "Economic writes, transaction signing, and mainnet remain off.",
            "Economic writes, transaction signing, and mainnet remain off. "
            "Browser Wallet proves human identity.",
            "wallet authentication presented as identity proof",
        )

    def test_main_requires_exact_provider_studio_route(self) -> None:
        self.run_mutation(
            "README.md",
            "https://stele.monolythium.com/studio",
            "https://stele.monolythium.com/providers",
            "missing Stele status anchor 'https://stele.monolythium.com/studio'",
        )


if __name__ == "__main__":
    unittest.main()
