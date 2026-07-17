#!/usr/bin/env python3
"""Fail closed on regressions in the reconciled public capability boundary."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


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
CANONICAL_STUDIO_URL = "https://stele.monolythium.com/studio"

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

DESKTOP_STELE_EMBEDDING = {
    "Stele presented as embedded in the desktop wallet": re.compile(
        r"(?:\bStele\b(?:(?![.!?]).){0,100}?\b(?:"
        r"ships?\s+(?:inside|in|with)|is\s+(?:built|bundled|embedded)\s+into|"
        r"runs?\s+(?:inside|in))\s+(?:the\s+)?(?:Desktop\s+Wallet|desktop\s+wallet)\b|"
        r"\b(?:the\s+)?(?:Desktop\s+Wallet|desktop\s+wallet)\b"
        r"(?:(?![.!?]).){0,100}?\b(?:includes?|bundles?|embeds?|contains?|ships?\s+with)\s+"
        r"(?:an?\s+)?Stele(?:\s+marketplace)?\b)",
        re.IGNORECASE | re.DOTALL,
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
NONZERO_COUNT_TOKEN = (
    r"(?:[1-9]\d*|"
    + "|".join(token for token in COUNT_VALUES if token != "zero")
    + r")"
)
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
    rf"(?:(?:[a-z][a-z0-9/-]*)(?:,\s*|\s+)){{0,4}}"
    rf"(?:tools?|capabilit(?:y|ies))\b",
    re.IGNORECASE,
)
TOOL_ENDPOINT_COUNT_CLAIM = re.compile(
    rf"\b(?:exposes?|provides?|offers?|has|includes?)\s+"
    rf"(?:(?P<qualifier>exactly|only|at\s+least|more\s+than|fewer\s+than|"
    rf"up\s+to|about|approximately)\s+)?(?P<count>{TOOL_COUNT_TOKEN})\s+"
    rf"(?:(?:[a-z][a-z0-9/-]*)(?:,\s*|\s+)){{0,3}}endpoints?\b",
    re.IGNORECASE,
)
TOOL_COUNT_REVERSED_AFTER_SURFACE = re.compile(
    rf"\b(?:tool|endpoint|capability)\s+count\s*(?:is|=|:)\s*"
    rf"(?:(?P<qualifier>exactly|only|at\s+least|more\s+than|fewer\s+than|"
    rf"up\s+to|about|approximately)\s+)?(?P<count>{TOOL_COUNT_TOKEN})\b",
    re.IGNORECASE,
)
NEGATED_TOOL_COUNT_AFTER_SURFACE = re.compile(
    rf"\b(?:"
    rf"(?:tool|endpoint|capability)\s+count\s*(?:is|=|:)\s*not\s+"
    rf"(?P<count_direct>{TOOL_COUNT_TOKEN})|"
    rf"(?:tool|endpoint|capability)\s+count\s+"
    rf"(?:differs?\s+from|is\s+(?:different\s+from|other\s+than))\s+"
    rf"(?P<count_diff>{TOOL_COUNT_TOKEN})|"
    rf"(?:does\s+not|doesn['’]t|cannot)\s+"
    rf"(?:have|expose|provide|offer|include)\s+"
    rf"(?:(?:the\s+)?required\s+|exactly\s+|only\s+)?"
    rf"(?P<count_verb>{TOOL_COUNT_TOKEN})\s+"
    rf"(?:tools?|endpoints?|capabilit(?:y|ies))"
    rf")\b",
    re.IGNORECASE,
)
NO_TOOL_SURFACE_AFTER_MCP = re.compile(
    r"\b(?:"
    r"(?:has|offers?|provides?|exposes?|includes?)\s+no\s+"
    r"(?:tools?|endpoints?|capabilit(?:y|ies))|"
    r"lacks?\s+(?:all\s+)?(?:tools?|endpoints?|capabilit(?:y|ies))"
    r")\b",
    re.IGNORECASE,
)
TOOL_ABSENCE_EXCEPTION_SUFFIX = re.compile(
    rf"^\s+(?:beyond|besides|other\s+than|except(?:\s+for)?|apart\s+from|outside)"
    rf"\s+(?:(?:its|the)\s+)?(?:exactly\s+)?(?P<count>{TOOL_COUNT_TOKEN})\b",
    re.IGNORECASE,
)
MCP_SURFACE_REVERSE_COUNT = re.compile(
    rf"\b(?:(?:there\s+(?:is|are)|the\s+surface\s+has)\s+)?"
    rf"(?:(?P<qualifier>exactly|only|at\s+least|more\s+than|fewer\s+than|"
    rf"up\s+to|about|approximately)\s+)?(?P<count>{TOOL_COUNT_TOKEN})\s+"
    rf"(?:tools?|endpoints?|capabilit(?:y|ies))\s+"
    rf"(?:in|on|at|through)\s+(?:the\s+)?(?:(?P<hosted>Hosted)\s+|"
    rf"(?P<local>local)\s+)(?:Stele\s+)?MCP\b",
    re.IGNORECASE,
)
UNRELATED_TOOL_COUNT_SUBJECT = re.compile(
    r"\b(?:(?:another|other|separate|unrelated|the)\s+)?"
    r"(?:API|website|system|application|server|client|agent|product|surface|"
    r"Provider\s+Studio|public\s+web|Browser\s+Wallet|Desktop\s+Wallet)\b"
    r"(?:(?![,;.!?]).){0,60}?\b(?:(?:"
    r"has|exposes?|offers?|uses?|includes?|provides?|reports?|lists?"
    r")\b|(?:tool|endpoint|capability)\s+count\s*(?:is\b|=|:))",
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
        r"\b(?:public\s+)?catalog\s+is\s+no\s+longer\s+empty\b|"
        r"\b(?:public\s+)?catalog\s+is\s+not\s+empty\b|"
        r"\b(?:public\s+)?catalog\s+(?:now\s+)?(?:contains?|lists?|has)\s+"
        r"(?:an?|one)\s+(?:services?|listings?)\b|"
        r"\b(?:public\s+)?catalog\s+(?:now\s+)?has\s+"
        r"(?:an?\s+)?(?:entry|entries)\b|"
        r"\b(?:public\s+)?catalog\b[^.!?\n]{0,100}\b(?:contains|lists|offers|has)\s+"
        r"(?:some|several|multiple|many|live|available)\s+(?:services?|listings?)\b",
        re.IGNORECASE,
    ),
}

CATALOG_REVERSE_ENABLED = {
    "Stele catalog claims a published service": re.compile(
        rf"\b(?P<count>{NONZERO_COUNT_TOKEN})\s+(?:services?|listings?)\s+"
        r"(?:is|are)\s+published\s+"
        r"in\s+(?:the\s+)?(?:Stele|public)\s+catalog\b|"
        r"\ban?\s+(?:service|listing)\s+(?:is\s+)?(?:live|published|available)\s+"
        r"in\s+(?:the\s+)?public\s+catalog\b",
        re.IGNORECASE,
    ),
}

HOSTED_TOOL_INVENTORY_OVERCLAIMS = {
    "hosted Stele MCP claims more than exactly two tools": re.compile(
        r"\bHosted\s+(?:Stele\s+)?MCP\b(?:(?![.!?]).){0,180}?\b(?:"
        r"(?:exposes?|has|offers?|provides?)\s+(?:an?\s+)?pair\s+of\s+tools?\s+"
        r"plus\s+(?:an?\s+)?(?:status|third)\b|"
        r"(?:exposes?|has|offers?|provides?)\s+"
        r"(?:public\s+)?catalog\s+search\s*,\s*"
        r"booking[- ]draft\s+preparation\s*,?\s*(?:and|plus)\s+status\b"
        r"|(?:provides?|exposes?|offers?|has)\s+status\s+in\s+addition\s+to\s+"
        r"(?:its\s+)?(?:exactly\s+)?two\b(?:(?![.!?]).){0,80}?\btools?\b"
        r"|(?:does\s+not|doesn['’]t|cannot)\s+lack\s+(?:an?\s+)?third\s+tool\b"
        r"|(?:exposes?|provides?|offers?|has)\s+(?:exactly\s+)?two\b"
        r"(?:(?![.!?]).){0,80}?\btools?\s+plus\s+status\b"
        r"|has\s+(?:an?\s+)?third\s+status\s+capability\s+alongside\s+"
        r"(?:its\s+)?two\s+tools?\b"
        r")",
        re.IGNORECASE | re.DOTALL,
    ),
}

GATED_CAPABILITIES = {
    "economic writes": r"economic\s+writes?",
    "transaction signing": r"transaction\s+signing",
    "mainnet": r"mainnet",
    "provider publication": r"provider\s+publication",
}
GATED_CAPABILITY_ACTIVATION = {
    "Stele provider publication incorrectly presented as enabled": re.compile(
        r"\bprovider\s+publication\s+(?:ships?|launches?|works?)\s+"
        r"(?:today|now|currently)\b|"
        r"\bprovider\s+publication\s+is\s+not\s+"
        r"(?:unavailable|gated|off|disabled|inactive)\b",
        re.IGNORECASE,
    ),
    "Stele transaction signing incorrectly presented as enabled": re.compile(
        r"\btransaction\s+signing\s+(?:works?|ships?|runs?)\s+"
        r"(?:today|now|currently)\b",
        re.IGNORECASE,
    ),
    "Stele mainnet incorrectly presented as enabled": re.compile(
        r"\bmainnet\s+(?:(?:has\s+)?(?:launched|shipped|started|opened)|"
        r"is\s+no\s+longer\s+off|is\s+not\s+(?:off|gated|unavailable|"
        r"disabled|inactive))\b",
        re.IGNORECASE,
    ),
}
ENABLED_STATE = r"(?:on|enabled|live|active|available|operational|permitted|open|ready)"
REVERSE_ENABLED_STATE = (
    r"(?:enabled|live|active|available|operational|permitted|open|ready)"
)
DISABLED_STATE = r"(?:off|gated|unavailable|disabled|inactive|closed|blocked)"
STATE_TIME_MODIFIER = r"(?:(?:now|currently|today|already|presently)\s+)?"
STATE_COPULA = (
    rf"(?:is|are|remains?|(?:has|have)\s+{STATE_TIME_MODIFIER}been)"
)
NEGATED_DISABLED_RELATION = (
    rf"(?:"
    rf"{STATE_COPULA}\s+{STATE_TIME_MODIFIER}"
    rf"(?:not|never|no\s+longer)\s+{STATE_TIME_MODIFIER}"
    rf"(?:still\s+)?{DISABLED_STATE}|"
    rf"(?:isn['’]t|aren['’]t)\s+{STATE_TIME_MODIFIER}(?:still\s+)?"
    rf"{DISABLED_STATE}|"
    rf"(?:has|have)\s+{STATE_TIME_MODIFIER}"
    rf"(?:not|never|no\s+longer)\s+{STATE_TIME_MODIFIER}been\s+"
    rf"{STATE_TIME_MODIFIER}(?:still\s+)?{DISABLED_STATE}|"
    rf"(?:hasn['’]t|haven['’]t)\s+{STATE_TIME_MODIFIER}been\s+"
    rf"{STATE_TIME_MODIFIER}(?:still\s+)?{DISABLED_STATE}"
    rf")"
)

PUBLIC_WEB_BOOKING_DRAFT_CREATION = {
    "public web claims booking-approval draft creation": re.compile(
        r"\b(?:the\s+)?(?:public\s+web|Provider\s+Studio)\b"
        r"(?:(?![.!?]).){0,180}?\b(?:"
        r"(?:can|does|will|now|currently)\s+(?!not\b)"
        r"(?:create|prepare|generate|build|author|produce)|"
        r"(?<!not\s)(?:creates|prepares|generates|builds|authors|produces)"
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
        r"(?:is\s+)?available\s+without|"
        r"works?\s+without"
        r")\s+(?:an?\s+)?published\s+listing\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

BOOKING_DRAFT_PREREQUISITE_CONTRADICTIONS = {
    "booking-draft preparation claims no listing prerequisite": re.compile(
        r"(?:\b(?:hosted\s+(?:Stele\s+)?MCP\s+)?"
        r"(?:booking(?:-approval)?|approval)[- ]draft\s+preparation\b"
        r"(?:(?![.!?]).){0,120}?\bdoes\s+not\s+"
        r"(?:require|depend\s+on|rely\s+on)\s+(?:an?\s+)?published\s+listing\b|"
        r"\ba\s+published\s+listing\s+is\s+optional\s+for\s+"
        r"(?:hosted\s+)?booking[- ]draft\s+preparation\b|"
        r"\bbooking[- ]draft\s+preparation\s+works?\s+against\s+"
        r"unpublished\s+listings?\b)",
        re.IGNORECASE | re.DOTALL,
    ),
}

PROVIDER_DRAFT_BOUNDARY = {
    "provider-listing draft presented as public or executable": re.compile(
        r"\b(?:private\s+|wallet-owned\s+){0,3}provider[- ]listing\s+drafts?\b"
        r"(?:(?![.!?]).){0,120}?\b(?:"
        r"(?:is|are|becomes?|remains?)\s+(?:now\s+)?"
        r"(?!not\b)(?:published|discoverable|transactable|on-chain)|"
        r"(?:is|are|becomes?|remains?)\s+(?:now\s+)?visible\s+in\s+"
        r"(?:the\s+)?public\s+catalog"
        r")\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "Provider Studio presented as a publication or transaction surface": re.compile(
        r"\bProvider\s+Studio\b(?:(?![.!?]).){0,180}?\b(?:"
        r"(?:can|does|will|now|currently)\s+(?!not\b)"
        r"(?:(?:create|prepare|manage)\s+and\s+)?"
        r"(?:publish|submit|broadcast|transact|execute)\w*|"
        r"(?<!not\s)(?:publishes|submits|broadcasts|transacts|executes)|"
        r"(?<!not\s)sends?\s+provider[- ]listing\s+drafts?\s+into\s+"
        r"(?:the\s+)?public\s+catalog"
        r")\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "hosted MCP claims provider-listing draft authority": re.compile(
        r"\bHosted\s+(?:Stele\s+)?MCP\b(?:(?![.!?]).){0,180}?\b(?:"
        r"(?:can|does|will|now|currently)\s+(?!not\b)"
        r"(?:create|prepare|access|manage|read|update|edit|delete|write)|"
        r"(?<!not\s)(?:creates|prepares|accesses|manages|reads|updates|edits|deletes|writes)"
        r")\s+(?:private\s+|wallet-owned\s+){0,3}provider[- ]listing\s+drafts?\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "provider-listing and booking-approval drafts are conflated": re.compile(
        r"(?:\bprovider[- ]listing\s+drafts?\b(?:(?![.!?]).){0,100}?\b"
        r"(?:is|are|means?|equals?|doubles?\s+as|serves?\s+as|"
        r"(?:is|are)\s+the\s+same\s+as)\s+"
        r"(?:an?\s+)?booking[- ]approval\s+drafts?\b|"
        r"\bbooking[- ]approval\s+drafts?\b(?:(?![.!?]).){0,100}?\b"
        r"(?:is|are|means?|equals?|doubles?\s+as|serves?\s+as|"
        r"(?:is|are)\s+the\s+same\s+as)\s+"
        r"(?:an?\s+)?provider[- ]listing\s+drafts?\b)",
        re.IGNORECASE | re.DOTALL,
    ),
}

WALLET_AUTH_SURFACE = (
    r"(?:Browser[- ]Wallet(?:\s+authentication)?|"
    r"wallet[- ](?:authentication|auth|login)(?:\s+proof)?|"
    r"(?:wallet[- ]|login\s+)signature|"
    r"that\s+authentication)"
)
IDENTITY_CLAIM_VERB = (
    r"(?:prove|verify|validate|establish|confirm|certify|demonstrate|authenticate|"
    r"attest|guarantee|identify|assert)"
)
IDENTITY_CLAIM_FINITE_VERB = (
    r"(?:proves|verifies|validates|establishes|confirms|certifies|demonstrates|"
    r"authenticates|attests|guarantees|identifies|asserts)"
)
IDENTITY_CLAIM_TARGET = (
    r"(?:"
    r"(?:an?\s+|the\s+|user(?:['’]s)?\s+|provider\s+){0,3}"
    r"(?:human\s+|legal\s+|real-world\s+)?(?:identity|credentials|authority|ownership)|"
    r"(?:the\s+)?(?:provider\s+)?"
    r"(?:licen[cs]e|licensure|accreditation|certification)|"
    r"(?:licensed|credentialed|accredited|certified)(?:\s+provider)?(?:\s+status)?|"
    r"KYC\s+(?:identity|status)|"
    r"(?:the\s+)?account\s+belongs\s+to\s+(?:an?\s+)?(?:person|individual|"
    r"[a-z][a-z'-]{1,40})|"
    r"(?:the\s+)?person\s+behind\s+(?:the\s+)?(?:wallet\s+)?address|"
    r"who\s+(?:the\s+)?user\s+is|"
    r"that\s+(?:the\s+)?provider\s+is\s+(?!not\b)"
    r"(?:licensed|credentialed|accredited|certified)"
    r")"
)

IDENTITY_OVERCLAIMS = {
    "wallet authentication presented as identity proof": re.compile(
        rf"\b{WALLET_AUTH_SURFACE}\b"
        rf"(?:(?![.!?]).){{0,180}}?\b(?:"
        r"owns?\s+(?:the\s+)?identity\s+proof|"
        r"(?:can|does|now|currently|is\s+able\s+to)\s+(?!not\b)"
        rf"{IDENTITY_CLAIM_VERB}\w*\s+{IDENTITY_CLAIM_TARGET}|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        rf"{IDENTITY_CLAIM_FINITE_VERB}\s+{IDENTITY_CLAIM_TARGET}|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)(?<!or\s)"
        r"(?!identity\b|credentials?\b|authority\b|ownership\b|signatures?\b|"
        r"licen[cs]e\b|licensure\b|accreditation\b|certification\b)"
        r"[a-z][a-z-]{2,}(?:s|es)\b"
        r"(?:(?![.!?;|]|\b(?:no|not|never|cannot|without|could|would|will|may|"
        r"might|future|retired|former|previous|legacy|off|gated|unavailable)\b|"
        r"n['’]t).){0,100}?\b"
        rf"{IDENTITY_CLAIM_TARGET}|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:is|constitutes?|serves\s+as|represents?)\s+(?!not\b|no\b)"
        r"(?:an?\s+)?(?:proof|evidence)\s+of\s+"
        r"(?:(?:an?\s+|the\s+|user(?:['’]s)?\s+|provider\s+){0,3})"
        r"(?:human\s+|legal\s+|real-world\s+)?(?:identity|credentials|authority|ownership)|"
        r"(?:is|remains?)\s+(?!not\b)(?:sufficient|enough|adequate|valid)\s+"
        r"(?:for\s+)?KYC|"
        r"(?:(?:can|does|now|currently)\s+(?!not\b)"
        r"(?:satisfy|meet|pass|clear|complete|suffice\s+for)|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:satisfies|meets|passes|clears|completes|suffices\s+for))\s+"
        r"(?:the\s+)?(?:KYC|know[- ]your[- ]customer)|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:counts?|serves?)\s+as\s+(?:an?\s+)?"
        r"(?:KYC|know[- ]your[- ]customer)(?:\s+(?:proof|check))?|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:provides?|supplies?|yields?)\s+(?:an?\s+)?"
        r"(?:KYC|know[- ]your[- ]customer)\s+"
        r"(?:proof|verification|clearance|compliance)|"
        r"(?:is|remains?)\s+(?!not\b)"
        r"(?:KYC|know[- ]your[- ]customer)[- ](?:compliant|verified|cleared)"
        r")\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

IDENTITY_REVERSE_OVERCLAIMS = {
    "identity proof assigned to wallet authentication": re.compile(
        rf"(?:\b{IDENTITY_CLAIM_TARGET}\b"
        r"(?:(?![.!?;|]|\b(?:no|not|never|without|could|would|will|may|might|"
        r"future|retired|former|previous|legacy|gated|off|unavailable)\b|"
        r"n['’]t|\bonly\s+after\b).){0,140}?"
        rf"\b(?:by|through|via)\s+(?:the\s+)?{WALLET_AUTH_SURFACE}\b|"
        r"(?<!future\s)(?<!retired\s)(?<!former\s)(?<!legacy\s)"
        r"\b(?:KYC|know[- ]your[- ]customer)\b"
        r"(?:(?![.!?;|]|\b(?:no|not|never|without|could|would|will|may|might|"
        r"future|retired|former|previous|legacy|gated|off|unavailable)\b|"
        r"n['’]t|\bonly\s+after\b).){0,100}?"
        r"\b(?:is|are)\s+(?:satisfied|completed|verified|established)\s+"
        rf"(?:by|through|via)\s+(?:the\s+)?{WALLET_AUTH_SURFACE}\b|"
        r"(?<!future\s)(?<!retired\s)(?<!former\s)(?<!legacy\s)"
        r"\b(?:KYC|know[- ]your[- ]customer)\b"
        r"(?:(?![.!?;|]|\b(?:no|not|never|without|could|would|will|may|might|"
        r"future|retired|former|previous|legacy|gated|off|unavailable)\b|"
        r"n['’]t|\bonly\s+after\b).){0,100}?"
        r"\b(?:relies?|depends?|rests?)\s+on\s+(?:the\s+)?"
        rf"{WALLET_AUTH_SURFACE}\b|"
        rf"(?<!future\s)(?<!retired\s)(?<!former\s)(?<!legacy\s)\b"
        rf"{IDENTITY_CLAIM_TARGET}\b"
        r"(?:(?![.!?;|]|\b(?:no|not|never|without|could|would|will|may|might|"
        r"future|retired|former|previous|legacy|gated|off|unavailable)\b|"
        r"n['’]t|\bonly\s+after\b).){0,100}?"
        r"\b(?:(?:comes?|stems?|derives?|originates?|results?|follows?)\s+from|"
        r"(?:is|are)\s+(?:derived|obtained|established)\s+from)\s+"
        rf"(?:the\s+)?{WALLET_AUTH_SURFACE}\b)",
        re.IGNORECASE | re.DOTALL,
    ),
}

IDENTITY_NAMED_OVERCLAIMS = {
    "wallet authentication presented as identity proof": re.compile(
        rf"\b(?i:{WALLET_AUTH_SURFACE})\b"
        r"(?:(?![.!?]).){0,100}?\b"
        r"(?i:authenticates|identifies|verifies|validates|certifies)\s+"
        r"[A-Z][a-z][A-Za-z'-]{1,39}\b",
        re.DOTALL,
    ),
}

MARKDOWN_INLINE_LINK = re.compile(
    r"\[(?P<label>[^\]\n]+)\]"
    r"\((?P<destination>[^\s]+?)(?:\s+['\"][^)]*['\"])?\)",
    re.IGNORECASE,
)
MARKDOWN_REFERENCE_LINK = re.compile(
    r"\[(?P<label>[^\]\n]+)\]\[(?P<reference>[^\]\n]+)\]",
    re.IGNORECASE,
)
MARKDOWN_REFERENCE_DEFINITION = re.compile(
    r"(?m)^\s*\[(?P<reference>[^\]\n]+)\]:\s*<?(?P<destination>\S+?)>?"
    r"(?:\s+['\"(][^\n]*['\")])?\s*$",
)
STUDIO_RAW_DESTINATION = re.compile(
    r"(?P<destination>"
    r"(?:https?:)?//[^\s<>()\[\]{}\"']+|"
    r"[a-z][a-z0-9+.-]*:[^\s<>()\[\]{}\"']+|"
    r"(?<![\w:/])(?:\.\.?/|/|#)[a-z0-9%._~!$&'()*+,;=:@/?-]+|"
    r"(?<![\w./:@\[])\b(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}"
    r"(?:/[^)\s<]*)?"
    r")",
    re.IGNORECASE,
)
STUDIO_PRODUCT_ACTION = re.compile(
    r"\bProvider\s+Studio\b.{0,100}?\b(?:"
    r"at|hosted\s+at|available\s+at|destination|URL|route|href|"
    r"open(?:ed)?|visit|use|links?|points?)\b|"
    r"\b(?:open|visit|use)\b.{0,140}?\bProvider\s+Studio\b",
    re.IGNORECASE | re.DOTALL,
)
STUDIO_EXPLICIT_DESTINATION = re.compile(
    r"\bProvider\s+Studio\b(?:(?![.!?]).){0,100}?\b"
    r"(?:destination|URL|route|href)\b\s*(?:is|=|:)\s*"
    r"(?P<destination>\S+)",
    re.IGNORECASE | re.DOTALL,
)
STUDIO_DOCUMENTATION_CONTEXT = re.compile(
    r"\bProvider\s+Studio\s+(?:documentation|docs?|guide|reference)\s+"
    r"(?:is|are|lives?|resides?|exists?)\s+(?:available\s+)?"
    r"(?:at|on|under)\b",
    re.IGNORECASE,
)

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
        r"\b(?:the\s+)?(?:public\s+web|Stele\s+web|web\s+app|Provider\s+Studio)\b"
        r"(?:(?![.!?]).){0,180}?\b(?:"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:includes?|contains?|offers?|provides?|exposes?|supports?|enables?|has|hosts?)"
        r"\s+(?!no\b|not\b)(?:(?![.!?]).){0,120}?\b"
        r"(?:booking|payment|settlement|economic)"
        r"(?:\s*(?:,\s*(?:and\s+)?|\s+and\s+)"
        r"(?:booking|payment|settlement|economic)){0,3}\s+"
        r"(?:controls?|actions?|buttons?|workflows?)\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:supports?|enables?|offers?|provides?|handles?|collects?)"
        r"\s+(?!no\b|not\b)(?:bookings?|payments?|settlements?|"
        r"(?:service\s+)?fees?|funds?)\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)(?<!or\s)"
        r"(?:accepts?|takes?)\s+(?!no\b|not\b)bookings?\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:lets?|allows?)\s+(?!no\b|not\b)(?:users?|customers?)\s+"
        r"(?:to\s+)?(?:book|pay|purchase|settle)\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)(?<!or\s)"
        r"(?:charges?|bills?)\s+(?!no\b|not\b)"
        r"(?:customers?|users?|buyers?|providers?|visitors?|clients?)\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)(?<!or\s)"
        r"(?:transfers?|moves?|debits?|withdraws?)\s+"
        r"(?:(?:service\s+)?funds?|(?:the\s+)?buyer(?:['’]s)?\s+wallet)\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)(?<!or\s)"
        r"(?:process(?:es)?\s+(?:bookings?(?![- ](?:approval|draft))|payments?|"
        r"checkout|purchases?|orders?)|"
        r"settles?\s+bookings?)\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)(?<!or\s)"
        r"(?:operates?|runs?|performs?|conducts?)\s+(?!no\b|not\b)"
        r"(?:booking|payment|settlement|economic)\s+workflows?\b|"
        r"(?:can|does|now|currently|is\s+able\s+to)\s+(?!not\b)"
        r"(?:book|pay|settle|purchase|execute)\w*\b|"
        r"(?:can|does|is\s+able\s+to)\s+(?!not\b)"
        r"(?:create|accept|collect|host|run|perform|conduct)\w*\b"
        r"(?:(?![.!?;|]).){0,100}?\b(?:"
        r"bookings?(?![- ](?:approval|draft|record|preview))|payments?|settlements?|"
        r"economic\s+(?:actions?|controls?|workflows?))\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)(?<!or\s)"
        r"(?!bookings?\b|payments?\b|settlements?\b|workflows?\b|controls?\b|actions?\b)"
        r"[a-z][a-z-]{2,}(?:s|es)\b"
        r"(?:(?![.!?;|]|\b(?:no|not|never|cannot|without|could|would|will|may|"
        r"might|future|retired|former|previous|legacy|off|gated|unavailable)\b|"
        r"n['’]t).){0,100}?\b(?:"
        r"bookings?(?![- ](?:approval|draft|record|preview))|"
        r"payments?|settlements?|checkout|purchases?|orders?|"
        r"(?:service\s+)?fees?|funds?|"
        r"economic\s+(?:actions?|controls?|workflows?)"
        r")\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:(?:is|remains?)|(?:acts?|serves?|functions?)\s+as)\s+"
        r"(?!not\b)(?:(?:an?|the)\s+)?"
        r"(?:(?:booking|payment|settlement|checkout|economic)\s+"
        r"(?:processor|handler|gateway|platform|surface)|checkout|merchant)\b|"
        r"(?:is|remains?)\s+(?!not\b)(?:the\s+)?(?:place\s+)?where\b"
        r"(?:(?![.!?;|]|\b(?:no|not|never|cannot|could|would|will|may|might|"
        r"future|retired|former|previous|legacy|gated|off|unavailable)\b|"
        r"n['’]t|\bonly\s+after\b).){0,120}?\b(?:"
        r"(?:customers?|users?|buyers?|providers?|visitors?|clients?)\b"
        r"(?:(?![.!?;|]|\b(?:no|not|never|cannot|could|would|will|may|might)\b|"
        r"n['’]t).){0,50}?\b(?:book|pay|purchase|settle)\b|"
        r"(?:bookings?|payments?|settlements?|checkout|purchases?)\b"
        r"(?:(?![.!?;|]|\b(?:no|not|never|cannot|could|would|will|may|might)\b|"
        r"n['’]t).){0,50}?\b"
        r"(?:are|is|get|gets)\s+(?:accepted|handled|processed|collected|settled)\b"
        r")"
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
    "booking or payment activity assigned to Provider Studio": re.compile(
        r"\b(?:customers?|users?|buyers?|providers?|visitors?|clients?)\b"
        r"(?:(?![.!?]).){0,120}?\b(?:"
        r"can\s+(?!not\b)(?:book|buy|pay|purchase|settle)\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)(?<!or\s)(?<!cannot\s)"
        r"(?<!can't\s)(?<!can’t\s)"
        r"(?:book|buy|pay|purchase|settle|make\s+payments?|place\s+bookings?)\b|"
        r"(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:are|get)\s+(?:charged|billed)\b"
        r")"
        r"(?:(?![.!?]).){0,100}?\b(?:at|by|in|inside|on|through|via|with|within)\s+"
        r"(?:the\s+)?"
        r"Provider\s+Studio\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "booking or payment state assigned to Provider Studio": re.compile(
        r"\b(?:bookings?(?![- ](?:approval|draft|record|preview))|payments?|settlements?|"
        r"checkout|purchases?|orders?)\b"
        r"(?:(?![.!?;|]|\b(?:no|not|never|cannot|could|would|will|may|might|"
        r"future|retired|former|previous|legacy|gated|off|unavailable)\b|"
        r"n['’]t|\bonly\s+after\b).){0,140}?"
        r"\b(?:at|by|in|inside|on|through|via|with|within)\s+(?:the\s+)?"
        r"Provider\s+Studio\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

HOSTED_TRANSACTION_ENABLED = {
    "hosted Stele MCP claims transaction capability": re.compile(
        r"\b(?:can|does|now|currently|is\s+able\s+to)\s+(?!not\b)"
        r"(?:create|prepare|generate|handle|control|manage|process|sign|broadcast|"
        r"submit|settle|execute|authorize|approve|move)\w*\b"
        r"(?:(?![.!?]).){0,120}?\b"
        r"(?:transactions?|transaction\s+signatures?|payments?|settlements?|"
        r"transfers?|funds?|service\s+wallet|wallet\s+payloads?|payloads?)\b|"
        r"\b(?:is|remains?)\s+(?!not\b)(?:capable|able)\s+of\s+"
        r"(?:creating|preparing|generating|handling|controlling|managing|processing|"
        r"signing|broadcasting|submitting|settling|executing|authorizing|approving)\b"
        r"(?:(?![.!?;|]).){0,100}?\b(?:transactions?|payments?|settlements?|"
        r"wallet\s+payloads?|payloads?)\b|"
        r"\b(?:is|remains?)\s+(?!not\b)(?:(?:an?|the)\s+)?(?:"
        r"transaction[- ]capable|signing[- ]capable|custodial|"
        r"(?:(?:transaction|wallet)\s+)?signing\s+(?:service|engine|provider))\b|"
        r"\b(?:is|remains?)\s+(?!not\b)(?:used|configured|deployed)\s+to\s+"
        r"(?:sign|broadcast|submit|authorize)\w*\b"
        r"(?:(?![.!?;|]).){0,80}?\b(?:transactions?|wallet\s+requests?|requests?)\b|"
        r"\b(?<!not\s)(?<!never\s)(?:signs|broadcasts|submits|settles|executes|"
        r"authorizes|approves|generates|handles|controls|manages|processes)\b"
        r"(?:(?![.!?]).){0,100}?\b"
        r"(?:transactions?|transaction\s+signatures?|payments?|settlements?|transfers?|"
        r"wallet\s+payloads?|payloads?|(?:wallet\s+|user\s+)?requests?|"
        r"orders?|intents?)\b|"
        r"\b(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:supports?|enables?|offers?|provides?|exposes?|includes?|has|holds|"
        r"handles?|controls?|owns?|maintains?|manages?|possess(?:es)?)\s+"
        r"(?!no\b|not\b)(?:an?\s+)?"
        r"(?:hosted\s+|wallet\s+|transaction\s+|signing\s+){0,3}"
        r"(?:signer|signing|broadcast|submission|settlement|authorization|"
        r"authority|capabilit(?:y|ies)|transaction\s+tools?)\b|"
        r"\b(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?:is|acts\s+as|serves\s+as)\s+"
        r"(?!no\b|not\b)"
        r"(?:(?:an?|the)\s+)?"
        r"(?:transaction\s+|wallet\s+)?signer\b|"
        r"\b(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"performs?\s+(?!no\b|not\b)(?:transaction\s+)?"
        r"(?:signing|broadcast|signatures?)(?:\s+and\s+"
        r"(?:broadcast|signing|signatures?))?\b|"
        r"\b(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:relays?|forwards?|sends?)\s+(?!no\b|not\b)(?:signed\s+)?"
        r"(?:transactions?|wallet\s+payloads?|payloads?)\b|"
        r"\bhosted\s+(?:transaction\s+)?(?:signing|broadcast)\s+"
        r"(?:is|remains?)\s+(?:now\s+)?(?:available|enabled|live|active|operational)\b|"
        r"\b(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)"
        r"(?:has|holds|keeps|controls?|owns?|maintains?|operates?|runs?|"
        r"possess(?:es)?)\s+"
        r"(?!no\b|not\b)"
        r"(?:(?:an?|the)\s+)?(?:wallet\s+|transaction\s+|signing\s+){0,2}"
        r"(?:custody|(?:hot|custodial|signing)\s+wallet|wallet\s+secrets?|"
        r"seed\s+phrases?|recovery\s+phrases?|private\s+keys?|"
        r"signing\s+keys?|authority|"
        r"capabilit(?:y|ies)|signer|transaction\s+tools?)\b|"
        r"\b(?:is|remains?)\s+(?!not\b)(?:directly\s+)?"
        r"(?:responsible\s+for|in\s+charge\s+of)\s+"
        r"(?:transaction\s+|wallet\s+)?(?:signing|broadcast|submission|"
        r"settlement|authorization)\b|"
        r"\b(?:has|holds|keeps|stores|retains|maintains)\s+access\s+to\s+"
        r"(?:wallet\s+)?(?:secrets?|seed\s+phrases?|recovery\s+phrases?|"
        r"private\s+keys?)\b|"
        r"\b(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)(?<!or\s)"
        r"(?!transactions?\b|signatures?\b|signers?\b|capabilit(?:y|ies)\b|"
        r"keys?\b|authority\b|custody\b)"
        r"[a-z][a-z-]{2,}(?:s|es)\b"
        r"(?:(?![.!?;|]|\b(?:no|not|never|cannot|without|could|would|will|may|"
        r"might|future|retired|former|previous|legacy|off|gated|unavailable)\b|"
        r"n['’]t).){0,100}?\b(?:"
        r"signed\s+transactions?|transaction\s+(?:signatures?|signers?|tools?|"
        r"capabilit(?:y|ies)|authorization|submission|signing|broadcast|settlement)|"
        r"signing\s+(?:authority|keys?|capabilit(?:y|ies))|private\s+keys?|"
        r"wallet\s+custody"
        r")\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

HOSTED_TRANSACTION_REVERSE = {
    "transaction capability assigned to hosted Stele MCP": re.compile(
        r"\b(?:transactions?|signed\s+transactions?|transaction\s+(?:signatures?|"
        r"signing|broadcast|submission|settlement|authorization)|signing\s+(?:authority|"
        r"keys?|capabilit(?:y|ies))|private\s+keys?|wallet\s+custody)\b"
        r"(?:(?![.!?;|]|\b(?:no|not|never|without|could|would|will|may|might|"
        r"future|retired|former|previous|legacy|gated|off|unavailable)\b|"
        r"n['’]t|\bonly\s+after\b).){0,160}?"
        r"\b(?:at|by|in|inside|on|through|via|with|within)\s+(?:the\s+)?"
        r"Hosted\s+(?:Stele\s+)?MCP\b",
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
        r"(?:(?!\bno\b|[.!?]).){0,140}?\btransaction\s+tools?\b|"
        r"\badds?\s+(?:an?\s+)?(?:transaction|signing|broadcast)\s+tools?\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

DOUBLE_NEGATION_CONTRADICTIONS = {
    "hosted Stele MCP claims transaction capability": re.compile(
        r"\bHosted\s+(?:Stele\s+)?MCP\b(?:(?![.!?]).){0,140}?\b"
        r"(?:"
        r"(?:cannot|can\s+not|does\s+not|doesn['’]t|never)\s+"
        r"(?:fails?|refuses?)\s+to\s+(?:sign|broadcast|submit|authorize|approve|"
        r"execute|settle|process|relay|hold|keep|store|retain|maintain)\w*\b"
        r"(?:(?![.!?]).){0,100}?\b(?:transactions?|payments?|transfers?|"
        r"private\s+keys?|wallet\s+secrets?|seed\s+phrases?|signing\s+authority)|"
        r"(?:cannot|can\s+not|does\s+not|doesn['’]t|never)\s+lacks?\s+"
        r"(?:an?\s+)?(?:signing\s+authority|transaction\s+tool|"
        r"private\s+keys?|wallet\s+secrets?)"
        r")\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "public web claims booking, payment, settlement, or economic controls": re.compile(
        r"\b(?:the\s+)?(?:public\s+web|Stele\s+web|web\s+app|Provider\s+Studio)\b"
        r"(?:(?![.!?]).){0,140}?\b"
        r"(?:cannot|can\s+not|does\s+not|doesn['’]t|never)\s+(?:"
        r"(?:fails?\s+to\s+)?(?:accept|take|collect|charge|bill|process|run|operate)|"
        r"refuse)\w*\s+(?:bookings?|payments?|settlements?|checkout|"
        r"(?:service\s+)?fees?|funds?)\b|"
        r"\b(?:the\s+)?(?:public\s+web|Stele\s+web|web\s+app|Provider\s+Studio)\b"
        r"(?:(?![.!?]).){0,140}?\b"
        r"(?:cannot|can\s+not|does\s+not|doesn['’]t|never)\s+avoid\s+"
        r"(?:charging|billing|collecting|accepting|processing)\s+"
        r"(?:buyers?|customers?|users?|payments?|fees?)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "wallet authentication presented as identity proof": re.compile(
        rf"\b{WALLET_AUTH_SURFACE}\b(?:(?![.!?]).){{0,140}}?\b"
        r"(?:cannot|can\s+not|does\s+not|doesn['’]t)\s+(?:fail|refuse)\s+to\s+"
        rf"{IDENTITY_CLAIM_VERB}\w*\s+{IDENTITY_CLAIM_TARGET}\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

SEMANTIC_NEGATED_ABSENCE = {
    "hosted Stele MCP claims transaction capability": re.compile(
        r"\bHosted\s+(?:Stele\s+)?MCP\b(?:(?![.!?]).){0,100}?\b"
        r"(?:is|remains?)\s+not\s+without\s+(?:an?\s+)?"
        r"(?:private\s+keys?|wallet\s+secrets?|seed\s+phrases?|"
        r"signing\s+authority|transaction\s+tool)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "Stele catalog denies zero published services; expected zero": re.compile(
        r"\b(?:Stele|the\s+(?:public\s+)?catalog)\b(?:(?![.!?]).){0,100}?\b"
        r"(?:does\s+not|doesn['’]t|cannot)\s+(?:have|contain|report|show)\s+"
        r"zero\s+published\s+services?\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

COORDINATED_TARGET_ASSERTIONS = {
    "public web claims booking-approval draft creation": re.compile(
        r"\b(?:the\s+)?(?:public\s+web|Provider\s+Studio)\b"
        r"(?:(?![.!?]).){0,180}?"
        r"(?:\b(?:and|or|but|however|yet|while|whereas)\b|[,:—])\s*"
        r"(?:now\s+|currently\s+)?(?:creates?|prepares?|generates?|builds?|"
        r"authors?|produces?)\s+(?:an?\s+|short-lived\s+|non-economic\s+){0,4}"
        r"(?:booking(?:-approval)?|approval)[- ](?:drafts?|previews?)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "Stele provider publication incorrectly presented as enabled": re.compile(
        r"\bprovider\s+publication\b(?:(?![.!?]).){0,120}?"
        r"(?:\b(?:and|or|but|however|yet|while|whereas)\b|[,:—])\s*"
        r"(?:now\s+|currently\s+)?(?:works?|ships?|launches?)\s+"
        r"(?:today|now|currently)\b",
        re.IGNORECASE | re.DOTALL,
    ),
}


CLAIM_NONCURRENT = re.compile(
    r"\b(?:future|retired|former|previous|legacy|historical|prototype|"
    r"previously|formerly)\b|"
    r"\b(?:will|could|would|may|might)\b|"
    r"\b(?:was|were)\b|"
    r"\b(?:Stele|MCP|web|Studio|wallet|catalog|it|they)\s+used\s+to\b|"
    r"\bonly\s+after\b|\bafter\s+(?:activation|release|review)\b",
    re.IGNORECASE,
)
CLAIM_NONCURRENT_SUFFIX = re.compile(
    r"^\s*,?\s*(?:(?:but|and)\s+)?(?:only\s+after\b|"
    r"after\s+(?:activation|release|review)\b)",
    re.IGNORECASE,
)
CLAIM_DENIAL = re.compile(
    r"\b(?:no|not|never|cannot|neither|nor|lacks?|refuses?|blocks?|bars?|"
    r"fails?|rejects?|forbids?|prevents?|denies?|unavailable|gated|off|empty|"
    r"false|invalid|incorrect|wrong|misleading|obsolete|avoid|unsafe|untrue|"
    r"deprecated|disabled|inactive|closed|blocked)\b|"
    r"n['’]t\b",
    re.IGNORECASE,
)
COUNT_DENIAL_PREFIX = re.compile(
    r"(?:\b(?:no|not|never|neither|nor)\s+|n['’]t\s+)$",
    re.IGNORECASE,
)

ASSERTION_FINITE_LEAD = (
    r"(?:am|is|are|has|have|does|do|can|"
    r"holds?|keeps?|stores?|retains?|maintains?|possess(?:es)?|owns?|"
    r"signs?|broadcasts?|submits?|settles?|executes?|authorizes?|approves?|"
    r"generates?|handles?|manages?|processes?|relays?|forwards?|"
    r"collects?|accepts?|takes?|charges?|bills?|transfers?|moves?|debits?|"
    r"withdraws?|operates?|runs?|performs?|conducts?|publishes?|lists?|"
    r"lacks?|refuses?|rejects?|blocks?|bars?|fails?|denies?|forbids?|prevents?|"
    r"creates?|prepares?|accesses?|reads?|updates?|edits?|deletes?|writes?|"
    r"authors?|produces?|sends?|doubles?|serves?|functions?|works?|ships?|"
    r"launches?|bundles?|embeds?|includes?|contains?|confirms?|proves?|"
    r"verifies|validates|authenticates|certifies|attests?|identifies|"
    r"provides?|exposes?|offers?|supports?|enables?|adds?|opens?|uses?|visits?)"
)
ASSERTION_COORDINATE_LEAD = (
    r"(?:am|is|are|has|have|does|do|can|will|could|would|may|might|"
    r"holds|keeps|stores|retains|maintains|possesses|owns|signs|broadcasts|"
    r"submits|settles|executes|authorizes|approves|generates|handles|manages|"
    r"processes|relays|forwards|collects|accepts|takes|charges|bills|transfers|"
    r"moves|debits|withdraws|operates|runs|performs|conducts|publishes|lists|"
    r"lacks|refuses|rejects|blocks|bars|fails|denies|forbids|prevents|creates|"
    r"prepares|accesses|reads|updates|edits|deletes|writes|authors|produces|"
    r"sends|doubles|serves|functions|works|ships|launches|bundles|embeds|"
    r"includes|contains|confirms|proves|verifies|validates|authenticates|"
    r"certifies|attests|identifies|provides|exposes|offers|supports|enables|"
    r"adds|opens|uses|visits|open|use|visit)"
)
ASSERTION_SUBJECT = (
    r"(?:(?:the|an?)\s+)?(?:"
    r"Hosted\s+(?:Stele\s+)?MCP|local\s+(?:Stele\s+)?MCP|"
    r"Provider\s+Studio|public\s+web|Stele\s+web|web\s+app|"
    r"Desktop\s+Wallet|desktop\s+wallet|Browser\s+Wallet|"
    r"wallet[- ](?:authentication|auth|login)|login\s+signature|"
    r"provider\s+publication|transaction\s+signing|mainnet|"
    r"booking(?:-approval)?[- ]draft\s+preparation|"
    r"provider[- ]listing\s+draft|booking[- ]approval\s+draft|"
    r"public\s+catalog|Stele\s+catalog|catalog|service|listing|metrics?|"
    r"Stele|Studio|it|they|we|he|she|this|that|"
    r"users?|customers?|buyers?|providers?|visitors?|clients?)"
)
ASSERTION_RELATION_LEAD = re.compile(
    rf"(?:(?:now|currently|today|previously|formerly|not|never)\s+)*"
    rf"(?:{ASSERTION_COORDINATE_LEAD}\b|"
    rf"\[(?:Provider\s+)?Studio\]\([^\n)]+\)\s+"
    rf"(?:will|could|would|may|might|{ASSERTION_FINITE_LEAD})\b|"
    rf"{ASSERTION_SUBJECT}\b(?:(?![,:;.!?]|\b(?:and|or|but|however|yet|while|"
    rf"whereas|though|plus|then|nor)\b).){{0,100}}?\b(?:will|could|would|may|might|"
    rf"{ASSERTION_FINITE_LEAD})\b)",
    re.IGNORECASE | re.DOTALL,
)
ASSERTION_CONNECTOR = re.compile(
    r"(?P<connector>"
    r"(?:,\s*)?\b(?:and|or|but|however|yet|while|whereas|though|plus|then)\b\s+|"
    r",\s+|:\s+|\s+[—–/]\s+"
    r")",
    re.IGNORECASE,
)
FALSE_ASSERTION_PREFIX = re.compile(
    r"\b(?:false|invalid|incorrect|wrong|misleading|obsolete)\s+"
    r"(?:claim|assertion|statement|description)\s+(?:that|saying)\b",
    re.IGNORECASE,
)
FALSE_ASSERTION_SUFFIX = re.compile(
    r"^[\s\"'”’)\]]*(?:(?:link|URL|destination|claim|assertion|statement)\s+)?"
    r"(?:"
    r"(?:is|are|was|were|remains?)\s+(?:not\s+true|false|invalid|incorrect|"
    r"wrong|misleading|obsolete|unsafe|untrue|deprecated)|"
    r"(?:is|are|was|were|remains?)\s+not\s+(?:the\s+)?"
    r"(?:current|live|canonical)\s+(?:product\s+)?(?:destination|URL|link)|"
    r"(?:should|must)\s+not\s+be\s+used|"
    r"must\s+be\s+(?:removed|rejected|ignored)|"
    r"should\s+be\s+(?:removed|rejected|ignored)"
    r")\b",
    re.IGNORECASE,
)
PARENTHETICAL_TEMPORAL = re.compile(
    r"\([^)]*\b(?:was|were|previously|formerly)\b[^)]*\)",
    re.IGNORECASE,
)
RELATIVE_TEMPORAL = re.compile(
    rf"\b(?:that|which|who)\b(?:(?![,;.!?]).){{0,120}}?"
    r"\b(?:was|were|previously|formerly)\b(?:(?![,;.!?]).){0,120}?"
    rf"(?=\b{ASSERTION_FINITE_LEAD}\b)",
    re.IGNORECASE | re.DOTALL,
)
INCIDENTAL_NEGATIVE_MODIFIER = re.compile(
    rf"\b(?:with|despite)\s+no\b(?:(?![,;.!?]).){{0,100}}?"
    rf"(?=\b{ASSERTION_FINITE_LEAD}\b)",
    re.IGNORECASE | re.DOTALL,
)


def claim_scope_bounds(text: str, offset: int) -> tuple[int, int]:
    """Return sentence/table bounds containing an assertion offset."""
    starts = [text.rfind(marker, 0, offset) for marker in ("\n", ";", "|")]
    for marker in (". ", "! ", "? "):
        position = text.rfind(marker, 0, offset)
        starts.append(position + 1 if position >= 0 else -1)
    start = max(starts) + 1

    ends = [
        position
        for position in (
            text.find("\n", offset),
            text.find(";", offset),
            text.find("|", offset),
        )
        if position >= 0
    ]
    for marker in (". ", "! ", "? "):
        position = text.find(marker, offset)
        if position >= 0:
            ends.append(position + 1)
    end = min(ends, default=len(text))
    return start, end


def claim_scope(text: str, offset: int) -> str:
    """Return the sentence/table scope containing an assertion offset."""
    start, end = claim_scope_bounds(text, offset)
    return text[start:end]


def claim_assertion_bounds(
    text: str, offset: int, end: int | None = None
) -> tuple[int, int]:
    """Bound the predicate containing a matched relation, not the whole sentence."""
    sentence_start, sentence_end = claim_scope_bounds(text, offset)
    relation_end = min(end if end is not None else offset + 1, sentence_end)
    anchor = max(offset, relation_end - 1)
    boundaries: list[tuple[int, int]] = []
    for connector in ASSERTION_CONNECTOR.finditer(
        text, sentence_start, sentence_end
    ):
        if not ASSERTION_RELATION_LEAD.match(text, connector.end(), sentence_end):
            continue
        boundaries.append((connector.start(), connector.end()))

    assertion_start = sentence_start
    assertion_end = sentence_end
    for connector_start, relation_start in boundaries:
        if relation_start <= anchor:
            assertion_start = max(assertion_start, relation_start)
        elif connector_start >= relation_end:
            assertion_end = min(assertion_end, connector_start)
            break
    return assertion_start, assertion_end


def claim_relation_scope(text: str, offset: int, end: int | None = None) -> str:
    """Return predicate-local context through the matched relation."""
    start, assertion_end = claim_assertion_bounds(text, offset, end)
    return text[start : min(end if end is not None else assertion_end, assertion_end)]


def claim_assertion_scope(text: str, offset: int, end: int | None = None) -> str:
    """Return the full predicate-local assertion, including a rejection suffix."""
    start, assertion_end = claim_assertion_bounds(text, offset, end)
    return text[start:assertion_end]


def claim_is_explicitly_rejected(
    text: str, offset: int, end: int | None = None
) -> bool:
    relation_end = end if end is not None else offset + 1
    start, assertion_end = claim_assertion_bounds(text, offset, relation_end)
    prefix = text[start:relation_end]
    suffix = text[relation_end:assertion_end]
    return bool(
        FALSE_ASSERTION_PREFIX.search(prefix)
        or FALSE_ASSERTION_SUFFIX.search(suffix)
    )


def claim_is_noncurrent(text: str, offset: int, end: int | None = None) -> bool:
    relation_end = end if end is not None else offset + 1
    _, assertion_end = claim_assertion_bounds(text, offset, relation_end)
    prefix = claim_relation_scope(text, offset, relation_end)
    prefix = PARENTHETICAL_TEMPORAL.sub(" ", prefix)
    prefix = RELATIVE_TEMPORAL.sub(" ", prefix)
    return bool(
        CLAIM_NONCURRENT.search(prefix)
        or CLAIM_NONCURRENT_SUFFIX.match(text[relation_end:assertion_end])
    )


def claim_is_denied(text: str, offset: int, end: int | None = None) -> bool:
    if claim_is_explicitly_rejected(text, offset, end):
        return True
    scope = claim_relation_scope(text, offset, end)
    scope = INCIDENTAL_NEGATIVE_MODIFIER.sub(" ", scope)
    if re.search(r"\bneither\b(?:(?![.!?]).){0,160}?\bnor\b", scope, re.I):
        return True
    return sum(1 for _ in CLAIM_DENIAL.finditer(scope)) % 2 == 1


def claim_is_current_semantic(
    text: str, offset: int, end: int | None = None
) -> bool:
    """Filter time/rejected attribution while preserving encoded negative semantics."""
    return not claim_is_noncurrent(text, offset, end) and not claim_is_explicitly_rejected(
        text, offset, end
    )


def claim_is_current_affirmative(
    text: str, offset: int, end: int | None = None
) -> bool:
    return not claim_is_noncurrent(text, offset, end) and not claim_is_denied(
        text, offset, end
    )


def count_claim_is_denied(text: str, offset: int) -> bool:
    prefix = text[max(0, offset - 24) : offset]
    return bool(COUNT_DENIAL_PREFIX.search(prefix))


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


def decoded_url_path(path: str) -> str:
    """Decode nested URL escapes enough to compare a public route canonically."""
    decoded = path
    # Each effective unquote shortens an encoded path, so this input-derived
    # bound reaches the fixed point at any possible nesting depth.
    for _ in range(len(path) + 1):
        unescaped = unquote(decoded)
        if unescaped == decoded:
            break
        decoded = unescaped
    return decoded


def provider_studio_url_violations(text: str) -> list[int]:
    """Reject current product destinations that are not the exact public Studio URL."""

    def current_product_scope(offset: int, end: int) -> tuple[str, bool, bool]:
        scope = claim_assertion_scope(text, offset, end)
        sentence = claim_scope(text, offset)
        if claim_is_noncurrent(text, offset, end) or claim_is_denied(
            text, offset, end
        ):
            return scope, False, False
        if STUDIO_DOCUMENTATION_CONTEXT.search(scope):
            return scope, False, False
        provider_context = bool(
            re.search(r"\bProvider\s+Studio\b", sentence, re.IGNORECASE)
        )
        studio_draft_context = bool(
            re.search(r"\bStudio\b", sentence, re.IGNORECASE)
            and re.search(
                r"\bprovider(?:-listing)?\s+drafts?\b", sentence, re.IGNORECASE
            )
        )
        return scope, provider_context or studio_draft_context, True

    def product_label(label: str, scope: str) -> bool:
        if re.search(r"\b(?:documentation|docs?|guide|reference)\b", label, re.I):
            return False
        if re.search(r"\bProvider\s+Studio\b", label, re.IGNORECASE):
            return True
        return bool(
            re.fullmatch(r"\s*Studio\s*", label, re.IGNORECASE)
            and re.search(r"\bprovider(?:-listing)?\s+drafts?\b", scope, re.I)
        )

    violations: list[int] = []
    linked_spans: list[tuple[int, int]] = []
    for match in MARKDOWN_INLINE_LINK.finditer(text):
        scope, relevant_scope, current = current_product_scope(
            match.start(), match.end()
        )
        linked_spans.append(match.span("destination"))
        if not current:
            continue
        relevant = product_label(match.group("label"), scope) or (
            relevant_scope and bool(STUDIO_PRODUCT_ACTION.search(scope))
        )
        if relevant and match.group("destination") != CANONICAL_STUDIO_URL:
            violations.append(match.start("destination"))

    reference_definitions: dict[str, list[str]] = {}
    for definition in MARKDOWN_REFERENCE_DEFINITION.finditer(text):
        reference = " ".join(
            definition.group("reference").casefold().split()
        )
        reference_definitions.setdefault(reference, []).append(
            definition.group("destination")
        )
    for match in MARKDOWN_REFERENCE_LINK.finditer(text):
        scope, relevant_scope, current = current_product_scope(
            match.start(), match.end()
        )
        if not current:
            continue
        relevant = product_label(match.group("label"), scope) or (
            relevant_scope and bool(STUDIO_PRODUCT_ACTION.search(scope))
        )
        if not relevant:
            continue
        reference = " ".join(match.group("reference").casefold().split())
        destinations = reference_definitions.get(reference, [])
        if len(destinations) != 1 or destinations[0] != CANONICAL_STUDIO_URL:
            violations.append(match.start())

    for match in STUDIO_EXPLICIT_DESTINATION.finditer(text):
        _, _, current = current_product_scope(match.start(), match.end())
        if not current:
            continue
        destination = match.group("destination")
        if destination.startswith("["):
            continue
        candidate = destination.strip("<>\"'").rstrip(".,;:")
        if candidate != CANONICAL_STUDIO_URL:
            violations.append(match.start("destination"))

    for match in STUDIO_RAW_DESTINATION.finditer(text):
        if any(start <= match.start() < end for start, end in linked_spans):
            continue
        candidate = match.group("destination").rstrip(".,;:")
        scope, relevant_scope, current = current_product_scope(
            match.start(), match.end()
        )
        if not current:
            continue
        parsed = urlsplit(candidate)
        decoded_path = decoded_url_path(parsed.path).casefold()
        stele_host = (parsed.hostname or "").casefold() == "stele.monolythium.com"
        studio_like = stele_host and decoded_path.startswith(("/studio", "/provider"))
        actionable = relevant_scope and bool(
            STUDIO_PRODUCT_ACTION.search(scope)
            or re.search(r"\bProvider\s+Studio\s*:\s*#", scope, re.IGNORECASE)
        )
        if (studio_like or actionable) and candidate != CANONICAL_STUDIO_URL:
            violations.append(match.start())

    return sorted(set(violations))


def stele_status_contradictions(text: str) -> list[tuple[int, str]]:
    """Return every present-tense claim that conflicts with the release snapshot."""
    prose = status_prose(text)
    contradictions: list[tuple[int, str]] = []

    def record_tool_count(
        kind: str,
        claim: re.Match[str],
        count_token: str,
        qualifier_token: str | None,
    ) -> None:
        if claim_is_noncurrent(
            prose, claim.start(), claim.end()
        ) or claim_is_denied(
            prose, claim.start(), claim.end()
        ) or count_claim_is_denied(prose, claim.start()):
            return
        expected = 2 if kind == "hosted" else 3
        actual = count_value(count_token)
        qualifier = (qualifier_token or "").casefold()
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

    surfaces = list(STELE_MCP_SURFACE.finditer(prose))
    for index, surface in enumerate(surfaces):
        kind = "hosted" if surface.group("hosted") else "local"
        next_surface = (
            surfaces[index + 1].start() if index + 1 < len(surfaces) else len(prose)
        )
        segment_end = min(next_surface, surface.end() + 600)
        for claim in TOOL_COUNT_CLAIM.finditer(prose, surface.end(), segment_end):
            if UNRELATED_TOOL_COUNT_SUBJECT.search(
                prose[surface.end() : claim.end()]
            ):
                continue
            record_tool_count(
                kind,
                claim,
                claim.group("count"),
                claim.group("qualifier"),
            )
        for claim in TOOL_ENDPOINT_COUNT_CLAIM.finditer(
            prose, surface.end(), segment_end
        ):
            if UNRELATED_TOOL_COUNT_SUBJECT.search(
                prose[surface.end() : claim.end()]
            ):
                continue
            record_tool_count(
                kind,
                claim,
                claim.group("count"),
                claim.group("qualifier"),
            )
        for claim in TOOL_COUNT_REVERSED_AFTER_SURFACE.finditer(
            prose, surface.end(), segment_end
        ):
            if UNRELATED_TOOL_COUNT_SUBJECT.search(
                prose[surface.end() : claim.end()]
            ):
                continue
            record_tool_count(
                kind,
                claim,
                claim.group("count"),
                claim.group("qualifier"),
            )
        expected_count = 2 if kind == "hosted" else 3
        for claim in NEGATED_TOOL_COUNT_AFTER_SURFACE.finditer(
            prose, surface.end(), segment_end
        ):
            if UNRELATED_TOOL_COUNT_SUBJECT.search(
                prose[surface.end() : claim.end()]
            ):
                continue
            count_token = (
                claim.group("count_direct")
                or claim.group("count_diff")
                or claim.group("count_verb")
            )
            if count_value(count_token) == expected_count and claim_is_current_semantic(
                prose, claim.start(), claim.end()
            ):
                contradictions.append(
                    (
                        claim.start(),
                        f"{kind} Stele MCP denies its required {expected_count}-tool surface",
                    )
                )
        for claim in NO_TOOL_SURFACE_AFTER_MCP.finditer(
            prose, surface.end(), segment_end
        ):
            if UNRELATED_TOOL_COUNT_SUBJECT.search(
                prose[surface.end() : claim.end()]
            ):
                continue
            _, assertion_end = claim_assertion_bounds(
                prose, claim.start(), claim.end()
            )
            exception = TOOL_ABSENCE_EXCEPTION_SUFFIX.match(
                prose[claim.end() : assertion_end]
            )
            if exception and count_value(exception.group("count")) == expected_count:
                continue
            if claim_is_current_semantic(prose, claim.start(), claim.end()):
                contradictions.append(
                    (
                        claim.start(),
                        f"{kind} Stele MCP denies its required {expected_count}-tool surface",
                    )
                )

        if kind == "hosted":
            segment = prose[surface.start() : segment_end]
            for label, pattern in HOSTED_TRANSACTION_ENABLED.items():
                for match in pattern.finditer(segment):
                    offset = surface.start() + match.start()
                    if claim_is_current_affirmative(
                        prose, offset, surface.start() + match.end()
                    ):
                        contradictions.append((offset, label))

        if kind == "local":
            segment = prose[surface.start() : segment_end]
            for label, pattern in LOCAL_TRANSACTION_ENABLED.items():
                for match in pattern.finditer(segment):
                    offset = surface.start() + match.start()
                    if claim_is_current_affirmative(
                        prose, offset, surface.start() + match.end()
                    ):
                        contradictions.append((offset, label))

    for claim in MCP_SURFACE_REVERSE_COUNT.finditer(prose):
        kind = "hosted" if claim.group("hosted") else "local"
        record_tool_count(
            kind,
            claim,
            claim.group("count"),
            claim.group("qualifier"),
        )

    for claim in PUBLISHED_SERVICE_COUNT.finditer(prose):
        if claim_is_noncurrent(
            prose, claim.start(), claim.end()
        ) or claim_is_denied(
            prose, claim.start(), claim.end()
        ) or count_claim_is_denied(prose, claim.start()):
            continue
        actual = count_value(claim.group("count"))
        if actual != 0:
            contradictions.append(
                (
                    claim.start(),
                    f"Stele catalog claims {actual} published services; expected zero",
                )
            )

    for patterns, polarity_mode in (
        (INVENTORY_ENABLED, "affirmative"),
        (CATALOG_REVERSE_ENABLED, "affirmative"),
        (HOSTED_TOOL_INVENTORY_OVERCLAIMS, "affirmative"),
        (PUBLIC_WEB_BOOKING_DRAFT_CREATION, "affirmative"),
        (STALE_PUBLIC_WEB_DRAFT_DENIAL, "semantic"),
        (BOOKING_DRAFT_WITHOUT_LISTING, "affirmative"),
        (BOOKING_DRAFT_PREREQUISITE_CONTRADICTIONS, "semantic"),
        (PROVIDER_DRAFT_BOUNDARY, "affirmative"),
        (IDENTITY_OVERCLAIMS, "affirmative"),
        (IDENTITY_REVERSE_OVERCLAIMS, "affirmative"),
        (IDENTITY_NAMED_OVERCLAIMS, "affirmative"),
        (DESKTOP_STELE_EMBEDDING, "affirmative"),
        (STALE_ECONOMIC_PREVIEW, "affirmative"),
        (PUBLIC_WEB_FORBIDDEN_CAPABILITIES, "affirmative"),
        (HOSTED_TRANSACTION_REVERSE, "affirmative"),
        (GATED_CAPABILITY_ACTIVATION, "affirmative"),
        (DOUBLE_NEGATION_CONTRADICTIONS, "affirmative"),
        (SEMANTIC_NEGATED_ABSENCE, "semantic"),
        (COORDINATED_TARGET_ASSERTIONS, "affirmative"),
    ):
        for label, pattern in patterns.items():
            for match in pattern.finditer(prose):
                eligible = (
                    claim_is_current_affirmative(prose, match.start(), match.end())
                    if polarity_mode == "affirmative"
                    else claim_is_current_semantic(prose, match.start(), match.end())
                )
                if eligible:
                    contradictions.append((match.start(), label))

    for offset in provider_studio_url_violations(prose):
        contradictions.append((offset, "non-canonical Provider Studio URL"))

    for label, capability in GATED_CAPABILITIES.items():
        forward = re.compile(
            rf"\b{capability}\b(?:(?![.!?]).){{0,90}}?\b"
            rf"{STATE_COPULA}\s+{STATE_TIME_MODIFIER}{ENABLED_STATE}\b",
            re.IGNORECASE | re.DOTALL,
        )
        reverse = re.compile(
            rf"\b{STATE_TIME_MODIFIER}{REVERSE_ENABLED_STATE}\s+"
            rf"(?:Stele\s+)?{capability}\b",
            re.IGNORECASE,
        )
        negated_disabled = re.compile(
            rf"\b{capability}\b(?:(?![.!?]).){{0,90}}?\b"
            rf"{NEGATED_DISABLED_RELATION}\b",
            re.IGNORECASE | re.DOTALL,
        )
        for pattern in (forward, reverse, negated_disabled):
            for match in pattern.finditer(prose):
                if claim_is_current_affirmative(prose, match.start(), match.end()):
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
