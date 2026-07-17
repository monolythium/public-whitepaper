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


FIFTH_REVIEW_CONTRADICTIONS = (
    (
        "Hosted Stele MCP has access to wallet secrets.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP keeps the seed phrase used to authorize payments.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP signs transfers before sending them to the network.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP can move funds from its service wallet.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Buyers buy services inside Provider Studio.",
        "booking or payment activity assigned to Provider Studio",
    ),
    (
        "Provider Studio transfers funds to providers.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "Provider Studio collects service fees.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "Provider Studio debits the buyer's wallet.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "Wallet login proves the account belongs to Alice.",
        "wallet authentication presented as identity proof",
    ),
    (
        "Wallet authentication verifies the person behind the address.",
        "wallet authentication presented as identity proof",
    ),
    (
        "Wallet authentication confirms wallet ownership.",
        "wallet authentication presented as identity proof",
    ),
    (
        "Provider accreditation follows from wallet login.",
        "identity proof assigned to wallet authentication",
    ),
    (
        "The login signature authenticates Alice.",
        "wallet authentication presented as identity proof",
    ),
    (
        "Hosted Stele MCP reads provider-listing drafts.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "Hosted Stele MCP updates provider-listing drafts.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "Provider-listing drafts are visible in the public catalog.",
        "provider-listing draft presented as public or executable",
    ),
    (
        "Provider Studio sends provider-listing drafts into the public catalog.",
        "Provider Studio presented as a publication or transaction surface",
    ),
    (
        "A booking-approval draft is a provider-listing draft.",
        "provider-listing and booking-approval drafts are conflated",
    ),
    (
        "A provider-listing draft doubles as a booking-approval draft.",
        "provider-listing and booking-approval drafts are conflated",
    ),
    (
        "The public web authors booking-approval drafts.",
        "public web claims booking-approval draft creation",
    ),
    (
        "Provider Studio produces booking-approval drafts.",
        "public web claims booking-approval draft creation",
    ),
    (
        "A published listing is optional for booking-draft preparation.",
        "booking-draft preparation claims no listing prerequisite",
    ),
    (
        "Booking-draft preparation works against unpublished listings.",
        "booking-draft preparation claims no listing prerequisite",
    ),
    (
        "Hosted booking-draft preparation does not depend on a published listing.",
        "booking-draft preparation claims no listing prerequisite",
    ),
    (
        "Stele ships inside the desktop wallet.",
        "Stele presented as embedded in the desktop wallet",
    ),
    (
        "The desktop wallet includes a Stele marketplace.",
        "Stele presented as embedded in the desktop wallet",
    ),
    (
        "Stele is built into Desktop Wallet.",
        "Stele presented as embedded in the desktop wallet",
    ),
    (
        "Desktop Wallet bundles Stele.",
        "Stele presented as embedded in the desktop wallet",
    ),
    (
        "Provider publication ships today.",
        "Stele provider publication incorrectly presented as enabled",
    ),
    (
        "Mainnet has launched.",
        "Stele mainnet incorrectly presented as enabled",
    ),
    (
        "Transaction signing works now.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "One service is published in the Stele catalog.",
        "Stele catalog claims a published service",
    ),
    (
        "A service is live in the public catalog.",
        "Stele catalog claims a published service",
    ),
    (
        "Hosted Stele MCP exposes a pair of tools plus status.",
        "hosted Stele MCP claims more than exactly two tools",
    ),
    (
        "Hosted Stele MCP exposes catalog search, booking-draft preparation, and status.",
        "hosted Stele MCP claims more than exactly two tools",
    ),
    (
        "Local Stele MCP adds a signing tool to its three read/status tools.",
        "local Stele MCP claims transaction capability",
    ),
    (
        "Use [Studio](https://evil.example/stele) for provider drafts.",
        "non-canonical Provider Studio URL",
    ),
    (
        "Provider Studio can be opened with [this link](javascript:alert(1)).",
        "non-canonical Provider Studio URL",
    ),
    (
        "Provider Studio destination is javascript:alert(1).",
        "non-canonical Provider Studio URL",
    ),
)

FIFTH_REVIEW_TRUTHFUL_CONTROLS = (
    "Booking-draft preparation is not available without a published listing.",
    "The public web never creates booking-approval drafts.",
    "Provider Studio refuses payments.",
    "Provider Studio blocks checkout.",
    "Provider Studio bars payments.",
    "Provider Studio neither accepts payments nor runs checkout.",
    "Hosted Stele MCP refuses to sign transactions.",
    "Hosted Stele MCP lacks signing authority.",
    "Hosted Stele MCP neither signs nor broadcasts transactions.",
    "Wallet authentication fails to establish legal identity.",
    "Wallet authentication rejects claims of legal identity.",
    "Hosted Stele MCP exposes exactly two tools, not three tools.",
    "A future Hosted Stele MCP may expose three tools only after a separate release.",
    "The retired Hosted Stele MCP exposed three tools.",
    "Stele has zero published services, not one published service.",
    "Provider Studio is not hosted at https://evil.example/studio.",
    "The retired Provider Studio was hosted at https://old.example/studio.",
    "Provider Studio documentation is at https://docs.monolythium.com/stele.",
)

SIXTH_REVIEW_CONTRADICTIONS = (
    (
        "Hosted Stele MCP does not sign transactions and holds private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP has no rate limit and holds private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP, which was deployed yesterday, holds private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP holds private keys and serves requests only after authentication.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Provider Studio has no payment controls and charges buyers.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "Provider Studio has no advertisements and charges buyers.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "Wallet login does not prove identity and confirms the account belongs to Alice.",
        "wallet authentication presented as identity proof",
    ),
    (
        "Wallet login, which was introduced yesterday, confirms the account belongs to Alice.",
        "wallet authentication presented as identity proof",
    ),
    (
        "Hosted Stele MCP does not create provider-listing drafts and reads provider-listing drafts.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "Provider-listing drafts are not transactable and are visible in the public catalog.",
        "provider-listing draft presented as public or executable",
    ),
    (
        "The public web never creates approval drafts and authors booking-approval drafts.",
        "public web claims booking-approval draft creation",
    ),
    (
        "A provider-listing draft is not a booking-approval draft and a provider-listing draft doubles as a booking-approval draft.",
        "provider-listing and booking-approval drafts are conflated",
    ),
    (
        "Provider Studio does not publish listings and sends provider-listing drafts into the public catalog.",
        "Provider Studio presented as a publication or transaction surface",
    ),
    (
        "Booking-draft preparation is unavailable for archived records and works without a published listing.",
        "booking-draft preparation claims no listing prerequisite",
    ),
    (
        "Stele is not in the browser wallet and ships inside the desktop wallet.",
        "Stele presented as embedded in the desktop wallet",
    ),
    (
        "Provider publication is gated and works now.",
        "Stele provider publication incorrectly presented as enabled",
    ),
    (
        "The statement “provider publication remains off” is obsolete: provider publication works now.",
        "Stele provider publication incorrectly presented as enabled",
    ),
    (
        "No service is published and a service is live in the public catalog.",
        "Stele catalog claims a published service",
    ),
    (
        "The catalog previously had zero published services and now has one published service.",
        "Stele catalog claims 1 published services; expected zero",
    ),
    (
        "Hosted Stele MCP previously exposed two tools and now exposes three tools.",
        "hosted Stele MCP claims 3 tools; expected exactly 2",
    ),
    (
        "Hosted Stele MCP has no third capability and exposes a pair of tools plus status.",
        "hosted Stele MCP claims more than exactly two tools",
    ),
    (
        "Local Stele MCP has no transaction tool and adds a signing tool.",
        "local Stele MCP claims transaction capability",
    ),
    (
        "Provider Studio is not at the retired URL and open [Provider Studio](https://evil.example/studio) now.",
        "non-canonical Provider Studio URL",
    ),
    (
        "Provider Studio documentation says the live product is [Provider Studio](https://evil.example/studio).",
        "non-canonical Provider Studio URL",
    ),
    (
        r"Provider Studio destination is https:\evil.example\studio.",
        "non-canonical Provider Studio URL",
    ),
    (
        "Provider Studio destination is mailto:attacker@example.com.",
        "non-canonical Provider Studio URL",
    ),
    (
        "Hosted Stele MCP cannot fail to sign transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Provider Studio does not refuse payments.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "Wallet login does not fail to prove the account belongs to Alice.",
        "wallet authentication presented as identity proof",
    ),
    (
        "Mainnet is no longer off.",
        "Stele mainnet incorrectly presented as enabled",
    ),
    (
        "The public catalog is no longer empty.",
        "catalog claims an indefinite live inventory",
    ),
    (
        "The public catalog now contains a service.",
        "catalog claims an indefinite live inventory",
    ),
    (
        "Hosted Stele MCP provides status in addition to its two OAuth-protected tools.",
        "hosted Stele MCP claims more than exactly two tools",
    ),
)

