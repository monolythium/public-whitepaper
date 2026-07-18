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


EXACT_HISTORICAL_STUDIO_CONTROL = "In 2024, [Provider Studio](https://old.example/studio) was live before it was retired."
EXACT_DOCUMENTARY_BLEED_REJECT = "Provider Studio documentation is at [the docs](https://docs.example/studio). Open [Provider Studio](https://evil.example/studio) now."
EXACT_RETIRED_RELAUNCHED_REJECT = "The [Provider Studio](https://evil.example/studio) was retired, then relaunched today."
EXACT_HISTORY_REOPENED_REJECT = "In 2024, [Provider Studio](https://evil.example/studio) was live before retirement; it reopened today."
EXACT_DISTINCT_API_CONTROL = "In 2024, [Provider Studio](https://old.example/studio) was live before it was retired. The API was repaired, but it is now live."
EXACT_PRIOR_TO_RETIREMENT_CONTROL = "In 2024, [Provider Studio](https://old.example/studio) was live prior to being retired."
EXACT_UNTIL_DECOMMISSION_CONTROL = "In 2024, [Provider Studio](https://old.example/studio) was live until it was decommissioned."
EXACT_REVERSE_EDIT_REJECT = "Providers can [edit their draft](https://evil.example/edit) in Provider Studio."
EXACT_PREFIX_REVISE_REJECT = "In Provider Studio, providers [revise their draft](https://evil.example/edit)."
EXACT_REVERSE_MANAGE_REJECT = "Providers can now [manage their provider draft](https://wrong.example/studio) in Provider Studio"
EXACT_ADJACENT_OPEN_REJECT = "Provider Studio is live today. [Open the Studio](https://wrong.example/studio)."
EXACT_QUOTED_REJECTION_CONTROL = "The warning rejects the claim “[Provider Studio](https://wrong.example/studio) is live today.”"
EXACT_DISTINCT_PORTAL_CONTROL = "In 2024, [Provider Studio](https://old.example/studio) was live before it was retired, while customers now use [the customer portal](https://accounts.example/portal)."
EXACT_STRUCTURAL_HEADING_REJECT = "## Provider Studio is live today\n\n- [Open the Studio](https://evil.example/launch)"
EXACT_STRUCTURAL_IMAGE_REJECT = "Provider Studio is live today.\n[![Open the Studio](button.png)](https://evil.example/launch)."
EXACT_HISTORICAL_RANGE_CONTROL = "In 2019, [Provider Studio](https://old.example/studio) went live and stayed online until its retirement in 2021."
EXACT_NATURAL_DISAVOWAL_CONTROL = "The review says the sentence “[Provider Studio](https://wrong.example/studio) is public now” is false."


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
        "hosted Stele MCP presents an unconditional third capability",
    ),
    (
        "Hosted Stele MCP exposes catalog search, booking-draft preparation, and status.",
        "hosted Stele MCP presents an unconditional third capability",
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
    "Authenticated tools/list is the inventory authority for Hosted Stele MCP.",
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
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Hosted Stele MCP has no third capability and exposes a pair of tools plus status.",
        "hosted Stele MCP presents an unconditional third capability",
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
        "hosted Stele MCP presents an unconditional third capability",
    ),
)

