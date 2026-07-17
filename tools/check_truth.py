#!/usr/bin/env python3
"""Fail closed on regressions in the reconciled public capability boundary."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS = (
    ROOT / "2026/may/monolythium-whitepaper-v5.0.md",
    ROOT / "2026/may/monolythium-lightpaper-v5.0.md",
)
STELE_STATUS_DOCUMENTS = (
    *DOCUMENTS,
    ROOT / "README.md",
    ROOT / "CHANGELOG.md",
)
CANONICAL_STUDIO_MARKDOWN_DESTINATION = "](https://stele.monolythium.com/studio)"

FORBIDDEN = {
    "agent suite presented as shipped": re.compile(
        r"\b(?:Monolythium|the chain)\s+ships\s+(?:the\s+)?(?:four|eight|those)\b",
        re.IGNORECASE,
    ),
    "Stele Desktop product claim": re.compile(r"\bStele Desktop\b", re.IGNORECASE),
    "embedded Stele wallet claim": re.compile(
        r"\bStele\s+(?:is|ships|runs)\s+(?:as\s+)?(?:an?\s+)?(?:embedded|desktop-wallet)",
        re.IGNORECASE,
    ),
    "wallet feature presented as shipped": re.compile(
        r"\breference wallet ships\b", re.IGNORECASE
    ),
    "current agent-commerce fee claim": re.compile(
        r"\b(?:spending-policy registration.{0,100}pays? a small|escrow (?:opening|& dispute fees?).{0,100}(?:all )?settle(?:s)? in LYTH)\b",
        re.IGNORECASE,
    ),
    "hosted MCP status presented as a third capability": re.compile(
        r"\bHosted Stele MCP\s*\|\s*Keyless catalog search, status\b",
        re.IGNORECASE,
    ),
    "current USDC agent-payment route": re.compile(
        r"\bAgents paying USDC for an API call still pay LYTH gas\b",
        re.IGNORECASE,
    ),
    "agent-commerce modules presented as current": re.compile(
        r"\bNative protocol modules[^\n]*agent-commerce registries, spending policy\b",
        re.IGNORECASE,
    ),
    "spending policy presented as currently audited": re.compile(
        r"\bspending-policy enforcement\s+—\s+into a small set of native modules audited at the protocol layer\b",
        re.IGNORECASE,
    ),
    "agent identity presented as current": re.compile(
        r"\bAgent identity is chain-native\b", re.IGNORECASE
    ),
    "economic runbooks presented as current": re.compile(
        r"\bRunbooks are typed and signed\b", re.IGNORECASE
    ),
    "spending policy presented as currently enforced": re.compile(
        r"\bThe chain enforces policy at admission\b", re.IGNORECASE
    ),
    "categorical desktop removal claim": re.compile(
        r"\bThe desktop wallet has no Stele marketplace surface\b",
        re.IGNORECASE,
    ),
}

STALE_STELE_DEPLOYMENT = {
    "Stele hostname still described as reserved": re.compile(
        r"\b(?:"
        r"reserved(?:\s+canonical)?(?:\s+production)?\s+hostname|"
        r"(?:canonical\s+)?production\s+hostname\s+is\s+reserved|"
        r"reserved\s+Stele(?:\s+production)?\s+hostname"
        r")\b",
        re.IGNORECASE,
    ),
    "Stele deployment still described as unavailable": re.compile(
        r"\b(?:"
        r"does\s+not\s+publish(?:\s+it)?\s+as\s+a\s+live\s+link|"
        r"intentionally\s+not\s+(?:a\s+live\s+link|linked)|"
        r"not\s+published\s+as\s+a\s+live\s+link|"
        r"publication\s+of.{0,160}?live\s+destination\s+remains\s+gated"
        r")\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

REQUIRED = (
    "target agent-commerce",
    "standalone public web product",
    "three read/status tools",
    "no transaction tool",
    "degraded/stale",
    "exactly two OAuth-protected tools",
    "public catalog search",
    "booking-draft preparation",
    "legacy or unreconciled desktop builds",
)

STELE_STATUS_REQUIRED = (
    "public preview is live at",
    "https://stele.monolythium.com",
    "zero published services",
    "Browser Wallet v0.4.5 is a prerelease",
    "public web authenticates users through Browser Wallet",
    "authentication proves only current control of the selected wallet address",
    "does not prove a human or legal identity, durable ownership, credentials, or authority",
    "Provider Studio",
    "create, edit, preview, and delete private wallet-owned provider-listing drafts",
    "durable provider-listing drafts",
    "not published, discoverable, or transactable",
    "provider publication remains off",
    "Booking-approval drafts are separate",
    "inspect an existing valid non-economic booking-approval draft",
    "does not create booking-approval drafts",
    "public web exposes no booking, payment, settlement, or other economic controls",
    "Hosted Stele MCP",
    "exactly two OAuth-protected tools",
    "booking-draft preparation",
    "does not create or access provider-listing drafts",
    "Hosted booking-draft preparation is unavailable without a published listing",
    "local Stele MCP",
    "exactly three read/status tools",
    "no transaction tool",
    "economic writes",
    "transaction signing",
    "mainnet remain off",
)

COUNT_VALUES = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "a": 1,
    "an": 1,
}
COUNT_TOKEN = r"(?:\d+|" + "|".join(COUNT_VALUES) + r")"
TOOL_COUNT_TOKEN = (
    r"(?:\d+|"
    + "|".join(token for token in COUNT_VALUES if token not in {"a", "an"})
    + r")"
)

STELE_MCP_SURFACE = re.compile(
    r"\b(?:"
    r"(?P<hosted>Hosted\s+(?:Stele\s+)?MCP)|"
    r"(?P<local>(?:(?:isolated|separately\s+installed)\s+)?local\s+(?:Stele\s+)?MCP)"
    r")\b",
    re.IGNORECASE,
)
TOOL_COUNT_CLAIM = re.compile(
    rf"\b(?:(?P<qualifier>exactly|only|at\s+least|more\s+than|fewer\s+than|"
    rf"up\s+to|about|approximately)\s+)?(?P<count>{TOOL_COUNT_TOKEN})\s+"
    rf"(?:(?:[a-z][a-z0-9/-]*)(?:,\s*|\s+)){{0,4}}tools?\b",
    re.IGNORECASE,
)
PUBLISHED_SERVICE_COUNT = re.compile(
    rf"\b(?P<count>{COUNT_TOKEN})\s+published\s+services?\b",
    re.IGNORECASE,
)

INVENTORY_ENABLED = {
    "catalog claims an indefinite live inventory": re.compile(
        r"\b(?:some|several|multiple|many)\s+published\s+services?\b|"
        r"\b(?:non-empty|populated)\s+(?:public\s+)?catalog\b|"
        r"\b(?:public\s+)?catalog\s+(?:is\s+)?(?:non-empty|populated)\b|"
        r"\b(?:public\s+)?catalog\b[^.!?\n]{0,100}\b(?:contains|lists|offers|has)\s+"
        r"(?:some|several|multiple|many|live|available)\s+(?:services?|listings?)\b",
        re.IGNORECASE,
    ),
}

GATED_CAPABILITIES = {
    "economic writes": r"economic\s+writes?",
    "transaction signing": r"transaction\s+signing",
    "mainnet": r"mainnet",
    "provider publication": r"provider\s+publication",
}
ENABLED_STATE = r"(?:on|enabled|live|active|available|operational|permitted)"
REVERSE_ENABLED_STATE = r"(?:enabled|live|active|available|operational|permitted)"

PUBLIC_WEB_BOOKING_DRAFT_CREATION = {
    "public web claims booking-approval draft creation": re.compile(
        r"\b(?:the\s+)?(?:public\s+web|Provider\s+Studio)\b"
        r"(?:(?![.!?]).){0,180}?\b(?:"
        r"(?:can|does|will|now|currently)\s+(?!not\b)(?:create|prepare|generate|build)|"
        r"(?<!not\s)(?:creates|prepares|generates|builds)"
        r")\s+(?:an?\s+|short-lived\s+|non-economic\s+){0,4}"
        r"(?:booking(?:-approval)?|approval)[- ](?:drafts?|previews?)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "booking-approval draft creation assigned to public web": re.compile(
        r"\b(?:booking(?:-approval)?|approval)[- ](?:draft|preview)\s+creation\b"
        r"(?:(?![.!?]).){0,120}?\b(?:in|through|on)\s+(?:the\s+)?"
        r"(?:public\s+web|Provider\s+Studio)\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

STALE_PUBLIC_WEB_DRAFT_DENIAL = {
    "public web still denies every draft class": re.compile(
        r"\b(?:the\s+)?public\s+web\b(?:(?![.!?]).){0,160}?\b(?:"
        r"does\s+not|cannot|can't"
        r")\s+(?:create|prepare|manage)\s+(?:any\s+)?drafts?\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

BOOKING_DRAFT_WITHOUT_LISTING = {
    "booking-draft preparation claims no listing prerequisite": re.compile(
        r"\b(?:hosted\s+(?:Stele\s+)?MCP\s+)?"
        r"(?:booking(?:-approval)?|approval)[- ]draft\s+preparation\b"
        r"(?:(?![.!?]).){0,120}?\b(?:"
        r"(?:is\s+)?available\s+without|does\s+not\s+require|works?\s+without"
        r")\s+(?:an?\s+)?published\s+listing\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

PROVIDER_DRAFT_BOUNDARY = {
    "provider-listing draft presented as public or executable": re.compile(
        r"\b(?:private\s+|wallet-owned\s+){0,3}provider[- ]listing\s+drafts?\b"
        r"(?:(?![.!?]).){0,120}?\b(?:is|are|becomes?|remains?)\s+(?:now\s+)?"
        r"(?!not\b)(?:published|discoverable|transactable|on-chain)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "Provider Studio presented as a publication or transaction surface": re.compile(
        r"\bProvider\s+Studio\b(?:(?![.!?]).){0,180}?\b(?:"
        r"(?:can|does|will|now|currently)\s+(?!not\b)"
        r"(?:(?:create|prepare|manage)\s+and\s+)?"
        r"(?:publish|submit|broadcast|transact|execute)\w*|"
        r"(?<!not\s)(?:publishes|submits|broadcasts|transacts|executes)"
        r")\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "hosted MCP claims provider-listing draft authority": re.compile(
        r"\bHosted\s+(?:Stele\s+)?MCP\b(?:(?![.!?]).){0,180}?\b(?:"
        r"(?:can|does|will|now|currently)\s+(?!not\b)(?:create|prepare|access|manage)|"
        r"(?<!not\s)(?:creates|prepares|accesses|manages)"
        r")\s+(?:private\s+|wallet-owned\s+){0,3}provider[- ]listing\s+drafts?\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "provider-listing and booking-approval drafts are conflated": re.compile(
        r"\bprovider[- ]listing\s+drafts?\b(?:(?![.!?]).){0,100}?\b"
        r"(?:is|are|means?|equals?|(?:is|are)\s+the\s+same\s+as)\s+"
        r"(?:an?\s+)?booking[- ]approval\s+drafts?\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

IDENTITY_OVERCLAIMS = {
    "wallet authentication presented as identity proof": re.compile(
        r"\b(?:Browser\s+Wallet|wallet\s+authentication|that\s+authentication)\b"
        r"(?:(?![.!?]).){0,180}?\b(?:"
        r"owns?\s+(?:the\s+)?identity\s+proof|"
        r"(?:can|does|now|currently)\s+(?!not\b)"
        r"(?:prove|verify|establish|confirm|certify|demonstrate|authenticate|attest)\w*\s+(?:"
        r"(?:an?\s+|the\s+|user(?:['’]s)?\s+){0,3}"
        r"(?:human\s+|legal\s+|real-world\s+)?(?:identity|credentials|authority|ownership)|"
        r"who\s+(?:the\s+)?user\s+is)|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:proves|verifies|establishes|confirms|certifies|demonstrates|authenticates|attests)\s+(?:"
        r"(?:an?\s+|the\s+|user(?:['’]s)?\s+){0,3}"
        r"(?:human\s+|legal\s+|real-world\s+)?(?:identity|credentials|authority|ownership)|"
        r"who\s+(?:the\s+)?user\s+is)"
        r")\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

STUDIO_LINK_VIOLATIONS = {
    "non-canonical Provider Studio URL": re.compile(
        r"\bhttps://stele\.monolythium\.com/studio(?:/[^)\s]*|\?[^)\s]*|#[^)\s]*)",
        re.IGNORECASE,
    ),
}

STALE_ECONOMIC_PREVIEW = {
    "retired economic-preview claim": re.compile(
        r"\beconomic\s+actions?\s+remain\s+user-approved\s+previews?\b",
        re.IGNORECASE,
    ),
}

PUBLIC_WEB_FORBIDDEN_CAPABILITIES = {
    "public web claims provider-publication authority": re.compile(
        r"\b(?:the\s+)?(?:public\s+web|Stele\s+web|web\s+app)\b"
        r"(?:(?![.!?]).){0,180}?\b(?:"
        r"(?:can|does|now|currently)\s+(?!not\b)(?:publish|list)\w*"
        r"(?:(?![.!?]).){0,80}?\b(?:provider|service)\s+listings?\b|"
        r"(?<!not\s)(?<!never\s)(?:publishes|lists)\s+"
        r"(?:provider|service)\s+listings?\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:supports?|enables?|offers?|provides?|exposes?|includes?|has)"
        r"\s+(?!no\b|not\b)(?:provider\s+publication|publication\s+controls?)\b"
        r"|(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:lets?|allows?)\s+(?!no\b|not\b)(?:providers?|users?)\s+"
        r"(?:to\s+)?publish\w*\s+(?:(?:provider|service)\s+)?listings?\b"
        r"|(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:has|contains?|shows?|exposes?)\s+(?!no\b|not\b)(?:an?\s+)?"
        r"publish[- ]listing\s+(?:button|control|action)\b"
        r")",
        re.IGNORECASE | re.DOTALL,
    ),
    "provider publication assigned to public web": re.compile(
        r"\bprovider\s+publication\b(?:(?![.!?]).){0,120}?\b"
        r"(?:is|remains?)\s+(?:now\s+)?(?:available|enabled|live|active|operational)\b"
        r"(?:(?![.!?]).){0,80}?\b(?:on|through|in)\s+(?:the\s+)?"
        r"(?:public\s+web|Stele\s+web|web\s+app)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "public web claims booking, payment, settlement, or economic controls": re.compile(
        r"\b(?:the\s+)?(?:public\s+web|Stele\s+web|web\s+app)\b"
        r"(?:(?![.!?]).){0,180}?\b(?:"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:includes?|contains?|offers?|provides?|exposes?|supports?|enables?|has)"
        r"\s+(?!no\b|not\b)(?:(?![.!?]).){0,120}?\b"
        r"(?:booking|payment|settlement|economic)\s+"
        r"(?:controls?|actions?|buttons?|workflows?)\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:supports?|enables?|offers?|provides?|handles?)"
        r"\s+(?!no\b|not\b)(?:bookings?|payments?|settlements?)\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:accepts?)\s+(?!no\b|not\b)bookings?\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:lets?|allows?)\s+(?!no\b|not\b)(?:users?|customers?)\s+"
        r"(?:to\s+)?(?:book|pay|purchase|settle)\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)(?<!or\s)"
        r"(?:process(?:es)?\s+(?:bookings?(?![- ](?:approval|draft))|payments?)|"
        r"settles?\s+bookings?)\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)(?<!or\s)"
        r"operates?\s+(?!no\b|not\b)"
        r"(?:booking|payment|settlement|economic)\s+workflows?\b|"
        r"(?:can|does|now|currently)\s+(?!not\b)"
        r"(?:book|pay|settle|purchase|execute)\w*\b"
        r")",
        re.IGNORECASE | re.DOTALL,
    ),
    "booking, payment, settlement, or economic controls assigned to public web": re.compile(
        r"\b(?:booking|payment|settlement|economic)\s+"
        r"(?:controls?|actions?|buttons?|workflows?)\b"
        r"(?:(?![.!?]).){0,120}?\b(?:are|remain)\s+(?:now\s+)?"
        r"(?:available|enabled|live|active|operational)\b"
        r"(?:(?![.!?]).){0,80}?\b(?:on|through|in)\s+(?:the\s+)?"
        r"(?:public\s+web|Stele\s+web|web\s+app)\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

HOSTED_TRANSACTION_ENABLED = {
    "hosted Stele MCP claims transaction capability": re.compile(
        r"\b(?:can|does|now|currently)\s+(?!not\b)"
        r"(?:create|prepare|sign|broadcast|submit|settle|execute)\w*\b"
        r"(?:(?![.!?]).){0,120}?\b"
        r"(?:transactions?|payments?|settlements?|wallet\s+payloads?|payloads?)\b|"
        r"\b(?<!not\s)(?<!never\s)(?:signs|broadcasts|submits|settles|executes)\b"
        r"(?:(?![.!?]).){0,100}?\b"
        r"(?:transactions?|payments?|settlements?|wallet\s+payloads?|payloads?)\b|"
        r"\b(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:supports?|enables?|offers?|provides?|exposes?|includes?)\s+"
        r"(?!no\b|not\b)(?:an?\s+)?(?:hosted\s+|wallet\s+|transaction\s+){0,3}"
        r"(?:signer|signing|broadcast|submission|settlement|transaction\s+tools?)\b|"
        r"\b(?:is|acts\s+as|serves\s+as)\s+(?!no\b|not\b)(?:an?\s+)?"
        r"(?:transaction\s+|wallet\s+)?signer\b|"
        r"\b(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"performs?\s+(?!no\b|not\b)(?:transaction\s+)?"
        r"(?:signing|broadcast)(?:\s+and\s+(?:broadcast|signing))?\b|"
        r"\b(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:relays?|forwards?|sends?)\s+(?!no\b|not\b)(?:signed\s+)?"
        r"(?:transactions?|wallet\s+payloads?|payloads?)\b|"
        r"\bhosted\s+(?:transaction\s+)?(?:signing|broadcast)\s+"
        r"(?:is|remains?)\s+(?:now\s+)?(?:available|enabled|live|active|operational)\b|"
        r"\b(?<!not\s)(?<!never\s)(?:has|holds|keeps)\s+(?!no\b|not\b)"
        r"(?:an?\s+)?(?:wallet\s+|transaction\s+){0,2}"
        r"(?:custody|private\s+keys?|signing\s+keys?|transaction\s+tools?)\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

LOCAL_TRANSACTION_ENABLED = {
    "local Stele MCP claims transaction capability": re.compile(
        r"\btransaction-capable\b|"
        r"\b(?:can|does|will)\s+(?!not\b)(?:create|prepare|sign|broadcast|submit)\b"
        r"(?:(?![.!?]).){0,100}?\btransactions?\b|"
        r"\b(?:supports?|enables?)\s+(?:wallet\s+)?(?:transaction\s+)?"
        r"(?:signing|broadcast|submission)\b|"
        r"\b(?:has|includes|provides|ships|offers|exposes)\b"
        r"(?:(?!\bno\b|[.!?]).){0,140}?\btransaction\s+tools?\b",
        re.IGNORECASE | re.DOTALL,
    ),
}


def folded_prose(text: str) -> str:
    """Normalize Markdown wrapping before checking required prose anchors."""
    without_quote_prefixes = re.sub(r"(?m)^>\s?", "", text)
    return " ".join(without_quote_prefixes.casefold().split())


def status_prose(text: str) -> str:
    """Remove Markdown quote markers without changing offsets or line numbers."""
    return re.sub(
        r"(?m)^>\s?",
        lambda match: " " * len(match.group(0)),
        text,
    )


def count_value(token: str) -> int:
    folded = token.casefold()
    return int(folded) if folded.isdigit() else COUNT_VALUES[folded]


def stele_status_contradictions(text: str) -> list[tuple[int, str]]:
    """Return every present-tense claim that conflicts with the release snapshot."""
    prose = status_prose(text)
    contradictions: list[tuple[int, str]] = []

    surfaces = list(STELE_MCP_SURFACE.finditer(prose))
    for index, surface in enumerate(surfaces):
        kind = "hosted" if surface.group("hosted") else "local"
        expected = 2 if kind == "hosted" else 3
        next_surface = (
            surfaces[index + 1].start() if index + 1 < len(surfaces) else len(prose)
        )
        segment_end = min(next_surface, surface.end() + 600)
        for claim in TOOL_COUNT_CLAIM.finditer(prose, surface.end(), segment_end):
            actual = count_value(claim.group("count"))
            qualifier = (claim.group("qualifier") or "").casefold()
            inexact = qualifier in {
                "at least",
                "more than",
                "fewer than",
                "up to",
                "about",
                "approximately",
            }
            if actual != expected or inexact:
                qualified = f"{qualifier} " if qualifier else ""
                contradictions.append(
                    (
                        claim.start(),
                        f"{kind} Stele MCP claims {qualified}{actual} tools; "
                        f"expected exactly {expected}",
                    )
                )

        if kind == "hosted":
            segment = prose[surface.start() : segment_end]
            for label, pattern in HOSTED_TRANSACTION_ENABLED.items():
                match = pattern.search(segment)
                if match:
                    contradictions.append((surface.start() + match.start(), label))

        if kind == "local":
            segment = prose[surface.start() : segment_end]
            for label, pattern in LOCAL_TRANSACTION_ENABLED.items():
                match = pattern.search(segment)
                if match:
                    contradictions.append((surface.start() + match.start(), label))

    for claim in PUBLISHED_SERVICE_COUNT.finditer(prose):
        actual = count_value(claim.group("count"))
        if actual != 0:
            contradictions.append(
                (
                    claim.start(),
                    f"Stele catalog claims {actual} published services; expected zero",
                )
            )

    for patterns in (
        INVENTORY_ENABLED,
        PUBLIC_WEB_BOOKING_DRAFT_CREATION,
        STALE_PUBLIC_WEB_DRAFT_DENIAL,
        BOOKING_DRAFT_WITHOUT_LISTING,
        PROVIDER_DRAFT_BOUNDARY,
        IDENTITY_OVERCLAIMS,
        STUDIO_LINK_VIOLATIONS,
        STALE_ECONOMIC_PREVIEW,
        PUBLIC_WEB_FORBIDDEN_CAPABILITIES,
    ):
        for label, pattern in patterns.items():
            for match in pattern.finditer(prose):
                contradictions.append((match.start(), label))

    for label, capability in GATED_CAPABILITIES.items():
        forward = re.compile(
            rf"\b{capability}\b(?:(?![.!?]).){{0,90}}?\b"
            rf"(?:is|are|remains?|has\s+been)\s+(?:now\s+)?{ENABLED_STATE}\b",
            re.IGNORECASE | re.DOTALL,
        )
        reverse = re.compile(
            rf"\b{REVERSE_ENABLED_STATE}\s+(?:Stele\s+)?{capability}\b",
            re.IGNORECASE,
        )
        for pattern in (forward, reverse):
            for match in pattern.finditer(prose):
                contradictions.append(
                    (match.start(), f"Stele {label} incorrectly presented as enabled")
                )

    return sorted(set(contradictions))


def main() -> int:
    failures: list[str] = []
    for path in DOCUMENTS:
        text = path.read_text(encoding="utf-8")
        for label, pattern in FORBIDDEN.items():
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                failures.append(f"{path.relative_to(ROOT)}:{line}: {label}")
        folded = folded_prose(text)
        for phrase in REQUIRED:
            if phrase.casefold() not in folded:
                failures.append(
                    f"{path.relative_to(ROOT)}: missing capability anchor {phrase!r}"
                )

    for path in STELE_STATUS_DOCUMENTS:
        text = path.read_text(encoding="utf-8")
        if CANONICAL_STUDIO_MARKDOWN_DESTINATION not in text:
            failures.append(
                f"{path.relative_to(ROOT)}: missing exact Provider Studio Markdown destination "
                f"{CANONICAL_STUDIO_MARKDOWN_DESTINATION!r}"
            )
        for label, pattern in STALE_STELE_DEPLOYMENT.items():
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                failures.append(f"{path.relative_to(ROOT)}:{line}: {label}")
        for offset, label in stele_status_contradictions(text):
            line = text.count("\n", 0, offset) + 1
            failures.append(f"{path.relative_to(ROOT)}:{line}: {label}")
        folded = folded_prose(text)
        for phrase in STELE_STATUS_REQUIRED:
            if phrase.casefold() not in folded:
                failures.append(
                    f"{path.relative_to(ROOT)}: missing Stele status anchor {phrase!r}"
                )

    if failures:
        print("public truth check failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print("public truth check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
