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
    "Hosted Stele MCP",
    "exactly two OAuth-protected tools",
    "local Stele MCP",
    "exactly three read/status tools",
    "no transaction tool",
    "economic writes",
    "transaction signing",
    "mainnet remain off",
)


def folded_prose(text: str) -> str:
    """Normalize Markdown wrapping before checking required prose anchors."""
    without_quote_prefixes = re.sub(r"(?m)^>\s?", "", text)
    return " ".join(without_quote_prefixes.casefold().split())


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
        for label, pattern in STALE_STELE_DEPLOYMENT.items():
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
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