SIXTH_REVIEW_TRUTHFUL_CONTROLS = (
    "A future booking-draft preparation does not require a published listing.",
    "Retired booking-draft preparation does not depend on a published listing.",
    "A future public web cannot create any drafts.",
    "The retired public web cannot create any drafts.",
    "The false claim that Hosted Stele MCP holds private keys must be removed.",
    "The claim that Hosted Stele MCP exposes three tools is false.",
    "Authenticated tools/list is authoritative for the Hosted Stele MCP inventory.",
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
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
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
        "hosted Stele MCP presents an unconditional third capability",
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
    "Authenticated tools/list is authoritative for the Hosted Stele MCP inventory.",
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
        "hosted Stele MCP presents an unconditional third capability",
    ),
    (
        "Hosted Stele MCP has a third status capability alongside its two tools.",
        "hosted Stele MCP presents an unconditional third capability",
    ),
    (
        "Hosted Stele MCP tool count is three.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "There are three tools in Hosted Stele MCP.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
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
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Hosted Stele MCP exposes\nthree endpoints.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Hosted Stele MCP tool count is not two.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Local Stele MCP tool count is not three.",
        "local Stele MCP denies its required 3-tool surface",
    ),
    (
        "Hosted Stele MCP has no tools.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Local Stele MCP has no tools.",
        "local Stele MCP denies its required 3-tool surface",
    ),
    (
        "Hosted Stele MCP lacks tools.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Hosted Stele MCP has no tools beyond imagination.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "There are exactly two tools in Hosted Stele MCP.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Hosted Stele MCP lacks tools other than its two OAuth-protected tools.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Hosted Stele MCP inventory consists of exactly two tools.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Exactly two tools are available through Hosted Stele MCP.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Hosted Stele MCP tool count is not three.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Hosted Stele MCP does not expose three tools.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Hosted Stele MCP has no third tool.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Hosted Stele MCP does not have a third tool.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Hosted Stele MCP is without a third tool.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Two tools are not available through Hosted Stele MCP.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Exactly two tools are unavailable through Hosted Stele MCP.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "No third tool exists in Hosted Stele MCP.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "No tools are available through Hosted Stele MCP.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
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
    "Local Stele MCP tool count is three.",
    "There are three tools in Local Stele MCP.",
    "In a future release there are three tools in Hosted Stele MCP.",
    "The claim that there are three tools in Hosted Stele MCP is false.",
    "Hosted Stele MCP uses authenticated tools/list as its inventory authority.",
    "Authenticated tools/list, not a static total, defines the Hosted Stele MCP inventory.",
    "Hosted Stele MCP serves catalog search. Another API exposes three tools.",
    "Hosted Stele MCP serves booking-draft preparation; another API exposes three tools.",
    "Hosted Stele MCP serves catalog search and another API exposes three tools.",
    "Hosted Stele MCP serves catalog search, while the website exposes three tools.",
    "Hosted Stele MCP serves catalog search.\nAnother API exposes three tools.",
    "Local Stele MCP tool count is not two.",
    "The claim that Hosted Stele MCP tool count is not two is false.",
    "In 2024, no third tool existed in Hosted Stele MCP.",
    "The claim that no third tool exists in Hosted Stele MCP is false.",
    "A future Hosted Stele MCP may have no tools before release.",
    "Hosted Stele MCP serves catalog search. Another API has no tools.",
    "Hosted Stele MCP serves catalog search. Another API tool count is not two.",
    "Hosted Stele MCP serves catalog search. Another API tool count: not two.",
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

INDEPENDENT_REREVIEW_CONTRADICTIONS = (
    (
        "Hosted Stele MCP is creating transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP is building transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP is live. It creates transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP does not fail to create transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP can't fail to create transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP isn't unable to create transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "There are two listings in the public catalog.",
        "Stele catalog claims 2 listings; expected zero",
    ),
    (
        "There is a pair of listings in the public catalog.",
        "Stele catalog claims 2 listings; expected zero",
    ),
    (
        "There are a couple of listings in the public catalog.",
        "Stele catalog claims 2 listings; expected zero",
    ),
    (
        "Transaction signing is generally available.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Use [Provider Studio][].\n"
        "[Provider Studio]: https://evil.example/studio",
        "non-canonical Provider Studio URL",
    ),
    (
        "Published listings are optional for booking-draft preparation.",
        "booking-draft preparation claims no listing prerequisite",
    ),
    (
        "Desktop Wallet has Stele.",
        "Stele presented as embedded in the desktop wallet",
    ),
    (
        "Escrow is managed by Provider Studio.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
)

INDEPENDENT_REREVIEW_TRUTHFUL_CONTROLS = (
    "Warning: if Hosted Stele MCP creates transactions, stop the release.",
    "In the next release, Hosted Stele MCP creates transactions.",
    "Hosted Stele MCP serves catalog, but the mobile wallet creates transactions.",
    "Hosted Stele MCP has zero transaction tools.",
)

INDEPENDENT_REREVIEW_VARIATION_CONTRADICTIONS = (
    (
        "Hosted Stele MCP is currently creating transaction payloads.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP remains actively building transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP is operational. This service builds transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP is available! The MCP is signing transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP cannot fail to construct transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP is not unable to submit transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "There exist three public listings in the Stele catalog.",
        "Stele catalog claims 3 listings; expected zero",
    ),
    (
        "There is one published service listing in the public catalog.",
        "Stele catalog claims 1 listings; expected zero",
    ),
    (
        "Transaction signing is broadly available.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Transaction signing is publicly operational.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Open [Provider Studio][].\n"
        "[provider studio]: /studio",
        "non-canonical Provider Studio URL",
    ),
    (
        "Use [Provider Studio][].",
        "non-canonical Provider Studio URL",
    ),
    (
        "A published service listing remains optional for booking-draft preparation.",
        "booking-draft preparation claims no listing prerequisite",
    ),
    (
        "Desktop Wallet has the Stele marketplace.",
        "Stele presented as embedded in the desktop wallet",
    ),
    (
        "The desktop wallet currently has Stele.",
        "Stele presented as embedded in the desktop wallet",
    ),
    (
        "Escrow management is currently handled by Provider Studio.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "Escrow operations are run by Provider Studio.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "Hosted Stele MCP has one signing tool.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP exposes two OAuth tools and one signing tool.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP serves catalog. Its wallet creates transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP serves catalog. The wallet creates transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP serves catalog, but the service creates transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP isn't without a transaction tool.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP isn’t without signing authority.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "A pair of listings exists in the public catalog.",
        "Stele catalog claims 2 listings; expected zero",
    ),
    (
        "A couple of listings exists in the public catalog.",
        "Stele catalog claims 2 listings; expected zero",
    ),
    (
        "A pair of listings is present in the public catalog.",
        "Stele catalog claims 2 listings; expected zero",
    ),
    (
        "Hosted Stele MCP serves catalog. The service's wallet signs transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP serves catalog. Its service wallet builds transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP isn't without a broadcast tool.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "A trio of listings appears within the Stele catalog.",
        "Stele catalog claims 3 listings; expected zero",
    ),
    (
        "One listing is available inside the public catalog.",
        "Stele catalog claims 1 listings; expected zero",
    ),
    (
        "Hosted Stele MCP serves catalog. The hosted service creates transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP serves catalog. The hosted service's wallet creates transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP is not lacking a transaction tool.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP isn't lacking a transaction tool.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP can't avoid signing transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Two listings are presently available on the public catalog.",
        "Stele catalog claims 2 listings; expected zero",
    ),
    (
        "A pair of listings can be found within the public catalog.",
        "Stele catalog claims 2 listings; expected zero",
    ),
    (
        "Hosted Stele MCP acts as the operator. The operator wallet signs transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP is the provider. The provider's wallet creates transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP is an auditor, and the auditor-owned wallet creates transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP serves catalog. The public hosted service creates transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP serves catalog. The hosted wallet's signer creates transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP is never unable to create transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP is never without signing authority.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP is no longer without signing authority.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP never avoids signing transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP serves catalog. It is never unable to create transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP serves catalog. It has a transaction tool.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP is the operator. The operator wallet is never unable to create transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "There is one pair of listings in the public catalog.",
        "Stele catalog claims 2 listings; expected zero",
    ),
    (
        "There are two pairs of listings in the public catalog.",
        "Stele catalog claims 4 listings; expected zero",
    ),
    (
        "There are currently two listings in the public catalog.",
        "Stele catalog claims 2 listings; expected zero",
    ),
    (
        "There currently are two listings in the public catalog.",
        "Stele catalog claims 2 listings; expected zero",
    ),
    (
        "Inside the public catalog are two listings.",
        "Stele catalog claims 2 listings; expected zero",
    ),
    (
        "There aren't zero listings in the public catalog.",
        "Stele catalog denies zero listings; expected zero",
    ),
    (
        "There are no longer zero listings in the public catalog.",
        "Stele catalog denies zero listings; expected zero",
    ),
    (
        "The public catalog doesn't contain zero listings.",
        "Stele catalog denies zero listings; expected zero",
    ),
)

INDEPENDENT_REREVIEW_VARIATION_TRUTHFUL_CONTROLS = (
    "Hosted Stele MCP is not creating transactions.",
    "The retired Hosted Stele MCP was creating transactions.",
    "Hosted Stele MCP is live. It does not create transactions.",
    "Hosted Stele MCP is live. It creates transactions in the next release.",
    "Security warning — if Hosted Stele MCP creates transactions, stop the release.",
    "Deployment caution: unless Hosted Stele MCP creates transactions, continue the release.",
    "Next release, Hosted Stele MCP creates transactions.",
    "In the upcoming release, Hosted Stele MCP builds transactions.",
    "Hosted Stele MCP serves catalog, but the user wallet creates transactions.",
    "Hosted Stele MCP serves catalog, while the buyer wallet builds transactions.",
    "Hosted Stele MCP serves catalog, but the provider wallet creates transactions.",
    "Hosted Stele MCP serves catalog, while the customer wallet builds transactions.",
    "Hosted Stele MCP serves catalog, but the provider's wallet creates transactions.",
    "Hosted Stele MCP serves catalog, but a customer-controlled wallet builds transactions.",
    "Hosted Stele MCP serves catalog, but a role-specific wallet signs transactions.",
    "Hosted Stele MCP serves catalog, but a provider-owned wallet creates transactions.",
    "Hosted Stele MCP serves catalog, but an externally-controlled wallet signs transactions.",
    "Hosted Stele MCP serves catalog, but a third-party wallet builds transactions.",
    "Hosted Stele MCP serves catalog, but a separate wallet signs transactions.",
    "Hosted Stele MCP serves catalog, but the auditor's wallet creates transactions.",
    "Hosted Stele MCP serves catalog, but a treasury wallet creates transactions.",
    "Hosted Stele MCP serves catalog, but the administrator wallet creates transactions.",
    "Hosted Stele MCP serves catalog, but the developer's wallet creates transactions.",
    "Hosted Stele MCP serves catalog, but a custodian-controlled wallet creates transactions.",
    "Hosted Stele MCP serves catalog, but an external wallet creates transactions.",
    "Hosted Stele MCP serves catalog, but a hardware wallet creates transactions.",
    "Hosted Stele MCP serves catalog, but a self-custodial wallet creates transactions.",
    "Hosted Stele MCP serves catalog, but the customer's browser wallet creates transactions.",
    "Hosted Stele MCP serves catalog, but an external wallet is never unable to create transactions.",
    "Hosted Stele MCP serves catalog, but the administrator wallet is not without signing authority.",
    "Hosted Stele MCP serves catalog. It has a transaction tool warning.",
    "A future Hosted Stele MCP will launch. It creates transactions.",
    "The retired Hosted Stele MCP served catalog. It creates transactions.",
    "A future Hosted Stele MCP will be the operator. The operator wallet signs transactions.",
    "Hosted Stele MCP is without a transaction tool.",
    "Hosted Stele MCP operates without a transaction tool.",
    "A pair of listings does not exist within the public catalog.",
    "Hosted Stele MCP has zero signing tools.",
    "Hosted Stele MCP has no transaction tools.",
    "There are zero listings in the public catalog.",
    "Transaction signing is generally unavailable.",
    "Use [Provider Studio][].\n"
    "[provider studio]: https://stele.monolythium.com/studio",
    "Avoid [Provider Studio][].\n"
    "[provider studio]: https://evil.example/studio",
    "Published listings are not optional for booking-draft preparation.",
    "Desktop Wallet has no Stele marketplace.",
    "A future Desktop Wallet will have Stele only after release.",
    "Escrow is not managed by Provider Studio.",
    "Escrow is managed by another service, not Provider Studio.",
    "Hosted Stele MCP documents a transaction tool restriction.",
    "Hosted Stele MCP displays a transaction tool warning.",
    "Hosted Stele MCP has a transaction tool prohibition.",
    "Hosted Stele MCP is not lacking a transaction tool prohibition.",
    "Hosted Stele MCP documents a transaction tool's restriction.",
    "Hosted Stele MCP does not lack documentation for a transaction tool.",
    "Hosted Stele MCP has documentation for a transaction tool.",
    "Hosted Stele MCP has a restriction and a transaction tool warning.",
    "Two listings are hypothetical examples, while zero listings are present in the public catalog.",
    "A pair of listings appears in the public catalog documentation as a hypothetical example.",
)


CONDITIONAL_AUTHORITY_REREVIEW_CONTRADICTIONS = (
    (
        "stele_create_provider_listing_draft exists even when its exact name is absent from authenticated tools/list.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Hosted Stele MCP provides provider-listing draft creation.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Provider-listing draft creation is available through Hosted Stele MCP.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Hosted Stele MCP provides existing provider-listing draft deletion.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "stele_create_provider_listing_draft reads an existing provider-listing draft.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "stele_create_provider_listing_draft deletes an existing provider-listing draft.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "stele_create_provider_listing_draft publishes an existing provider-listing draft.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "stele_create_provider_listing_draft signs a transaction.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "stele_create_provider_listing_draft broadcasts a transaction.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Clients may invoke stele_create_provider_listing_draft without seeing it in authenticated tools/list.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Hosted Stele MCP exposes stele_create_provider_draft.",
        "hosted MCP exposes a noncanonical provider-draft tool name",
    ),
    (
        "Hosted Stele MCP offers provider-listing draft creation.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Hosted Stele MCP supports creation of provider-listing drafts.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Hosted Stele MCP enables clients to create provider-listing drafts.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Hosted Stele MCP is keyless. It provides provider-listing draft creation.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Provider-listing draft creation is supported via Hosted Stele MCP.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Provider-listing drafts may be created through Hosted Stele MCP.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Hosted Stele MCP offers deletion of existing provider-listing drafts.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "Existing provider-listing draft deletion is provided by Hosted Stele MCP.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "Existing provider-listing drafts may be read through Hosted Stele MCP.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "stele_create_provider_listing_draft may delete an existing provider-listing draft.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "stele_create_provider_listing_draft creates a provider-listing draft.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "A provider-listing draft is created by stele_create_provider_listing_draft.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "stele_create_provider_listing_draft is available now.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Users can invoke stele_create_provider_listing_draft.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "When authenticated tools/list includes stele_create_provider_listing_draft, the tool is available. It deletes an existing provider-listing draft.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "When authenticated tools/list includes stele_create_provider_listing_draft, it is available. The tool signs a transaction.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "A transaction may be signed by stele_create_provider_listing_draft.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Transaction broadcast is available through stele_create_provider_listing_draft.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP is keyless. It exposes stele_create_provider_draft.",
        "hosted MCP exposes a noncanonical provider-draft tool name",
    ),
    (
        "stele_create_provider_draft is available through Hosted Stele MCP.",
        "hosted MCP exposes a noncanonical provider-draft tool name",
    ),
    (
        "When authenticated tools/list includes stele_create_provider_draft, Hosted Stele MCP exposes stele_create_provider_draft.",
        "hosted MCP exposes a noncanonical provider-draft tool name",
    ),
    (
        "Hosted Stele MCP creates a new provider-listing draft.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "A new provider-listing draft is created by Hosted Stele MCP.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Provider-listing draft creation is possible through Hosted Stele MCP.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Hosted Stele MCP is keyless. It creates a new provider-listing draft.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Hosted Stele MCP is permitted to create provider-listing drafts.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Hosted Stele MCP could create provider-listing drafts today.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "stele_create_provider_listing_draft permits deletion of an existing provider-listing draft.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "Transaction signing is possible through stele_create_provider_listing_draft.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Clients can invoke stele_create_provider_draft through Hosted Stele MCP.",
        "hosted MCP exposes a noncanonical provider-draft tool name",
    ),
    (
        "When authenticated tools/list includes stele_create_listing_draft, Hosted Stele MCP exposes stele_create_listing_draft for provider-listing draft creation.",
        "hosted MCP exposes a noncanonical provider-draft tool name",
    ),
    (
        "Hosted Stele MCP supports deleting existing provider-listing drafts.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "stele_create_provider_listing_draft supports transaction signing.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP is authorized to create provider-listing drafts.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Provider-listing drafts are allowed to be created through Hosted Stele MCP.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Hosted Stele MCP is keyless. Its API authors provider-listing drafts.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "stele_create_provider_draft can be invoked through Hosted Stele MCP.",
        "hosted MCP exposes a noncanonical provider-draft tool name",
    ),
    (
        "When authenticated tools/list includes STELE_CREATE_PROVIDER_LISTING_DRAFT, Hosted Stele MCP exposes STELE_CREATE_PROVIDER_LISTING_DRAFT.",
        "hosted MCP exposes a noncanonical provider-draft tool name",
    ),
    (
        "Existing provider-listing drafts are readable through Hosted Stele MCP.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "stele_create_provider_listing_draft permits transaction signing.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "In 2026, Hosted Stele MCP exposes exactly two tools.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Hosted Stele MCP has permission to create provider-listing drafts.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Users have permission to create provider-listing drafts through Hosted Stele MCP.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "When authenticated tools/list includes STELE_CREATE_PROVIDER_LISTING_DRAFT, Hosted Stele MCP provides provider-listing draft creation.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
)

CONDITIONAL_AUTHORITY_REREVIEW_TRUTHFUL_CONTROLS = (
    "stele_create_provider_listing_draft exists only when that exact name appears in authenticated tools/list.",
    "When authenticated tools/list includes stele_create_provider_listing_draft, Hosted Stele MCP provides provider-listing draft creation.",
    "Hosted Stele MCP provides provider-listing draft creation only when authenticated tools/list includes stele_create_provider_listing_draft.",
    "After authenticated tools/list returns stele_create_provider_listing_draft, Hosted Stele MCP supports provider-listing draft creation.",
    "Clients may invoke stele_create_provider_listing_draft unless its exact name is absent from authenticated tools/list.",
    "When listed, stele_create_provider_listing_draft creates exactly one new private wallet-owned unpublished provider-listing draft.",
    "When authenticated tools/list includes stele_create_provider_listing_draft, it is available. When listed, the tool creates exactly one new private wallet-owned unpublished provider-listing draft.",
    "Hosted Stele MCP does not provide provider-listing draft creation.",
    "Provider-listing draft creation is unavailable through Hosted Stele MCP.",
    "Hosted Stele MCP does not provide deletion of existing provider-listing drafts.",
    "stele_create_provider_listing_draft cannot read, delete, or publish an existing provider-listing draft.",
    "stele_create_provider_listing_draft does not sign or broadcast a transaction.",
    "Clients cannot invoke stele_create_provider_listing_draft unless it appears in authenticated tools/list.",
    "Hosted Stele MCP does not expose stele_create_provider_draft.",
    "A future Hosted Stele MCP may provide provider-listing draft creation after release.",
    "In 2025, Hosted Stele MCP provided provider-listing draft creation.",
    "The retired Hosted Stele MCP provided provider-listing draft creation.",
    "The archived Hosted Stele MCP exposed stele_create_provider_draft.",
    "The claim “Hosted Stele MCP provides provider-listing draft creation” is false.",
    "The warning rejects the claim “stele_create_provider_listing_draft signs a transaction.”",
    "The integration test for Hosted Stele MCP exposes stele_create_provider_draft.",
    "Hosted Stele MCP fixture exposes stele_create_provider_draft.",
    "An idempotent replay never creates another draft.",
    "An idempotent replay cannot create another draft.",
    "Historically, Hosted Stele MCP exposed exactly two tools.",
    "In 2025, Hosted Stele MCP exposed exactly two tools.",
    "The archived Hosted Stele MCP exposed exactly two tools.",
    "Whenever authenticated tools/list includes stele_create_provider_listing_draft, Hosted Stele MCP provides provider-listing draft creation.",
    "The presence of stele_create_provider_listing_draft in authenticated tools/list is required before Hosted Stele MCP provides provider-listing draft creation.",
    "Upon a future activation, Hosted Stele MCP provides provider-listing draft creation.",
    "In 2027, Hosted Stele MCP provides provider-listing draft creation.",
    "As of 2025, Hosted Stele MCP provides provider-listing draft creation.",
    "We deny that Hosted Stele MCP provides provider-listing draft creation.",
    "A regression fixture says Hosted Stele MCP exposes stele_create_provider_draft.",
    "Hosted Stele MCP provides provider-listing draft creation so long as authenticated tools/list includes stele_create_provider_listing_draft.",
    "Starting in 2027, Hosted Stele MCP exposes stele_create_provider_draft.",
    "Until 2025, Hosted Stele MCP provides provider-listing draft creation.",
    "Through 2025, Hosted Stele MCP provides provider-listing draft creation.",
    "Scheduled for 2027, Hosted Stele MCP exposes stele_create_provider_draft.",
    "We disavow the claim that Hosted Stele MCP exposes stele_create_provider_draft.",
    "A unit test asserts Hosted Stele MCP exposes stele_create_provider_draft.",
)


FINAL_TRANSITION_REVIEW_CONTRADICTIONS = (
    (
        "Clients invoke stele_create_provider_listing_draft through Hosted Stele MCP.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "When authenticated tools/list does not include "
        "stele_create_provider_listing_draft, Hosted Stele MCP provides "
        "provider-listing draft creation.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "When authenticated tools/list excludes stele_create_provider_listing_draft, "
        "Hosted Stele MCP provides provider-listing draft creation.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "The gated stele_create_provider_listing_draft tool exists only when that "
        "exact name appears in authenticated tools/list. The tool exists even if "
        "authenticated tools/list is absent.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Hosted Stele MCP has a provider-listing draft composer.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Provider-listing draft creation operates through Hosted Stele MCP.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "stele_create_provider_listing_draft opens an existing provider-listing draft.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "stele_create_provider_listing_draft removes an existing provider-listing draft.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "A transaction is signed using stele_create_provider_listing_draft.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "stele_create_provider_listing_draft is a transaction signer.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP exposes stele-create-provider-listing-draft.",
        "hosted MCP exposes a noncanonical provider-draft tool name",
    ),
    (
        "Each successful create operation produces two provider-listing drafts.",
        "provider-draft creation claims a non-unit result",
    ),
    (
        "Two provider-listing drafts are produced by each successful operation.",
        "provider-draft creation claims a non-unit result",
    ),
    (
        "When authenticated tools/list includes stele_create_provider_listing_draft, "
        "each successful operation creates exactly one new private wallet-owned "
        "unpublished provider-listing draft. The operation also produces two "
        "provider-listing drafts.",
        "provider-draft creation claims a non-unit result",
    ),
    (
        "An idempotent replay does not return that same provider-listing draft.",
        "idempotent provider-draft replay denies same-draft return",
    ),
    (
        "A replay with the same idempotency key creates another provider-listing draft.",
        "idempotent provider-draft replay claims duplicate creation",
    ),
    (
        "## Hosted Stele MCP\n\n- Provider-listing draft creation is available.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "| Surface | Capability |\n|---|---|\n"
        "| Hosted Stele MCP | Provider-listing draft creation |",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Three tools comprise the Hosted Stele MCP inventory.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "The tool count for Hosted Stele MCP is not three.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    (
        "Two tools comprise the local Stele MCP inventory.",
        "local Stele MCP claims 2 tools; expected exactly 3",
    ),
)


FINAL_TRANSITION_NEARBY_CONTRADICTIONS = (
    *(
        (
            f"When authenticated tools/list {predicate} "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
            "hosted provider-draft tool availability is not tools/list-conditional",
        )
        for predicate in ("fails to include", "refuses to list")
    ),
    (
        "Only if authenticated tools/list omits stele_create_provider_listing_draft, "
        "Hosted Stele MCP provides provider-listing draft creation.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Provided that authenticated tools/list never returns "
        "stele_create_provider_listing_draft, Hosted Stele MCP supports "
        "provider-listing draft creation.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "The gated stele_create_provider_listing_draft tool exists only when that "
        "exact name appears in authenticated tools/list. It remains available when "
        "authenticated tools/list omits that exact name.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "The gated stele_create_provider_listing_draft tool exists only when that "
        "exact name appears in authenticated tools/list.\n\n- The tool remains "
        "callable without authenticated tools/list.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    *(
        (
            f"Hosted Stele MCP {verb} provider-listing draft creation.",
            "hosted provider-draft tool availability is not tools/list-conditional",
        )
        for verb in ("implements", "facilitates", "features")
    ),
    (
        "Provider-listing drafting is live on Hosted Stele MCP.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Provider-listing drafts are generated using Hosted Stele MCP.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    *(
        (
            f"stele_create_provider_listing_draft {verb} an existing "
            "provider-listing draft.",
            "hosted MCP claims provider-listing draft authority",
        )
        for verb in ("revises", "replaces", "erases", "returns")
    ),
    *(
        (
            "When authenticated tools/list includes "
            "stele_create_provider_listing_draft, the tool is available. "
            f"The tool {verb} an existing provider-listing draft.",
            "hosted MCP claims provider-listing draft authority",
        )
        for verb in ("opens", "revises", "removes")
    ),
    (
        "An existing provider-listing draft gets deleted through "
        "stele_create_provider_listing_draft.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "stele_create_provider_listing_draft has custody of private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "When authenticated tools/list includes stele_create_provider_listing_draft, "
        "the tool is available. It has custody of private keys.",
        "hosted Stele MCP claims transaction capability",
    ),
    *(
        (
            "When authenticated tools/list includes stele_create_provider_listing_draft, "
            "each successful operation creates exactly one new private wallet-owned "
            f"unpublished provider-listing draft. {tail}",
            expected,
        )
        for tail, expected in (
            (
                "It also produces two provider-listing drafts.",
                "provider-draft creation claims a non-unit result",
            ),
            (
                "A second draft is created too.",
                "provider-draft creation claims a non-unit result",
            ),
            (
                "Each call yields two provider-listing drafts.",
                "provider-draft creation claims a non-unit result",
            ),
            (
                "A retry returns a different provider-listing draft.",
                "idempotent provider-draft replay claims duplicate creation",
            ),
            (
                "Reusing the same idempotency key creates another draft.",
                "idempotent provider-draft replay claims duplicate creation",
            ),
            (
                "It does not return that same draft on an idempotent replay.",
                "idempotent provider-draft replay denies same-draft return",
            ),
        )
    ),
    (
        "An idempotent replay is not guaranteed to return the same "
        "provider-listing draft.",
        "idempotent provider-draft replay denies same-draft return",
    ),
    (
        "Each successful call creates no provider-listing draft.",
        "provider-draft creation claims a non-unit result",
    ),
    (
        "> Hosted Stele MCP\n>\n> Provider-listing draft creation is available.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "Hosted Stele MCP:\n\n1. Provider-listing draft creation is available.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    *(
        (
            sample,
            "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
        )
        for sample in (
            "A pair of tools makes up the Hosted Stele MCP inventory.",
            "Two tools make up Hosted Stele MCP.",
            "The number of tools in Hosted Stele MCP is two.",
            "Hosted Stele MCP is a two-tool service.",
        )
    ),
    *(
        (sample, expected)
        for sample, expected in (
            (
                "The tool count for local Stele MCP is two.",
                "local Stele MCP claims 2 tools; expected exactly 3",
            ),
            (
                "Local Stele MCP has no third tool.",
                "local Stele MCP denies its required 3-tool surface",
            ),
            (
                "No third tool is available through local Stele MCP.",
                "local Stele MCP denies its required 3-tool surface",
            ),
            (
                "A pair of tools makes up the local Stele MCP inventory.",
                "local Stele MCP claims 2 tools; expected exactly 3",
            ),
        )
    ),
)


FINAL_TRANSITION_TRUTHFUL_CONTROLS = (
    "Clients cannot invoke stele_create_provider_listing_draft unless it appears "
    "in authenticated tools/list.",
    "The gated stele_create_provider_listing_draft tool exists only when that exact "
    "name appears in authenticated tools/list. It remains available when "
    "authenticated tools/list includes that exact name.",
    "The gated stele_create_provider_listing_draft tool exists only when that exact "
    "name appears in authenticated tools/list. The tool remains callable when "
    "authenticated tools/list returns that exact name.",
    "The gated stele_create_provider_listing_draft tool exists only when that exact "
    "name appears in authenticated tools/list. The tool is not available when "
    "authenticated tools/list is absent.",
    "Hosted Stele MCP does not implement provider-listing draft creation.",
    "Provider-listing drafting is not live on Hosted Stele MCP.",
    "Provider-listing drafts cannot be generated using Hosted Stele MCP.",
    "## Hosted Stele MCP\n\n- Provider-listing draft creation is unavailable.",
    "| Surface | Capability |\n|---|---|\n"
    "| Hosted Stele MCP | Provider-listing draft creation unavailable |",
    "stele_create_provider_listing_draft does not revise an existing "
    "provider-listing draft.",
    "stele_create_provider_listing_draft cannot replace an existing "
    "provider-listing draft.",
    "stele_create_provider_listing_draft does not have custody of private keys.",
    "A future stele_create_provider_listing_draft may revise an existing draft "
    "after release.",
    "The retired stele_create_provider_listing_draft returned an existing draft.",
    "The warning rejects the claim “stele_create_provider_listing_draft has "
    "custody of private keys.”",
    "An idempotent replay never creates another draft.",
    "An idempotent replay cannot create another draft.",
    "An idempotent replay returns the same draft without creating any additional draft.",
    "The gated stele_create_provider_listing_draft tool exists only when that exact "
    "name appears in authenticated tools/list. The tool cannot read existing drafts.\n\n"
    "## Studio viewer\n\nThe tool opens an existing provider-listing draft.",
    "The gated stele_create_provider_listing_draft tool exists only when that exact "
    "name appears in authenticated tools/list. The tool cannot sign transactions.\n\n"
    "## Wallet transaction tool\n\nThe tool exists and signs transactions.",
    "When authenticated tools/list includes stele_create_provider_listing_draft, "
    "each successful operation creates exactly one new private wallet-owned "
    "unpublished provider-listing draft.\n\n## Batch importer\n\nIt also produces "
    "two provider-listing drafts.",
    "When authenticated tools/list includes stele_create_provider_listing_draft, "
    "each successful operation creates exactly one new private wallet-owned "
    "unpublished provider-listing draft.\n\n## Retry simulator\n\nA retry returns "
    "a different provider-listing draft.",
    "Local Stele MCP exposes exactly three tools.",
    "Three tools comprise the local Stele MCP inventory.",
    "Local Stele MCP has a tool count of three.",
    "The tool count for local Stele MCP is three.",
    "The local Stele MCP inventory is composed of exactly three tools.",
    "Local Stele MCP exposes precisely three tools.",
    "Hosted Stele MCP exposed exactly two tools in 2025.",
    "Hosted Stele MCP exposed exactly two tools until 2025.",
    "Hosted Stele MCP exposed exactly two tools through 2025.",
    "Hosted Stele MCP exposed exactly two tools before 2026.",
    "Hosted Stele MCP exposed exactly two tools during 2025.",
    "Hosted Stele MCP exposed exactly two tools from 2024 to 2025.",
    "Hosted Stele MCP exposed exactly two tools between 2024 and 2025.",
    "Hosted Stele MCP once exposed exactly two tools.",
)


FINAL_TRANSITION_GATE_ANCHOR = (
    "The gated stele_create_provider_listing_draft tool exists only when that "
    "exact name appears in authenticated tools/list."
)


FINAL_TRANSITION_ADVERSARIAL_CONTRADICTIONS = (
    (
        "Hosted Stele MCP does not implement provider-listing draft creation, "
        "but it facilitates provider-listing draft creation.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "A future Hosted Stele MCP will implement provider-listing draft creation, "
        "but currently it facilitates provider-listing draft creation.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        "The claim “Hosted Stele MCP provides provider-listing draft creation” is "
        "false, but in fact it supports provider-listing draft creation.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    (
        FINAL_TRANSITION_GATE_ANCHOR
        + " The tool does not open an existing provider-listing draft, but the "
        "tool removes an existing provider-listing draft.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        FINAL_TRANSITION_GATE_ANCHOR
        + " The tool does not sign a transaction, but the tool broadcasts a "
        "transaction.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Each successful operation does not produce exactly one provider-listing "
        "draft.",
        "provider-draft creation claims a non-unit result",
    ),
    (
        "No successful operation produces exactly one provider-listing draft.",
        "provider-draft creation claims a non-unit result",
    ),
    (
        "Each successful operation fails to create exactly one provider-listing "
        "draft.",
        "provider-draft creation claims a non-unit result",
    ),
    (
        "A replay reusing the same idempotency key yields another provider-listing "
        "draft.",
        "idempotent provider-draft replay claims duplicate creation",
    ),
    (
        FINAL_TRANSITION_GATE_ANCHOR
        + " On retry, a second provider-listing draft is created.",
        "idempotent provider-draft replay claims duplicate creation",
    ),
    (
        "An idempotent replay cannot avoid creating another provider-listing draft.",
        "idempotent provider-draft replay claims duplicate creation",
    ),
    (
        FINAL_TRANSITION_GATE_ANCHOR
        + "\n\n## Hosted Stele MCP\n\nThe tool opens an existing provider-listing "
        "draft.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        FINAL_TRANSITION_GATE_ANCHOR
        + "\n\n### Same tool\n\nIt remains callable without authenticated "
        "tools/list.",
        "hosted provider-draft tool availability is not tools/list-conditional",
    ),
    *(
        (
            sample,
            "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
        )
        for sample in (
            "Hosted Stele MCP is not a two-tool service.",
            "Hosted Stele MCP is not a three-tool service.",
            "The tool count for Hosted Stele MCP isn't three.",
            "Hosted Stele MCP does not have a tool count of two.",
        )
    ),
    *(
        (sample, "local Stele MCP denies its required 3-tool surface")
        for sample in (
            "Local Stele MCP is not a three-tool service.",
            "The tool count for local Stele MCP isn't three.",
            "Local Stele MCP does not have a tool count of three.",
        )
    ),
    (
        FINAL_TRANSITION_GATE_ANCHOR
        + " The tool never fails to broadcast a transaction.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "A transaction cannot fail to be signed using "
        "stele_create_provider_listing_draft.",
        "hosted Stele MCP claims transaction capability",
    ),
    *(
        (sample, "hosted MCP exposes a noncanonical provider-draft tool name")
        for sample in (
            "Hosted Stele MCP exposes stele_create-provider-listing-draft.",
            "Hosted Stele MCP exposes stele-create_provider_listing_draft.",
            "Hosted Stele MCP exposes stele_create_provider-listing_draft.",
        )
    ),
    (
        "Hosted Stele MCP\n================\n\nThe tool opens an existing "
        "provider-listing draft.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "<h2>Hosted Stele MCP</h2>\n\nThe tool opens an existing "
        "provider-listing draft.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        FINAL_TRANSITION_GATE_ANCHOR
        + " The hosted service does not sign transactions, but this MCP "
        "broadcasts transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        FINAL_TRANSITION_GATE_ANCHOR
        + " This MCP never opens an existing provider-listing draft, but the "
        "hosted service revises an existing provider-listing draft.",
        "hosted MCP claims provider-listing draft authority",
    ),
    *(
        (
            sample,
            "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
        )
        for sample in (
            "Hosted Stele MCP does not lack a tool count of two.",
            "Hosted Stele MCP is anything but a two-tool service.",
            "The tool count for Hosted Stele MCP differs from three.",
        )
    ),
    *(
        (sample, "local Stele MCP denies its required 3-tool surface")
        for sample in (
            "Local Stele MCP is anything but a three-tool service.",
            "Local Stele MCP does not expose precisely three tools.",
            "Exactly three tools do not comprise the local Stele MCP inventory.",
            "The tool count for local Stele MCP differs from three.",
        )
    ),
    *(
        (sample, "idempotent provider-draft replay claims duplicate creation")
        for sample in (
            "An idempotent replay is unable to avoid creating another "
            "provider-listing draft.",
            "An idempotent replay cannot help but create another "
            "provider-listing draft.",
            "An idempotent replay returns a fresh provider-listing draft.",
            "A replay with the same idempotency key yields a distinct "
            "provider-listing draft.",
            "A retry results in a second provider-listing draft.",
            "On retry, another provider-listing draft emerges.",
        )
    ),
    *(
        (sample, "idempotent provider-draft replay denies same-draft return")
        for sample in (
            "An idempotent replay returns anything except the same "
            "provider-listing draft.",
            "An idempotent replay does not return the original "
            "provider-listing draft.",
        )
    ),
    *(
        (
            sample,
            "hosted provider-draft tool availability is not tools/list-conditional",
        )
        for sample in (
            "When authenticated tools/list cannot include "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
            "When authenticated tools/list is unable to include "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
            "When authenticated tools/list lacks stele_create_provider_listing_draft, "
            "Hosted Stele MCP provides provider-listing draft creation.",
            "When authenticated tools/list withholds "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
            "When no stele_create_provider_listing_draft appears in authenticated "
            "tools/list, Hosted Stele MCP provides provider-listing draft creation.",
            "When authenticated tools/list returns anything except "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
            "Clients invoke stele_create_provider_listing_draft if authenticated "
            "tools/list cannot include that exact name.",
            "Invocation of stele_create_provider_listing_draft occurs through Hosted "
            "Stele MCP.",
        )
    ),
    *(
        (sample, "hosted MCP claims provider-listing draft authority")
        for sample in (
            "## Hosted Stele MCP\n\nAccording to this guide, the service opens "
            "existing provider-listing drafts.",
            "Hosted Stele MCP owns existing provider-listing drafts.",
            "Hosted Stele MCP controls existing provider-listing drafts.",
            "Hosted Stele MCP maintains existing provider-listing drafts.",
            "Hosted Stele MCP is the custodian of private wallet-owned "
            "provider-listing drafts.",
            "## Hosted Stele MCP\n\n### Draft ownership\n\nThis service owns "
            "existing provider-listing drafts.",
            FINAL_TRANSITION_GATE_ANCHOR
            + " The tool cannot open existing drafts, yet it deletes them.",
            FINAL_TRANSITION_GATE_ANCHOR
            + " The tool does not publish provider-listing drafts; instead, it "
            "deletes existing provider-listing drafts.",
            FINAL_TRANSITION_GATE_ANCHOR
            + " The tool is unable to publish drafts while still erasing existing "
            "provider-listing drafts.",
        )
    ),
    (
        FINAL_TRANSITION_GATE_ANCHOR
        + " The tool does not sign transactions; nevertheless, it submits them.",
        "hosted Stele MCP claims transaction capability",
    ),
    *(
        (
            sample,
            "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
        )
        for sample in (
            "Hosted Stele MCP is anything but a two-tool service.",
            "Hosted Stele MCP is by no means a two-tool service.",
        )
    ),
    *(
        (sample, "idempotent provider-draft replay claims duplicate creation")
        for sample in (
            "An idempotent replay cannot fail to create a duplicate provider-listing "
            "draft.",
            "An idempotent replay returns the same provider-listing draft while also "
            "producing a duplicate provider-listing draft.",
            "A retry with the unchanged idempotency key results in a new "
            "provider-listing draft.",
            "A replay with the same idempotency key yields a distinct provider-listing "
            "draft.",
        )
    ),
    *(
        (sample, "idempotent provider-draft replay denies same-draft return")
        for sample in (
            "No idempotent replay returns the same provider-listing draft.",
            "An idempotent replay is unable to return the original provider-listing "
            "draft.",
            "It is false that an idempotent replay returns the same provider-listing "
            "draft.",
            "A replay with the same idempotency key returns neither the same nor "
            "original provider-listing draft.",
            "An idempotent replay does anything but return the same provider-listing "
            "draft.",
        )
    ),
    *(
        (
            sample,
            "hosted provider-draft tool availability is not tools/list-conditional",
        )
        for sample in (
            "When authenticated tools/list includes "
            "stele_create_provider_listing_draft but then omits "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
            "When authenticated tools/list cannot include "
            "stele_create_provider_listing_draft but cannot omit "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
            "When authenticated tools/list fails to exclude "
            "stele_create_provider_listing_draft but then excludes "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
        )
    ),
    *(
        (
            sample,
            "hosted provider-draft tool availability is not tools/list-conditional",
        )
        for sample in (
            "When authenticated tools/list is prohibited from including "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
            "When authenticated tools/list contains every tool except "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
        )
    ),
    (
        FINAL_TRANSITION_GATE_ANCHOR
        + " The tool does not broadcast transactions; even so, the same tool "
        "submits a transaction.",
        "hosted Stele MCP claims transaction capability",
    ),
    *(
        (
            sample,
            "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
        )
        for sample in (
            "Hosted Stele MCP cannot be described as a three-tool service.",
            "The Hosted Stele MCP tool count is anything except three.",
        )
    ),
    *(
        (sample, "local Stele MCP denies its required 3-tool surface")
        for sample in (
            "Local Stele MCP cannot be described as a three-tool service.",
            "The local Stele MCP inventory contains anything except three tools.",
        )
    ),
    *(
        (sample, "idempotent provider-draft replay denies same-draft return")
        for sample in (
            "An idempotent replay is incapable of returning the original "
            "provider-listing draft.",
            "An idempotent replay returns a draft other than the original "
            "provider-listing draft.",
            "An idempotent replay avoids returning the same provider-listing draft.",
        )
    ),
    *(
        (sample, "idempotent provider-draft replay claims duplicate creation")
        for sample in (
            "The same idempotency key leads to a second provider-listing draft.",
            "Retrying the unchanged request produces a fresh provider-listing draft.",
        )
    ),
    (
        "Each successful operation is not limited to one provider-listing draft.",
        "provider-draft creation claims a non-unit result",
    ),
    *(
        (
            sample,
            "hosted provider-draft tool availability is not tools/list-conditional",
        )
        for sample in (
            "When authenticated tools/list is barred from returning "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
            "When authenticated tools/list includes every name other than "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
        )
    ),
    (
        "Hosted Stele MCP is not describable as a three-tool service.",
        "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
    ),
    *(
        (sample, "local Stele MCP denies its required 3-tool surface")
        for sample in (
            "Local Stele MCP is in no way a three-tool service.",
            "The local Stele MCP inventory is anything other than exactly three "
            "tools.",
        )
    ),
    (
        "An idempotent replay is not capable of returning the original "
        "provider-listing draft.",
        "idempotent provider-draft replay denies same-draft return",
    ),
    (
        "An unchanged retry creates a novel provider-listing draft.",
        "idempotent provider-draft replay claims duplicate creation",
    ),
    (
        "Each successful operation is not restricted to a single provider-listing "
        "draft.",
        "provider-draft creation claims a non-unit result",
    ),
)


FINAL_TRANSITION_ADVERSARIAL_CONTROLS = (
    "When authenticated tools/list does not omit "
    "stele_create_provider_listing_draft, Hosted Stele MCP provides "
    "provider-listing draft creation.",
    "When authenticated tools/list never omits "
    "stele_create_provider_listing_draft, Hosted Stele MCP provides "
    "provider-listing draft creation.",
    "When authenticated tools/list does not exclude "
    "stele_create_provider_listing_draft, Hosted Stele MCP provides "
    "provider-listing draft creation.",
    "When authenticated tools/list does not fail to include "
    "stele_create_provider_listing_draft, Hosted Stele MCP provides "
    "provider-listing draft creation.",
    "An idempotent replay does not fail to return the same provider-listing draft.",
    FINAL_TRANSITION_GATE_ANCHOR
    + "\n\nBrowser Wallet\n--------------\n\nIt holds private keys.",
    FINAL_TRANSITION_GATE_ANCHOR
    + "\n\nProvider Studio\n---------------\n\nIt opens an existing "
    "provider-listing draft.",
    FINAL_TRANSITION_GATE_ANCHOR
    + "\n\n<h2>Browser Wallet</h2>\n\nIt holds private keys.",
    FINAL_TRANSITION_GATE_ANCHOR
    + "\n\n<h2>Provider Studio</h2>\n\nIt opens an existing provider-listing "
    "draft.",
    FINAL_TRANSITION_GATE_ANCHOR
    + " Browser Wallet is a different actor. It holds private keys.",
    FINAL_TRANSITION_GATE_ANCHOR
    + " Provider Studio opens an existing provider-listing draft. It revises the "
    "existing provider-listing draft.",
    "Hosted Stele MCP serves catalog, while Provider Studio facilitates "
    "provider-listing draft creation.",
    "Hosted Stele MCP serves catalog and Provider Studio implements "
    "provider-listing draft creation.",
    "Hosted Stele MCP serves catalog, but Provider Studio features "
    "provider-listing draft creation.",
    "Hosted Stele MCP serves catalog, while Provider Studio has a "
    "provider-listing draft composer.",
    "Hosted Stele MCP documentation exposes stele-create-provider-listing-draft "
    "as an invalid example.",
    "Hosted Stele MCP fixture exposes stele-create-provider-listing-draft.",
    "A test for Hosted Stele MCP exposes stele-create-provider-listing-draft.",
    "Hosted Stele MCP documentation features provider-listing draft creation as "
    "a future example.",
    "Hosted Stele MCP fixture implements provider-listing draft creation.",
    "An integration test for Hosted Stele MCP facilitates provider-listing draft "
    "creation.",
    "Hosted Stele MCP documentation has a provider-listing draft composer example.",
    "When authenticated tools/list cannot fail to include "
    "stele_create_provider_listing_draft, Hosted Stele MCP provides "
    "provider-listing draft creation.",
    "When authenticated tools/list never excludes "
    "stele_create_provider_listing_draft, Hosted Stele MCP provides "
    "provider-listing draft creation.",
    "Each successful operation does not fail to create exactly one "
    "provider-listing draft.",
    "No successful operation fails to create exactly one provider-listing draft.",
    "Local Stele MCP is not a two-tool service.",
    "Local Stele MCP does not have a tool count of two.",
    "Hosted Stele MCP documentation describes an invalid example. It facilitates "
    "provider-listing draft creation in the fixture.",
    FINAL_TRANSITION_GATE_ANCHOR
    + " A unit test says the tool opens an existing provider-listing draft.",
    FINAL_TRANSITION_GATE_ANCHOR
    + " The documentation uses “The tool removes an existing provider-listing "
    "draft” as an invalid example.",
    FINAL_TRANSITION_GATE_ANCHOR
    + " A fixture asserts that the tool holds private keys.",
    FINAL_TRANSITION_GATE_ANCHOR
    + " The warning rejects the claim “The tool broadcasts a transaction.”",
    FINAL_TRANSITION_GATE_ANCHOR
    + " An archived simulation says the tool signs a transaction.",
    *(
        FINAL_TRANSITION_GATE_ANCHOR + " " + sample
        for sample in (
            "The provider wallet holds private keys. It signs transactions.",
            "A hardware wallet holds private keys. It signs transactions.",
            "The user wallet holds private keys. It broadcasts transactions.",
            "An external signer holds private keys. It signs transactions.",
            "A self-custodial wallet holds private keys. It signs transactions.",
        )
    ),
    "Hosted Stele MCP serves catalog, while the web app facilitates "
    "provider-listing draft creation.",
    "Hosted Stele MCP is keyless, and Studio implements provider-listing draft "
    "creation.",
    "Hosted Stele MCP serves catalog, while a browser extension wallet signs "
    "transactions.",
    "Local Stele MCP does not lack exactly three tools.",
    "An idempotent replay does not create any other provider-listing draft.",
    "An idempotent replay cannot create any additional provider-listing draft.",
    "An idempotent replay never returns anything except the same provider-listing "
    "draft.",
    "An idempotent replay does not return a different provider-listing draft.",
    "An idempotent replay cannot fail to avoid creating another provider-listing "
    "draft.",
    "A replay with the same idempotency key never yields another provider-listing "
    "draft.",
    *(
        sample
        for sample in (
            "When authenticated tools/list cannot omit "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
            "When authenticated tools/list fails to exclude "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
            "When authenticated tools/list refuses to omit "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
            "When authenticated tools/list never fails to include "
            "stele_create_provider_listing_draft, Hosted Stele MCP provides "
            "provider-listing draft creation.",
        )
    ),
    "It is untrue that local Stele MCP does not expose exactly three tools.",
    "Local Stele MCP has no more and no fewer than three tools.",
    "When authenticated tools/list cannot omit "
    "stele_create_provider_listing_draft and includes "
    "stele_create_provider_listing_draft, Hosted Stele MCP provides "
    "provider-listing draft creation.",
    "When authenticated tools/list is required not to omit "
    "stele_create_provider_listing_draft, Hosted Stele MCP provides "
    "provider-listing draft creation.",
    FINAL_TRANSITION_GATE_ANCHOR
    + " A regression harness records “The tool opens an existing draft” as a "
    "rejected assertion.",
    FINAL_TRANSITION_GATE_ANCHOR
    + " The security manual warns that “The tool broadcasts a transaction” is "
    "false.",
    FINAL_TRANSITION_GATE_ANCHOR
    + "\n\n<h2>Hosted Stele MCP documentation</h2>\n\nAn invalid example "
    "says this service owns existing drafts.",
    FINAL_TRANSITION_GATE_ANCHOR
    + " An audit marks “The tool opens an existing draft” as false.",
    FINAL_TRANSITION_GATE_ANCHOR
    + "\n\n<h3>Hosted Stele MCP reference</h3>\n\nAn invalid example claims "
    "this service owns existing drafts.",
)


RELEASE_AUDIT_EXACT_CONTRADICTIONS = (
    (
        "Hosted Stele MCP creates transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Local Stele MCP exposes a pair of tools.",
        "local Stele MCP claims 2 tools; expected exactly 3",
    ),
    (
        "The public catalog contains two listings.",
        "Stele catalog claims 2 listings; expected zero",
    ),
    (
        "Transaction signing has launched.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Provider-listing drafts can be published.",
        "provider-listing draft presented as public or executable",
    ),
    (
        "Hosted Stele MCP fetches provider-listing drafts.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "No listing is needed for booking-draft preparation.",
        "booking-draft preparation claims no listing prerequisite",
    ),
    (
        "Desktop Wallet hosts Stele.",
        "Stele presented as embedded in the desktop wallet",
    ),
    (
        "Provider Studio manages escrow.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        '<a href="https://evil.example/studio">Provider Studio</a>',
        "non-canonical Provider Studio URL",
    ),
)

RELEASE_AUDIT_EXACT_TRUTHFUL_CONTROLS = (
    "If Hosted Stele MCP signs transactions, that is a critical defect.",
    "When transaction signing is enabled after a future release, keys must stay local.",
    "Economic writes are enabled only in a future release.",
)

RELEASE_AUDIT_VARIATION_CONTRADICTIONS = (
    (
        "Hosted Stele MCP builds transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP constructs transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP initiates transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP submits transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP broadcasts transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP sends transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Transaction signing launched.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Transaction signing goes live.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Transaction signing went live.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Transaction signing has gone live.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Transaction signing became active.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Transaction signing has become ready.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Provider-listing drafts publish.",
        "provider-listing draft presented as public or executable",
    ),
    (
        "Provider-listing drafts are publishable.",
        "provider-listing draft presented as public or executable",
    ),
    (
        "Provider-listing drafts can be submitted.",
        "provider-listing draft presented as public or executable",
    ),
    (
        "The service publishes provider-listing drafts.",
        "provider-listing draft presented as public or executable",
    ),
    (
        "Hosted Stele MCP reads provider-listing drafts.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "Hosted Stele MCP retrieves provider-listing drafts.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "Hosted Stele MCP is inspecting provider-listing drafts.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "Hosted Stele MCP has retrieved provider-listing drafts.",
        "hosted MCP claims provider-listing draft authority",
    ),
    (
        "Zero published listings are required for booking-draft preparation.",
        "booking-draft preparation claims no listing prerequisite",
    ),
    (
        "Booking-draft preparation needs no listing.",
        "booking-draft preparation claims no listing prerequisite",
    ),
    (
        "Booking-draft preparation does not need any listing.",
        "booking-draft preparation claims no listing prerequisite",
    ),
    (
        "Booking-draft preparation is listing-free.",
        "booking-draft preparation claims no listing prerequisite",
    ),
    (
        "Booking-draft preparation can proceed without a listing.",
        "booking-draft preparation claims no listing prerequisite",
    ),
    (
        "Desktop Wallet contains Stele.",
        "Stele presented as embedded in the desktop wallet",
    ),
    (
        "Desktop Wallet ships with Stele.",
        "Stele presented as embedded in the desktop wallet",
    ),
    (
        "Desktop Wallet houses Stele.",
        "Stele presented as embedded in the desktop wallet",
    ),
    (
        "Stele is hosted in Desktop Wallet.",
        "Stele presented as embedded in the desktop wallet",
    ),
    (
        "Provider Studio books.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "Provider Studio pays.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "Provider Studio settles.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "Provider Studio processes escrow.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "Provider Studio can hold escrow.",
        "public web claims booking, payment, settlement, or economic controls",
    ),
    (
        "When transaction signing is enabled during incident response, keys stay local.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Economic writes are enabled only in production.",
        "Stele economic writes incorrectly presented as enabled",
    ),
    (
        "Hosted Stele MCP creates transactions only after authentication.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Transaction signing is enabled after authentication.",
        "Stele transaction signing incorrectly presented as enabled",
    ),
    (
        "Hosted Stele MCP that had no audit creates transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP serves catalog and creates transactions.",
        "hosted Stele MCP claims transaction capability",
    ),
    (
        "Hosted Stele MCP serves catalog and fetches provider-listing drafts.",
        "hosted MCP claims provider-listing draft authority",
    ),
)

RELEASE_AUDIT_VARIATION_TRUTHFUL_CONTROLS = (
    "If Hosted Stele MCP creates transactions, reject the deployment.",
    "Unless Hosted Stele MCP creates transactions, this warning does not apply.",
    "“Hosted Stele MCP creates transactions” would be a critical defect.",
    "The statement “Hosted Stele MCP builds transactions” is false.",
    "Hosted Stele MCP would create transactions only after activation.",
    "Hosted Stele MCP creates transactions only after activation.",
    "Hosted Stele MCP creates transactions only in a future release.",
    "When Hosted Stele MCP creates transactions after a future release, reject it.",
    "Transaction signing will launch only after a future release.",
    "Transaction signing launched in a retired prototype.",
    "Provider-listing drafts will be publishable only in a future release.",
    "If Hosted Stele MCP fetches provider-listing drafts, that is a defect.",
    "A future booking-draft preparation may need no listing after release.",
    "If Desktop Wallet hosts Stele, remove that build.",
    "If Provider Studio manages escrow, that is a release blocker.",
    "In a future release, Local Stele MCP exposes a pair of tools.",
    "After protocol activation, Hosted Stele MCP creates transactions.",
    "The public catalog is documented, but another API contains two listings.",
    "Desktop Wallet is generic, but another service hosts Stele.",
    "Provider Studio documents drafts, but another service manages escrow.",
    "Hosted Stele MCP serves catalog, but another service creates transactions.",
    "Hosted Stele MCP serves catalog. Another service creates transactions.",
    "Hosted Stele MCP serves catalog, while the public web fetches provider-listing drafts.",
)

RELEASE_AUDIT_ANCHOR_CONTRADICTIONS = tuple(
    (sample, "non-canonical Provider Studio URL")
    for sample in (
        "Use [Provider Studio](https://evil.example/studio).",
        "Use [Provider Studio](/studio).",
        "Use [Provider Studio](https://stele.monolythium.com/studio?draft=1).",
        "Use [Provider Studio](https://stele.monolythium.com/studio#draft).",
        "Use [Provider Studio](javascript:alert(1)).",
        "Use [Provider Studio][bad].\n[bad]: https://evil.example/studio",
        "Use [Provider Studio][bad].\n[bad]: /studio",
        "Use [Provider Studio][bad].\n[bad]: https://stele.monolythium.com/studio?draft=1",
        '<a href="https://evil.example/studio">Provider Studio</a>',
        "<a href='/studio'>Provider Studio</a>",
        '<a href="https://stele.monolythium.com/studio?draft=1">Provider Studio</a>',
        '<a href="https://stele.monolythium.com/studio#draft">Provider Studio</a>',
        '<a href="javascript:alert(1)">Provider Studio</a>',
        '<a class="button" href="//evil.example/studio">Provider <strong>Studio</strong></a>',
        '<a href="https://stele.monolythium.com/studio" href="https://evil.example/studio">Provider Studio</a>',
        '<a href="https://stele.monolythium.com/&#x73;tudio">Provider Studio</a>',
        '<a href="https://evil.example/studio">Provider Studio',
    )
)

RELEASE_AUDIT_ANCHOR_TRUTHFUL_CONTROLS = (
    "Use [Provider Studio](https://stele.monolythium.com/studio).",
    "Use [Provider Studio][live].\n[live]: https://stele.monolythium.com/studio",
    '<a href="https://stele.monolythium.com/studio">Provider Studio</a>',
    '<a class="button" href=https://stele.monolythium.com/studio>Provider <strong>Studio</strong></a>',
    'Avoid <a href="https://evil.example/studio">Provider Studio</a>.',
    'The <a href="https://evil.example/studio">Provider Studio</a> URL is invalid.',
    '<a href="https://evil.example/studio">Provider Studio docs</a>',
    'A future <a href="https://evil.example/studio">Provider Studio</a> is not released.',
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
> Hosted Stele MCP is keyless and OAuth-protected. Its authenticated tools/list response is the
> authoritative inventory for that session. Its baseline tools provide public catalog search and
> booking-draft preparation. Hosted booking-draft preparation is unavailable without a published listing.
> The gated stele_create_provider_listing_draft tool exists only when that exact name appears in
> authenticated tools/list. When listed, each successful stele_create_provider_listing_draft operation
> creates exactly one new private wallet-owned unpublished provider-listing draft. An idempotent replay
> returns the same draft without creating another. The tool cannot list, read, update, delete, or publish
> an existing draft.
> Hosted MCP does not sign, submit, broadcast, or settle transactions.
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

    def test_hosted_provider_tool_conditional_create_only_boundary_is_allowed(self) -> None:
        current = (
            "Hosted Stele MCP is keyless. Its authenticated tools/list response is authoritative. "
            "The gated stele_create_provider_listing_draft tool exists only when that exact name "
            "appears in authenticated tools/list. When listed, each successful "
            "stele_create_provider_listing_draft operation creates exactly one new private "
            "wallet-owned unpublished provider-listing draft. An idempotent replay returns the "
            "same draft without creating another. The tool cannot list, read, update, delete, or "
            "publish an existing draft. Hosted MCP does not sign, submit, broadcast, or settle "
            "transactions."
        )
        self.assertEqual([], check_truth.stele_status_contradictions(current))

    def test_hosted_provider_tool_unconditional_or_existing_draft_authority_is_rejected(self) -> None:
        samples = (
            (
                "Hosted Stele MCP exposes stele_create_provider_listing_draft.",
                "hosted provider-draft tool availability is not tools/list-conditional",
            ),
            (
                "stele_create_provider_listing_draft is available now.",
                "hosted provider-draft tool availability is not tools/list-conditional",
            ),
            (
                "Hosted Stele MCP lists provider-listing drafts.",
                "hosted MCP claims provider-listing draft authority",
            ),
            (
                "Hosted Stele MCP publishes provider-listing drafts.",
                "hosted MCP claims provider-listing draft authority",
            ),
            (
                "Each successful stele_create_provider_listing_draft operation creates two "
                "new private wallet-owned unpublished provider-listing drafts.",
                "provider-draft creation claims a non-unit result",
            ),
            (
                "An idempotent replay creates another provider-listing draft.",
                "idempotent provider-draft replay claims duplicate creation",
            ),
            (
                "An idempotent replay does not return the same draft.",
                "idempotent provider-draft replay denies same-draft return",
            ),
        )
        for sample, expected in samples:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

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

    def test_independent_rereview_counterexamples_are_rejected(self) -> None:
        for sample, expected in INDEPENDENT_REREVIEW_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_independent_rereview_truthful_controls_are_allowed(self) -> None:
        for sample in INDEPENDENT_REREVIEW_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_independent_rereview_variations_are_rejected(self) -> None:
        for sample, expected in INDEPENDENT_REREVIEW_VARIATION_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_independent_rereview_variation_controls_are_allowed(self) -> None:
        for sample in INDEPENDENT_REREVIEW_VARIATION_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_conditional_authority_rereview_corpus_is_rejected(self) -> None:
        for sample, expected in CONDITIONAL_AUTHORITY_REREVIEW_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_conditional_authority_rereview_controls_are_allowed(self) -> None:
        for sample in CONDITIONAL_AUTHORITY_REREVIEW_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_final_transition_review_corpus_is_rejected(self) -> None:
        for sample, expected in FINAL_TRANSITION_REVIEW_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_final_transition_nearby_variants_are_rejected(self) -> None:
        for sample, expected in FINAL_TRANSITION_NEARBY_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_final_transition_truthful_controls_are_allowed(self) -> None:
        for sample in FINAL_TRANSITION_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_final_transition_adversarial_corpus_is_rejected(self) -> None:
        for sample, expected in FINAL_TRANSITION_ADVERSARIAL_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_final_transition_adversarial_controls_are_allowed(self) -> None:
        for sample in FINAL_TRANSITION_ADVERSARIAL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_corrected_hosted_actor_attribution_matrix(self) -> None:
        hosted_referents = (
            "It",
            "This service",
            "That service",
            "The service",
            "The hosted service",
            "The public hosted service",
            "The Stele service",
            "The same service",
            "This MCP",
            "The hosted MCP",
            "The same hosted MCP",
            "Its service",
            "Its hosted service",
            "Its wallet",
            "Its service wallet",
            "The wallet",
            "The hosted wallet",
            "The hosted wallet's signer",
            "The service's wallet",
            "The hosted service's wallet",
            "The MCP's wallet",
        )
        for referent in hosted_referents:
            sample = f"Hosted Stele MCP serves catalog. {referent} creates transactions."
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "hosted Stele MCP claims transaction capability"
                )

        roles = (
            "user",
            "buyer",
            "provider",
            "customer",
            "seller",
            "merchant",
            "payer",
            "owner",
            "operator",
            "arbiter",
            "auditor",
            "treasury",
            "finance",
            "accounting",
            "compliance",
            "reviewer",
            "delegate",
            "agent",
            "administrator",
            "developer",
            "custodian",
            "approver",
        )
        for role in roles:
            for actor in (
                f"the {role} wallet",
                f"the {role}'s wallet",
                f"a {role}-controlled wallet",
                f"a {role}-owned wallet",
            ):
                sample = (
                    f"Hosted Stele MCP serves catalog, but {actor} creates transactions."
                )
                with self.subTest(sample=sample):
                    self.assertEqual([], check_truth.stele_status_contradictions(sample))

        for actor in (
            "an external wallet",
            "a hardware wallet",
            "a self-custodial wallet",
            "the customer's browser wallet",
            "an independently-managed wallet",
        ):
            sample = f"Hosted Stele MCP serves catalog, but {actor} creates transactions."
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_contextual_role_wallet_anaphora_matrix(self) -> None:
        for role in (
            "provider",
            "operator",
            "auditor",
            "administrator",
            "developer",
            "custodian",
            "approver",
        ):
            samples = (
                f"Hosted Stele MCP is the {role}. The {role} wallet signs transactions.",
                f"Hosted Stele MCP acts as the {role}. The {role}'s wallet creates transactions.",
                f"Hosted Stele MCP serves as the {role}, and the {role}-owned wallet builds transactions.",
                f"Hosted Stele MCP operates as the {role}; the {role}-controlled wallet signs transactions.",
                f"Hosted Stele MCP works as the {role}. The {role} wallet signs transactions.",
                f"Hosted Stele MCP becomes the {role}. The {role}'s wallet creates transactions.",
                f"Hosted Stele MCP represents the {role}. The {role} wallet builds transactions.",
                f"Hosted Stele MCP is itself the {role}. The {role} wallet signs transactions.",
                f"Hosted Stele MCP is the {role}. The {role}-controlled browser wallet signs transactions.",
            )
            for sample in samples:
                with self.subTest(sample=sample):
                    self.assert_contradiction(
                        sample, "hosted Stele MCP claims transaction capability"
                    )

        sample = (
            "Hosted Stele MCP is the customer agent. "
            "The agent wallet creates transactions."
        )
        self.assert_contradiction(
            sample, "hosted Stele MCP claims transaction capability"
        )

        for sample in (
            "Hosted Stele MCP is the operator, but another operator wallet signs transactions.",
            "Hosted Stele MCP is the operator, but a separate operator wallet signs transactions.",
            "Hosted Stele MCP is the operator, but an external operator-owned hardware wallet signs transactions.",
        ):
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_corrected_transaction_negation_parity_matrix(self) -> None:
        contradictions = (
            "does not fail to create transactions",
            "doesn't fail to create transactions",
            "can't fail to create transactions",
            "does not lack a transaction tool",
            "doesn't lack a transaction tool",
            "is not unable to create transactions",
            "isn't unable to create transactions",
            "is not incapable of signing transactions",
            "isn't incapable of signing transactions",
            "is not lacking a transaction tool",
            "isn't lacking signing authority",
            "is not without a transaction tool",
            "isn't without signing authority",
            "can't avoid signing transactions",
            "does not avoid creating transactions",
            "is never unable to create transactions",
            "is never incapable of signing transactions",
            "is never lacking a transaction tool",
            "is never without signing authority",
            "is no longer unable to create transactions",
            "is no longer incapable of signing transactions",
            "is no longer lacking a transaction tool",
            "is no longer without signing authority",
            "never avoids signing transactions",
            "can't avoid transaction signing",
            "never avoids transaction signing",
            "can't not sign transactions",
            "doesn't not create transactions",
        )
        for predicate in contradictions:
            sample = f"Hosted Stele MCP {predicate}."
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "hosted Stele MCP claims transaction capability"
                )

        controls = (
            "cannot create transactions",
            "doesn't create transactions",
            "fails to create transactions",
            "refuses to create transactions",
            "lacks a transaction tool",
            "is lacking a transaction tool",
            "is unable to create transactions",
            "is incapable of signing transactions",
            "is without a transaction tool",
            "operates without a transaction tool",
            "avoids signing transactions",
            "avoids transaction signing",
            "has no transaction tool",
            "has zero transaction tools",
            "documents a transaction tool restriction",
            "displays a transaction tool warning",
            "has a transaction tool prohibition",
            "is not lacking a transaction tool prohibition",
        )
        for predicate in controls:
            sample = f"Hosted Stele MCP {predicate}."
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_transaction_capability_meta_noun_matrix_is_allowed(self) -> None:
        for target in (
            "transaction tool",
            "signing tool",
            "broadcast tool",
            "signing authority",
            "private key",
            "transaction signing",
        ):
            for meta_noun in (
                "restriction",
                "warning",
                "prohibition",
                "policy",
                "documentation",
                "claim",
            ):
                predicates = (
                    f"has a {target} {meta_noun}",
                    f"documents a {target} {meta_noun}",
                    f"is not lacking a {target} {meta_noun}",
                )
                for predicate in predicates:
                    sample = f"Hosted Stele MCP {predicate}."
                    with self.subTest(sample=sample):
                        self.assertEqual(
                            [], check_truth.stele_status_contradictions(sample)
                        )

        for verb in (
            "describes",
            "discusses",
            "displays",
            "documents",
            "mentions",
            "prohibits",
            "reports",
            "restricts",
            "warns about",
        ):
            sample = f"Hosted Stele MCP {verb} a transaction tool."
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_corrected_reverse_catalog_count_matrix(self) -> None:
        counts = (
            ("One", "listing", 1),
            ("Two", "listings", 2),
            ("A pair of", "listings", 2),
            ("A couple of", "listings", 2),
            ("A trio of", "listings", 3),
        )
        verbs = ["exists", "exist", "appears", "appear", "can be found"]
        for copula in ("is", "are"):
            for time_modifier in (
                "",
                "now ",
                "currently ",
                "today ",
                "already ",
                "presently ",
                "right now ",
                "at present ",
                "at the moment ",
            ):
                for state in ("present", "available", "live", "published"):
                    verbs.append(f"{copula} {time_modifier}{state}")
        for count, noun, actual in counts:
            for verb in verbs:
                for preposition in ("in", "on", "within", "inside"):
                    sample = (
                        f"{count} {noun} {verb} {preposition} the public catalog."
                    )
                    with self.subTest(sample=sample):
                        labels = {
                            label
                            for _, label in check_truth.stele_status_contradictions(sample)
                        }
                        self.assertIn(
                            f"Stele catalog claims {actual} listings; expected zero",
                            labels,
                            msg=f"expected typed rejection for {sample!r}",
                        )

    def test_contextual_catalog_existential_and_control_matrices(self) -> None:
        compound_counts = (
            ("one pair of", 2),
            ("two pairs of", 4),
            ("three couples of", 6),
            ("two trios of", 6),
            ("one dozen", 12),
        )
        for count_phrase, actual in compound_counts:
            for time_modifier in (
                "",
                "now ",
                "currently ",
                "presently ",
                "right now ",
                "at present ",
                "at the moment ",
            ):
                samples = (
                    f"There {time_modifier}are {count_phrase} listings in the public catalog.",
                    f"There are {time_modifier}{count_phrase} listings within the public catalog.",
                )
                for sample in samples:
                    with self.subTest(sample=sample):
                        self.assert_contradiction(
                            sample,
                            f"Stele catalog claims {actual} listings; expected zero",
                        )

        for count_phrase, actual in (("one listing", 1), ("two listings", 2)):
            for preposition in ("In", "On", "Within", "Inside"):
                sample = f"{preposition} the public catalog are {count_phrase}."
                with self.subTest(sample=sample):
                    self.assert_contradiction(
                        sample,
                        f"Stele catalog claims {actual} listings; expected zero",
                    )

        controls = (
            "Two listings are hypothetical examples, while zero listings are present in the public catalog.",
            "Two listings appear in this document, while zero listings are present in the public catalog.",
            "Two listings are shown as examples; zero listings are present in the public catalog.",
            "A pair of listings appears in the public catalog documentation as a hypothetical example.",
            "A pair of listings appears in the public catalog's documentation as a hypothetical example.",
            "A pair of listings is available in the public catalog schema as an example.",
            "The public catalog documentation contains two listings.",
            "There are two listings in the public catalog docs.",
            "Inside the public catalog schema are two listings.",
            "The public catalog's documentation contains two listings.",
            "There are zero listings in the public catalog.",
            "Two listings do not exist in the public catalog.",
            "A future public catalog will contain two listings only after release.",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_seventh_review_same_surface_wallet_matrix(self) -> None:
        for referent in (
            "Its signer",
            "Its operator wallet",
            "Its provider-controlled wallet",
            "The MCP signer",
            "The service signer",
            "This service's signer",
            "That MCP's signer",
            "The wallet signer",
        ):
            sample = f"Hosted Stele MCP serves catalog. {referent} signs transactions."
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "hosted Stele MCP claims transaction capability"
                )

        for relation in (
            "identifies as",
            "identifies itself as",
            "is acting as",
            "plays the role of",
            "takes the role of",
            "takes on the role of",
            "assumes the role of",
            "fills the role of",
        ):
            sample = (
                f"Hosted Stele MCP {relation} the operator. "
                "The operator wallet signs transactions."
            )
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "hosted Stele MCP claims transaction capability"
                )

    def test_seventh_review_external_role_wallet_controls(self) -> None:
        samples = (
            "Hosted Stele MCP is the operator. A user-controlled operator wallet signs transactions.",
            "Hosted Stele MCP is the operator. Alice's operator wallet signs transactions.",
            "Hosted Stele MCP is the operator. The independently managed operator wallet signs transactions.",
            "Hosted Stele MCP is the operator. The operator wallet controlled by Alice signs transactions.",
            "Hosted Stele MCP is the operator. The operator wallet owned by another service signs transactions.",
            "Hosted Stele MCP is the operator. The operator wallet for another service signs transactions.",
            "Hosted Stele MCP is the operator. The operator wallet of another service signs transactions.",
            "Hosted Stele MCP is the operator. Another service is the operator. The operator wallet signs transactions.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_round_two_fresh_typed_tool_count_holdout(self) -> None:
        contradictions = (
            "Hosted Stele MCP supplies two pairs of OAuth tools.",
            "Hosted Stele MCP offers a trio of public endpoints.",
            "Hosted Stele MCP has one lookup tool plus two drafting endpoints.",
            "Hosted Stele MCP has two tools and a third endpoint.",
            "Hosted Stele MCP reports no fewer than three capabilities.",
            "Hosted Stele MCP exposes a maximum of two tools.",
            "Hosted Stele MCP provides roughly two endpoints.",
            "Hosted Stele MCP advertises one+two tools.",
            "Hosted Stele MCP exposes no more than two tools.",
            "Hosted Stele MCP exposes one or two tools.",
            "Local Stele MCP exposes between two and three tools.",
            "Hosted Stele MCP, despite archived documentation, exposes four tools.",
            "Local Stele MCP supplies one pair of read tools.",
            "Four endpoints are available through Hosted Stele MCP.",
            "Hosted Stele MCP supplies one pair of OAuth tools.",
            "Hosted Stele MCP has one lookup tool and one drafting endpoint.",
            "Hosted Stele MCP exposes exactly two tools. The SDK fixture exposes six tools.",
            "Hosted Stele MCP exposes two tools, whereas another service offers four endpoints.",
            "Hosted Stele MCP exposes two tools. A test harness exposes seven endpoints.",
            "There are exactly two tools in Hosted Stele MCP.",
            "Hosted Stele MCP lacks tools other than its two OAuth-protected tools.",
            "Hosted Stele MCP inventory consists of exactly two tools.",
            "Exactly two tools are available through Hosted Stele MCP.",
            "Hosted Stele MCP tool count is not three.",
            "Hosted Stele MCP does not expose three tools.",
            "Hosted Stele MCP has no third tool.",
        )
        for sample in contradictions:
            with self.subTest(sample=sample):
                labels = {
                    label
                    for _, label in check_truth.stele_status_contradictions(sample)
                }
                self.assertTrue(
                    any(
                        "expected exactly 3" in label
                        or "authenticated tools/list is authoritative" in label
                        for label in labels
                    ),
                    msg=f"expected typed-count rejection for {sample!r}",
                )

        controls = (
            "Hosted Stele MCP documents an SDK fixture with five tools.",
            "The false claim that four endpoints are in Hosted Stele MCP must be rejected.",
            "Four tools are in Hosted Stele MCP documentation.",
            "Four tools are in Hosted Stele MCP test fixtures.",
            "Hosted Stele MCP documentation lists four tools.",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_round_two_fresh_actor_and_transaction_parity_holdout(self) -> None:
        same_actor = (
            "Hosted Stele MCP acts in its capacity as operator. The operator signer signs transactions.",
            "Hosted Stele MCP assumes operator duties. The role signer broadcasts transactions.",
            "Hosted Stele MCP carries provider responsibilities. The provider wallet signs transactions.",
            "Hosted Stele MCP serves in the capacity of broker. The broker signer submits transactions.",
            "Hosted Stele MCP works in the operator capacity. The signer for that role signs transactions.",
            "Hosted Stele MCP performs the duties of broker. That role's signer broadcasts transactions.",
        )
        parity = (
            "Hosted Stele MCP is no longer prohibited from signing transactions.",
            "Hosted Stele MCP is not forbidden from transaction signing.",
            "Hosted Stele MCP is by no means without signing authority.",
            "Hosted Stele MCP transaction signing is not absent.",
            "Hosted Stele MCP has > 0 transaction endpoints.",
            "Hosted Stele MCP has at least one signing endpoint.",
            "Hosted Stele MCP exposes two transaction endpoints.",
            "Hosted Stele MCP transaction endpoint count is greater than 0.",
            "Hosted Stele MCP transaction endpoint count is 2.",
            "Hosted Stele MCP isn't prohibited from signing transactions.",
            "Hosted Stele MCP signing authority isn't absent.",
            "Hosted Stele MCP has no prohibition on transaction signing.",
            "Hosted Stele MCP: nothing prevents it from signing transactions.",
            "Hosted Stele MCP exposes a pair of transaction endpoints.",
            "Local Stele MCP exposes three signing endpoints.",
        )
        for sample in same_actor + parity:
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample,
                    (
                        "local Stele MCP claims transaction capability"
                        if sample.startswith("Local")
                        else "hosted Stele MCP claims transaction capability"
                    ),
                )

        controls = (
            "Hosted Stele MCP serves catalog. The externally owned wallet signs transactions.",
            "Hosted Stele MCP is the operator. Its separately administered operator wallet signs transactions.",
            "Hosted Stele MCP serves catalog. The replacement wallet signs transactions.",
            "Hosted Stele MCP is the operator. The operator wallet administered by another company signs transactions.",
            "Hosted Stele MCP is the operator. Its externally-owned operator wallet signs transactions.",
            "Hosted Stele MCP is the operator. Its operator wallet, separately administered, signs transactions.",
            "Hosted Stele MCP is prohibited from signing transactions.",
            "Hosted Stele MCP has zero transaction endpoints.",
            "Hosted Stele MCP has no signing endpoint.",
            "Hosted Stele MCP documents that a test fixture has two transaction endpoints.",
            "Hosted Stele MCP serves catalog. A browser wallet has at least one signing endpoint.",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_round_two_fresh_catalog_grammar_holdout(self) -> None:
        contradictions = (
            "The public catalog contains a minimum of one listing.",
            "The Stele catalog has more than zero services.",
            "The public catalog includes a set of two listings.",
            "The public catalog holds two sets of three listings.",
            "The public catalog comprises 2 × 3 listings.",
            "The public catalog's current inventory totals two listings.",
            "The current inventory in the public catalog stands at three services.",
            "Two listings are currently in the public catalog.",
            "Today, the public catalog is home to one listing.",
            "Within the public catalog currently reside two listings.",
            "Two listings are live at stele.monolythium.com.",
            "At stele.monolythium.com, there are three published listings.",
            "The public catalog, despite archived docs, contains two listings.",
        )
        for sample in contradictions:
            with self.subTest(sample=sample):
                labels = {
                    label
                    for _, label in check_truth.stele_status_contradictions(sample)
                }
                self.assertTrue(
                    any("expected zero" in label for label in labels),
                    msg=f"expected catalog rejection for {sample!r}",
                )

        controls = (
            'Archived documentation says "The public catalog contains two listings."',
            '"The public catalog has three services" is a hypothetical example.',
            "In an archived simulation, the public catalog contains four listings.",
            "The public catalog reference documentation contains two sample listings.",
            "The SDK fixture contains two listings, while the public catalog contains zero listings.",
            "The public catalog contains up to two listings.",
            "At most two listings can appear after a future catalog release.",
            "Two listings appear at stele.monolythium.com/docs.",
            "Example: Hosted Stele MCP exposes four tools.",
            "Historical simulation: Hosted Stele MCP has two transaction endpoints.",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_round_two_rendered_anchor_and_commonmark_link_holdout(self) -> None:
        hidden = """
<!--
authenticated tools/list response is the authoritative inventory for that session
stele_create_provider_listing_draft
authentication proves only current control of the selected wallet address
[Provider Studio](https://stele.monolythium.com/studio)
-->
"""
        searchable = check_truth.folded_prose(hidden)
        self.assertNotIn("authenticated tools/list response", searchable)
        self.assertNotIn("stele_create_provider_listing_draft", searchable)
        self.assertNotIn("authentication proves only current control", searchable)
        self.assertFalse(check_truth.has_canonical_provider_studio_link(hidden))

        inline = check_truth.folded_prose(
            "Use `stele_create_provider_listing_draft` only when listed."
        )
        fenced = check_truth.folded_prose(
            "```text\nstele_create_provider_listing_draft\n```"
        )
        self.assertIn("stele_create_provider_listing_draft", inline)
        self.assertNotIn("stele_create_provider_listing_draft", fenced)

        contradictions = (
            "Open [Provider Studio].\n\n[Provider Studio]: https://evil.example/studio",
            "Open [Provider\nStudio](https://evil.example/studio).",
            "Open [Provider Studio](https://stele.monolythium.com/studio&#x3F;mode=edit).",
            "Use [Provider Studio][].\n\n[Provider Studio]: https://evil.example/studio",
            "Open [Provider Studio].\n\n"
            "[Provider Studio]: https://stele.monolythium.com/studio\n"
            "[Provider Studio]: https://evil.example/studio",
        )
        for sample in contradictions:
            with self.subTest(sample=sample):
                self.assertNotEqual(
                    [], check_truth.provider_studio_url_violations(sample)
                )

        controls = (
            "Reference documentation for Provider Studio is [available here](https://docs.example/studio).",
            "[Provider Studio reference documentation](https://docs.example/studio) describes the API.",
            "Archived docs say [Provider Studio](https://old.example/studio) was the route.",
            "A historical simulation used [Provider Studio](https://old.example/studio).",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual(
                    [], check_truth.provider_studio_url_violations(sample)
                )

        sample = (
            "Hosted Stele MCP is the operator. "
            "The operator wallet controlled by Hosted Stele MCP signs transactions."
        )
        self.assert_contradiction(
            sample, "hosted Stele MCP claims transaction capability"
        )

    def test_seventh_review_typed_transaction_negation_matrix(self) -> None:
        contradictions = (
            "does not have zero transaction tools",
            "doesn't have no signing tools",
            "cannot expose exactly zero broadcast tools",
            "never includes no submission tools",
            "has not zero transaction tools",
            "has a nonzero signing tool",
            "has a positive number of broadcast tools",
            "transaction tool count is not zero",
            "signing tool count: nonzero",
            "broadcast tool count = positive",
        )
        for predicate in contradictions:
            sample = f"Hosted Stele MCP {predicate}."
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "hosted Stele MCP claims transaction capability"
                )

        controls = (
            "Hosted Stele MCP does not have any transaction tools.",
            "Hosted Stele MCP has zero signing tools.",
            "Hosted Stele MCP has no broadcast tools.",
            "Hosted Stele MCP transaction tool count is zero.",
            "Hosted Stele MCP does not have zero transaction-tool warnings.",
            "Hosted Stele MCP has a positive number of transaction-tool restrictions.",
            "A future Hosted Stele MCP will not have zero signing tools after release.",
            "The retired Hosted Stele MCP did not have zero transaction tools.",
            "Hosted Stele MCP serves catalog, but the user wallet does not have zero signing tools.",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_seventh_review_qualified_catalog_count_matrix(self) -> None:
        for qualifier in (
            "exactly",
            "only",
            "about",
            "approximately",
            "roughly",
            "at least",
            "more than",
            "no fewer than",
            "no less than",
        ):
            samples = (
                f"The public catalog contains {qualifier} two listings.",
                f"There are {qualifier} two listings in the public catalog.",
                f"In the public catalog are {qualifier} two listings.",
                f"{qualifier.title()} two listings currently exist within the public catalog.",
            )
            for sample in samples:
                with self.subTest(sample=sample):
                    self.assert_contradiction(
                        sample,
                        f"Stele catalog claims {qualifier} 2 listings; expected zero",
                    )

        compound_samples = (
            ("The public catalog contains exactly two pairs of listings.", 4),
            ("There are at least three couples of listings in the public catalog.", 6),
            ("Inside the public catalog are roughly two trios of listings.", 6),
            ("No fewer than one dozen listings currently exist in the public catalog.", 12),
        )
        for sample, actual in compound_samples:
            with self.subTest(sample=sample):
                labels = {
                    label
                    for _, label in check_truth.stele_status_contradictions(sample)
                }
                self.assertTrue(
                    any(
                        label.endswith(f" {actual} listings; expected zero")
                        for label in labels
                    ),
                    msg=f"expected qualified compound rejection for {sample!r}",
                )

    def test_seventh_review_catalog_scope_and_documentation_controls(self) -> None:
        contradictions = (
            "In the public catalog, two listings currently exist.",
            "In the public catalog two listings are currently available.",
            "In the public catalog, two listings can currently be found.",
            "The public catalog contains currently two listings.",
            "Two listings do currently exist in the public catalog.",
            "The Stele catalog has two published services.",
            "The catalog reported zero published services; it now has two published services.",
        )
        for sample in contradictions:
            with self.subTest(sample=sample):
                self.assertNotEqual([], check_truth.stele_status_contradictions(sample))

        controls = (
            "Another API contains two published services.",
            "This document includes two published services as hypothetical examples.",
            "The public catalog is documented, but another API contains two published services.",
            "The public catalog documentation contains exactly two listings.",
            "There are approximately two listings in the public catalog docs.",
            "Inside the public catalog schema are roughly two listings.",
            "The public catalog contains up to two listings.",
            "There are at most two listings in the public catalog.",
            "The public catalog contains exactly zero listings.",
            "Two listings do not currently exist in the public catalog.",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_release_audit_exact_contradictions_are_rejected(self) -> None:
        for sample, expected in RELEASE_AUDIT_EXACT_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_release_audit_exact_truthful_controls_are_allowed(self) -> None:
        for sample in RELEASE_AUDIT_EXACT_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_release_audit_predicate_variations_are_rejected(self) -> None:
        for sample, expected in RELEASE_AUDIT_VARIATION_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_release_audit_predicate_truthful_controls_are_allowed(self) -> None:
        for sample in RELEASE_AUDIT_VARIATION_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_embedded_condition_does_not_hide_a_current_claim(self) -> None:
        for sample in (
            "Hosted Stele MCP, if audited, creates transactions.",
            "Hosted Stele MCP, unless blocked, builds transactions.",
            "Hosted Stele MCP, if reviewed, fetches provider-listing drafts.",
        ):
            with self.subTest(sample=sample):
                expected = (
                    "hosted MCP claims provider-listing draft authority"
                    if "provider-listing" in sample
                    else "hosted Stele MCP claims transaction capability"
                )
                self.assert_contradiction(sample, expected)

    def test_release_audit_tool_count_word_and_digit_matrix(self) -> None:
        count_forms = (
            ("zero", 0),
            ("0", 0),
            ("one", 1),
            ("1", 1),
            ("a pair of", 2),
            ("two", 2),
            ("2", 2),
            ("a trio of", 3),
            ("three", 3),
            ("3", 3),
            ("four", 4),
            ("4", 4),
        )
        for surface, kind, expected_count in (
            ("Hosted Stele MCP", "hosted", None),
            ("Local Stele MCP", "local", 3),
        ):
            for count_phrase, actual in count_forms:
                sample = f"{surface} exposes {count_phrase} tools."
                with self.subTest(sample=sample):
                    contradictions = check_truth.stele_status_contradictions(sample)
                    if kind == "hosted":
                        self.assertIn(
                            check_truth.HOSTED_DYNAMIC_INVENTORY_ERROR,
                            {label for _, label in contradictions},
                        )
                    elif actual == expected_count:
                        self.assertEqual([], contradictions)
                    else:
                        self.assertIn(
                            f"{kind} Stele MCP claims {actual} tools; "
                            f"expected exactly {expected_count}",
                            {label for _, label in contradictions},
                        )

    def test_release_audit_catalog_count_word_and_digit_matrix(self) -> None:
        count_forms = (
            ("zero", 0),
            ("0", 0),
            ("one", 1),
            ("1", 1),
            ("a pair of", 2),
            ("two", 2),
            ("2", 2),
            ("four", 4),
            ("4", 4),
        )
        for count_phrase, actual in count_forms:
            sample = f"The public catalog contains {count_phrase} listings."
            with self.subTest(sample=sample):
                contradictions = check_truth.stele_status_contradictions(sample)
                if actual == 0:
                    self.assertEqual([], contradictions)
                else:
                    self.assertIn(
                        f"Stele catalog claims {actual} listings; expected zero",
                        {label for _, label in contradictions},
                    )

    def test_release_audit_capability_transition_matrix(self) -> None:
        for capability, _, expected in GATED_STATE_MATRIX_CAPABILITIES:
            perfect = "have" if capability == "Economic writes" else "has"
            for relation in (
                "launched",
                f"{perfect} launched",
                "goes live",
                "went live",
                f"{perfect} gone live",
                "became active",
                f"{perfect} become ready",
                "turned on",
            ):
                sample = f"{capability} {relation}."
                with self.subTest(sample=sample):
                    self.assert_contradiction(sample, expected)

    def test_release_audit_anchor_variations_are_rejected(self) -> None:
        for sample, expected in RELEASE_AUDIT_ANCHOR_CONTRADICTIONS:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

    def test_release_audit_anchor_truthful_controls_are_allowed(self) -> None:
        for sample in RELEASE_AUDIT_ANCHOR_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_truth_gate_limitation_remains_documented(self) -> None:
        documentation = (check_truth.ROOT / "tools/README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "bounded semantic regression gate over enumerated capability, predicate, count, state, and",
            documentation,
        )
        self.assertIn(
            "It does not prove arbitrary\nnatural-language prose truthful or complete.",
            documentation,
        )
        self.assertIn("Human review remains required", documentation)

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

    def test_strict_review_count_and_transaction_families(self) -> None:
        for verb in ("has", "offers", "provides", "reports"):
            for noun in ("tools", "endpoints", "capabilities"):
                sample = f"Hosted Stele MCP {verb} three or more {noun}."
                with self.subTest(sample=sample):
                    labels = {
                        label
                        for _, label in check_truth.stele_status_contradictions(sample)
                    }
                    self.assertTrue(
                        any("authenticated tools/list is authoritative" in label for label in labels),
                        msg=f"expected bounded tool-count rejection for {sample!r}",
                    )

        for predicate in (
            "is not without a transaction endpoint",
            "cannot be described as having no signing capability",
            "fails to lack transaction tooling",
            "transaction endpoint count exceeds zero",
            "is not devoid of broadcast capability",
            "cannot be characterized as having zero submission endpoints",
            "refuses to be without signing functionality",
            "broadcast capability count surpasses 0",
        ):
            sample = f"Hosted Stele MCP {predicate}."
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "hosted Stele MCP claims transaction capability"
                )

        for sample in (
            "Hosted Stele MCP has signing authority despite a policy requiring fewer than one transaction tool.",
            "Hosted Stele MCP exposes fewer than one transaction tool plus a signing capability.",
        ):
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "hosted Stele MCP claims transaction capability"
                )

        sample = "Hosted Stele MCP exposes seven tools and one mock endpoint."
        labels = {
            label for _, label in check_truth.stele_status_contradictions(sample)
        }
        self.assertTrue(
            any("authenticated tools/list is authoritative" in label for label in labels)
        )

        for test_kind in ("integration", "unit", "conformance"):
            for descriptor in ("mock", "fixture", "sample", "synthetic"):
                sample = (
                    f"The {test_kind} test for Hosted Stele MCP exposes seven "
                    f"{descriptor} endpoints."
                )
                with self.subTest(sample=sample):
                    self.assertEqual(
                        [], check_truth.stele_status_contradictions(sample)
                    )

        for sample in (
            "The integration test for Hosted Stele MCP exposes seven endpoints.",
            "The SDK fixture for Hosted Stele MCP reports nine capabilities.",
            "Hosted Stele MCP integration test exposes seven endpoints.",
            "Hosted Stele MCP's conformance test reports nine capabilities.",
            "Hosted Stele MCP does not fail to lack transaction tooling.",
        ):
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

        for descriptor in ("transaction", "signing", "broadcast", "submission"):
            for upper_bound in ("fewer than one", "less than 1", "at most zero"):
                sample = (
                    f"Hosted Stele MCP exposes {upper_bound} {descriptor} tools."
                )
                with self.subTest(sample=sample):
                    self.assertEqual(
                        [], check_truth.stele_status_contradictions(sample)
                    )

    def test_strict_review_catalog_expression_families(self) -> None:
        contradictions = (
            ("The public catalog contains between one and three listings.", 1),
            ("The Stele catalog holds one to four services.", 1),
            ("The catalog has no fewer than one published service.", 1),
            ("The public catalog holds twice three listings.", 6),
            ("The public catalog contains two groups, each with three listings.", 6),
            ("The public catalog contains a pair and a trio of listings.", 5),
            ("The public catalog has half a dozen listings.", 6),
            ("The public catalog, as of today, holds a trio of services.", 3),
            ("Inventory at the public catalog: two listings.", 2),
            ("The public catalog contains one plus a pair plus a trio of listings.", 6),
            ("The public catalog contains three or more listings.", 3),
            ("The public catalog holds three batches, each containing two entries.", 6),
        )
        for sample, actual in contradictions:
            with self.subTest(sample=sample):
                labels = {
                    label
                    for _, label in check_truth.stele_status_contradictions(sample)
                }
                self.assertTrue(
                    any(
                        str(actual) in label and "expected zero" in label
                        for label in labels
                    ),
                    msg=f"expected typed catalog rejection for {sample!r}",
                )

        controls = (
            "The public catalog contains one or fewer listings.",
            "The public catalog contains between zero and three listings.",
            "The public catalog contains up to half a dozen listings.",
            "The warning says “The public catalog contains two listings” and rejects that claim.",
            "The note says ‘The Stele catalog holds four services’ and refutes this statement.",
            "The warning says “The public catalog contains two listings.” and rejects that claim.",
            "The warning says “The public catalog contains two listings. The Stele catalog has three services.” and rejects that claim.",
            "The catalog does not have no fewer than one published service.",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_strict_review_provider_studio_link_scope_families(self) -> None:
        contradictions = (
            "In Provider Studio, [create a provider draft](https://evil.example/studio) now.",
            "Within Provider Studio, [edit provider-listing drafts](https://evil.example/edit).",
            "Use Provider Studio to [preview a provider draft](../studio-preview).",
            "Provider Studio has no payment controls and lets users [create a provider draft](https://evil.example/studio).",
            "[Provider Studio](https://evil.example/studio) was a prototype and is now live.",
        )
        for sample in contradictions:
            with self.subTest(sample=sample):
                self.assertNotEqual(
                    [], check_truth.provider_studio_url_violations(sample)
                )

        controls = (
            "In 2024, [Provider Studio](https://old.example/studio) was a prototype.",
            "The [Provider Studio](https://old.example/studio) was a retired preview.",
            "In a future release, [Provider Studio](https://future.example/studio) will be a preview.",
            "Provider Studio is safe, but another API lets you [create a provider draft](https://evil.example/studio).",
            "Provider Studio does not let users [create a provider draft](https://evil.example/studio).",
            "Provider Studio prevents users from [creating a provider draft](https://evil.example/studio).",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual(
                    [], check_truth.provider_studio_url_violations(sample)
                )

    def test_second_no_go_named_scope_and_ownership_families(self) -> None:
        contradictions = (
            (
                "Hosted Stele MCP exposes public catalog search, bounded "
                "booking-draft preparation, and service health.",
                "hosted Stele MCP presents 3 unconditional named capabilities; authenticated tools/list is authoritative",
            ),
            (
                "The public catalog lists a GPU rental service and an indexing service.",
                "Stele catalog names 2 live inventory items; expected zero",
            ),
            (
                "Hosted Stele MCP has fewer than one broadcast endpoint; "
                "nevertheless, it signs transactions.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP does not fail not to lack transaction tooling.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Provider Studio lets providers "
                "[delete their draft](https://evil.example/delete).",
                "non-canonical Provider Studio URL",
            ),
            (
                "Hosted Stele MCP includes service search, booking draft preparation, "
                "and diagnostic export.",
                "hosted Stele MCP presents 3 unconditional named capabilities; authenticated tools/list is authoritative",
            ),
            (
                "The Stele catalog features GPU compute and vector indexing services.",
                "Stele catalog names 2 live inventory items; expected zero",
            ),
            (
                "Hosted Stele MCP exposes fewer than one signing endpoint; "
                "it still signs transactions.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Providers use Provider Studio to "
                "[manage their drafts](https://wrong.example/drafts).",
                "non-canonical Provider Studio URL",
            ),
        )
        for sample, expected in contradictions:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

        controls = (
            "The warning says “Hosted Stele MCP exposes three tools; the public "
            "catalog has two listings.”; it rejects both claims.",
            "The archived audit report says Hosted Stele MCP exposed three tools.",
            "According to the archived audit report, Hosted Stele MCP exposed "
            "three endpoints.",
            "Hosted Stele MCP fixture models seven endpoints.",
            "Hosted Stele MCP simulation depicts a dozen capabilities.",
            "Hosted Stele MCP does not fail to lack transaction tooling.",
            "Hosted Stele MCP exposes fewer than one signing endpoint; another API "
            "exists; nevertheless, it signs transactions.",
            "Hosted Stele MCP exposes no broadcast endpoint; a separate worker "
            "exists; yet it broadcasts transactions.",
            "Providers use Provider Studio, but another API lets them "
            "[manage their drafts](https://wrong.example/drafts).",
            "Provider Studio does not let providers "
            "[delete their draft](https://evil.example/delete).",
            "Keep [Provider Studio](https://old.example/studio), which was retired "
            "in 2024, for audit history.",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_second_no_go_exact_nine_case_acceptance_corpus(self) -> None:
        contradictions = (
            (
                "Hosted Stele MCP exposes public catalog search, bounded "
                "booking-draft preparation, and service health.",
                "hosted Stele MCP presents 3 unconditional named capabilities; authenticated tools/list is authoritative",
            ),
            (
                "The public catalog lists a GPU rental service and an indexing service.",
                "Stele catalog names 2 live inventory items; expected zero",
            ),
            (
                "Hosted Stele MCP has fewer than one broadcast endpoint; "
                "nevertheless, it signs transactions.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP does not fail not to lack transaction tooling.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Provider Studio lets providers "
                "[delete their draft](https://evil.example/delete).",
                "non-canonical Provider Studio URL",
            ),
        )
        for sample, expected in contradictions:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, expected)

        controls = (
            "The warning says “Hosted Stele MCP exposes three tools; the public "
            "catalog has two listings.”; it rejects both claims.",
            "The archived audit report says Hosted Stele MCP exposed three tools.",
            EXACT_HISTORICAL_STUDIO_CONTROL,
            "Hosted Stele MCP fixture models seven endpoints.",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

    def test_dated_historical_studio_lifecycle_scope(self) -> None:
        controls = (
            EXACT_HISTORICAL_STUDIO_CONTROL,
            "During the 2023 beta, [Provider Studio](https://old.example/studio) "
            "was active until its decommissioning.",
            "In 2022, [Provider Studio](https://old.example/studio) was available "
            "prior to its removal.",
            "From 2021 to 2023, [Provider Studio](https://old.example/studio) was "
            "operational before being retired.",
            "In 2020, [Provider Studio](https://old.example/studio) was reachable "
            "but was later shut down.",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

        contradictions = (
            "In 2024, [Provider Studio](https://wrong.example/studio) was live "
            "before it was retired, but it is now live.",
            "In 2024, [Provider Studio](https://old.example/studio) was live before "
            "it was retired. Provider Studio now lets providers "
            "[edit their draft](https://wrong.example/edit).",
            "In 2024, [Provider Studio](https://old.example/studio) was active "
            "until its removal; today, "
            "[Provider Studio](https://wrong.example/studio) is available.",
            "[Provider Studio](https://wrong.example/studio) is currently available.",
            "In 2024, [Provider Studio](https://wrong.example/studio) was live "
            "before it was retired, but it has since reopened.",
            "The historical report says "
            "[Provider Studio](https://wrong.example/studio) is now live.",
        )
        for sample in contradictions:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, "non-canonical Provider Studio URL")

    def test_eighth_review_exact_clause_local_studio_corpus(self) -> None:
        controls = (
            EXACT_HISTORICAL_STUDIO_CONTROL,
            EXACT_DISTINCT_API_CONTROL,
            EXACT_PRIOR_TO_RETIREMENT_CONTROL,
            EXACT_UNTIL_DECOMMISSION_CONTROL,
            EXACT_QUOTED_REJECTION_CONTROL,
            EXACT_DISTINCT_PORTAL_CONTROL,
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

        contradictions = (
            EXACT_DOCUMENTARY_BLEED_REJECT,
            EXACT_RETIRED_RELAUNCHED_REJECT,
            EXACT_HISTORY_REOPENED_REJECT,
            EXACT_REVERSE_EDIT_REJECT,
            EXACT_PREFIX_REVISE_REJECT,
            EXACT_REVERSE_MANAGE_REJECT,
            EXACT_ADJACENT_OPEN_REJECT,
        )
        for sample in contradictions:
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, "non-canonical Provider Studio URL")

    def test_eighth_review_generated_studio_grammar(self) -> None:
        for verb, base in (
            ("denies", "deny"),
            ("disputes", "dispute"),
            ("rejects", "reject"),
            ("refutes", "refute"),
        ):
            sample = (
                f"The review {verb} the statement “"
                "[Provider Studio](https://wrong.example/studio) is live today.”"
            )
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

            current = (
                f"The review does not {base} the statement “"
                "[Provider Studio](https://wrong.example/studio) is live today.”"
            )
            with self.subTest(sample=current):
                self.assert_contradiction(
                    current, "non-canonical Provider Studio URL"
                )

        historical_controls = (
            "In 2021, [Provider Studio](https://old.example/studio) was active "
            "prior to being decommissioned.",
            "In 2022, [Provider Studio](https://old.example/studio) was available "
            "until it was removed.",
            "In 2023, [Provider Studio](https://old.example/studio) was live "
            "before it was shut down.",
            "In 2020, [Provider Studio](https://old.example/studio) was operational "
            "but was later withdrawn.",
        )
        for sample in historical_controls:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

        for verb in ("reactivated", "relaunched", "reopened", "returned"):
            same_clause = (
                "The [Provider Studio](https://wrong.example/studio) was retired, "
                f"then {verb} today."
            )
            adjacent = (
                "In 2024, [Provider Studio](https://wrong.example/studio) was live "
                f"before retirement; it {verb} today."
            )
            for sample in (same_clause, adjacent):
                with self.subTest(sample=sample):
                    self.assert_contradiction(
                        sample, "non-canonical Provider Studio URL"
                    )

        for verb in ("edit", "manage", "revise", "update"):
            reverse = (
                f"Providers can [{verb} their draft](https://wrong.example/edit) "
                "in Provider Studio."
            )
            forward = (
                f"In Provider Studio, providers [{verb} their draft]"
                "(https://wrong.example/edit)."
            )
            for sample in (reverse, forward):
                with self.subTest(sample=sample):
                    self.assert_contradiction(
                        sample, "non-canonical Provider Studio URL"
                    )

        for action in ("Access", "Enter", "Launch", "Open", "Use", "Visit"):
            sample = (
                "Provider Studio remains available today. "
                f"[{action} the Studio](https://wrong.example/studio)."
            )
            with self.subTest(sample=sample):
                self.assert_contradiction(sample, "non-canonical Provider Studio URL")

        distinct_controls = (
            "In 2024, [Provider Studio](https://old.example/studio) was live before "
            "retirement. The customer portal was repaired, but it is now live.",
            "In 2024, [Provider Studio](https://old.example/studio) was live before "
            "retirement. The system was repaired, but it is now available.",
            "In 2024, [Provider Studio](https://old.example/studio) was live before "
            "retirement, while clients now use "
            "[the account portal](https://accounts.example/portal).",
        )
        for sample in distinct_controls:
            with self.subTest(sample=sample):
                self.assertEqual([], check_truth.stele_status_contradictions(sample))

        mixed = (
            "The warning rejects the claim “"
            "[Provider Studio](https://wrong.example/studio) is live today.” "
            "Open [Provider Studio](https://evil.example/studio) now."
        )
        self.assert_contradiction(mixed, "non-canonical Provider Studio URL")

    def test_final_review_exact_structural_and_control_corpus(self) -> None:
        for sample in (
            EXACT_STRUCTURAL_HEADING_REJECT,
            EXACT_STRUCTURAL_IMAGE_REJECT,
        ):
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "non-canonical Provider Studio URL"
                )

        for sample in (
            EXACT_HISTORICAL_RANGE_CONTROL,
            EXACT_NATURAL_DISAVOWAL_CONTROL,
        ):
            with self.subTest(sample=sample):
                self.assertEqual(
                    [], check_truth.stele_status_contradictions(sample)
                )

    def test_final_review_structural_link_families(self) -> None:
        contradictions = (
            "## Provider Studio\n\n"
            "[Open the workspace](https://evil.example/launch).",
            "## Provider Studio\n\n"
            "1. Authenticate with Browser Wallet.\n"
            "2. [Launch the editor](https://evil.example/editor).",
            "Provider Studio is live today.\n\n"
            "1. Sign in...\n"
            "2. [Manage your provider draft](https://evil.example/manage).",
            "## Provider Studio\n\n"
            "Sign in. Continue. "
            "[Manage your provider draft](https://evil.example/manage).",
            "Provider Studio is live today. It is ready for providers. "
            "[Open the workspace](https://evil.example/launch).",
            "Provider Studio remains available today. Wallet authentication "
            "comes first. [Enter the editor](https://evil.example/editor).",
            "## Provider Studio\n\n"
            "[![Enter the editor](studio-button.png)]"
            "(https://evil.example/editor).",
            "## Provider Studio\n\n"
            "[![Visit the Studio](studio-button.png)][wrong]\n\n"
            "[wrong]: https://evil.example/studio",
            "The review rejects the claim “"
            "[Provider Studio](https://wrong.example/studio) is live today.”\n\n"
            "- [Open the Studio](https://evil.example/studio) now.",
            "The audit refutes “"
            "[Provider Studio](https://wrong.example/studio) is available.”\n\n"
            "1. Read the warning.\n"
            "2. [Launch the workspace](https://evil.example/workspace).",
        )
        for sample in contradictions:
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "non-canonical Provider Studio URL"
                )

        controls = (
            "Book a tour: [Visit the Studio](https://art.example/studio).",
            "The film crew will "
            "[enter the Studio](https://art.example/soundstage).",
            "# Provider Studio\n\n## Customer portal\n\n"
            "[Manage your provider draft](https://accounts.example/manage).",
            "# Provider Studio\n\n## Service API\n\n"
            "[Open the workspace](https://api.example/workspace).",
            "## Retired Provider Studio\n\n"
            "[Open the Studio](https://old.example/studio) for audit history.",
            "## Provider Studio documentation\n\n"
            "[Open the guide](https://docs.example/studio).",
            "## Provider Studio\n\n"
            "[Open the workspace](https://stele.monolythium.com/studio).",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual(
                    [], check_truth.stele_status_contradictions(sample)
                )

    def test_final_review_historical_documentary_and_renderer_parity(self) -> None:
        controls = (
            "From 2019 to 2021, "
            "[Provider Studio](https://old.example/studio) served providers.",
            "Between 2018 and 2020, "
            "[Provider Studio](https://old.example/studio) operated for beta users.",
            "Provider drafts had been handled by "
            "[Provider Studio](https://old.example/studio) before its retirement "
            "in 2021.",
            "The [Provider Studio](https://old.example/studio), a retired 2021 "
            "prototype, is preserved for audit history.",
            "The [Provider Studio](https://old.example/studio), a deprecated "
            "beta interface, remains in the changelog.",
            "[Provider Studio](https://old.example/studio) was decommissioned in "
            "2021 after operating as a beta.",
            "In 2019, <a href=\"https://old.example/studio\">Provider Studio</a> "
            "went live and stayed online until its retirement in 2021.",
            "In 2019, [Provider Studio][old] went live and stayed online until "
            "its retirement in 2021.\n\n[old]: https://old.example/studio",
            "The migration guide preserves "
            "[Provider Studio](https://old.example/studio) as an archived example.",
            "The deployment archive records "
            "[Provider Studio](https://old.example/studio) as a retired interface.",
            "The release record documents "
            "[Provider Studio](https://old.example/studio) as a deprecated reference.",
            "See the [Provider Studio](https://docs.example/studio) guide for an "
            "archived interface example.",
            "[Provider Studio](https://evil.example/studio) is explicitly not "
            "the current product destination.",
            "[Provider Studio](https://old.example/studio) formerly served providers.",
            "[Provider Studio](https://old.example/studio) previously served providers.",
            "[Provider Studio](https://old.example/studio) had served providers "
            "before 2021.",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual(
                    [], check_truth.stele_status_contradictions(sample)
                )

        documentary_overrides = (
            "[Provider Studio guide — open the live app]"
            "(https://evil.example/studio)",
            "[Provider Studio documentation and live product]"
            "(https://evil.example/studio)",
            "[Provider Studio examples — launch now]"
            "(https://evil.example/studio)",
        )
        for sample in documentary_overrides:
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "non-canonical Provider Studio URL"
                )

    def test_final_review_disavowal_polarity_and_current_return(self) -> None:
        disavowal_controls = (
            "The report calls “"
            "[Provider Studio](https://wrong.example/studio) is live” an "
            "incorrect statement.",
            "The audit identifies “"
            "[Provider Studio](https://wrong.example/studio) is live” as misleading.",
            "The note labels “"
            "[Provider Studio](https://wrong.example/studio) is current” a false claim.",
        )
        for sample in disavowal_controls:
            with self.subTest(sample=sample):
                self.assertEqual(
                    [], check_truth.stele_status_contradictions(sample)
                )

        disavowal_reversals = (
            "The review does not say the sentence “"
            "[Provider Studio](https://evil.example/studio) is public now” is false.",
            "The review never said the sentence “"
            "[Provider Studio](https://evil.example/studio) is public now” was false.",
            "No review says the sentence “"
            "[Provider Studio](https://evil.example/studio) is public now” is false.",
            "The review says “"
            "[Provider Studio](https://evil.example/studio) is public now” is "
            "false, but actually true.",
            "The audit did not call “"
            "[Provider Studio](https://evil.example/studio) is live” invalid.",
            "The auditor doesn’t call “"
            "[Provider Studio](https://evil.example/studio) is live” a wrong "
            "statement.",
        )
        for sample in disavowal_reversals:
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "non-canonical Provider Studio URL"
                )

        historical_base = (
            "In 2019, [Provider Studio](https://old.example/studio) went live "
            "and stayed online until its retirement in 2021"
        )
        current_returns = (
            ", but it is back online today.",
            ", but it came back online today.",
            ", but users can access it again today.",
            ", but it resumed service today.",
            ", but it returned to service today.",
            ", and today it serves providers again.",
            ", yet customers use it again today.",
            ", then it resumed operations today.",
            ", but it restored operations today.",
        )
        for suffix in current_returns:
            sample = historical_base + suffix
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "non-canonical Provider Studio URL"
                )

        for sample in (
            "[Provider Studio](https://evil.example/studio) was never retired.",
            "[Provider Studio](https://evil.example/studio) was not decommissioned.",
        ):
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "non-canonical Provider Studio URL"
                )

    def test_final_review_fresh_structural_holdouts(self) -> None:
        for heading, action in (
            ("Provider Studio workspace", "Access your provider draft"),
            ("Provider Studio is operational", "Visit the editor"),
            ("Provider Studio", "Use this workspace"),
        ):
            sample = (
                f"### {heading}\n\n1. Connect the wallet.\n"
                f"2. [{action}](https://holdout.invalid/studio)."
            )
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "non-canonical Provider Studio URL"
                )

        controls = (
            "During 2018, [Provider Studio](https://archive.invalid/studio) "
            "hosted a closed prototype before it was sunset.",
            "The interface manual preserves "
            "[Provider Studio](https://archive.invalid/studio) as an archived "
            "reference.",
            "The assessor marks “"
            "[Provider Studio](https://wrong.invalid/studio) is production” as "
            "an invalid assertion.",
            "# Provider Studio\n\n## Buyer account portal\n\n"
            "[Use this workspace](https://accounts.invalid/workspace).",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual(
                    [], check_truth.stele_status_contradictions(sample)
                )

    def test_final_independent_holdout_regressions(self) -> None:
        contradictions = (
            "## Future Provider Studio workspace\n\n"
            "The product is released now: "
            "[Enter this workspace](https://rogue.example/current).",
            "## Provider Studio workspace\n\n"
            "- [Go to the workspace](https://rogue.example/go)",
            "## Provider Studio workspace\n\n"
            "[![Start a listing draft](start.svg)]"
            "(https://rogue.example/start)",
            "## Provider Studio\n\n"
            "[![Start your provider draft](go.svg)]"
            "(https://rogue.example/provider-start)",
            "[Provider Studio](https://legacy.example/studio) was retired in "
            "2023, but it has been restored and is serving providers today.",
            "The operations guide shows the "
            "[Provider Studio](https://rogue.example/console) as the production "
            "console.",
        )
        for sample in contradictions:
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "non-canonical Provider Studio URL"
                )

        controls = (
            "Provider Studio is operational. The recording studio is "
            "[open here](https://music.example/room) for musicians.",
            "# Provider Studio reference\n\n"
            "## Unrelated recording studio\n\n"
            "[Open this workspace](https://music.example/workspace)",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual(
                    [], check_truth.stele_status_contradictions(sample)
                )

    def test_final_raw_destination_tokens_do_not_change_polarity(self) -> None:
        for hostname in (
            "false.example",
            "invalid.example",
            "obsolete.example",
            "unsafe.example",
            "wrong.example",
        ):
            sample = (
                "Provider Studio's production route is "
                f"https://{hostname}/studio and providers use it now."
            )
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "non-canonical Provider Studio URL"
                )

        controls = (
            "Provider Studio is not hosted at https://invalid.example/studio.",
            "The https://wrong.example/studio route is not the Provider Studio "
            "destination.",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual(
                    [], check_truth.stele_status_contradictions(sample)
                )

    def test_final_postfix_holdout_regressions(self) -> None:
        contradictions = (
            "During 2016, [Provider Studio](https://old.invalid/a) operated, "
            "yet it was restored and became active today.",
            "During 2016, [Provider Studio](https://old.invalid/a) operated, "
            "but it has been restored and now services providers.",
            "The report isn’t saying “"
            "[Provider Studio](https://x.invalid/a) is live” is false.",
            "No auditor calls “"
            "[Provider Studio](https://x.invalid/a) is current” an invalid claim.",
        )
        for sample in contradictions:
            with self.subTest(sample=sample):
                self.assert_contradiction(
                    sample, "non-canonical Provider Studio URL"
                )

        controls = (
            "Provider Studio is operational. The art studio is "
            "[open here](https://art.invalid/a) for painters.",
            "# Provider Studio\n\n## Community dance studio\n\n"
            "[Enter this workspace](https://dance.invalid/a).",
            "Provider Studio route https://invalid.example/a is explicitly "
            "invalid and must not be used.",
            "https://unsafe.example/a isn't the current Provider Studio route.",
        )
        for sample in controls:
            with self.subTest(sample=sample):
                self.assertEqual(
                    [], check_truth.stele_status_contradictions(sample)
                )


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

    def test_main_rejects_independent_rereview_counterexamples(self) -> None:
        for sample, expected in INDEPENDENT_REREVIEW_CONTRADICTIONS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_allows_independent_rereview_truthful_controls(self) -> None:
        for sample in INDEPENDENT_REREVIEW_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_rejects_independent_rereview_variations(self) -> None:
        for sample, expected in INDEPENDENT_REREVIEW_VARIATION_CONTRADICTIONS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_allows_independent_rereview_variation_controls(self) -> None:
        for sample in INDEPENDENT_REREVIEW_VARIATION_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_rejects_conditional_authority_rereview_corpus(self) -> None:
        for sample, expected in CONDITIONAL_AUTHORITY_REREVIEW_CONTRADICTIONS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_allows_conditional_authority_rereview_controls(self) -> None:
        for sample in CONDITIONAL_AUTHORITY_REREVIEW_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_wires_final_transition_contract_corpus(self) -> None:
        samples = (
            *(sample for sample, _ in FINAL_TRANSITION_REVIEW_CONTRADICTIONS),
            *(sample for sample, _ in FINAL_TRANSITION_NEARBY_CONTRADICTIONS),
            *(sample for sample, _ in FINAL_TRANSITION_ADVERSARIAL_CONTRADICTIONS),
        )
        result, stdout, stderr = self.run_append_check("\n\n".join(samples))
        self.assertEqual(1, result, msg=stdout)
        for expected in {
            *(expected for _, expected in FINAL_TRANSITION_REVIEW_CONTRADICTIONS),
            *(expected for _, expected in FINAL_TRANSITION_NEARBY_CONTRADICTIONS),
            *(expected for _, expected in FINAL_TRANSITION_ADVERSARIAL_CONTRADICTIONS),
        }:
            self.assertIn(expected, stderr)

    def test_main_allows_final_transition_truthful_controls(self) -> None:
        result, stdout, stderr = self.run_append_check(
            "\n\n".join(
                (
                    *FINAL_TRANSITION_TRUTHFUL_CONTROLS,
                    *FINAL_TRANSITION_ADVERSARIAL_CONTROLS,
                )
            )
        )
        self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_rejects_release_audit_exact_corpus(self) -> None:
        for sample, expected in RELEASE_AUDIT_EXACT_CONTRADICTIONS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_allows_release_audit_exact_truthful_controls(self) -> None:
        for sample in RELEASE_AUDIT_EXACT_TRUTHFUL_CONTROLS:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_rejects_fixed_hosted_tool_count_when_authority_anchor_remains(self) -> None:
        self.run_mutation(
            "2026/may/monolythium-whitepaper-v5.0.md",
            "| Hosted Stele MCP | Keyless and OAuth-protected; authenticated `tools/list` is the authoritative inventory;",
            "| Hosted Stele MCP | Keyless and OAuth-protected; authenticated `tools/list` is the authoritative inventory; "
            "Hosted Stele MCP exposes exactly four tools;",
            "hosted Stele MCP presents a fixed tool inventory; authenticated tools/list is authoritative",
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
            "hosted booking-draft preparation is unavailable without a published listing.",
            "hosted booking-draft preparation is unavailable without a published listing. "
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
            "exists only when that exact name appears in authenticated `tools/list`.",
            "exists only when that exact name appears in authenticated `tools/list`. "
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

    def test_main_rejects_seventh_review_semantic_representatives(self) -> None:
        samples = (
            (
                "Hosted Stele MCP serves catalog. Its operator wallet signs transactions.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP does not have zero transaction tools.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "The public catalog contains exactly two pairs of listings.",
                "Stele catalog claims exactly 4 listings; expected zero",
            ),
            (
                "In the public catalog, two listings currently exist.",
                "Stele catalog claims 2 listings; expected zero",
            ),
        )
        for sample, expected in samples:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_allows_seventh_review_semantic_controls(self) -> None:
        samples = (
            "Hosted Stele MCP is the operator. Alice's operator wallet signs transactions.",
            "Hosted Stele MCP serves catalog, but the user wallet does not have zero signing tools.",
            "The public catalog documentation contains exactly two listings.",
            "Another API contains two published services.",
            "The public catalog contains up to two listings.",
        )
        result, stdout, stderr = self.run_append_check("\n".join(samples))
        self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_rejects_required_anchors_present_only_in_html_comments(self) -> None:
        mutations = (
            (
                "Its authenticated `tools/list` response is the authoritative inventory for that session.",
                "Its inventory is deployment-specific. "
                "<!-- authenticated tools/list response is the authoritative inventory for that session -->",
                "missing Stele status anchor 'authenticated tools/list response is the authoritative inventory for that session'",
            ),
            (
                "The gated `stele_create_provider_listing_draft` tool exists only when that exact name appears in authenticated `tools/list`.",
                "The gated provider-draft tool is deployment-specific. "
                "<!-- stele_create_provider_listing_draft exists only when that exact name appears in authenticated tools/list -->",
                "missing Stele status anchor 'exists only when that exact name appears in authenticated tools/list'",
            ),
            (
                "When listed, each successful `stele_create_provider_listing_draft` operation creates exactly one new private wallet-owned unpublished provider-listing draft.",
                "When listed, the tool creates a private draft. "
                "<!-- each successful stele_create_provider_listing_draft operation creates exactly one new private wallet-owned unpublished provider-listing draft -->",
                "missing Stele status anchor 'each successful stele_create_provider_listing_draft operation creates exactly one new private wallet-owned unpublished provider-listing draft'",
            ),
            (
                "An idempotent replay returns the same draft without creating another.",
                "A retry is implementation-defined. "
                "<!-- an idempotent replay returns the same draft without creating another -->",
                "missing Stele status anchor 'an idempotent replay returns the same draft without creating another'",
            ),
            (
                "authentication proves only current control of the selected wallet address",
                "authentication verifies the selected address "
                "<!-- authentication proves only current control of the selected wallet address -->",
                "missing Stele status anchor 'authentication proves only current control of the selected wallet address'",
            ),
            (
                "[stele.monolythium.com/studio](https://stele.monolythium.com/studio)",
                "stele.monolythium.com/studio "
                "<!-- [Provider Studio](https://stele.monolythium.com/studio) -->",
                "missing visible canonical Provider Studio link",
            ),
        )
        for old, new, expected in mutations:
            with self.subTest(old=old):
                result, stdout, stderr = self.run_check("README.md", old, new)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

    def test_main_round_two_fresh_representative_holdout(self) -> None:
        contradictions = (
            (
                "Hosted Stele MCP has two tools and a third endpoint.",
                "authenticated tools/list is authoritative",
            ),
            (
                "Hosted Stele MCP acts in its capacity as operator. The operator signer signs transactions.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "Hosted Stele MCP transaction endpoint count is greater than 0.",
                "hosted Stele MCP claims transaction capability",
            ),
            (
                "The public catalog holds two sets of three listings.",
                "expected zero",
            ),
            (
                "Open [Provider Studio].\n\n[Provider Studio]: https://evil.example/studio",
                "non-canonical Provider Studio URL",
            ),
        )
        for sample, expected in contradictions:
            with self.subTest(sample=sample):
                result, stdout, stderr = self.run_append_check(sample)
                self.assertEqual(1, result, msg=stdout)
                self.assertIn(expected, stderr)

        controls = (
            "Hosted Stele MCP documents an SDK fixture with five tools.",
            "Hosted Stele MCP serves catalog. The replacement wallet signs transactions.",
            'Archived documentation says "The public catalog contains two listings."',
            "Reference documentation for Provider Studio is [available here](https://docs.example/studio).",
        )
        result, stdout, stderr = self.run_append_check("\n\n".join(controls))
        self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_strict_review_semantic_and_link_candidate(self) -> None:
        contradictions = (
            "Hosted Stele MCP offers three or more capabilities.",
            "Hosted Stele MCP is not without a transaction endpoint.",
            "Hosted Stele MCP cannot be described as having no signing capability.",
            "Hosted Stele MCP fails to lack transaction tooling.",
            "Hosted Stele MCP transaction endpoint count exceeds zero.",
            "Hosted Stele MCP is not devoid of broadcast capability.",
            "The public catalog contains between one and three listings.",
            "The Stele catalog holds one to four services.",
            "The catalog has no fewer than one published service.",
            "The public catalog holds twice three listings.",
            "The public catalog contains two groups, each with three listings.",
            "The public catalog contains a pair and a trio of listings.",
            "The public catalog has half a dozen listings.",
            "The public catalog, as of today, holds a trio of services.",
            "Inventory at the public catalog: two listings.",
            "In Provider Studio, [create a provider draft](https://evil.example/studio) now.",
            "Hosted Stele MCP has signing authority despite a policy requiring fewer than one transaction tool.",
            "Hosted Stele MCP exposes seven tools and one mock endpoint.",
            "Provider Studio has no payment controls and lets users [create a provider draft](https://evil.example/studio).",
            "[Provider Studio](https://evil.example/studio) was a prototype and is now live.",
        )
        result, stdout, stderr = self.run_append_check("\n\n".join(contradictions))
        self.assertEqual(1, result, msg=stdout)
        for expected in (
            "authenticated tools/list is authoritative",
            "hosted Stele MCP claims transaction capability",
            "expected zero",
            "non-canonical Provider Studio URL",
        ):
            self.assertIn(expected, stderr)

        controls = (
            "The integration test for Hosted Stele MCP exposes seven mock endpoints.",
            "Hosted Stele MCP exposes fewer than one transaction tool.",
            "The warning says “The public catalog contains two listings” and rejects that claim.",
            "In 2024, [Provider Studio](https://old.example/studio) was a prototype.",
            "The integration test for Hosted Stele MCP exposes seven endpoints.",
            "Hosted Stele MCP does not fail to lack transaction tooling.",
            "The catalog does not have no fewer than one published service.",
            "The warning says “The public catalog contains two listings. The Stele catalog has three services.” and rejects that claim.",
            "Provider Studio is safe, but another API lets you [create a provider draft](https://evil.example/studio).",
        )
        result, stdout, stderr = self.run_append_check("\n\n".join(controls))
        self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_second_no_go_scope_ownership_candidate(self) -> None:
        contradictions = (
            "Hosted Stele MCP exposes public catalog search, bounded "
            "booking-draft preparation, and service health.",
            "The public catalog lists a GPU rental service and an indexing service.",
            "Hosted Stele MCP has fewer than one broadcast endpoint; "
            "nevertheless, it signs transactions.",
            "Hosted Stele MCP does not fail not to lack transaction tooling.",
            "Provider Studio lets providers "
            "[delete their draft](https://evil.example/delete).",
        )
        result, stdout, stderr = self.run_append_check("\n\n".join(contradictions))
        self.assertEqual(1, result, msg=stdout)
        for expected in (
            "authenticated tools/list is authoritative",
            "expected zero",
            "hosted Stele MCP claims transaction capability",
            "non-canonical Provider Studio URL",
        ):
            self.assertIn(expected, stderr)

        controls = (
            "The warning says “Hosted Stele MCP exposes three tools; the public "
            "catalog has two listings.”; it rejects both claims.",
            "The archived audit report says Hosted Stele MCP exposed three tools.",
            "Hosted Stele MCP fixture models seven endpoints.",
            "Hosted Stele MCP does not fail to lack transaction tooling.",
            "Providers use Provider Studio, but another API lets them "
            "[manage their drafts](https://wrong.example/drafts).",
            "Keep [Provider Studio](https://old.example/studio), which was retired "
            "in 2024, for audit history.",
            EXACT_HISTORICAL_STUDIO_CONTROL,
        )
        result, stdout, stderr = self.run_append_check("\n\n".join(controls))
        self.assertEqual(0, result, msg=stderr or stdout)

    def test_main_eighth_review_clause_local_studio_candidate(self) -> None:
        controls = (
            EXACT_HISTORICAL_STUDIO_CONTROL,
            EXACT_DISTINCT_API_CONTROL,
            EXACT_PRIOR_TO_RETIREMENT_CONTROL,
            EXACT_UNTIL_DECOMMISSION_CONTROL,
            EXACT_QUOTED_REJECTION_CONTROL,
            EXACT_DISTINCT_PORTAL_CONTROL,
        )
        result, stdout, stderr = self.run_append_check("\n\n".join(controls))
        self.assertEqual(0, result, msg=stderr or stdout)

        contradictions = (
            EXACT_DOCUMENTARY_BLEED_REJECT,
            EXACT_RETIRED_RELAUNCHED_REJECT,
            EXACT_HISTORY_REOPENED_REJECT,
            EXACT_REVERSE_EDIT_REJECT,
            EXACT_PREFIX_REVISE_REJECT,
            EXACT_REVERSE_MANAGE_REJECT,
            EXACT_ADJACENT_OPEN_REJECT,
        )
        result, stdout, stderr = self.run_append_check("\n\n".join(contradictions))
        self.assertEqual(1, result, msg=stdout)
        self.assertIn("non-canonical Provider Studio URL", stderr)


if __name__ == "__main__":
    unittest.main()