SIXTH_REVIEW_TRUTHFUL_CONTROLS = (
    "A future booking-draft preparation does not require a published listing.",
    "Retired booking-draft preparation does not depend on a published listing.",
    "A future public web cannot create any drafts.",
    "The retired public web cannot create any drafts.",
    "The false claim that Hosted Stele MCP holds private keys must be removed.",
    "The claim that Hosted Stele MCP exposes three tools is false.",
    "Hosted Stele MCP exposes exactly two tools rather than three tools.",
    "The assertion that Stele has one published service is false.",
    "Avoid [Provider Studio](https://evil.example/studio); use the canonical destination.",
    "The [Provider Studio](https://evil.example/studio) link is invalid.",
)

SIXTH_REVIEW_CONNECTOR_CONTRADICTIONS = tuple(
    (
        sample,
        "hosted Stele MCP claims transaction capability",
    )
    for sample in (
        "Hosted Stele MCP has no rate limit and holds private keys.",
        "Hosted Stele MCP has no rate limit, and holds private keys.",
        "Hosted Stele MCP has no rate limit but holds private keys.",
        "Hosted Stele MCP has no rate limit, but holds private keys.",
        "Hosted Stele MCP has no rate limit however holds private keys.",
        "Hosted Stele MCP has no rate limit yet holds private keys.",
        "Hosted Stele MCP has no rate limit, while it holds private keys.",
        "Hosted Stele MCP has no rate limit, whereas it holds private keys.",
        "Hosted Stele MCP has no rate limit, holds private keys.",
        "Hosted Stele MCP has no rate limit: it holds private keys.",
        "Hosted Stele MCP has no rate limit — it holds private keys.",
        "Hosted Stele MCP has no rate limit or holds private keys.",
        "Hosted Stele MCP, which was audited yesterday, holds private keys.",
        "Old docs said it was keyless: Hosted Stele MCP holds private keys.",
        "Hosted Stele MCP will publish metrics and holds private keys.",
        "Hosted Stele MCP holds private keys and publishes metrics only after auth.",
    )
)

SIXTH_REVIEW_URL_CONTRADICTIONS = tuple(
    (sample, "non-canonical Provider Studio URL")
    for sample in (
        "Use [Provider Studio](https://evil.example/studio).",
        "Open [Provider Studio](javascript:alert(1)).",
        "Provider Studio destination is javascript:alert(1).",
        "Provider Studio destination is data:text/html,boom.",
        "Provider Studio destination is /studio.",
        "Provider Studio destination is ./studio.",
        "Provider Studio destination is //stele.monolythium.com/studio.",
        "Provider Studio destination is stele.monolythium.com/studio.",
        "Provider Studio destination is #studio.",
        "Provider Studio destination is https://stele.monolythium.com/studio?next=1.",
        "Provider Studio destination is https://stele.monolythium.com/studio%2525252Fadmin.",
        "Provider Studio destination is https://stele.monolythium.com/studio%253Fnext=1.",
        "Use [Provider Studio][live].\n[live]: https://evil.example/studio",
        "Use [Provider Studio][live].\n[live]: /studio",
        "Provider Studio destination is ftp://evil.example/studio.",
        "Provider Studio destination is mailto:attacker@example.com.",
        'Use <a href="https://evil.example/studio">Provider Studio</a>.',
        "Use [Provider Studio][live].\n"
        "[live]: https://evil.example/studio\n"
        "[live]: https://stele.monolythium.com/studio",
        "Use [Provider Studio][live].\n"
        "[live]: https://stele.monolythium.com/studio\n"
        "[live]: https://evil.example/studio",
    )
)

SIXTH_REVIEW_URL_TRUTHFUL_CONTROLS = (
    "Use [Provider Studio](https://stele.monolythium.com/studio).",
    "Provider Studio is at https://stele.monolythium.com/studio.",
    "Use [Provider Studio][live].\n[live]: https://stele.monolythium.com/studio",
    "Provider Studio is not hosted at https://evil.example/studio.",
    "The retired Provider Studio was hosted at https://old.example/studio.",
    "Provider Studio documentation is at https://docs.example/studio.",
    "Avoid [Provider Studio](https://evil.example/studio).",
    "The [Provider Studio](https://evil.example/studio) link is invalid.",
)

PREDICATE_ATTRIBUTION_FRESH_CONTRADICTIONS = (
    (
        "Hosted Stele MCP that was audited yesterday holds private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP (which was audited yesterday) holds private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "After it was audited yesterday, Hosted Stele MCP holds private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP with no rate limit holds private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP holds private keys, with metrics available only after authentication.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP holds private keys (metrics are available only after authentication).",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Provider Studio with no advertisements charges buyers.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "Wallet login with no fee confirms the account belongs to Alice.",
        "wallet authentication presented as identity proof",
    ),
    (
        "Provider publication was documented yesterday as gated, but works now.",
        "Stele provider publication incorrectly presented as enabled",
    ),
    (
        "The catalog previously reported zero published services; it now has one published service.",
        "Stele catalog claims 1 published services; expected zero",
    ),
    (
        "Hosted Stele MCP previously reported two tools; it now exposes three tools.",
        "hosted Stele MCP claims 3 tools; expected exactly 2",
    ),
    (
        "The false alarm was cleared, and Hosted Stele MCP holds private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Although Hosted Stele MCP does not sign transactions, it holds private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP has no rate limit plus it holds private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP has no rate limit then it holds private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP has no rate limit / it holds private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP holds private keys, though metrics launch only after authentication.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP holds private keys even though metrics launch only after authentication.",
        "hosted Stele MCP claims transaction capability",
    ),
)

PREDICATE_ATTRIBUTION_FRESH_TRUTHFUL_CONTROLS = (
    "The retired Hosted Stele MCP that was audited yesterday held private keys.",
    "A future Hosted Stele MCP (which will be audited) could hold private keys after review.",
    "Hosted Stele MCP with no private keys serves catalog requests.",
    "Hosted Stele MCP holds no private keys, with metrics available only after authentication.",
    "Provider Studio with no advertisements refuses payments.",
    "Provider Studio does not accept, process, or settle payments.",
    "Wallet login with no fee does not confirm the account belongs to Alice.",
    "Provider publication remains gated, though metrics launch only after authentication.",
    "Hosted Stele MCP has no rate limit plus it refuses to sign transactions.",
    "Hosted Stele MCP neither holds nor stores private keys.",
    "Hosted Stele MCP could hold private keys only after activation.",
    "Hosted Stele MCP holds private keys only after activation.",
    "Hosted Stele MCP holds private keys, but only after activation.",
    "Hosted Stele MCP holds private keys, after activation.",
    "The false claim that Hosted Stele MCP holds private keys remains invalid.",
)

NEGATION_PARITY_FRESH_CONTRADICTIONS = (
    (
        "Hosted Stele MCP never fails to sign transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP does not lack signing authority.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP is not without private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Provider Studio cannot avoid charging buyers.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "Provider Studio never fails to collect payments.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "Wallet login cannot fail to confirm the account belongs to Alice.",
        "wallet authentication presented as identity proof",
    ),
    (
        "Provider publication is not unavailable now.",
        "Stele provider publication incorrectly presented as enabled",
    ),
    (
        "Mainnet is not off.",
        "Stele mainnet incorrectly presented as enabled",
    ),
    (
        "The public catalog is not empty.",
        "catalog claims an indefinite live inventory",
    ),
    (
        "Hosted Stele MCP does not lack a third tool.",
        "hosted Stele MCP claims more than exactly two tools",
    ),
    (
        "Stele does not have zero published services.",
        "Stele catalog denies zero published services; expected zero",
    ),
)

NEGATION_PARITY_FRESH_TRUTHFUL_CONTROLS = (
    "Hosted Stele MCP cannot sign transactions.",
    "Hosted Stele MCP never signs transactions.",
    "Hosted Stele MCP does not have signing authority.",
    "Hosted Stele MCP is without private keys.",
    "Provider Studio cannot charge buyers.",
    "Wallet login fails to confirm the account belongs to Alice.",
    "Provider publication is unavailable now.",
    "Mainnet is off.",
    "The public catalog is empty.",
    "Hosted Stele MCP exposes exactly two tools rather than three tools.",
    "Stele has zero published services.",
)

ATTRIBUTED_WARNING_FRESH_CONTRADICTIONS = (
    (
        "The warning is invalid: use [Provider Studio](https://evil.example/studio).",
        "non-canonical Provider Studio URL",
    ),
    (
        "The old URL is invalid, but [Provider Studio](https://evil.example/studio) is live.",
        "non-canonical Provider Studio URL",
    ),
    (
        "The false report was removed; Hosted Stele MCP holds private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "The claim was once false, but Hosted Stele MCP now holds private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
)

ATTRIBUTED_WARNING_FRESH_TRUTHFUL_CONTROLS = (
    "It is not true that Hosted Stele MCP holds private keys.",
    "The statement that Hosted Stele MCP holds private keys is not true.",
    "“Hosted Stele MCP holds private keys” is false.",
    "The statement “Hosted Stele MCP holds private keys” is incorrect.",
    "Never use [Provider Studio](https://evil.example/studio).",
    "Do not use [Provider Studio](https://evil.example/studio).",
    "[Provider Studio](https://evil.example/studio) should not be used.",
    "The deprecated [Provider Studio](https://evil.example/studio) link must be removed.",
    "The [Provider Studio](https://evil.example/studio) URL is unsafe.",
    "The claim that Hosted Stele MCP exposes three tools is not true.",
    "The assertion that Stele has one published service is incorrect.",
)

EXPLICIT_DESTINATION_FRESH_CONTRADICTIONS = tuple(
    (sample, "non-canonical Provider Studio URL")
    for sample in (
        "Provider Studio destination is jav%61script%3Aalert(1).",
        "Provider Studio destination is @attacker.",
        "Provider Studio route is evil.",
        "Provider Studio href: nonsense.",
    )
)

EXPLICIT_DESTINATION_FRESH_TRUTHFUL_CONTROLS = (
    "Provider Studio destination is https://stele.monolythium.com/studio.",
    "Provider Studio destination is not configured.",
    "A future Provider Studio destination is weird only after review.",
    "Provider Studio destination is [here](https://stele.monolythium.com/studio).",
    "Provider Studio documentation is at https://docs.example/studio.",
)

TYPED_COUNT_FRESH_CONTRADICTIONS = (
    (
        "One listing is published in the public catalog.",
        "Stele catalog claims a published service",
    ),
    (
        "A listing is live in the public catalog.",
        "Stele catalog claims a published service",
    ),
    (
        "The public catalog has an entry.",
        "catalog claims an indefinite live inventory",
    ),
    (
        "Hosted Stele MCP exposes two OAuth-protected tools plus status.",
        "hosted Stele MCP claims more than exactly two tools",
    ),
    (
        "Hosted Stele MCP has a third status capability alongside its two tools.",
        "hosted Stele MCP claims more than exactly two tools",
    ),
    (
        "Hosted Stele MCP tool count is three.",
        "hosted Stele MCP claims 3 tools; expected exactly 2",
    ),
    (
        "There are three tools in Hosted Stele MCP.",
        "hosted Stele MCP claims 3 tools; expected exactly 2",
    ),
    (
        "Local Stele MCP tool count is four.",
        "local Stele MCP claims 4 tools; expected exactly 3",
    ),
    (
        "There are four tools in Local Stele MCP.",
        "local Stele MCP claims 4 tools; expected exactly 3",
    ),
    (
        "Hosted Stele MCP exposes three endpoints.",
        "hosted Stele MCP claims 3 tools; expected exactly 2",
    ),
    (
        "Hosted Stele MCP exposes\nthree endpoints.",
        "hosted Stele MCP claims 3 tools; expected exactly 2",
    ),
    (
        "Hosted Stele MCP tool count is not two.",
        "hosted Stele MCP denies its required 2-tool surface",
    ),
    (
        "Local Stele MCP tool count is not three.",
        "local Stele MCP denies its required 3-tool surface",
    ),
    (
        "Hosted Stele MCP has no tools.",
        "hosted Stele MCP denies its required 2-tool surface",
    ),
    (
        "Local Stele MCP has no tools.",
        "local Stele MCP denies its required 3-tool surface",
    ),
    (
        "Hosted Stele MCP lacks tools.",
        "hosted Stele MCP denies its required 2-tool surface",
    ),
    (
        "Hosted Stele MCP has no tools beyond imagination.",
        "hosted Stele MCP denies its required 2-tool surface",
    ),
    (
        "Local Stele MCP lacks tools other than four tools.",
        "local Stele MCP denies its required 3-tool surface",
    ),
)

TYPED_COUNT_FRESH_TRUTHFUL_CONTROLS = (
    "Zero listings are published in the public catalog.",
    "No listing is live in the public catalog.",
    "The public catalog has no entries.",
    "Hosted Stele MCP exposes two endpoints.",
    "Hosted Stele MCP tool count is two.",
    "Local Stele MCP tool count is three.",
    "There are two tools in Hosted Stele MCP.",
    "There are three tools in Local Stele MCP.",
    "In a future release there are three tools in Hosted Stele MCP.",
    "The claim that there are three tools in Hosted Stele MCP is false.",
    "Hosted Stele MCP has no third status capability alongside its two tools.",
    "Hosted Stele MCP exposes exactly two tools. Another API exposes three tools.",
    "Hosted Stele MCP exposes exactly two tools; another API exposes three tools.",
    "Hosted Stele MCP exposes exactly two tools and another API exposes three tools.",
    "Hosted Stele MCP exposes exactly two tools, while the website exposes three tools.",
    "Hosted Stele MCP exposes exactly two tools.\nAnother API exposes three tools.",
    "Hosted Stele MCP tool count is not three.",
    "Local Stele MCP tool count is not two.",
    "Hosted Stele MCP has no third tool.",
    "The claim that Hosted Stele MCP tool count is not two is false.",
    "A future Hosted Stele MCP may have no tools before release.",
    "Hosted Stele MCP exposes exactly two tools. Another API has no tools.",
    "Hosted Stele MCP exposes exactly two tools. Another API tool count is not two.",
    "Hosted Stele MCP exposes exactly two tools. Another API tool count: not two.",
    "Hosted Stele MCP has no tools beyond the two OAuth-protected tools.",
    "Hosted Stele MCP lacks tools other than its two OAuth-protected tools.",
)

GATED_STATE_FRESH_CONTRADICTIONS = (
    (
        "Provider publication is no longer gated.",
        "Stele provider publication incorrectly presented as enabled",
    ),
    (
        "Transaction signing is no longer unavailable.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Economic writes are not disabled.",
        "Stele economic writes incorrectly presented as enabled",
    ),
    (
        "Mainnet is not gated.",
        "Stele mainnet incorrectly presented as enabled",
    ),
    (
        "Provider publication is open.",
        "Stele provider publication incorrectly presented as enabled",
    ),
    (
        "Transaction signing is ready.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Economic writes are permitted.",
        "Stele economic writes incorrectly presented as enabled",
    ),
    (
        "Mainnet is operational.",
        "Stele mainnet incorrectly presented as enabled",
    ),
    (
        "Provider publication isn't gated.",
        "Stele provider publication incorrectly presented as enabled",
    ),
    (
        "Transaction signing hasn't been unavailable.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Economic writes aren't disabled.",
        "Stele economic writes incorrectly presented as enabled",
    ),
    (
        "Mainnet has not been closed.",
        "Stele mainnet incorrectly presented as enabled",
    ),
)

GATED_STATE_FRESH_TRUTHFUL_CONTROLS = (
    "Provider publication remains gated.",
    "Transaction signing remains unavailable.",
    "Economic writes are disabled.",
    "Mainnet is gated.",
    "Provider publication is not open.",
    "Transaction signing is not ready.",
    "A future mainnet will be operational only after release.",
    "The retired prototype had open provider publication.",
    "The claim that transaction signing is ready is false.",
    "Economic writes are not permitted.",
    "Mainnet is not operational.",
    "Provider publication is open only after activation.",
    "Transaction signing is ready, but only after activation.",
    "Economic writes are not disabled only after activation.",
    "Mainnet isn't closed only after activation.",
)

GATED_STATE_MATRIX_CAPABILITIES = (
    (
        "Provider publication",
        "is",
        "Stele provider publication incorrectly presented as enabled",
    ),
    (
        "Transaction signing",
        "is",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Economic writes",
        "are",
        "Stele economic writes incorrectly presented as enabled",
    ),
    ("Mainnet", "is", "Stele mainnet incorrectly presented as enabled"),
)
GATED_STATE_MATRIX_ENABLED = (
    "on",
    "enabled",
    "live",
    "active",
    "available",
    "operational",
    "permitted",
    "open",
    "ready",
)
GATED_STATE_MATRIX_DISABLED = (
    "off",
    "gated",
    "unavailable",
    "disabled",
    "inactive",
    "closed",
    "blocked",
)
GATED_STATE_MATRIX_TIME_MODIFIERS = (
    "",
    "now ",
    "currently ",
    "today ",
    "already ",
    "presently ",
)


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
> Provider Studio at
> [stele.monolythium.com/studio](https://stele.monolythium.com/studio)
> can create, edit, preview, and delete
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
        self.assertIn(check_truth.CANONICAL_STUDIO_MARKDOWN_DESTINATION, current)
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

    def test_fifth_review_frozen_contradiction_corpus_is_rejected(self) -> None:
        for sample, expected in FIFTH_REVIEW_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_fifth_review_frozen_truthful_controls_are_allowed(self) -> None:
        for sample in FIFTH_REVIEW_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_sixth_review_frozen_contradiction_corpus_is_rejected(self) -> None:
        for sample, expected in SIXTH_REVIEW_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_sixth_review_frozen_truthful_controls_are_allowed(self) -> None:
        for sample in SIXTH_REVIEW_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_sixth_review_connector_corpus_is_rejected(self) -> None:
        for sample, expected in SIXTH_REVIEW_CONNECTOR_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_sixth_review_url_corpus_is_rejected(self) -> None:
        for sample, expected in SIXTH_REVIEW_URL_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_sixth_review_url_truthful_controls_are_allowed(self) -> None:
        for sample in SIXTH_REVIEW_URL_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_fresh_predicate_attribution_contradictions_are_rejected(self) -> None:
        for sample, expected in PREDICATE_ATTRIBUTION_FRESH_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_fresh_predicate_attribution_truthful_controls_are_allowed(self) -> None:
        for sample in PREDICATE_ATTRIBUTION_FRESH_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_fresh_negation_parity_contradictions_are_rejected(self) -> None:
        for sample, expected in NEGATION_PARITY_FRESH_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_fresh_negation_parity_truthful_controls_are_allowed(self) -> None:
        for sample in NEGATION_PARITY_FRESH_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_fresh_attributed_warning_contradictions_are_rejected(self) -> None:
        for sample, expected in ATTRIBUTED_WARNING_FRESH_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_fresh_attributed_warning_truthful_controls_are_allowed(self) -> None:
        for sample in ATTRIBUTED_WARNING_FRESH_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_fresh_explicit_destination_contradictions_are_rejected(self) -> None:
        for sample, expected in EXPLICIT_DESTINATION_FRESH_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_fresh_explicit_destination_truthful_controls_are_allowed(self) -> None:
        for sample in EXPLICIT_DESTINATION_FRESH_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_fresh_typed_count_contradictions_are_rejected(self) -> None:
        for sample, expected in TYPED_COUNT_FRESH_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_fresh_typed_count_truthful_controls_are_allowed(self) -> None:
        for sample in TYPED_COUNT_FRESH_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_fresh_gated_state_contradictions_are_rejected(self) -> None:
        for sample, expected in GATED_STATE_FRESH_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_fresh_gated_state_truthful_controls_are_allowed(self) -> None:
        for sample in GATED_STATE_FRESH_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_gated_state_cross_product_is_rejected(self) -> None:
        for capability, copula, expected in GATED_STATE_MATRIX_CAPABILITIES:
            contraction = "aren't" if copula == "are" else "isn't"
            perfect = "have" if copula == "are" else "has"
            for state in GATED_STATE_MATRIX_ENABLED:
                for modifier in GATED_STATE_MATRIX_TIME_MODIFIERS:
                    sample = f"{capability} {copula} {modifier}{state}."
                    with self.subTest(sample=sample):
                        self.assert_contradiction(sample, expected)
            for state in GATED_STATE_MATRIX_DISABLED:
                samples = (
                    f"{capability} {copula} not {state}.",
                    f"{capability} {copula} no longer {state}.",
                    f"{capability} {contraction} {state}.",
                    f"{capability} {perfect} not been {state}.",
                )
                for sample in samples:
                    with self.subTest(sample=sample):
                        self.assert_contradiction(sample, expected)

    def test_gated_state_cross_product_truthful_controls_are_allowed(self) -> None:
        for capability, copula, _ in GATED_STATE_MATRIX_CAPABILITIES:
            for state in GATED_STATE_MATRIX_DISABLED:
                sample = f"{capability} {copula} {state}."
                with self.subTest(sample=sample):
                    self.assertEqual(
                        [], check_truth.stele_status_contradictions(sample)
                    )
            for state in GATED_STATE_MATRIX_ENABLED:
                samples = (
                    f"{capability} {copula} not {state}.",
                    f"{capability} {copula} {state} only after activation.",
                )
                for sample in samples:
                    with self.subTest(sample=sample):
                        self.assertEqual(
                            [], check_truth.stele_status_contradictions(sample)
                        )

    def test_subordinate_history_does_not_mask_a_current_claim(self) -> None:
        samples = (
            "Hosted Stele MCP stores private keys that were generated offline.",
            "Provider Studio charges customers who were previously approved.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertNotEqual([], check_truth.stele_status_contradictions(sample))

    def test_hosted_transaction_capability_paraphrases_are_rejected(self) -> None:
        samples = (
            "Hosted Stele MCP can sign and broadcast transactions.",
            "Hosted MCP broadcasts signed transactions.",
            "Hosted Stele MCP supports transaction submission.",
            "Hosted MCP offers hosted signing.",
            "Hosted Stele MCP has wallet custody.",
            "Hosted Stele MCP signs wallet payloads and sends them on-chain.",
            "Hosted Stele MCP exposes a transaction signer.",
            "Hosted Stele MCP performs signing and broadcast.",
            "Hosted Stele MCP relays signed transactions.",
            "Hosted Stele MCP is a transaction signer.",
            "Hosted Stele MCP has a transaction tool.",
            "Hosted Stele MCP includes transaction signing.",
            "Hosted Stele MCP possesses a transaction tool.",
            "Hosted Stele MCP handles transaction signing.",
            "Hosted Stele MCP can authorize transactions.",
            "Hosted Stele MCP holds signing authority.",
            "Hosted Stele MCP controls a transaction signer.",
            "Hosted Stele MCP generates transaction signatures.",
            "Hosted Stele MCP has transaction authorization.",
            "Hosted Stele MCP handles transactions.",
            "Hosted Stele MCP owns private keys.",
            "Hosted Stele MCP maintains transaction signing capability.",
            "Hosted Stele MCP creates signed transactions.",
            "Hosted Stele MCP produces transaction signatures.",
            "Hosted Stele MCP operates a transaction signer.",
            "Hosted Stele MCP fabricates signed transactions.",
            "Hosted Stele MCP powers transaction signing.",
            "Hosted Stele MCP is able to create signed transactions.",
            "Hosted Stele MCP is capable of signing transactions.",
            "Hosted Stele MCP performs signatures.",
            "Hosted Stele MCP is responsible for transaction signing.",
            "Hosted Stele MCP is the signer for wallet transactions.",
            "Hosted Stele MCP serves as the wallet signer.",
            "Hosted Stele MCP maintains a hot wallet.",
            "Hosted Stele MCP is in charge of wallet signing.",
            "Hosted Stele MCP keeps a custodial wallet.",
            "Hosted Stele MCP is transaction-capable.",
            "Hosted Stele MCP signs requests.",
            "Hosted Stele MCP is used to sign transactions.",
            "Hosted Stele MCP is a signing service.",
            "Hosted Stele MCP runs a hot wallet.",
            "Hosted Stele MCP is custodial.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "hosted Stele MCP claims transaction capability"
                )

    def test_reverse_hosted_transaction_capability_claims_are_rejected(self) -> None:
        samples = (
            "Transactions are signed by Hosted Stele MCP.",
            "Transaction signing occurs in Hosted Stele MCP.",
            "Transactions are signed at Hosted Stele MCP.",
            "Transaction signing occurs on Hosted Stele MCP.",
            "Transactions are authorized within Hosted Stele MCP.",
            "Transaction signatures originate via Hosted Stele MCP.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "transaction capability assigned to hosted Stele MCP"
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
            (
                "The public web lets providers publish listings.",
                "public web claims provider-publication authority",
            ),
            (
                "The public web has a Publish listing button.",
                "public web claims provider-publication authority",
            ),
            (
                "The public web accepts bookings.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "The public web lets users book and pay.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "The public web processes payments and settles bookings.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "The public web contains payment controls.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "The public web processes bookings.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "The public web operates payment workflows.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "The public web runs payment workflows.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "The public web takes bookings.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio processes payments.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio hosts booking and payment workflows.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio collects payments.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Customers can book and pay in Provider Studio.",
                "booking or payment activity assigned to Provider Studio",
            ),
            (
                "Provider Studio conducts payment workflows.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "The public web performs booking workflows.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio accepts payments.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio creates bookings.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Bookings and payments happen in Provider Studio.",
                "booking or payment state assigned to Provider Studio",
            ),
            (
                "Provider Studio is able to accept payments.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Visitors pay in Provider Studio.",
                "booking or payment activity assigned to Provider Studio",
            ),
            (
                "Payments flow through Provider Studio.",
                "booking or payment state assigned to Provider Studio",
            ),
            (
                "Provider Studio is a payment processor.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Payments are accepted by Provider Studio.",
                "booking or payment state assigned to Provider Studio",
            ),
            (
                "Checkout happens in Provider Studio.",
                "booking or payment state assigned to Provider Studio",
            ),
            (
                "Provider Studio is where payments are accepted.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Payments are handled via Provider Studio.",
                "booking or payment state assigned to Provider Studio",
            ),
            (
                "Provider Studio serves as a checkout platform.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio processes checkout.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio is a payment gateway.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio charges customers.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio is where customers pay.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio functions as a settlement handler.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio bills users.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio is the place where buyers purchase.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Orders are processed inside Provider Studio.",
                "booking or payment state assigned to Provider Studio",
            ),
            (
                "Provider Studio is a checkout.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Customers are charged in Provider Studio.",
                "booking or payment activity assigned to Provider Studio",
            ),
            (
                "Users get billed through Provider Studio.",
                "booking or payment activity assigned to Provider Studio",
            ),
            (
                "Provider Studio acts as a merchant.",
                "public web claims booking, payment, settlement, or economic controls",
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
            "Browser Wallet confirms the user’s identity.",
            "Wallet authentication certifies legal identity.",
            "That authentication demonstrates ownership.",
            "Browser Wallet proves who the user is.",
            "Browser Wallet authenticates the user’s legal identity.",
            "Wallet authentication attests the user’s identity.",
            "Browser Wallet validates the user’s legal identity.",
            "Wallet authentication is proof of legal identity.",
            "Wallet authentication guarantees provider credentials.",
            "That authentication identifies who the user is.",
            "Wallet login proves legal identity.",
            "The wallet-auth proof validates provider credentials.",
            "Wallet authentication verifies that the provider is licensed.",
            "Wallet authentication serves as proof of legal identity.",
            "Browser Wallet asserts legal identity.",
            "Wallet authentication verifies the provider licence.",
            "The login signature proves legal identity.",
            "Wallet authentication proves that the provider is accredited.",
            "Wallet login indicates legal identity.",
            "The login signature shows accredited provider status.",
            "Wallet authentication is sufficient KYC.",
            "Wallet authentication suffices for KYC.",
            "Wallet authentication satisfies KYC.",
            "Wallet authentication is adequate for KYC.",
            "Wallet authentication meets KYC.",
            "Wallet authentication is valid KYC.",
            "Wallet authentication passes KYC.",
            "Wallet authentication counts as KYC.",
            "Wallet authentication provides KYC verification.",
            "Wallet authentication is KYC-compliant.",
            "Wallet authentication clears KYC.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "wallet authentication presented as identity proof"
                )

    def test_reverse_wallet_identity_overclaims_are_rejected(self) -> None:
        samples = (
            "Legal identity is proven by wallet authentication.",
            "Provider credentials are verified by wallet login.",
            "KYC is satisfied via wallet login.",
            "Provider credentials come from wallet login.",
            "Know-your-customer is completed through Browser Wallet authentication.",
            "Provider accreditation derives from the wallet signature.",
            "KYC relies on wallet login.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "identity proof assigned to wallet authentication"
                )

    def test_retired_economic_preview_claim_is_rejected(self) -> None:
        self.assert_contradiction(
            "Economic actions remain user-approved previews.",
            "retired economic-preview claim",
        )

    def test_noncanonical_provider_studio_urls_are_rejected(self) -> None:
        samples = (
            "https://stele.monolythium.com/providers",
            "http://stele.monolythium.com/studio",
            "https://stele.monolythium.com/studio/evil",
            "https://stele.monolythium.com/studio?draft=private",
            "https://stele.monolythium.com/studio#draft=private",
            "https://stele.monolythium.com/studio%2Fadmin",
            "//stele.monolythium.com/providers",
            "https://stele.monolythium.com/%73tudio",
            "https://stele.monolythium.com/s%74udio",
            "https://stele.monolythium.com/%2573tudio",
            "https://stele.monolythium.com:443/studio",
            "https://example.com/studio",
            "/studio",
            "stele.monolythium.com/providers",
            "stele.monolythium.com",
            "./studio",
            "https://stele.monolythium.com/%25252573tudio",
            "#studio",
            "#providers",
            "https://example.org/market",
            "/market",
            "example.org/market",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    f"Provider Studio is at {sample}.",
                    "non-canonical Provider Studio URL",
                )
        self.assert_contradiction(
            "Provider Studio: #studio.",
            "non-canonical Provider Studio URL",
        )

    def test_arbitrarily_nested_encoded_studio_path_is_rejected(self) -> None:
        nested_path = "%" + ("25" * 64) + "73tudio"
        self.assert_contradiction(
            f"https://stele.monolythium.com/{nested_path}",
            "non-canonical Provider Studio URL",
        )

    def test_historical_future_gated_and_negative_copy_is_allowed(self) -> None:
        samples = (
            "Hosted Stele MCP does not sign or broadcast transactions.",
            "A future Hosted Stele MCP could support transaction signing after a separate release.",
            "Hosted Stele MCP does not sign wallet payloads or send them on-chain.",
            "A future Hosted Stele MCP could expose a transaction signer after review.",
            "A future Hosted Stele MCP could perform signing and broadcast after activation.",
            "The retired Hosted Stele MCP exposed a transaction signer.",
            "Hosted Stele MCP signing and broadcast remain separately gated.",
            "Hosted Stele MCP is not a transaction signer.",
            "Hosted Stele MCP has no transaction tool.",
            "Hosted Stele MCP does not include transaction signing.",
            "A future Hosted Stele MCP could include transaction signing after review.",
            "The retired Hosted Stele MCP included transaction signing.",
            "Hosted Stele MCP does not possess a transaction tool.",
            "A future Hosted Stele MCP could possess a transaction tool after review.",
            "The retired Hosted Stele MCP possessed a transaction tool.",
            "Hosted Stele MCP transaction authorization remains separately gated.",
            "Hosted Stele MCP does not hold signing authority.",
            "A future Hosted Stele MCP could control a transaction signer after review.",
            "The retired Hosted Stele MCP generated transaction signatures.",
            "Hosted Stele MCP signing authority remains separately gated.",
            "Hosted Stele MCP does not own private keys.",
            "A future Hosted Stele MCP could handle transactions after activation.",
            "The retired Hosted Stele MCP maintained transaction signing capability.",
            "Hosted Stele MCP does not create signed transactions.",
            "Hosted Stele MCP doesn't create signed transactions.",
            "A future Hosted Stele MCP could produce transaction signatures after activation.",
            "The retired Hosted Stele MCP operated a transaction signer.",
            "Hosted Stele MCP transaction-signature generation remains separately gated.",
            "Hosted Stele MCP does not fabricate signed transactions.",
            "A future Hosted Stele MCP will power transaction signing only after activation.",
            "The retired Hosted Stele MCP fabricated signed transactions.",
            "Hosted Stele MCP is not capable of signing transactions.",
            "A future Hosted Stele MCP could be capable of signing transactions after release.",
            "The retired Hosted Stele MCP was capable of signing transactions.",
            "Transactions are not signed by Hosted Stele MCP.",
            "Future transactions will be signed by Hosted Stele MCP only after activation.",
            "Transactions were signed by the retired Hosted Stele MCP.",
            "Transaction signing remains gated in Hosted Stele MCP.",
            "Hosted Stele MCP does not perform signatures.",
            "Hosted Stele MCP never performs signatures.",
            "A future Hosted Stele MCP will perform signatures only after activation.",
            "The retired Hosted Stele MCP performed signatures.",
            "Hosted Stele MCP is not responsible for transaction signing.",
            "A future Hosted Stele MCP will be responsible for transaction signing only after activation.",
            "The retired Hosted Stele MCP was responsible for transaction signing.",
            "Transactions are not signed at Hosted Stele MCP.",
            "Future transactions will be signed at Hosted Stele MCP only after activation.",
            "Transactions were signed at the retired Hosted Stele MCP.",
            "Transaction signing remains unavailable on Hosted Stele MCP.",
            "Hosted Stele MCP is not the signer for wallet transactions.",
            "Hosted Stele MCP never serves as the wallet signer.",
            "Hosted Stele MCP never acts as the transaction signer.",
            "A future Hosted Stele MCP will be the wallet signer only after activation.",
            "The retired Hosted Stele MCP served as the wallet signer.",
            "Hosted Stele MCP does not maintain a hot wallet.",
            "A future Hosted Stele MCP will maintain a hot wallet only after activation.",
            "The retired Hosted Stele MCP maintained a hot wallet.",
            "Hosted Stele MCP is not in charge of wallet signing.",
            "A future Hosted Stele MCP could keep a custodial wallet after activation.",
            "Transaction signatures do not originate via Hosted Stele MCP.",
            "Hosted Stele MCP is not transaction-capable.",
            "A future Hosted Stele MCP will be transaction-capable only after activation.",
            "The retired Hosted Stele MCP was transaction-capable.",
            "Hosted Stele MCP does not sign requests.",
            "Hosted Stele MCP never signs requests.",
            "A future Hosted Stele MCP will sign requests only after activation.",
            "The retired Hosted Stele MCP signed requests.",
            "Hosted Stele MCP is not used to sign transactions.",
            "A future Hosted Stele MCP will be used to sign transactions only after activation.",
            "The retired Hosted Stele MCP was used to sign transactions.",
            "Hosted Stele MCP is not a signing service.",
            "A future Hosted Stele MCP will be a signing service only after activation.",
            "The retired Hosted Stele MCP was a signing service.",
            "Hosted Stele MCP does not run a hot wallet.",
            "A future Hosted Stele MCP will run a hot wallet only after activation.",
            "The retired Hosted Stele MCP ran a hot wallet.",
            "Hosted Stele MCP is not custodial.",
            "A future Hosted Stele MCP will be custodial only after activation.",
            "The retired Hosted Stele MCP was custodial.",
            "The public web exposes no booking, payment, settlement, or other economic controls.",
            "The public web will support payments only after protocol activation.",
            "The retired public web used to offer payment controls.",
            "The public web does not accept bookings or process payments.",
            "The public web does not process bookings or operate payment workflows.",
            "The public web processes booking-approval draft records for read-only inspection.",
            "The public web has no Publish listing button.",
            "A future public web may let providers publish listings after activation.",
            "A future public web will operate payment workflows only after activation.",
            "The retired public web accepted bookings.",
            "The retired public web processed bookings and operated payment workflows.",
            "The public web does not run payment workflows or take bookings.",
            "A future public web will run payment workflows only after activation.",
            "The retired public web ran payment workflows and took bookings.",
            "Provider Studio does not process payments.",
            "Provider Studio payment processing remains off.",
            "Provider Studio does not host booking or payment workflows.",
            "Provider Studio does not collect payments.",
            "A future Provider Studio will host payment workflows only after activation.",
            "The retired Provider Studio collected payments.",
            "Customers cannot book or pay in Provider Studio.",
            "Customers could book in a future Provider Studio after activation.",
            "Provider Studio does not conduct payment workflows.",
            "A future public web may perform booking workflows after activation.",
            "The retired Provider Studio conducted payment workflows.",
            "Provider Studio does not accept payments or create bookings.",
            "Provider Studio doesn't accept payments.",
            "A future Provider Studio will create bookings only after activation.",
            "The retired Provider Studio accepted payments.",
            "Bookings do not happen in Provider Studio.",
            "Future bookings could happen in Provider Studio only after activation.",
            "Bookings happened in the retired Provider Studio.",
            "Booking-approval draft records are inspected in Provider Studio.",
            "Visitors cannot pay in Provider Studio.",
            "Future visitors will pay in Provider Studio only after activation.",
            "The retired clients paid in Provider Studio.",
            "Payments do not flow through Provider Studio.",
            "Provider Studio is not a payment processor.",
            "A future Provider Studio could be a payment processor after activation.",
            "The retired Provider Studio was a payment processor.",
            "Payments are not accepted by Provider Studio.",
            "Future payments will be accepted by Provider Studio only after activation.",
            "Payments were accepted by the retired Provider Studio.",
            "Checkout remains unavailable in Provider Studio.",
            "Provider Studio is not where payments are accepted.",
            "A future Provider Studio will be where payments are accepted only after activation.",
            "The retired Provider Studio was where payments were accepted.",
            "Payments are not handled via Provider Studio.",
            "Future payments will be handled via Provider Studio only after activation.",
            "Payments were handled via the retired Provider Studio.",
            "Provider Studio does not serve as a checkout platform.",
            "A future Provider Studio could serve as a checkout platform after activation.",
            "The retired Provider Studio served as a checkout platform.",
            "Provider Studio does not process checkout.",
            "A future Provider Studio will process checkout only after activation.",
            "The retired Provider Studio processed checkout.",
            "Provider Studio is not a payment gateway.",
            "A future Provider Studio could be a payment gateway after activation.",
            "The retired Provider Studio was a payment gateway.",
            "Provider Studio does not charge customers.",
            "Provider Studio never charges customers.",
            "A future Provider Studio will charge customers only after activation.",
            "The retired Provider Studio charged customers.",
            "Provider Studio is where customers cannot pay.",
            "A future Provider Studio will be where customers pay only after activation.",
            "The retired Provider Studio was where customers paid.",
            "Provider Studio does not function as a settlement handler.",
            "A future Provider Studio will bill users only after activation.",
            "Provider Studio is the place where buyers cannot purchase.",
            "Orders are not processed inside Provider Studio.",
            "Provider Studio is not a checkout.",
            "A future Provider Studio will be a checkout only after activation.",
            "The retired Provider Studio was a checkout.",
            "Customers are not charged in Provider Studio.",
            "Future customers will be charged in Provider Studio only after activation.",
            "Customers were charged in the retired Provider Studio.",
            "Users do not get billed through Provider Studio.",
            "Future users will get billed through Provider Studio only after activation.",
            "Users got billed through the retired Provider Studio.",
            "Provider Studio does not act as a merchant.",
            "A future Provider Studio could act as a merchant after activation.",
            "The retired Provider Studio acted as a merchant.",
            "Provider publication could be available through a future public web after release.",
            "Wallet authentication does not prove human identity or authority.",
            "Browser Wallet does not confirm the user's identity.",
            "Browser Wallet does not authenticate the user's legal identity.",
            "Wallet authentication does not attest the user's identity.",
            "A future Browser Wallet could authenticate legal identity after a separate release.",
            "The retired Browser Wallet authenticated legal identity.",
            "A future wallet could certify credentials only after a separate identity release.",
            "The retired Browser Wallet claimed to confirm identity.",
            "Browser Wallet does not validate the user's legal identity.",
            "Wallet authentication is not proof of legal identity.",
            "A future wallet authentication could constitute proof after a separate release.",
            "A future wallet authentication could guarantee provider credentials after review.",
            "The retired wallet authentication guaranteed provider credentials.",
            "That authentication does not identify who the user is.",
            "Wallet-authentication legal-identity validation remains separately gated.",
            "Wallet login does not prove legal identity.",
            "A future wallet login could prove legal identity after a separate release.",
            "The retired wallet login proved legal identity.",
            "The wallet-auth proof does not validate provider credentials.",
            "Wallet authentication does not verify that the provider is licensed.",
            "Wallet-login legal-identity proof remains separately gated.",
            "Wallet authentication does not serve as proof of legal identity.",
            "A future Browser Wallet could assert legal identity after a separate release.",
            "The retired Browser Wallet asserted legal identity.",
            "Wallet authentication does not verify the provider licence.",
            "A future login signature could prove legal identity after a separate release.",
            "The retired login signature proved legal identity.",
            "Wallet authentication does not prove that the provider is accredited.",
            "Login-signature legal-identity proof remains separately gated.",
            "Wallet login does not indicate legal identity.",
            "A future login signature could show accredited provider status after review.",
            "The retired wallet login indicated legal identity.",
            "Legal identity is not proven by wallet authentication.",
            "Future legal identity could be proven by wallet login after a separate release.",
            "Legal identity was proven by the retired wallet login.",
            "Provider credentials remain gated through wallet login.",
            "Wallet authentication is not sufficient KYC.",
            "A future wallet authentication could be sufficient for KYC after review.",
            "The retired wallet authentication was sufficient KYC.",
            "Wallet authentication does not suffice for KYC.",
            "A future wallet authentication will suffice for KYC only after review.",
            "The retired wallet authentication sufficed for KYC.",
            "Wallet authentication does not satisfy KYC.",
            "A future wallet authentication will satisfy KYC only after review.",
            "The retired wallet authentication satisfied KYC.",
            "Wallet authentication is not adequate for KYC.",
            "A future wallet authentication could be adequate for KYC after review.",
            "The retired wallet authentication was adequate for KYC.",
            "KYC is not satisfied via wallet login.",
            "Future KYC will be satisfied via wallet login only after review.",
            "KYC was satisfied via the retired wallet login.",
            "Provider credentials do not come from wallet login.",
            "Future provider credentials will come from wallet login only after review.",
            "Provider credentials came from the retired wallet login.",
            "Wallet authentication does not meet KYC.",
            "A future wallet authentication will meet KYC only after review.",
            "Know-your-customer is not completed through Browser Wallet authentication.",
            "Provider accreditation does not derive from the wallet signature.",
            "Wallet authentication does not pass KYC.",
            "A future wallet authentication will pass KYC only after review.",
            "The retired wallet authentication passed KYC.",
            "Wallet authentication does not count as KYC.",
            "A future wallet authentication will count as KYC only after review.",
            "The retired wallet authentication counted as KYC.",
            "Wallet authentication does not provide KYC verification.",
            "A future wallet authentication will provide KYC verification only after review.",
            "The retired wallet authentication provided KYC verification.",
            "Wallet authentication is not KYC-compliant.",
            "A future wallet authentication will be KYC-compliant only after review.",
            "The retired wallet authentication was KYC-compliant.",
            "Wallet authentication does not clear KYC.",
            "A future wallet authentication will clear KYC only after review.",
            "The retired wallet authentication cleared KYC.",
            "KYC does not rely on wallet login.",
            "Future KYC will rely on wallet login only after review.",
            "KYC relied on the retired wallet login.",
            "Provider Studio documentation discusses issue #123.",
            "Provider Studio contact is studio@stele.monolythium.com.",
            "A retired prototype described economic previews as user-approved.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))


class SteleTruthMainBlackBoxTests(unittest.TestCase):
    """Mutate copies of real public documents and exercise the CLI entry point."""

    def run_check(
        self,
        relative: str,
        old: str,
        new: str,
    ) -> tuple[int, str, str]:
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

            return result, stdout.getvalue(), stderr.getvalue()

    def run_append_check(self, addition: str) -> tuple[int, str, str]:
        """Replay the frozen reviewer method without removing any correct anchor."""
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

            target = root / "2026/may/monolythium-whitepaper-v5.0.md"
            original = target.read_text(encoding="utf-8")
            target.write_text(original + "\n\n" + addition + "\n", encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.multiple(
                check_truth,
                ROOT=root,
                DOCUMENTS=tuple(root / path for path in document_relatives),
                STELE_STATUS_DOCUMENTS=tuple(root / path for path in status_relatives),
            ), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = check_truth.main()

            return result, stdout.getvalue(), stderr.getvalue()

    def run_mutation(
        self,
        relative: str,
        old: str,
        new: str,
        expected_error: str,
    ) -> None:
        result, stdout, stderr = self.run_check(relative, old, new)
        self.assertEqual(1, result, msg=stdout)
        self.assertIn(expected_error, stderr)

    def run_allowed_mutation(self, relative: str, old: str, new: str) -> None:
        result, stdout, stderr = self.run_check(relative, old, new)
        self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_rejects_fifth_review_frozen_contradiction_corpus(self) -> None:
        for sample, expected in FIFTH_REVIEW_CONTRADICTIONS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_allows_fifth_review_frozen_truthful_controls(self) -> None:
        for sample in FIFTH_REVIEW_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_rejects_sixth_review_frozen_contradiction_corpus(self) -> None:
        for sample, expected in SIXTH_REVIEW_CONTRADICTIONS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_allows_sixth_review_frozen_truthful_controls(self) -> None:
        for sample in SIXTH_REVIEW_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_rejects_sixth_review_connector_corpus(self) -> None:
        for sample, expected in SIXTH_REVIEW_CONNECTOR_CONTRADICTIONS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_rejects_sixth_review_url_corpus(self) -> None:
        for sample, expected in SIXTH_REVIEW_URL_CONTRADICTIONS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_allows_sixth_review_url_truthful_controls(self) -> None:
        for sample in SIXTH_REVIEW_URL_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_rejects_fresh_predicate_attribution_corpus(self) -> None:
        for sample, expected in PREDICATE_ATTRIBUTION_FRESH_CONTRADICTIONS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_allows_fresh_predicate_attribution_truthful_controls(self) -> None:
        for sample in PREDICATE_ATTRIBUTION_FRESH_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_rejects_fresh_negation_parity_corpus(self) -> None:
        for sample, expected in NEGATION_PARITY_FRESH_CONTRADICTIONS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_allows_fresh_negation_parity_truthful_controls(self) -> None:
        for sample in NEGATION_PARITY_FRESH_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_rejects_fresh_attributed_warning_corpus(self) -> None:
        for sample, expected in ATTRIBUTED_WARNING_FRESH_CONTRADICTIONS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_allows_fresh_attributed_warning_truthful_controls(self) -> None:
        for sample in ATTRIBUTED_WARNING_FRESH_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_rejects_fresh_explicit_destination_corpus(self) -> None:
        for sample, expected in EXPLICIT_DESTINATION_FRESH_CONTRADICTIONS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_allows_fresh_explicit_destination_truthful_controls(self) -> None:
        for sample in EXPLICIT_DESTINATION_FRESH_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_rejects_fresh_typed_count_corpus(self) -> None:
        for sample, expected in TYPED_COUNT_FRESH_CONTRADICTIONS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_allows_fresh_typed_count_truthful_controls(self) -> None:
        for sample in TYPED_COUNT_FRESH_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_rejects_fresh_gated_state_corpus(self) -> None:
        for sample, expected in GATED_STATE_FRESH_CONTRADICTIONS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_allows_fresh_gated_state_truthful_controls(self) -> None:
        for sample in GATED_STATE_FRESH_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(0, result, msg=stderr or stdout)

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
            "missing exact Provider Studio Markdown destination "
            f"{check_truth.CANONICAL_STUDIO_MARKDOWN_DESTINATION!r}",
        )

    def test_main_rejects_every_second_review_truth_bypass(self) -> None:
        samples = (
            (
                "Hosted Stele MCP signs wallet payloads and sends them on-chain.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP exposes a transaction signer.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP performs signing and broadcast.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP relays signed transactions.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "The public web lets providers publish listings.",
                "public web claims provider-publication authority",
            ),
            (
                "The public web has a Publish listing button.",
                "public web claims provider-publication authority",
            ),
            (
                "The public web accepts bookings.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "The public web lets users book and pay.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "The public web processes payments and settles bookings.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "The public web contains payment controls.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Economic actions remain user-approved previews.",
                "retired economic-preview claim",
            ),
            (
                "Browser Wallet confirms the user’s identity.",
                "wallet authentication presented as identity proof",
            ),
            (
                "Wallet authentication certifies legal identity.",
                "wallet authentication presented as identity proof",
            ),
            (
                "That authentication demonstrates ownership.",
                "wallet authentication presented as identity proof",
            ),
            (
                "Browser Wallet proves who the user is.",
                "wallet authentication presented as identity proof",
            ),
        )
        for sample, expected in samples:
            with self.subTest(sample=sample):
                self.run_mutation(
                    "README.md",
                    "Economic writes, transaction signing, and mainnet remain off.",
                    "Economic writes, transaction signing, and mainnet remain off. "
                    + sample,
                    expected,
                )

    def test_main_rejects_noncanonical_provider_studio_destinations(self) -> None:
        destinations = (
            "https://stele.monolythium.com/providers",
            "http://stele.monolythium.com/studio",
            "https://stele.monolythium.com/studio/evil",
            "https://stele.monolythium.com/studio?draft=private",
            "https://stele.monolythium.com/studio#draft=private",
            "https://stele.monolythium.com/studio%2Fadmin",
            "//stele.monolythium.com/providers",
            "https://stele.monolythium.com/%73tudio",
            "https://stele.monolythium.com/s%74udio",
            "https://stele.monolythium.com/%2573tudio",
            "https://stele.monolythium.com:443/studio",
            "https://example.com/studio",
            "/studio",
            "stele.monolythium.com/providers",
            "./studio",
            "https://stele.monolythium.com/%25252573tudio",
            "#studio",
        )
        for destination in destinations:
            with self.subTest(destination=destination):
                self.run_mutation(
                    "README.md",
                    "Economic writes, transaction signing, and mainnet remain off.",
                    "Economic writes, transaction signing, and mainnet remain off. "
                    f"Provider Studio is also at {destination}.",
                    "non-canonical Provider Studio URL",
                )

    def test_main_rejects_every_latest_review_truth_bypass(self) -> None:
        samples = (
            (
                "Hosted Stele MCP possesses a transaction tool.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP handles transaction signing.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP can authorize transactions.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "The public web runs payment workflows.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "The public web takes bookings.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio processes payments.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Browser Wallet validates the user’s legal identity.",
                "wallet authentication presented as identity proof",
            ),
            (
                "Wallet authentication is proof of legal identity.",
                "wallet authentication presented as identity proof",
            ),
            (
                "Wallet authentication guarantees provider credentials.",
                "wallet authentication presented as identity proof",
            ),
            (
                "That authentication identifies who the user is.",
                "wallet authentication presented as identity proof",
            ),
        )
        for sample, expected in samples:
            with self.subTest(sample=sample):
                self.run_mutation(
                    "README.md",
                    "Economic writes, transaction signing, and mainnet remain off.",
                    "Economic writes, transaction signing, and mainnet remain off. "
                    + sample,
                    expected,
                )

    def test_main_rejects_independent_redteam_truth_bypasses(self) -> None:
        samples = (
            (
                "Hosted Stele MCP holds signing authority.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP controls a transaction signer.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP generates transaction signatures.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Provider Studio hosts booking and payment workflows.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio collects payments.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Customers can book and pay in Provider Studio.",
                "booking or payment activity assigned to Provider Studio",
            ),
            (
                "Wallet login proves legal identity.",
                "wallet authentication presented as identity proof",
            ),
            (
                "The wallet-auth proof validates provider credentials.",
                "wallet authentication presented as identity proof",
            ),
            (
                "Wallet authentication verifies that the provider is licensed.",
                "wallet authentication presented as identity proof",
            ),
        )
        for sample, expected in samples:
            with self.subTest(sample=sample):
                self.run_mutation(
                    "README.md",
                    "Economic writes, transaction signing, and mainnet remain off.",
                    "Economic writes, transaction signing, and mainnet remain off. "
                    + sample,
                    expected,
                )

    def test_main_rejects_second_independent_redteam_truth_bypasses(self) -> None:
        samples = (
            (
                "Hosted Stele MCP creates signed transactions.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP produces transaction signatures.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP operates a transaction signer.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Provider Studio accepts payments.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio creates bookings.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Bookings and payments happen in Provider Studio.",
                "booking or payment state assigned to Provider Studio",
            ),
            (
                "Wallet authentication verifies the provider licence.",
                "wallet authentication presented as identity proof",
            ),
            (
                "The login signature proves legal identity.",
                "wallet authentication presented as identity proof",
            ),
            (
                "Wallet authentication proves that the provider is accredited.",
                "wallet authentication presented as identity proof",
            ),
        )
        for sample, expected in samples:
            with self.subTest(sample=sample):
                self.run_mutation(
                    "README.md",
                    "Economic writes, transaction signing, and mainnet remain off.",
                    "Economic writes, transaction signing, and mainnet remain off. "
                    + sample,
                    expected,
                )

    def test_main_rejects_third_independent_redteam_truth_bypasses(self) -> None:
        samples = (
            (
                "Hosted Stele MCP is capable of signing transactions.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Transactions are signed by Hosted Stele MCP.",
                "transaction capability assigned to hosted Stele MCP",
            ),
            (
                "Transaction signing occurs in Hosted Stele MCP.",
                "transaction capability assigned to hosted Stele MCP",
            ),
            (
                "Provider Studio is a payment processor.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Payments are accepted by Provider Studio.",
                "booking or payment state assigned to Provider Studio",
            ),
            (
                "Checkout happens in Provider Studio.",
                "booking or payment state assigned to Provider Studio",
            ),
            (
                "Legal identity is proven by wallet authentication.",
                "identity proof assigned to wallet authentication",
            ),
            (
                "Provider credentials are verified by wallet login.",
                "identity proof assigned to wallet authentication",
            ),
            (
                "Wallet authentication is sufficient KYC.",
                "wallet authentication presented as identity proof",
            ),
        )
        for sample, expected in samples:
            with self.subTest(sample=sample):
                self.run_mutation(
                    "README.md",
                    "Economic writes, transaction signing, and mainnet remain off.",
                    "Economic writes, transaction signing, and mainnet remain off. "
                    + sample,
                    expected,
                )

    def test_main_rejects_fourth_independent_redteam_truth_bypasses(self) -> None:
        samples = (
            (
                "Hosted Stele MCP performs signatures.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Transactions are signed at Hosted Stele MCP.",
                "transaction capability assigned to hosted Stele MCP",
            ),
            (
                "Transaction signing occurs on Hosted Stele MCP.",
                "transaction capability assigned to hosted Stele MCP",
            ),
            (
                "Hosted Stele MCP is responsible for transaction signing.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Provider Studio is where payments are accepted.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Payments are handled via Provider Studio.",
                "booking or payment state assigned to Provider Studio",
            ),
            (
                "Provider Studio serves as a checkout platform.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio processes checkout.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Wallet authentication suffices for KYC.",
                "wallet authentication presented as identity proof",
            ),
            (
                "Wallet authentication satisfies KYC.",
                "wallet authentication presented as identity proof",
            ),
            (
                "KYC is satisfied via wallet login.",
                "identity proof assigned to wallet authentication",
            ),
            (
                "Provider credentials come from wallet login.",
                "identity proof assigned to wallet authentication",
            ),
            (
                "Hosted Stele MCP is the signer for wallet transactions.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP serves as the wallet signer.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP maintains a hot wallet.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Provider Studio is a payment gateway.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio charges customers.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Provider Studio is where customers pay.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Wallet authentication is adequate for KYC.",
                "wallet authentication presented as identity proof",
            ),
        )
        for sample, expected in samples:
            with self.subTest(sample=sample):
                self.run_mutation(
                    "README.md",
                    "Economic writes, transaction signing, and mainnet remain off.",
                    "Economic writes, transaction signing, and mainnet remain off. "
                    + sample,
                    expected,
                )

    def test_main_allows_fourth_review_safe_control_matrix(self) -> None:
        samples = (
            "Hosted Stele MCP does not perform signatures.",
            "A future Hosted Stele MCP will be responsible for transaction signing only after activation.",
            "The retired Hosted Stele MCP served as the wallet signer.",
            "Hosted Stele MCP does not maintain a hot wallet.",
            "Transactions are not signed at Hosted Stele MCP.",
            "Provider Studio is not where payments are accepted.",
            "Future payments will be handled via Provider Studio only after activation.",
            "The retired Provider Studio served as a checkout platform.",
            "Provider Studio does not process checkout.",
            "Provider Studio is not a payment gateway.",
            "A future Provider Studio will charge customers only after activation.",
            "Provider Studio is where customers cannot pay.",
            "Wallet authentication does not suffice for KYC.",
            "A future wallet authentication will satisfy KYC only after review.",
            "The retired wallet authentication was adequate for KYC.",
            "KYC is not satisfied via wallet login.",
            "Future provider credentials will come from wallet login only after review.",
            "Provider Studio documentation discusses issue #123.",
            "Provider Studio is at https://stele.monolythium.com/studio.",
        )
        self.run_allowed_mutation(
            "README.md",
            "Economic writes, transaction signing, and mainnet remain off.",
            "Economic writes, transaction signing, and mainnet remain off.\n"
            + "\n".join(samples),
        )

    def test_main_rejects_reference_and_url_before_label_studio_links(self) -> None:
        samples = (
            "[Provider Studio][entry]\n[entry]: https://example.com/studio",
            "Visit https://example.com/studio for the Provider Studio.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.run_mutation(
                    "README.md",
                    "Economic writes, transaction signing, and mainnet remain off.",
                    "Economic writes, transaction signing, and mainnet remain off.\n"
                    + sample,
                    "non-canonical Provider Studio URL",
                )

    def test_main_allows_exact_canonical_studio_link_forms(self) -> None:
        samples = (
            "[Provider Studio](https://stele.monolythium.com/studio)",
            "Provider Studio is at https://stele.monolythium.com/studio.",
            "[Provider Studio][entry]\n[entry]: https://stele.monolythium.com/studio",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.run_allowed_mutation(
                    "README.md",
                    "Economic writes, transaction signing, and mainnet remain off.",
                    "Economic writes, transaction signing, and mainnet remain off.\n"
                    + sample,
                )

    def test_main_allows_nonproduct_studio_link_contexts(self) -> None:
        samples = (
            "[Provider Studio](https://evil.example/studio) is not the current product destination.",
            "The retired [Provider Studio](https://old.example/studio) was a historical link.",
            "See [Provider Studio documentation](https://docs.example/studio) for the guide.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.run_allowed_mutation(
                    "README.md",
                    "Economic writes, transaction signing, and mainnet remain off.",
                    "Economic writes, transaction signing, and mainnet remain off.\n"
                    + sample,
                )

    def test_main_rejects_every_third_review_truth_bypass(self) -> None:
        samples = (
            (
                "Hosted Stele MCP is a transaction signer.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP has a transaction tool.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP includes transaction signing.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "The public web processes bookings.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "The public web operates payment workflows.",
                "public web claims booking, payment, settlement, or economic controls",
            ),
            (
                "Browser Wallet authenticates the user’s legal identity.",
                "wallet authentication presented as identity proof",
            ),
            (
                "Wallet authentication attests the user’s identity.",
                "wallet authentication presented as identity proof",
            ),
        )
        for sample, expected in samples:
            with self.subTest(sample=sample):
                self.run_mutation(
                    "README.md",
                    "Economic writes, transaction signing, and mainnet remain off.",
                    "Economic writes, transaction signing, and mainnet remain off. "
                    + sample,
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
