#!/usr/bin/env python3
"""Fail closed on regressions in the reconciled public capability boundary."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import markdown


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


@dataclass(frozen=True)
class RenderedLink:
    """A visible link after Markdown reference and entity resolution."""

    label: str
    destination: str
    context: str
    context_offset: int
    structural_context: str


@dataclass(frozen=True)
class RenderedMarkdown:
    """Visible prose and links produced by the same Markdown engine as the build."""

    prose: str
    links: tuple[RenderedLink, ...]


class _RenderedMarkdownParser(HTMLParser):
    """Collect visible prose while excluding code and hidden HTML containers."""

    _BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "dd",
        "div",
        "dl",
        "dt",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "nav",
        "p",
        "section",
        "td",
        "th",
    }
    # Inline code is visible publication prose and is commonly the only exact
    # spelling of a tool or protocol method. A surrounding <pre> still suppresses
    # fenced/indented code, so examples cannot satisfy release anchors.
    _NON_PROSE_TAGS = {"noscript", "pre", "script", "style", "template"}
    _VOID_TAGS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._tag_suppression: list[tuple[str, bool]] = []
        self._suppressed_depth = 0
        self._block_stack: list[int] = []
        self._blocks: list[list[str]] = []
        self._block_kinds: list[str] = []
        self._section_headings: dict[int, str] = {}
        self._active_link: tuple[str, int, list[str], str, str] | None = None
        self._raw_links: list[tuple[str, int, str, str, str]] = []

    @staticmethod
    def _is_hidden(tag: str, attrs: list[tuple[str, str | None]]) -> bool:
        attributes = {name.casefold(): (value or "") for name, value in attrs}
        style = re.sub(r"\s+", "", attributes.get("style", "").casefold())
        return bool(
            tag in _RenderedMarkdownParser._NON_PROSE_TAGS
            or "hidden" in attributes
            or attributes.get("aria-hidden", "").casefold() == "true"
            or "display:none" in style
            or "visibility:hidden" in style
        )

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        tag = tag.casefold()
        suppressed = self._suppressed_depth > 0 or self._is_hidden(tag, attrs)
        if tag not in self._VOID_TAGS:
            self._tag_suppression.append((tag, suppressed))
        if suppressed:
            if tag not in self._VOID_TAGS:
                self._suppressed_depth += 1
            return

        if tag in self._BLOCK_TAGS:
            self._blocks.append([])
            self._block_kinds.append(tag)
            self._block_stack.append(len(self._blocks) - 1)

        attributes = {name.casefold(): (value or "") for name, value in attrs}
        if tag == "a":
            destination = attributes.get("href")
            if destination is not None:
                block_index = self._block_stack[-1] if self._block_stack else -1
                prefix = (
                    "".join(self._blocks[block_index])
                    if 0 <= block_index < len(self._blocks)
                    else ""
                )
                ordered_headings = [
                    self._section_headings[level]
                    for level in sorted(self._section_headings)
                ]
                provider_levels = [
                    index
                    for index, heading in enumerate(ordered_headings)
                    if re.search(
                        r"\bProvider\s+Studio\b", heading, re.IGNORECASE
                    )
                ]
                structural_parts = (
                    ordered_headings[provider_levels[-1] :]
                    if provider_levels
                    else []
                )
                if (
                    0 <= block_index < len(self._block_kinds)
                    and self._block_kinds[block_index] == "li"
                ):
                    for prior_index in range(block_index - 1, -1, -1):
                        prior_kind = self._block_kinds[prior_index]
                        if re.fullmatch(r"h[1-6]", prior_kind):
                            break
                        prior = " ".join("".join(self._blocks[prior_index]).split())
                        if prior_kind == "p" and prior:
                            structural_parts.append(prior)
                            break
                structure = ": ".join(structural_parts)
                self._active_link = (
                    destination,
                    block_index,
                    [],
                    prefix,
                    structure,
                )
        elif tag == "img":
            # The image alt string is the published/accessibility label of an
            # image link and must receive the same destination checks as text.
            self.handle_data(attributes.get("alt", ""))

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)
        if tag.casefold() not in self._VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if not self._tag_suppression:
            return
        open_tag, suppressed = self._tag_suppression.pop()
        if open_tag != tag:
            # Python-Markdown emits balanced HTML. Treat an unexpected raw-HTML
            # mismatch as non-prose instead of trying to infer visibility.
            self._suppressed_depth = max(self._suppressed_depth, 1)
            return
        if suppressed:
            self._suppressed_depth -= 1
            return

        if tag == "a" and self._active_link is not None:
            destination, block_index, label, prefix, section = self._active_link
            self._raw_links.append(
                (destination, block_index, "".join(label), prefix, section)
            )
            self._active_link = None

        if re.fullmatch(r"h[1-6]", tag) and self._block_stack:
            level = int(tag[1])
            heading = " ".join(
                "".join(self._blocks[self._block_stack[-1]]).split()
            )
            self._section_headings = {
                key: value
                for key, value in self._section_headings.items()
                if key < level
            }
            if (
                STUDIO_DISTINCT_PRODUCT_ACTOR.search(heading)
                and not re.search(r"\bProvider\s+Studio\b", heading, re.IGNORECASE)
            ):
                self._section_headings.clear()
            if heading:
                self._section_headings[level] = heading

        if tag in self._BLOCK_TAGS and self._block_stack:
            self._block_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._suppressed_depth:
            return
        if not self._blocks:
            self._blocks.append([])
            self._block_kinds.append("text")
        block_index = self._block_stack[-1] if self._block_stack else 0
        self._blocks[block_index].append(data)
        if self._active_link is not None:
            self._active_link[2].append(data)

    def result(self) -> RenderedMarkdown:
        blocks = tuple(" ".join("".join(parts).split()) for parts in self._blocks)
        visible_blocks = tuple(block for block in blocks if block)
        links: list[RenderedLink] = []
        for destination, block_index, label, prefix, section in self._raw_links:
            normalized_label = " ".join(label.split())
            block = blocks[block_index] if 0 <= block_index < len(blocks) else ""
            normalized_prefix = " ".join(prefix.split())
            section_prefix = f"{section}: " if section and section != block else ""
            links.append(
                RenderedLink(
                    label=normalized_label,
                    destination=destination,
                    context=f"{section_prefix}{block}",
                    context_offset=(
                        len(section_prefix)
                        + len(normalized_prefix)
                        + int(bool(normalized_prefix and normalized_label))
                    ),
                    structural_context=section,
                )
            )
        return RenderedMarkdown(
            prose="\n".join(visible_blocks),
            links=tuple(links),
        )


@lru_cache(maxsize=32)
def rendered_markdown(text: str) -> RenderedMarkdown:
    """Render Markdown before evaluating anchors or structured links.

    This deliberately uses the repository's pinned renderer. Reference links,
    shortcut references, multiline labels, and HTML entities therefore have the
    same meaning here that they have in the published HTML. Comments, code, and
    hidden HTML cannot satisfy a release anchor.
    """

    html = markdown.markdown(
        text,
        extensions=["extra", "sane_lists", "smarty", "toc"],
        extension_configs={"toc": {"permalink": False, "marker": ""}},
        output_format="html5",
    )
    parser = _RenderedMarkdownParser()
    parser.feed(html)
    parser.close()
    return parser.result()

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
        r"is\s+(?:hosted|contained|included|bundled)\s+(?:inside|in|by|on)|"
        r"lives?\s+(?:inside|in)|runs?\s+(?:inside|in))\s+"
        r"(?:the\s+)?(?:Desktop\s+Wallet|desktop\s+wallet)\b|"
        r"\b(?:the\s+)?(?:Desktop\s+Wallet|desktop\s+wallet)\b"
        r"(?:(?![.!?,;]|\b(?:and|or|but|however|yet|while|whereas|though)\b).)"
        r"{0,100}?\b(?:"
        r"(?:can|does|now|currently)\s+(?!not\b)(?:host|house|carry|integrate)|"
        r"includes?|bundles?|embeds?|contains?|hosts?|houses?|carries?|integrates?|"
        r"ships?\s+with|has(?!\s+(?:no|not|zero)\b))\s+"
        r"(?:(?:an?|the)\s+)?Stele(?:\s+marketplace)?\b)",
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
    "authenticated tools/list response is the authoritative inventory",
    "stele_create_provider_listing_draft",
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
    "authenticated tools/list response is the authoritative inventory for that session",
    "baseline tools provide public catalog search",
    "booking-draft preparation",
    "Hosted booking-draft preparation is unavailable without a published listing",
    "stele_create_provider_listing_draft",
    "exists only when that exact name appears in authenticated tools/list",
    "each successful stele_create_provider_listing_draft operation creates exactly one new private wallet-owned unpublished provider-listing draft",
    "an idempotent replay returns the same draft without creating another",
    "cannot list, read, update, delete, or publish an existing draft",
    "does not sign, submit, broadcast, or settle transactions",
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
    "both": 2,
    "pair": 2,
    "couple": 2,
    "trio": 3,
    "dozen": 12,
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
TOOL_COUNT_QUALIFIER = (
    r"(?:exactly|only|(?:an?\s+)?total\s+of|at\s+least|more\s+than|"
    r"no\s+fewer\s+than|no\s+less\s+than|fewer\s+than|less\s+than|"
    r"up\s+to|at\s+most|no\s+more\s+than|(?:an?\s+)?maximum\s+of|"
    r"max(?:imum)?(?:\s+of)?|(?:an?\s+)?minimum\s+of|"
    r"min(?:imum)?(?:\s+of)?|"
    r"about|approximately|roughly|around)"
)
TOOL_COUNT_POST_QUALIFIER = r"(?:or\s+more|or\s+(?:fewer|less))"
TOOL_COMPOUND_UNIT = r"(?:pairs?|couples?|trios?|dozens?)"
TOOL_ORDINAL_COUNT = r"(?:second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)"
TOOL_COUNT_DESCRIPTOR_WORD = (
    rf"(?!(?:{COUNT_TOKEN})\b)"
    r"(?!(?:and|or|plus|then|with|of|in|from|now|currently|today|already|tools?|endpoints?|"
    r"capabilit(?:y|ies)|has|exposes?|offers?|provides?|includes?|reports?|"
    r"lists?|shows?)\b)[a-z][a-z0-9/-]*"
)
TOOL_TYPED_COUNT = re.compile(
    rf"\b(?:(?P<qualifier>{TOOL_COUNT_QUALIFIER})\s+)?(?P<expression>"
    rf"(?P<math_left>{COUNT_TOKEN})\s*(?P<math_operator>[x×*+])\s*"
    rf"(?P<math_right>{COUNT_TOKEN})|"
    rf"(?:(?P<compound_multiplier>{COUNT_TOKEN})\s+)?"
    rf"(?P<compound_unit>{TOOL_COMPOUND_UNIT})(?:\s+of)?|"
    rf"(?:(?:an?|the)\s+)?(?P<ordinal>{TOOL_ORDINAL_COUNT})|"
    rf"(?P<plain>{TOOL_COUNT_TOKEN}|an?)"
    rf")(?P<post_qualifier>\s+{TOOL_COUNT_POST_QUALIFIER})?\s+"
    rf"(?:(?:{TOOL_COUNT_DESCRIPTOR_WORD})(?:,\s*|\s+)){{0,6}}"
    rf"(?P<noun>tools?|endpoints?|capabilit(?:y|ies))\b",
    re.IGNORECASE,
)
TOOL_COUNT_CONNECTOR = re.compile(
    r"^\s*(?:,?\s*(?:and|plus)|\+)\s*$", re.IGNORECASE
)
TOOL_COUNT_META_CONTEXT = re.compile(
    r"(?:"
    r"\b(?:documents?|describes?|depicts?|models?|shows?|tests?)\b"
    r"(?:(?![.!?;]).){0,100}?\b(?:SDK|"
    r"(?:(?:conformance|end[- ]to[- ]end|integration|regression|system|unit)\s+test)|"
    r"test\s+(?:fixture|harness|case|server)|"
    r"fixture|mock|sample|example|reference\s+implementation)\b|"
    r"\b(?:SDK|"
    r"(?:(?:conformance|end[- ]to[- ]end|integration|regression|system|unit)\s+test)|"
    r"test\s+(?:fixture|harness|case|server)|fixture|mock|sample|"
    r"example|simulations?|reference\s+implementation)\b"
    r"(?:(?![.!?;]).){0,100}?\b"
    r"(?:depicts?|has|exposes?|models?|offers?|provides?|includes?|lists?|"
    r"reports?|shows?|simulates?)\b|"
    r"\b(?:documentation|docs?)\s+(?:contains?|has|includes?|lists?|shows?)\b"
    r")(?:(?![.!?;]).){0,80}$",
    re.IGNORECASE,
)
TOOL_COUNT_META_DESCRIPTOR = re.compile(
    r"\b(?:example|fixture|mock|sample|simulated|synthetic|test)\b"
    r"(?:(?![.!?;]).){0,80}\b(?:tools?|endpoints?|capabilit(?:y|ies))\b",
    re.IGNORECASE,
)
MCP_META_OBJECT_PREFIX = re.compile(
    r"\b(?:"
    r"(?:(?:conformance|end[- ]to[- ]end|integration|regression|system|unit)\s+)?"
    r"test|SDK\s+(?:example|fixture|sample)|documentation|docs?|example|fixture|"
    r"mockup|sample|simulation"
    r")\s+(?:about|covering|for|of)\s+(?:the\s+)?$|"
    r"\b(?:(?:conformance|end[- ]to[- ]end|integration|regression|system|unit)\s+)?"
    r"(?:documentation|docs?|example|fixture|mockup|sample|simulation|test)\s+"
    r"(?:asserts?|says?|states?|reports?|records?|shows?|depicts?|documents?)\s+"
    r"(?:that\s+)?$",
    re.IGNORECASE,
)
MCP_META_OBJECT_AFTER_SURFACE = re.compile(
    r"^\s+(?:documentation|docs?|example|fixture|mockup|sample|simulation|"
    r"SDK\s+(?:example|fixture|sample)|"
    r"(?:(?:conformance|end[- ]to[- ]end|integration|regression|system|unit)\s+)?"
    r"test(?:\s+(?:fixture|harness|case|server))?)\b(?:(?![.!?;]).){0,100}$",
    re.IGNORECASE | re.DOTALL,
)
MCP_COUNT_ANAPHORIC_PREDICATE = re.compile(
    r"[.!?;]\s+(?:it|this\s+(?:service|surface|MCP)|the\s+(?:service|surface|MCP))"
    r"\s+(?:(?:now|currently|today|presently|already)\s+)?"
    r"(?:has|exposes?|offers?|provides?|includes?|reports?|lists?|shows?)\b"
    r"(?:(?![.!?;]).){0,80}$",
    re.IGNORECASE,
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
MCP_AFTER_TYPED_COUNT = re.compile(
    r"^\s+(?:(?:is|are|remain)\s+"
    r"(?:(?:now|currently|today|presently)\s+)?"
    r"(?:(?:not\s+)?(?:available|exposed|offered|provided|listed|reported)|"
    r"unavailable|absent|missing)\s+)?"
    r"(?:in|on|at|through|from|for|by)\s+(?:the\s+)?"
    r"(?:(?P<hosted>Hosted)\s+|(?P<local>local)\s+)(?:Stele\s+)?MCP\b",
    re.IGNORECASE,
)
UNRELATED_TOOL_COUNT_SUBJECT = re.compile(
    r"\b(?:(?:another|other|separate|unrelated|the)\s+)?"
    r"(?:API|website|system|application|server|client|agent|product|surface|"
    r"Provider\s+Studio|public\s+web|Browser\s+Wallet|Desktop\s+Wallet|"
    r"Mobile\s+Wallet|user\s+wallet|buyer\s+wallet)\b"
    r"(?:(?![,;.!?]).){0,60}?\b(?:(?:"
    r"has|exposes?|offers?|uses?|includes?|provides?|reports?|lists?"
    r")\b|(?:tool|endpoint|capability)\s+count\s*(?:is\b|=|:))",
    re.IGNORECASE,
)
MCP_CLAIM_HARD_BOUNDARY = re.compile(r"[.!?;|]")
ROLE_WORD = r"[a-z][a-z-]{2,}"
ALTERNATE_ROLE_WORD = (
    r"(?!(?:hosted|MCP|public|same|service|Stele|this|that|its)\b)"
    + ROLE_WORD
)
ALTERNATE_WALLET_KIND = (
    r"(?:browser|desktop|external|externally[- ](?:owned|managed|administered|"
    r"controlled)|hardware|independently[- ](?:owned|managed|administered|"
    r"controlled)|local|mobile|replacement|separately[- ](?:owned|managed|"
    r"administered|controlled)|self[- ]custodial|successor|third[- ]party)"
)
DISTINCT_ROLE_PREFIX = (
    r"(?:(?:another|different|external|independent|other|separate|third[- ]party)\s+)?"
)
ALTERNATE_WALLET_ACTOR = (
    rf"(?:{DISTINCT_ROLE_PREFIX}{ALTERNATE_ROLE_WORD}(?:['’]s)?\s+"
    rf"(?:{ALTERNATE_WALLET_KIND}\s+)?wallet|"
    rf"{DISTINCT_ROLE_PREFIX}{ALTERNATE_ROLE_WORD}"
    rf"[- ](?:controlled|owned|managed|operated|specific)\s+"
    rf"(?:{ALTERNATE_WALLET_KIND}\s+)?wallet|"
    r"(?:role[- ]specific|external(?:ly)?[- ](?:controlled|owned|managed|"
    r"administered)|external|third[- ]party|separate(?:ly[- ]administered)?|"
    r"independent(?:ly[- ]administered)?|another|replacement|successor|hardware|"
    r"browser|desktop|local|mobile|self[- ]custodial)\s+wallet)"
)
HOSTED_ROLE_ASSIGNMENT = re.compile(
    rf"\b(?:is|becomes?|represents?|(?:acts?|is\s+acting)\s+as|serves?\s+as|"
    rf"(?:acts?|serves?|functions?|operates?|works?)\s+(?:in\s+)?"
    rf"(?:(?:its|the)\s+)?capacity\s+(?:as|of)|"
    rf"works?\s+as|operates?\s+as|functions?\s+as|identif(?:y|ies)\s+as|"
    rf"identif(?:y|ies)\s+itself\s+as|"
    rf"(?:plays?|takes?|assumes?|fills?)\s+(?:on\s+)?"
    rf"(?:(?:the|an?)\s+)?role\s+(?:of|as))"
    rf"\s+(?:itself\s+)?"
    rf"(?:(?:the|an?)\s+)?(?P<role_phrase>{ROLE_WORD}(?:\s+{ROLE_WORD}){{0,2}})"
    rf"(?=\s*(?:[,.;!?]|\b(?:and|but|however|while|whereas|yet)\b))",
    re.IGNORECASE,
)
HOSTED_ROLE_DUTY_ASSIGNMENT = re.compile(
    rf"\b(?:has|holds?|takes?\s+on|assumes?|performs?|fulfils?|fulfills?|carries?|"
    rf"is\s+(?:assigned|responsible\s+for))\s+"
    rf"(?:(?:the|an?)\s+)?(?P<role_phrase>{ROLE_WORD}(?:\s+{ROLE_WORD}){{0,2}}?)"
    rf"\s+(?:role|duties|duty|responsibilities|responsibility|functions?|capacity)\b",
    re.IGNORECASE,
)
HOSTED_ROLE_CAPACITY_ASSIGNMENT = re.compile(
    rf"\b(?:acts?|serves?|functions?|operates?|works?)\s+in\s+"
    rf"(?:(?:its|the|an?)\s+)?"
    rf"(?P<role_phrase>{ROLE_WORD}(?:\s+{ROLE_WORD}){{0,2}}?)\s+capacity\b",
    re.IGNORECASE,
)
HOSTED_ROLE_DUTY_OF_ASSIGNMENT = re.compile(
    rf"\b(?:assumes?|performs?|fulfils?|fulfills?|carries?|takes?\s+on)\s+"
    rf"(?:(?:the|its)\s+)?(?:role|duties|duty|responsibilities|responsibility|"
    rf"functions?)\s+(?:of|as)\s+(?:(?:the|an?)\s+)?"
    rf"(?P<role_phrase>{ROLE_WORD}(?:\s+{ROLE_WORD}){{0,2}}?)"
    rf"(?=\s*(?:[,.;!?]|\b(?:and|but|however|while|whereas|yet)\b))",
    re.IGNORECASE,
)
ROLE_WALLET_REFERENCE = re.compile(
    rf"\b(?:(?:the|an?)\s+)?(?P<role>{ROLE_WORD})(?:['’]s)?(?:"
    rf"\s+(?:{ALTERNATE_WALLET_KIND}\s+)?wallet|"
    r"[- ](?:controlled|owned|managed|operated|specific)\s+wallet)\b",
    re.IGNORECASE,
)
ROLE_QUALIFIED_WALLET_REFERENCE = re.compile(
    rf"\b(?:(?:the|an?)\s+)?(?P<role>{ROLE_WORD}?)"
    rf"[- ](?:controlled|owned|managed|operated|specific)\s+"
    rf"(?:{ALTERNATE_WALLET_KIND}\s+)?wallet\b",
    re.IGNORECASE,
)
ROLE_SIGNER_REFERENCE = re.compile(
    rf"\b(?:(?:the|an?)\s+)?(?P<role>{ROLE_WORD})(?:['’]s)?\s+signer\b",
    re.IGNORECASE,
)
GENERIC_ROLE_SIGNER_REFERENCE = re.compile(
    r"\b(?:"
    r"(?:(?:this|that|the|its)\s+)?role(?:['’]s)?[- ](?:wallet|signer)|"
    r"(?:wallet|signer)\s+(?:for|of)\s+(?:(?:this|that|the)\s+)?role"
    r")\b",
    re.IGNORECASE,
)
DISTINCT_ACTOR_PREFIX = re.compile(
    r"(?:"
    r"\b(?:(?:an?|the)\s+)?(?:another|different|external|externally[- ](?:owned|"
    r"managed|administered|controlled)|independent|independently[- ](?:owned|"
    r"managed|administered|controlled)|other|replacement|separate|"
    r"separately[- ](?:owned|managed|administered|controlled)|successor|"
    r"third[- ]party)\s+|"
    r"\b(?!(?:hosted|MCP|service|Stele|its)\b)[a-z][a-z0-9-]*(?:['’]s|"
    r"[- ](?:controlled|owned|managed|operated))\s+"
    r")$",
    re.IGNORECASE,
)
DISTINCT_ACTOR_SUFFIX = re.compile(
    r"^\s+(?:"
    r"(?:administered|controlled|owned|managed|operated)\s+by\s+"
    r"(?!(?:the\s+)?(?:hosted\s+)?(?:Stele\s+)?MCP\b|itself\b)"
    r"|(?:of|for)\s+(?:(?:an?|the)\s+)?(?:another|different|external|independent|"
    r"other|separate|third[- ]party)\s+(?:actor|service|user|wallet)\b"
    r")",
    re.IGNORECASE,
)
EXPLICITLY_DISTINCT_WALLET_SUBJECT = re.compile(
    r"(?:"
    r"\b(?:its|this|that|the|an?)\s+"
    r"(?:(?:externally|independently|separately)[- ]"
    r"(?:administered|controlled|managed|operated|owned)|replacement|successor|"
    r"third[- ]party)\s+(?:(?:[a-z][a-z-]{2,})\s+){0,2}(?:wallet|signer)\b|"
    r"\b(?:wallet|signer)\b(?:(?![.!?;]).){0,80}?\b"
    r"(?:administered|controlled|managed|operated|owned)\s+by\s+"
    r"(?!(?:the\s+)?(?:hosted\s+)?(?:Stele\s+)?MCP\b|itself\b)"
    r"|\b(?:wallet|signer)\b(?:(?![.!?;]).){0,60}?\b"
    r"(?:(?:externally|independently|separately)[- ]"
    r"(?:administered|controlled|managed|operated|owned)|replacement|successor)\b"
    r")",
    re.IGNORECASE,
)
INTERVENING_ROLE_ACTOR = re.compile(
    r"(?:^|[.!?;]|\b(?:and|or|but|however|yet|while|whereas|though|plus|then)\b)"
    r"\s*(?:(?:the|an?|another|different|external|independent|other|separate|"
    r"third[- ]party)\s+)?(?:API|service|system|application|server|client|agent|"
    r"product|surface|public\s+web|Provider\s+Studio|Browser\s+Wallet|"
    r"Desktop\s+Wallet|Mobile\s+Wallet|user|buyer|provider|customer|operator)\b",
    re.IGNORECASE,
)
HOSTED_ANAPHORIC_REFERENT = (
    r"(?:It|"
    r"Its\s+(?:(?:same|public|hosted|Stele|service|MCP|[a-z][a-z-]{2,})\s+){0,2}"
    r"(?:API|endpoint|interface|service|MCP|wallet|signer)|"
    r"(?:This|That|The)\s+(?:(?:same|public|hosted|Stele)\s+){0,2}"
    r"(?:API|endpoint|interface|service|MCP|wallet|signer)"
    r"(?:(?:['’]s)?\s+(?:wallet|signer))?"
    r")"
)
HOSTED_ANAPHORIC_REFERENCE = re.compile(
    rf"(?:"
    rf"[.!?;:—–]\s*(?:(?:despite\s+this|even\s+so|however|nevertheless|"
    rf"nonetheless|still|then|yet)\s*,?\s*)?|"
    rf",\s*(?:and|but|yet)\s+(?:(?:however|nevertheless|nonetheless|still)\s*,?\s*)?"
    rf"){HOSTED_ANAPHORIC_REFERENT}"
    rf"(?:\s+(?:also|currently|nevertheless|now|still|then|yet))?\s*$",
    re.IGNORECASE,
)
INTERVENING_UNRELATED_ASSERTION_SUBJECT = re.compile(
    r"(?:[,;]\s*|\b(?:and|or|but|however|yet|while|whereas|though|plus|then)\b\s+)"
    r"(?:"
    r"(?:(?:the|an?)\s+)?(?:(?:another|current|distinct|new|other|replacement|"
    r"separate|unrelated)\s+)?(?:"
    r"API|system|application|server|worker|client|agent|product|surface|"
    r"Provider\s+Studio|public\s+web|Stele\s+web|web\s+app|Browser\s+Wallet|"
    r"Desktop\s+Wallet|desktop\s+wallet|Mobile\s+Wallet|mobile\s+wallet|catalog|"
    r"(?:account|buyer|client|customer|service)\s+portal|"
    r"customer(?:[- ]account|[- ]service)?\s+portal|buyers?|clients?|customers?"
    r")|"
    r"(?:(?:an?|another)\s+service|(?:(?:the|an?)\s+)?(?:other|separate|unrelated|"
    r"external|third[- ]party)\s+service)|"
    rf"(?:(?:the|an?)\s+)?{ALTERNATE_WALLET_ACTOR}"
    r")\b",
    re.IGNORECASE,
)
NESTED_UNRELATED_ASSERTION_SUBJECT = re.compile(
    r"(?:\bthat\s+(?:(?:the|an?)\s+)?(?:SDK|API|test\s+(?:fixture|harness|"
    r"case|server)|fixture|mock|sample|example)\b\s*$|"
    r"\b(?:that\s+)?(?:(?:the|an?|another|other|separate|unrelated)\s+)?"
    r"(?:SDK|API|test\s+(?:fixture|harness|case|server)|fixture|mock|sample|"
    r"example|Browser\s+Wallet|Desktop\s+Wallet|Mobile\s+Wallet|user\s+wallet|"
    r"buyer\s+wallet|external\s+wallet|third[- ]party\s+wallet)\b"
    r"(?:(?![.!?;]).){0,80}?\b(?:has|exposes?|offers?|provides?|includes?|"
    r"holds?|keeps?|uses?|signs?|broadcasts?|submits?)\b"
    r"(?:(?![.!?;]).){0,80}$)",
    re.IGNORECASE,
)
PUBLISHED_SERVICE_COUNT = re.compile(
    rf"\b(?P<count>{COUNT_TOKEN})\s+published\s+services?\b",
    re.IGNORECASE,
)
PUBLISHED_SERVICE_LOWER_BOUND_PREFIX = re.compile(
    r"\b(?P<qualifier>at\s+least|no\s+(?:fewer|less)\s+than|"
    r"(?:an?\s+)?minimum\s+of)\s+$",
    re.IGNORECASE,
)
CATALOG_COMPOUND_UNIT = r"(?:pairs?|couples?|trios?|dozens?)"
CATALOG_COUNT_TOKEN = (
    rf"(?:{TOOL_COUNT_TOKEN}\s+{CATALOG_COMPOUND_UNIT}|{TOOL_COUNT_TOKEN})"
)
CATALOG_NONZERO_QUALIFIER = (
    r"(?:exactly|only|about|approximately|roughly|at\s+least|more\s+than|"
    r"no\s+(?:fewer|less)\s+than)"
)
CATALOG_TIME_MODIFIER = (
    r"(?:(?:now|currently|today|already|presently|right\s+now|at\s+present|"
    r"at\s+the\s+moment|at\s+this\s+time|for\s+now)\s+)?"
)
CATALOG_STATE = r"(?:present|available|live|published)"
CATALOG_ITEM_NOUN = (
    r"(?:(?:public|published|live|available|service|provider)\s+){0,3}"
    r"(?:services?|listings?|entries)"
)
CATALOG_META_SUFFIX = (
    r"(?!(?:(?:['’]s)?\s+|-|/)(?:documentation|docs?|schema|guide|manual|page|section|"
    r"description|reference|archive|archived|example|examples|sample|samples|"
    r"fixture|fixtures|test|simulation|simulations|screenshot|mockup|copy)\b)"
)
CATALOG_LOCATION = (
    r"(?:"
    r"(?:in|on|within|inside|at)\s+(?:the\s+)?(?:public|Stele)\s+catalog\b|"
    r"(?:in|on|at)\s+(?:https?://)?stele\.monolythium\.com\b"
    r")"
    rf"{CATALOG_META_SUFFIX}"
)
CATALOG_COUNT_SURFACE = re.compile(
    rf"\b(?:Stele(?:['’]s)?|(?:public|Stele)\s+catalog|catalog|"
    rf"stele\.monolythium\.com)\b{CATALOG_META_SUFFIX}",
    re.IGNORECASE,
)
CATALOG_PUBLISHED_REVERSE_LOCATION = re.compile(
    rf"^\s*(?:(?:is|are|exists?|appears?|remains?)\s+)?{CATALOG_LOCATION}",
    re.IGNORECASE,
)
CATALOG_COUNT_ANAPHORIC_PREFIX = re.compile(
    r"^\s*(?:"
    r"(?:it|its\s+catalog|the\s+(?:public\s+)?catalog)\b|"
    r"(?:(?:now|currently|today|already|presently)\s+)?"
    r"(?:has|contains?|includes?|lists?|offers?|shows?|reports?)\b"
    r")",
    re.IGNORECASE,
)
CATALOG_REVERSE_RELATION = (
    rf"(?:"
    rf"(?:(?:do|does)\s+{CATALOG_TIME_MODIFIER})?(?:exists?|appears?)\s+|"
    rf"(?:is|are|remains?)\s+{CATALOG_TIME_MODIFIER}(?:{CATALOG_STATE}\s+)?|"
    rf"can\s+{CATALOG_TIME_MODIFIER}be\s+found\s+"
    rf")"
)
CATALOG_LOCATION_FIRST_RELATION = (
    rf"(?:"
    rf"(?:(?:do|does)\s+{CATALOG_TIME_MODIFIER})?(?:exists?|appears?)|"
    rf"(?:is|are|remains?)\s+{CATALOG_TIME_MODIFIER}(?:{CATALOG_STATE})?|"
    rf"can\s+{CATALOG_TIME_MODIFIER}be\s+found"
    rf")\b"
)
CATALOG_ITEM_COUNT = re.compile(
    rf"(?:"
    rf"\b(?:the\s+)?(?:public|Stele)\s+catalog\b"
    rf"{CATALOG_META_SUFFIX}\s+"
    rf"{CATALOG_TIME_MODIFIER}"
    rf"(?:contains?|has|includes?|lists?|offers?|shows?|reports?)\s+"
    rf"{CATALOG_TIME_MODIFIER}(?:an?\s+)?"
    rf"(?:(?P<forward_qualifier>{CATALOG_NONZERO_QUALIFIER})\s+)?"
    rf"(?P<forward_count>{CATALOG_COUNT_TOKEN})\s+(?:of\s+)?"
    rf"{CATALOG_ITEM_NOUN}\b|"
    rf"\b(?:an?\s+)?"
    rf"(?:(?P<reverse_qualifier>{CATALOG_NONZERO_QUALIFIER})\s+)?"
    rf"(?P<reverse_count>{CATALOG_COUNT_TOKEN})\s+(?:of\s+)?"
    rf"{CATALOG_ITEM_NOUN}\b\s+{CATALOG_TIME_MODIFIER}"
    rf"{CATALOG_REVERSE_RELATION}{CATALOG_LOCATION}|"
    rf"\bthere\s+{CATALOG_TIME_MODIFIER}(?:is|are|exist|exists)\s+"
    rf"{CATALOG_TIME_MODIFIER}(?:an?\s+)?"
    rf"(?:(?P<existential_qualifier>{CATALOG_NONZERO_QUALIFIER})\s+)?"
    rf"(?P<existential_count>{CATALOG_COUNT_TOKEN})\s+(?:of\s+)?"
    rf"{CATALOG_ITEM_NOUN}\b\s+"
    rf"{CATALOG_TIME_MODIFIER}(?:(?:{CATALOG_STATE})\s+)?{CATALOG_LOCATION}|"
    rf"\b{CATALOG_LOCATION}\s*,?\s+(?:there\s+)?{CATALOG_TIME_MODIFIER}"
    rf"(?:is|are|exist|exists)\s+{CATALOG_TIME_MODIFIER}(?:an?\s+)?"
    rf"(?:(?P<location_qualifier>{CATALOG_NONZERO_QUALIFIER})\s+)?"
    rf"(?P<location_count>{CATALOG_COUNT_TOKEN})\s+(?:of\s+)?"
    rf"{CATALOG_ITEM_NOUN}\b|"
    rf"\b{CATALOG_LOCATION}\s*,?\s+{CATALOG_TIME_MODIFIER}(?:an?\s+)?"
    rf"(?:(?P<location_reverse_qualifier>{CATALOG_NONZERO_QUALIFIER})\s+)?"
    rf"(?P<location_reverse_count>{CATALOG_COUNT_TOKEN})\s+(?:of\s+)?"
    rf"{CATALOG_ITEM_NOUN}\b\s+{CATALOG_TIME_MODIFIER}"
    rf"{CATALOG_LOCATION_FIRST_RELATION}"
    rf")",
    re.IGNORECASE,
)

CATALOG_RICH_QUALIFIER = (
    r"(?:exactly|only|about|approximately|roughly|around|at\s+least|"
    r"more\s+than|no\s+(?:fewer|less)\s+than|at\s+most|up\s+to|"
    r"(?:an?\s+)?minimum\s+of|(?:an?\s+)?maximum\s+of)"
)
CATALOG_ARTICLED_COUNT = rf"(?:an?\s+)?{CATALOG_COUNT_TOKEN}"
CATALOG_RANGE_EXPRESSION = (
    rf"(?:between\s+{CATALOG_ARTICLED_COUNT}\s+and\s+{CATALOG_ARTICLED_COUNT}|"
    rf"{CATALOG_ARTICLED_COUNT}\s+(?:to|through|or|[-–—])\s+"
    rf"{CATALOG_ARTICLED_COUNT})"
)
CATALOG_POST_BOUND_EXPRESSION = (
    rf"{CATALOG_ARTICLED_COUNT}\s+or\s+(?:more|fewer|less)"
)
CATALOG_CURRENT_ASIDE = (
    r"(?:\s*,\s*(?:as\s+of\s+(?:now|today|the\s+present)|"
    r"at\s+(?:present|the\s+moment|this\s+time)|"
    r"despite|notwithstanding|regardless\s+of)"
    r"(?:(?![,;.!?]).){0,100},)?"
)
CATALOG_RICH_EXPRESSION = (
    rf"(?:"
    rf"{CATALOG_POST_BOUND_EXPRESSION}|"
    rf"{CATALOG_RANGE_EXPRESSION}|"
    rf"{TOOL_COUNT_TOKEN}\s*(?:x|×|\*)\s*{TOOL_COUNT_TOKEN}|"
    rf"(?:twice|thrice)\s+{CATALOG_ARTICLED_COUNT}|"
    rf"{TOOL_COUNT_TOKEN}\s+(?:sets?|groups?|batches?)\s+of\s+{TOOL_COUNT_TOKEN}|"
    rf"{TOOL_COUNT_TOKEN}\s+(?:sets?|groups?|batches?)\s*,?\s+"
    rf"each\s+(?:with|containing|holding)\s+{TOOL_COUNT_TOKEN}|"
    rf"(?:an?\s+)?(?:sets?|groups?|batches?)\s+of\s+{TOOL_COUNT_TOKEN}|"
    rf"half\s+(?:a\s+)?dozen|"
    rf"{CATALOG_ARTICLED_COUNT}(?:\s+(?:and|plus)\s+"
    rf"{CATALOG_ARTICLED_COUNT})+|"
    rf"{CATALOG_ARTICLED_COUNT}"
    rf")"
)
CATALOG_RICH_COUNT_PHRASE = (
    rf"(?:(?:{CATALOG_RICH_QUALIFIER})\s+)?{CATALOG_RICH_EXPRESSION}"
)
CATALOG_RICH_COUNT_PATTERNS = (
    re.compile(
        rf"\b(?:(?:now|currently|today|presently|already)\s*,?\s+)?"
        rf"(?:the\s+)?(?:public|Stele)\s+catalog\b{CATALOG_META_SUFFIX}"
        rf"{CATALOG_CURRENT_ASIDE}"
        rf"\s+(?:(?:now|currently|today|presently|already)\s+)?(?:"
        rf"contains?|has|includes?|lists?|offers?|shows?|reports?|holds?|"
        rf"carries|features|comprises|is\s+home\s+to)\s+"
        rf"(?P<count_phrase>{CATALOG_RICH_COUNT_PHRASE})\s+(?:of\s+)?"
        rf"{CATALOG_ITEM_NOUN}\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?:the\s+)?(?:"
        rf"(?:public|Stele)\s+catalog(?:['’]s)?\s+"
        rf"(?:(?:current|live|published|available)\s+)?inventory|"
        rf"(?:(?:current|live|published|available)\s+)?inventory\s+"
        rf"(?:of|at|in|inside|within)\s+(?:the\s+)?(?:public|Stele)\s+catalog"
        rf")\b{CATALOG_META_SUFFIX}\s*"
        rf"(?:(?:now|currently|today|presently)\s+)?"
        rf"(?:is|equals?|totals?|numbers?|stands?\s+at|contains?|comprises|:)\s+"
        rf"(?P<count_phrase>{CATALOG_RICH_COUNT_PHRASE})\s+(?:of\s+)?"
        rf"{CATALOG_ITEM_NOUN}\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?:there\s+)?(?:(?:now|currently|today|presently)\s+)?"
        rf"(?:is|are|exist|exists)\s+"
        rf"(?P<count_phrase>{CATALOG_RICH_COUNT_PHRASE})\s+(?:of\s+)?"
        rf"{CATALOG_ITEM_NOUN}\b\s+(?:(?:now|currently|today|presently)\s+)?"
        rf"{CATALOG_LOCATION}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?P<count_phrase>{CATALOG_RICH_COUNT_PHRASE})\s+(?:of\s+)?"
        rf"{CATALOG_ITEM_NOUN}\b\s+"
        rf"(?:(?:now|currently|today|presently)\s+)?"
        rf"(?:is|are|exist|exists|remain|remains|sit|sits|reside|resides|"
        rf"can\s+be\s+found)\s+"
        rf"(?:(?:now|currently|today|presently|available|live|published)\s+)?"
        rf"{CATALOG_LOCATION}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b{CATALOG_LOCATION}\s*,?\s+"
        rf"(?:(?:now|currently|today|presently)\s+)?"
        rf"(?:there\s+)?(?:is|are|exist|exists|remain|remains|sit|sits|"
        rf"reside|resides)\s+"
        rf"(?P<count_phrase>{CATALOG_RICH_COUNT_PHRASE})\s+(?:of\s+)?"
        rf"{CATALOG_ITEM_NOUN}\b",
        re.IGNORECASE,
    ),
)

CATALOG_NAMED_INVENTORY_CLAIM = re.compile(
    rf"\b(?:the\s+)?(?:public|Stele)\s+catalog\b{CATALOG_META_SUFFIX}"
    rf"{CATALOG_CURRENT_ASIDE}\s+"
    rf"(?:(?:now|currently|today|presently|already)\s+)?"
    rf"(?:carries|contains?|features|has|holds?|includes?|lists?|offers?|"
    rf"reports?|shows?)\s+"
    rf"(?P<inventory>(?:(?![.!?;|]).){{1,280}})",
    re.IGNORECASE | re.DOTALL,
)
CATALOG_NAMED_ITEM_PHRASE = re.compile(
    r"\b(?:an?|one)\s+(?:[a-z0-9][a-z0-9'’/-]*\s+){0,8}"
    r"(?:entries|entry|listings?|services?)\b",
    re.IGNORECASE,
)
CATALOG_SHARED_NOUN_COORDINATION = re.compile(
    r"\b[a-z0-9][a-z0-9'’/-]*(?:\s+[a-z0-9][a-z0-9'’/-]*){0,5}\s+"
    r"(?:and|plus)\s+"
    r"[a-z0-9][a-z0-9'’/-]*(?:\s+[a-z0-9][a-z0-9'’/-]*){0,5}\s+"
    r"(?:entries|listings|services)\b",
    re.IGNORECASE,
)
CATALOG_NAMED_META_ITEM = re.compile(
    r"\b(?:documentation|example|fixture|hypothetical|mock|sample|schema|"
    r"simulation|test)\b",
    re.IGNORECASE,
)
CATALOG_ZERO_COMPATIBLE_NAMED_BOUND = re.compile(
    r"\b(?:at\s+most|fewer\s+than\s+(?:one|1)|less\s+than\s+(?:one|1)|"
    r"no\s+more\s+than\s+(?:zero|0)|up\s+to)\b",
    re.IGNORECASE,
)
CATALOG_COUNTED_INVENTORY_LEAD = re.compile(
    rf"^\s*{CATALOG_RICH_COUNT_PHRASE}\s+(?:of\s+)?{CATALOG_ITEM_NOUN}\b",
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

HOSTED_DYNAMIC_INVENTORY_ERROR = (
    "hosted Stele MCP presents a fixed tool inventory; "
    "authenticated tools/list is authoritative"
)

HOSTED_TOOL_INVENTORY_OVERCLAIMS = {
    "hosted Stele MCP presents an unconditional third capability": re.compile(
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

# Public copy must remain true while hosted provider-draft availability transitions.
# A fixed total is therefore stale even if it happens to match one deployment at
# publication time; authenticated tools/list is the only session-specific inventory
# authority.
HOSTED_FIXED_INVENTORY_CLAIM = re.compile(
    rf"\bHosted\s+(?:Stele\s+)?MCP\b(?:(?![.!?]).){{0,220}}?\b(?:"
    rf"(?:exposes?|has|offers?|provides?|includes?|lists?|reports?|shows?)\s+"
    rf"(?:(?:exactly|only|at\s+least|more\s+than|fewer\s+than|up\s+to|"
    rf"about|approximately)\s+)?(?:{TOOL_COUNT_TOKEN}|pairs?|couples?|trios?|dozens?)\s+"
    rf"(?:(?:[a-z][a-z0-9/-]*)(?:,\s*|\s+)){{0,6}}(?:tools?|endpoints?|capabilit(?:y|ies))|"
    rf"(?:tool|endpoint|capability)\s+count\s*(?:is|=|:)\s*"
    rf"(?:(?:exactly|only)\s+)?{TOOL_COUNT_TOKEN}"
    rf")\b",
    re.IGNORECASE | re.DOTALL,
)

HOSTED_ORDINAL_TOOL_ABSENCE_AFTER_SURFACE = re.compile(
    r"\b(?:"
    r"(?:has|offers?|provides?|exposes?|includes?)\s+no\s+"
    r"(?:additional\s+)?(?:second|third|fourth|fifth|sixth|seventh|eighth|"
    r"ninth|tenth)\s+(?:(?:status|OAuth[- ]protected|read[- ]only)\s+){0,3}"
    r"(?:tools?|endpoints?|capabilit(?:y|ies))|"
    r"lacks?\s+(?:(?:an?|the|its)\s+)?(?:additional\s+)?"
    r"(?:second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+"
    r"(?:(?:status|OAuth[- ]protected|read[- ]only)\s+){0,3}"
    r"(?:tools?|endpoints?|capabilit(?:y|ies))|"
    r"(?:does\s+not|doesn['’]t|cannot)\s+"
    r"(?:have|expose|offer|provide|include|list)\s+(?:(?:an?|the)\s+)?"
    r"(?:additional\s+)?(?:second|third|fourth|fifth|sixth|seventh|eighth|"
    r"ninth|tenth)\s+(?:(?:status|OAuth[- ]protected|read[- ]only)\s+){0,3}"
    r"(?:tools?|endpoints?|capabilit(?:y|ies))|"
    r"is\s+without\s+(?:(?:an?|the)\s+)?(?:additional\s+)?"
    r"(?:second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+"
    r"(?:(?:status|OAuth[- ]protected|read[- ]only)\s+){0,3}"
    r"(?:tools?|endpoints?|capabilit(?:y|ies))"
    r")\b",
    re.IGNORECASE,
)

HOSTED_REVERSE_TOOL_ABSENCE = re.compile(
    r"\bno\s+(?:(?:additional\s+)?(?:second|third|fourth|fifth|sixth|"
    r"seventh|eighth|ninth|tenth)\s+)?"
    r"(?:(?:status|OAuth[- ]protected|read[- ]only)\s+){0,3}"
    r"(?:tools?|endpoints?|capabilit(?:y|ies))\s+"
    r"(?:is|are|remain|exists?)\s+(?:(?:currently|now|today)\s+)?"
    r"(?:(?:available|exposed|offered|provided|listed|present)\s+)?"
    r"(?:in|on|at|through|from|for|by)\s+(?:the\s+)?Hosted\s+"
    r"(?:Stele\s+)?MCP\b",
    re.IGNORECASE,
)

MCP_NAMED_CAPABILITY_CLAIM = re.compile(
    r"\b(?:exposes?|has|includes?|lists?|offers?|provides?|supports?)\s+"
    r"(?P<inventory>(?:(?![.!?;|]).){1,280})",
    re.IGNORECASE | re.DOTALL,
)
NAMED_CAPABILITY_META_LEAD = re.compile(
    r"^\s*(?:(?:an?|the)\s+)?(?:documentation|example|fixture|mock|sample|"
    r"simulation|test)\b",
    re.IGNORECASE,
)
NAMED_CAPABILITY_DENIED_ITEM = re.compile(
    r"^\s*(?:neither|no|not|nothing|without|zero)\b", re.IGNORECASE
)
NAMED_CAPABILITY_MODIFIER_ITEM = re.compile(
    r"^\s*(?:(?:bounded|current|hosted|non[- ]economic|OAuth[- ]protected|"
    r"private|public|read[- ]only|released|wallet[- ]authenticated)\s*)+$",
    re.IGNORECASE,
)
NAMED_CAPABILITY_FINITE_CLAUSE = re.compile(
    r"\b(?:another|other|separate|unrelated)\s+"
    r"(?:API|application|service|system)\b|"
    r"\b(?:can|could|does|is|may|might|was|were|will|would)\b",
    re.IGNORECASE,
)

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
STATE_TIME_MODIFIER = (
    r"(?:(?:now|currently|today|already|presently|generally|broadly|widely|"
    r"publicly|fully)\s+)?"
)
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
CAPABILITY_TRANSITION_RELATION = (
    rf"(?:"
    rf"(?:(?:has|have)\s+)?(?:launch(?:es|ed)|start(?:s|ed)|"
    rf"open(?:s|ed)|activate(?:s|d)|ship(?:s|ped))|"
    rf"(?:go(?:es)?|went|(?:has|have)\s+gone)\s+live|"
    rf"(?:becomes?|became|(?:has|have)\s+become|turns?|turned)\s+"
    rf"{ENABLED_STATE}"
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
        r"works?\s+without|"
        r"(?:can|does)\s+(?!not\b)(?:proceed|run|work)\s+without"
        r")\s+(?:an?\s+)?(?:published\s+)?listing\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

BOOKING_DRAFT_PREREQUISITE_CONTRADICTIONS = {
    "booking-draft preparation claims no listing prerequisite": re.compile(
        r"(?:\b(?:hosted\s+(?:Stele\s+)?MCP\s+)?"
        r"(?:booking(?:-approval)?|approval)[- ]draft\s+preparation\b"
        r"(?:(?![.!?]).){0,120}?\bdoes\s+not\s+"
        r"(?:require|need|depend\s+on|rely\s+on)\s+(?:(?:an?|any)\s+)?"
        r"(?:published\s+)?listing\b|"
        r"\b(?:hosted\s+)?booking[- ]draft\s+preparation\b"
        r"(?:(?![.!?]).){0,100}?\b(?:requires?|needs?|uses?)\s+"
        r"(?:no|zero)\s+(?:published\s+)?listings?\b|"
        r"\b(?:hosted\s+)?booking[- ]draft\s+preparation\b"
        r"(?:(?![.!?]).){0,100}?\b(?:is|remains?)\s+(?:"
        r"listing[- ]free|independent\s+of\s+(?:an?\s+)?(?:published\s+)?listing"
        r")\b|"
        r"\b(?:an?\s+)?published\s+(?:service\s+)?listings?\s+"
        r"(?:is|are|remains?)\s+optional\s+for\s+"
        r"(?:hosted\s+)?booking[- ]draft\s+preparation\b|"
        r"\b(?:no|zero)\s+(?:published\s+)?listings?\s+"
        r"(?:is|are)\s+(?:needed|required|necessary)\s+for\s+"
        r"(?:hosted\s+)?booking[- ]draft\s+preparation\b|"
        r"\b(?:an?\s+)?(?:published\s+)?listing\s+"
        r"(?:is|remains?)\s+(?:not\s+(?:needed|required|necessary)|unnecessary)\s+"
        r"for\s+(?:hosted\s+)?booking[- ]draft\s+preparation\b|"
        r"\bbooking[- ]draft\s+preparation\s+works?\s+against\s+"
        r"unpublished\s+listings?\b)",
        re.IGNORECASE | re.DOTALL,
    ),
}

PROVIDER_DRAFT_BOUNDARY = {
    "provider-listing draft presented as public or executable": re.compile(
        r"(?:\b(?:private\s+|wallet-owned\s+){0,3}provider[- ]listing\s+drafts?\b"
        r"(?:(?![.!?]).){0,120}?\b(?:"
        r"(?:is|are|becomes?|remains?)\s+(?:now\s+)?"
        r"(?!not\b)(?:published|discoverable|transactable|on-chain)|"
        r"(?:can|does)\s+(?!not\b)(?:be\s+)?"
        r"(?:published|listed|submitted|broadcast|transacted)|"
        r"(?:is|are)\s+(?!not\b)(?:publishable|listable|submittable|executable)|"
        r"(?:gets?|becomes?)\s+(?!not\b)(?:published|listed)|"
        r"(?:can|does)\s+(?!not\b)(?:enter|reach|appear\s+in)\s+"
        r"(?:the\s+)?public\s+catalog|"
        r"(?:is|are|becomes?|remains?)\s+(?:now\s+)?visible\s+in\s+"
        r"(?:the\s+)?public\s+catalog"
        r")\b|"
        r"\b(?:private\s+|wallet-owned\s+){0,3}provider[- ]listing\s+drafts?\b"
        r"(?:(?![.!?,;]|\b(?:and|or|but|however|yet|while|whereas|though)\b).)"
        r"{0,60}?\b(?:publishes|publish|(?<!/)lists?|submits?|broadcasts?|transacts?)\b|"
        r"\b(?:publishes|lists|submits|broadcasts|transacts)\s+"
        r"(?:private\s+|wallet-owned\s+){0,3}provider[- ]listing\s+drafts?\b)",
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

HOSTED_PROVIDER_DRAFT_AUTHORITY = {
    "hosted MCP claims provider-listing draft authority": re.compile(
        r"\b(?:"
        r"(?:can|does|will|may|now|currently)\s+(?!not\b)"
        r"(?:access|manage|list|read|fetch|retrieve|load|view|inspect|"
        r"query|update|edit|delete|publish|write)|"
        r"(?<!not\s)(?:accesses|manages|lists|reads|fetches|retrieves|"
        r"loads|views|inspects|queries|updates|edits|deletes|publishes|writes)|"
        r"(?:is|remains?)\s+(?!not\b)(?:reading|fetching|retrieving|loading|"
        r"viewing|inspecting|querying|updating|editing|deleting|publishing|writing)|"
        r"(?:has|have)\s+(?!not\b)(?:read|fetched|retrieved|loaded|viewed|"
        r"inspected|queried|updated|edited|deleted|published|written)"
        r")\s+(?:an?\s+|the\s+|existing\s+|private\s+|wallet-owned\s+){0,5}"
        r"provider[- ]listing\s+drafts?\b|"
        r"\b(?:provides?|offers?|supports?|enables?|exposes?|includes?|has)\s+"
        r"(?!no\b|not\b)(?:(?:the|an?)\s+)?(?:existing\s+)?"
        r"(?:private\s+|wallet-owned\s+){0,3}provider[- ]listing\s+drafts?\s+"
        r"(?:access|management|listing|reading|retrieval|loading|viewing|"
        r"inspection|querying|updates?|editing|deletion|publication|writing)\b|"
        r"\b(?:provides?|offers?|supports?|enables?|exposes?|includes?|has)\s+"
        r"(?!no\b|not\b)(?:(?:the|an?)\s+)?"
        r"(?:access|management|listing|reading|retrieval|loading|viewing|"
        r"inspection|querying|updates?|editing|deletion|publication|writing)\s+"
        r"(?:of|for|to)\s+(?:(?:the|an?)\s+)?(?:existing\s+)?"
        r"(?:private\s+|wallet-owned\s+){0,3}provider[- ]listing\s+drafts?\b|"
        r"\b(?:allows?|enables?|lets?|permits?|supports?|offers?)\s+"
        r"(?:(?:clients?|users?|providers?|agents?)\s+)?(?:to\s+)?"
        r"(?:access|accessing|manage|managing|list|listing|read|reading|fetch|"
        r"fetching|retrieve|retrieving|load|loading|view|viewing|inspect|inspecting|"
        r"query|querying|update|updating|edit|editing|delete|deleting|publish|"
        r"publishing|write|writing)\s+(?:(?:the|an?)\s+)?"
        r"(?:existing\s+)?(?:private\s+|wallet-owned\s+){0,3}"
        r"provider[- ]listing\s+drafts?\b|"
        r"\b(?:provides?|offers?|supports?|enables?|exposes?|includes?|has)\s+"
        r"(?:(?:the|an?)\s+)?(?:tool|endpoint|capability|facility|support)\s+for\s+"
        r"(?:accessing|managing|listing|reading|fetching|retrieving|loading|viewing|"
        r"inspecting|querying|updating|editing|deleting|publishing|writing)\s+"
        r"(?:(?:the|an?)\s+)?(?:existing\s+)?(?:private\s+|wallet-owned\s+){0,3}"
        r"provider[- ]listing\s+drafts?\b|"
        r"\b(?:makes?|renders?)\s+(?:(?:the|an?)\s+)?(?:existing\s+)?"
        r"(?:private\s+|wallet-owned\s+){0,3}provider[- ]listing\s+drafts?\s+"
        r"(?:access|management|listing|reading|retrieval|loading|viewing|"
        r"inspection|querying|updates?|editing|deletion|publication|writing)\s+"
        r"available\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

HOSTED_PROVIDER_DRAFT_CONDITIONAL_ERROR = (
    "hosted provider-draft tool availability is not tools/list-conditional"
)
HOSTED_PROVIDER_DRAFT_LOOKALIKE_ERROR = (
    "hosted MCP exposes a noncanonical provider-draft tool name"
)
CANONICAL_PROVIDER_DRAFT_TOOL_NAME = "stele_create_provider_listing_draft"
CANONICAL_PROVIDER_DRAFT_TOOL = r"\bstele_create_provider_listing_draft\b"
# Gate acceptance is deliberately case-sensitive even inside regexes compiled
# with ``re.IGNORECASE``. MCP tool identifiers are exact protocol names, so a
# display-normalized or lookalike spelling cannot establish availability.
CANONICAL_PROVIDER_DRAFT_TOOL_GATE = (
    r"(?-i:\bstele_create_provider_listing_draft\b)"
)
PROVIDER_DRAFT_TOOL_IDENTIFIER = re.compile(
    r"\bstele_(?=[a-z0-9_]*(?:provider|listing))"
    r"(?=[a-z0-9_]*draft)[a-z0-9_]+\b",
    re.IGNORECASE,
)
AUTHENTICATED_TOOLS_LIST = r"(?:authenticated\s+)?`?tools/list`?"
PROVIDER_DRAFT_CREATE_NOMINAL = (
    r"(?:"
    r"(?:provider[- ]listing|provider)[- ]draft\s+"
    r"(?:creation|preparation|authoring|generation|production)|"
    r"(?:creation|preparation|authoring|generation|production)\s+of\s+"
    r"(?:private\s+|wallet-owned\s+|unpublished\s+|new\s+){0,4}"
    r"(?:provider[- ]listing|provider)[- ]drafts?"
    r")"
)

HOSTED_PROVIDER_DRAFT_CREATE_CAPABILITY = re.compile(
    rf"\b(?:"
    rf"(?:provides?|offers?|supports?|enables?|exposes?|includes?|has|allows?|permits?)\s+"
    rf"(?!no\b|not\b)(?:(?:the|an?)\s+)?"
    rf"(?:bounded\s+|conditional\s+|gated\s+){{0,2}}"
    rf"{PROVIDER_DRAFT_CREATE_NOMINAL}|"
    rf"(?:supports?|enables?|allows?|lets?|permits?|offers?)\s+"
    rf"(?:(?:clients?|users?|providers?|agents?)\s+)?(?:to\s+)?"
    rf"(?:create|prepare|author|generate|produce|creating|preparing|authoring|"
    rf"generating|producing)\s+"
    rf"(?:private\s+|wallet-owned\s+|unpublished\s+|new\s+|an?\s+|the\s+){{0,5}}"
    rf"(?:provider[- ]listing|provider)[- ]drafts?\b"
    rf"|(?:provides?|offers?|supports?|enables?|exposes?|includes?|has)\s+"
    rf"(?:(?:the|an?)\s+)?(?:tool|endpoint|capability|facility|support)\s+for\s+"
    rf"(?:creating|preparing|authoring|generating|producing)\s+"
    rf"(?:private\s+|wallet-owned\s+|unpublished\s+|new\s+){{0,4}}"
    rf"(?:provider[- ]listing|provider)[- ]drafts?\b"
    rf"|(?:provides?|offers?|has)\s+(?:(?:the|an?)\s+)?"
    rf"(?:ability|authorization|capability|facility|permission)\s+to\s+"
    rf"(?:create|prepare|author|generate|produce)\s+"
    rf"(?:private\s+|wallet-owned\s+|unpublished\s+|new\s+){{0,4}}"
    rf"(?:provider[- ]listing|provider)[- ]drafts?\b"
    rf"|(?:makes?|renders?)\s+{PROVIDER_DRAFT_CREATE_NOMINAL}\s+available\b"
    rf"|(?:"
    rf"(?:can|does|may|could|will|now|currently)\s+(?!not\b)"
    rf"(?:create|prepare|author|generate|produce)|"
    rf"(?:is|remains?)\s+(?!not\b)(?:allowed|authorized|permitted|able)\s+to\s+"
    rf"(?:create|prepare|author|generate|produce)|"
    rf"(?<!not\s)(?<!never\s)(?:creates|prepares|authors|generates|produces)"
    rf")\s+(?:private\s+|wallet-owned\s+|unpublished\s+|new\s+|an?\s+|the\s+){{0,6}}"
    rf"(?:provider[- ]listing|provider)[- ]drafts?\b"
    rf")",
    re.IGNORECASE | re.DOTALL,
)

HOSTED_PROVIDER_DRAFT_REVERSE_CREATE = re.compile(
    rf"\b(?:"
    rf"{PROVIDER_DRAFT_CREATE_NOMINAL}\s+"
    rf"(?:is|remains?)\s+(?:(?:now|currently|presently)\s+)?"
    rf"(?:available|enabled|supported|provided|offered|exposed|included|possible)|"
    rf"(?:private\s+|wallet-owned\s+|unpublished\s+|new\s+|an?\s+|the\s+){{0,5}}"
    rf"(?:provider[- ]listing|provider)[- ]drafts?\s+"
    rf"(?:can|may)\s+be\s+(?:created|prepared|authored|generated|produced)|"
    rf"(?:private\s+|wallet-owned\s+|unpublished\s+|new\s+|an?\s+|the\s+){{0,5}}"
    rf"(?:provider[- ]listing|provider)[- ]drafts?\s+(?:is|are|remains?)\s+"
    rf"(?:created|prepared|authored|generated|produced)|"
    rf"(?:private\s+|wallet-owned\s+|unpublished\s+|new\s+|an?\s+|the\s+){{0,5}}"
    rf"(?:provider[- ]listing|provider)[- ]drafts?\s+(?:is|are|remains?)\s+"
    rf"(?:allowed|authorized|permitted)\s+to\s+be\s+"
    rf"(?:created|prepared|authored|generated|produced)|"
    rf"(?:private\s+|wallet-owned\s+|unpublished\s+|new\s+|an?\s+|the\s+){{0,5}}"
    rf"(?:provider[- ]listing|provider)[- ]drafts?\s+(?:is|are|remains?)\s+"
    rf"(?:creatable|preparable|authorable)"
    rf")\s+(?:at|by|from|in|on|through|via|with)\s+(?:the\s+)?"
    rf"Hosted\s+(?:Stele\s+)?MCP\b|"
    rf"\b(?:through|via)\s+(?:the\s+)?Hosted\s+(?:Stele\s+)?MCP\s*,?\s*"
    rf"(?:clients?|users?|providers?|agents?)\s+(?:can|may)\s+"
    rf"(?:create|prepare|author|generate|produce)\s+"
    rf"(?:private\s+|wallet-owned\s+|unpublished\s+|new\s+|an?\s+|the\s+){{0,5}}"
    rf"(?:provider[- ]listing|provider)[- ]drafts?\b|"
    rf"\b(?:clients?|users?|providers?|agents?)\s+(?:have|hold)\s+"
    rf"(?:(?:the|an?)\s+)?(?:authorization|permission)\s+to\s+"
    rf"(?:create|prepare|author|generate|produce)\s+"
    rf"(?:private\s+|wallet-owned\s+|unpublished\s+|new\s+|an?\s+|the\s+){{0,5}}"
    rf"(?:provider[- ]listing|provider)[- ]drafts?\s+"
    rf"(?:at|by|from|in|on|through|via|with)\s+(?:the\s+)?"
    rf"Hosted\s+(?:Stele\s+)?MCP\b",
    re.IGNORECASE | re.DOTALL,
)

HOSTED_PROVIDER_DRAFT_REVERSE_AUTHORITY = re.compile(
    r"\b(?:"
    r"(?:(?:existing\s+)?(?:private\s+|wallet-owned\s+){0,3}"
    r"provider[- ]listing\s+drafts?\s+(?:access|management|listing|reading|"
    r"retrieval|loading|viewing|inspection|querying|updates?|editing|deletion|"
    r"publication|writing)|"
    r"(?:access|management|listing|reading|retrieval|loading|viewing|inspection|"
    r"querying|updates?|editing|deletion|publication|writing)\s+(?:of|for|to)\s+"
    r"(?:(?:the|an?)\s+)?(?:existing\s+)?(?:private\s+|wallet-owned\s+){0,3}"
    r"provider[- ]listing\s+drafts?)\s+(?:is|remains?)\s+"
    r"(?:(?:now|currently|presently)\s+)?(?:available|enabled|supported|provided|"
    r"offered|exposed|included)|"
    r"(?:existing\s+)?(?:private\s+|wallet-owned\s+){0,3}"
    r"provider[- ]listing\s+drafts?\s+(?:can|may)\s+be\s+"
    r"(?:accessed|managed|listed|read|fetched|retrieved|loaded|viewed|inspected|"
    r"queried|updated|edited|deleted|published|written)|"
    r"(?:existing\s+)?(?:private\s+|wallet-owned\s+){0,3}"
    r"provider[- ]listing\s+drafts?\s+(?:is|are|remains?)\s+"
    r"(?:accessible|manageable|listable|readable|fetchable|retrievable|viewable|"
    r"inspectable|queryable|updatable|editable|deletable|publishable|writable)"
    r")\s+(?:at|by|from|in|on|through|via|with)\s+(?:the\s+)?"
    r"Hosted\s+(?:Stele\s+)?MCP\b|"
    r"\b(?:through|via)\s+(?:the\s+)?Hosted\s+(?:Stele\s+)?MCP\s*,?\s*"
    r"(?:clients?|users?|providers?|agents?)\s+(?:can|may)\s+"
    r"(?:access|manage|list|read|fetch|retrieve|load|view|inspect|query|update|"
    r"edit|delete|publish|write)\s+(?:(?:the|an?)\s+)?(?:existing\s+)?"
    r"(?:private\s+|wallet-owned\s+){0,3}provider[- ]listing\s+drafts?\b",
    re.IGNORECASE | re.DOTALL,
)

HOSTED_PROVIDER_DRAFT_NAMED_TOOL_CLAIM = re.compile(
    r"\b(?:exposes?|has|offers?|provides?|includes?|lists?|supports?|enables?)\s+"
    r"(?:the\s+)?`?(?P<name>stele_"
    r"(?=[a-z0-9_]*(?:provider|listing))"
    r"(?=[a-z0-9_]*draft)[a-z0-9_]+)\b`?",
    re.IGNORECASE,
)

HOSTED_PROVIDER_DRAFT_NAMED_TOOL_REVERSE = re.compile(
    r"\b`?(?P<name>stele_(?=[a-z0-9_]*(?:provider|listing))"
    r"(?=[a-z0-9_]*draft)[a-z0-9_]+)\b`?"
    r"(?:(?![.!?;]).){0,120}?\b(?:"
    r"(?:is|remains?)\s+(?:(?:now|currently|still)\s+)?"
    r"(?:available|enabled|exposed|listed|live|present|callable|invokable|usable)|"
    r"(?:can|may)\s+be\s+(?:invoked|called|used|run|executed|accessed)"
    r")\s+(?:at|by|from|in|on|through|via|with)\s+"
    r"(?:the\s+)?Hosted\s+(?:Stele\s+)?MCP\b",
    re.IGNORECASE | re.DOTALL,
)

PROVIDER_DRAFT_NAMED_TOOL_AVAILABILITY = re.compile(
    rf"(?:"
    rf"{CANONICAL_PROVIDER_DRAFT_TOOL}(?:(?![.!?;]).){{0,160}}?\b(?:"
    rf"exists?|(?:is|remains?)\s+(?:(?:now|currently|still|always|generally)\s+)?"
    rf"(?:available|enabled|exposed|listed|live|present|callable|invokable|usable)|"
    rf"(?:can|may)\s+(?:always\s+)?be\s+"
    rf"(?:invoked|called|used|run|executed|accessed))\b|"
    rf"\b(?:clients?|users?|agents?|callers?|integrations?)\b"
    rf"(?:(?![.!?;]).){{0,80}}?\b(?:can|may|are\s+(?:able|allowed|permitted)\s+to)\s+"
    rf"(?:invoke|call|use|run|execute|access)\s+(?:the\s+)?"
    rf"{CANONICAL_PROVIDER_DRAFT_TOOL}"
    rf"|\b(?:invocation|use|execution|access)\s+of\s+(?:the\s+)?"
    rf"{CANONICAL_PROVIDER_DRAFT_TOOL}(?:(?![.!?;]).){{0,100}}?\b"
    rf"(?:is|remains?)\s+(?:(?:now|currently)\s+)?"
    rf"(?:allowed|available|enabled|permitted|supported)\b"
    rf")",
    re.IGNORECASE | re.DOTALL,
)

PROVIDER_DRAFT_NAMED_TOOL_INVOCATION = re.compile(
    r"\b(?:clients?|users?|agents?|callers?|integrations?)\b"
    r"(?:(?![.!?;]).){0,80}?\b(?:can|may|are\s+(?:able|allowed|permitted)\s+to)\s+"
    r"(?:invoke|call|use|run|execute|access)\s+(?:the\s+)?`?"
    r"(?P<name>stele_(?=[a-z0-9_]*(?:provider|listing))"
    r"(?=[a-z0-9_]*draft)[a-z0-9_]+)\b`?"
    r"(?:(?![.!?;]).){0,100}?\b(?:Hosted\s+(?:Stele\s+)?MCP\b)?",
    re.IGNORECASE | re.DOTALL,
)

PROVIDER_DRAFT_TOOL_LIST_BYPASS = re.compile(
    rf"(?:"
    rf"\b(?:even\s+(?:if|when)|whether\s+or\s+not|regardless\s+of)\b"
    rf"(?:(?![.!?;]).){{0,180}}?\b(?:absent|missing|not\s+(?:listed|present)|"
    rf"does\s+not\s+appear)\b(?:(?![.!?;]).){{0,100}}?\b{AUTHENTICATED_TOOLS_LIST}\b|"
    rf"\bwithout\b(?:(?![.!?;]).){{0,120}}?\b(?:seeing|finding|receiving|having)\b"
    rf"(?:(?![.!?;]).){{0,100}}?\b{AUTHENTICATED_TOOLS_LIST}\b|"
    rf"\b(?:absent|missing|not\s+(?:listed|present)|does\s+not\s+appear)\b"
    rf"(?:(?![.!?;]).){{0,100}}?\b(?:in|from|on)\s+{AUTHENTICATED_TOOLS_LIST}\b"
    rf")",
    re.IGNORECASE | re.DOTALL,
)

PROVIDER_DRAFT_TOOL_POSITIVE_LIST_GATE = re.compile(
    rf"(?=[^.!?;]{{0,320}}{CANONICAL_PROVIDER_DRAFT_TOOL_GATE})"
    rf"(?=[^.!?;]{{0,320}}{AUTHENTICATED_TOOLS_LIST})"
    rf"(?=[^.!?;]{{0,320}}\b(?:if|when|whenever|only\s+when|provided\s+that|"
    rf"as\s+long\s+as|so\s+long\s+as|once|after)\b)"
    rf"(?=[^.!?;]{{0,320}}\b(?:appears?|present|listed|returned|included|shown|"
    rf"contains?|includes?|lists?|returns?|shows?)\b)"
    rf"[^.!?;]{{1,340}}",
    re.IGNORECASE,
)
PROVIDER_DRAFT_TOOL_REQUIRED_PRESENCE_GATE = re.compile(
    rf"(?:"
    rf"\b(?:the\s+)?presence\s+of\s+{CANONICAL_PROVIDER_DRAFT_TOOL_GATE}\s+"
    rf"(?:in|on)\s+{AUTHENTICATED_TOOLS_LIST}\s+(?:is|remains?)\s+required\s+before|"
    rf"\b{AUTHENTICATED_TOOLS_LIST}\s+(?:must|required\s+to)\s+"
    rf"(?:contain|include|list|return|show)\s+{CANONICAL_PROVIDER_DRAFT_TOOL_GATE}\s+before"
    rf")",
    re.IGNORECASE | re.DOTALL,
)
PROVIDER_DRAFT_TOOL_UNLESS_ABSENT_GATE = re.compile(
    rf"(?:"
    rf"{CANONICAL_PROVIDER_DRAFT_TOOL_GATE}(?:(?![.!?;]).){{0,180}}?\bunless\b|"
    rf"\bunless\b(?:(?![.!?;]).){{0,180}}?{CANONICAL_PROVIDER_DRAFT_TOOL_GATE}"
    rf")(?:(?![.!?;]).){{0,200}}?\b(?:absent|missing|"
    rf"not\s+(?:listed|present)|does\s+not\s+appear)\b"
    rf"(?:(?![.!?;]).){{0,100}}?\b(?:in|from|on)\s+{AUTHENTICATED_TOOLS_LIST}\b",
    re.IGNORECASE | re.DOTALL,
)
PROVIDER_DRAFT_TOOL_WHEN_LISTED_GATE = re.compile(
    rf"\bwhen\s+listed\b(?:(?![.!?;]).){{0,180}}?"
    rf"{CANONICAL_PROVIDER_DRAFT_TOOL_GATE}",
    re.IGNORECASE | re.DOTALL,
)

EXACT_PROVIDER_DRAFT_TOOL_CREATE = re.compile(
    rf"(?:"
    rf"{CANONICAL_PROVIDER_DRAFT_TOOL}(?:(?![.!?;]).){{0,120}}?\b"
    rf"(?:creates?|prepares?|authors?|generates?|produces?)\s+"
    rf"(?:private\s+|wallet-owned\s+|unpublished\s+|new\s+|exactly\s+one\s+|"
    rf"an?\s+|the\s+){{0,7}}(?:provider[- ]listing|provider)[- ]drafts?\b|"
    rf"(?:private\s+|wallet-owned\s+|unpublished\s+|new\s+|an?\s+|the\s+){{0,5}}"
    rf"(?:provider[- ]listing|provider)[- ]drafts?\s+(?:is|are)\s+"
    rf"(?:created|prepared|authored|generated|produced)\s+"
    rf"(?:by|through|via|with)\s+(?:the\s+)?{CANONICAL_PROVIDER_DRAFT_TOOL}"
    rf")",
    re.IGNORECASE | re.DOTALL,
)

EXACT_PROVIDER_DRAFT_TOOL_AUTHORITY = re.compile(
    rf"(?:"
    rf"{CANONICAL_PROVIDER_DRAFT_TOOL}(?:(?![.!?;]).){{0,120}}?\b"
    rf"(?:access(?:es|ed|ing)?|manag(?:e|es|ed|ing)|list(?:s|ed|ing)?|"
    rf"read(?:s|ing)?|fetch(?:es|ed|ing)?|retriev(?:e|es|ed|ing)|"
    rf"load(?:s|ed|ing)?|view(?:s|ed|ing)?|inspect(?:s|ed|ing)?|"
    rf"quer(?:y|ies|ied|ying)|updat(?:e|es|ed|ing)|edit(?:s|ed|ing)?|"
    rf"delet(?:e|es|ed|ing)|publish(?:es|ed|ing)?|writ(?:e|es|ten|ing))\s+"
    rf"(?:(?:the|an?)\s+)?(?:existing\s+)?(?:private\s+|wallet-owned\s+){{0,3}}"
    rf"provider[- ]listing\s+drafts?\b|"
    rf"(?:existing\s+)?(?:private\s+|wallet-owned\s+){{0,3}}"
    rf"provider[- ]listing\s+drafts?\s+(?:can|may)\s+be\s+"
    rf"(?:accessed|managed|listed|read|fetched|retrieved|loaded|viewed|inspected|"
    rf"queried|updated|edited|deleted|published|written)\s+"
    rf"(?:by|through|via|with)\s+(?:the\s+)?{CANONICAL_PROVIDER_DRAFT_TOOL}"
    rf"|{CANONICAL_PROVIDER_DRAFT_TOOL}(?:(?![.!?;]).){{0,120}}?\b"
    rf"(?:provides?|offers?|supports?|enables?|exposes?|includes?|has|allows?|permits?)\s+"
    rf"(?:(?:the|an?)\s+)?(?:existing\s+)?"
    rf"(?:private\s+|wallet-owned\s+){{0,3}}provider[- ]listing\s+drafts?\s+"
    rf"(?:access|management|listing|reading|retrieval|loading|viewing|inspection|"
    rf"querying|updates?|editing|deletion|publication|writing)\b"
    rf"|{CANONICAL_PROVIDER_DRAFT_TOOL}(?:(?![.!?;]).){{0,120}}?\b"
    rf"(?:provides?|offers?|supports?|enables?|exposes?|includes?|has|allows?|permits?)\s+"
    rf"(?:(?:the|an?)\s+)?(?:access|management|listing|reading|retrieval|loading|"
    rf"viewing|inspection|querying|updates?|editing|deletion|publication|writing)\s+"
    rf"(?:of|for|to)\s+(?:(?:the|an?)\s+)?(?:existing\s+)?"
    rf"(?:private\s+|wallet-owned\s+){{0,3}}provider[- ]listing\s+drafts?\b"
    rf"|(?:existing\s+)?(?:private\s+|wallet-owned\s+){{0,3}}"
    rf"provider[- ]listing\s+drafts?\s+(?:access|management|listing|reading|"
    rf"retrieval|loading|viewing|inspection|querying|updates?|editing|deletion|"
    rf"publication|writing)\s+(?:is|remains?)\s+"
    rf"(?:(?:now|currently)\s+)?(?:available|enabled|supported|provided|offered|"
    rf"exposed|included)\s+(?:by|through|via|with)\s+(?:the\s+)?"
    rf"{CANONICAL_PROVIDER_DRAFT_TOOL}"
    rf")",
    re.IGNORECASE | re.DOTALL,
)

EXACT_PROVIDER_DRAFT_TOOL_ANAPHOR = re.compile(
    rf"{CANONICAL_PROVIDER_DRAFT_TOOL}(?:(?![.!?;]).){{0,180}}?[.!?;]\s*"
    rf"(?P<claim>(?:when\s+listed\s*,\s*)?"
    rf"(?:it|this\s+tool|that\s+tool|the\s+tool)\s+"
    rf"(?:(?:can|does|may|now|currently)\s+)?(?P<action>"
    rf"creates?|prepares?|authors?|generates?|produces?|"
    rf"access(?:es)?|manages?|lists?|reads?|fetches?|retrieves?|loads?|views?|"
    rf"inspects?|queries|updates?|edits?|deletes?|publishes?|writes?|"
    rf"signs?|broadcasts?|submits?|settles?|executes?|authorizes?|approves?)\b"
    rf"(?:(?![.!?;]).){{0,140}}?\b(?P<target>"
    rf"(?:private\s+|wallet-owned\s+|unpublished\s+|new\s+|existing\s+|an?\s+|"
    rf"the\s+){{0,6}}(?:provider[- ]listing|provider)[- ]drafts?|"
    rf"transactions?|payments?|settlements?|transfers?|funds?|wallet\s+payloads?"
    rf")\b)",
    re.IGNORECASE | re.DOTALL,
)

HOSTED_PROVIDER_DRAFT_UNCONDITIONAL = {
    "hosted MCP claims provider-listing draft authority": re.compile(
        r"\bHosted\s+(?:Stele\s+)?MCP\b(?:(?![.!?]).){0,180}?\b(?:"
        r"(?:can|does|will|may|now|currently)\s+(?!not\b)(?:create|prepare)|"
        r"(?<!not\s)(?:creates|prepares)"
        r")\s+(?:private\s+|wallet-owned\s+|unpublished\s+){0,4}"
        r"provider[- ]listing\s+drafts?\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "hosted provider-draft tool availability is not tools/list-conditional": re.compile(
        r"(?:\bHosted\s+(?:Stele\s+)?MCP\b(?:(?![.!?]).){0,180}?\b"
        r"(?:exposes?|has|offers?|provides?|includes?|lists?)\s+"
        r"(?:the\s+)?`?stele_create_provider_listing_draft`?\b|"
        r"\b`?stele_create_provider_listing_draft`?\b(?:(?![.!?]).){0,120}?\b"
        r"(?:is|remains?)\s+(?!not\b)(?:available|enabled|exposed|listed|live|present)\b)",
        re.IGNORECASE | re.DOTALL,
    ),
}

PROVIDER_DRAFT_CREATE_AFFIRMATIVE_CONTRADICTIONS = {
    "provider-draft creation claims a non-unit result": re.compile(
        r"\b(?:`?stele_create_provider_listing_draft`?(?:\s+tool|\s+operation)?|"
        r"(?:each\s+)?successful\s+(?:provider[- ]draft\s+)?operation)\b"
        r"(?:(?![.!?]).){0,180}?\b(?:creates?|produces?|writes?)\s+"
        r"(?:zero|two|three|four|multiple|several|many|more\s+than\s+one|"
        r"at\s+least\s+two|one\s+or\s+more)\s+(?:new\s+)?"
        r"(?:private\s+|wallet-owned\s+|unpublished\s+){0,4}"
        r"provider[- ]listing\s+drafts?\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "idempotent provider-draft replay claims duplicate creation": re.compile(
        r"\bidempotent\s+(?:replay|retry)\b(?:(?![.!?]).){0,160}?\b"
        r"(?:creates?|produces?|writes?|returns?)\s+(?:(?:an?|the)\s+)?"
        r"(?:new|another|additional|different|second)\s+"
        r"(?:private\s+|wallet-owned\s+|unpublished\s+){0,4}"
        r"(?:provider[- ]listing\s+)?draft\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

PROVIDER_DRAFT_CREATE_SEMANTICS = {
    "idempotent provider-draft replay denies same-draft return": re.compile(
        r"\bidempotent\s+(?:replay|retry)\b(?:(?![.!?]).){0,160}?\b"
        r"(?:does\s+not|doesn['’]t|cannot|never|fails?\s+to)\s+return\s+"
        r"(?:the\s+)?same\s+(?:provider[- ]listing\s+)?draft\b",
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
    r"\[(?P<label>[^\]\n]+)\]\[(?P<reference>[^\]\n]*)\]",
    re.IGNORECASE,
)
MARKDOWN_SHORTCUT_REFERENCE_LINK = re.compile(
    r"(?<![!\[])\[(?P<label>[^\]]+)\](?!\s*(?:[\[(]|:))",
    re.IGNORECASE | re.DOTALL,
)
MARKDOWN_REFERENCE_DEFINITION = re.compile(
    r"(?m)^\s*\[(?P<reference>[^\]\n]+)\]:\s*<?(?P<destination>\S+?)>?"
    r"(?:\s+['\"(][^\n]*['\")])?\s*$",
)
HTML_ANCHOR_LINK = re.compile(
    r"<a\b(?:(?!>).)*?\s+href\s*=\s*(?:"
    r"(?P<quote>['\"])(?P<quoted_destination>.*?)(?P=quote)|"
    r"(?P<bare_destination>[^\s>]+))(?:(?!>).)*>"
    r"(?P<label>.*?)</a\s*>",
    re.IGNORECASE | re.DOTALL,
)
HTML_TAG = re.compile(r"<[^>]*>", re.DOTALL)
HTML_CLOSING_TAG = re.compile(r"</[^>]*>", re.DOTALL)
HTML_HREF_ATTRIBUTE = re.compile(r"(?<![-\w])href\s*=", re.IGNORECASE)
HTML_HREF_DESTINATION_PREFIX = re.compile(
    r"<a\b(?:(?!>).){0,300}?\bhref\s*=\s*['\"]?\s*$",
    re.IGNORECASE | re.DOTALL,
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
STUDIO_DRAFT_ACTION_LABEL = re.compile(
    r"\b(?:access|create|edit|enter|launch|manage|open|prepare|preview|remove|"
    r"revise|start|update|delete|use|visit)\w*\b"
    r"(?:(?![.!?;]).){0,100}?\b"
    r"(?:(?:an?|the|their|his|her|its|our|this|that|your)\s+)?"
    r"(?:private\s+|wallet[- ]owned\s+){0,2}"
    r"provider(?:[- ]listing)?\s+drafts?\b",
    re.IGNORECASE | re.DOTALL,
)
STUDIO_CONTEXTUAL_DRAFT_ACTION_LABEL = re.compile(
    r"\b(?:create|edit|manage|open|prepare|preview|remove|revise|update|delete)\w*\b"
    r"(?:(?![.!?;]).){0,100}?\b"
    r"(?:(?:private|wallet[- ]owned)\s+)?"
    r"(?:an?|the|their|his|her|its|our|this|that|your)\s+drafts?\b",
    re.IGNORECASE | re.DOTALL,
)
STUDIO_PROVIDER_ACTOR_CONTEXT = re.compile(
    r"(?:"
    r"\bProvider\s+Studio\b(?:(?![.!?;]).){0,120}?\bproviders?\b|"
    r"\bproviders?\b(?:(?![.!?;]).){0,120}?\bProvider\s+Studio\b"
    r")",
    re.IGNORECASE | re.DOTALL,
)
STUDIO_GENERIC_PRODUCT_ACTION_LABEL = re.compile(
    r"^\s*(?:access|enter|launch|open|use|visit)\s+(?:the\s+)?"
    r"(?:Provider\s+)?Studio\s*$",
    re.IGNORECASE,
)
STUDIO_CONTEXTUAL_PRODUCT_ACTION_LABEL = re.compile(
    r"^\s*(?:access|enter|go\s+to|launch|open|start|use|visit)\s+"
    r"(?:(?:an?|the|this|that|their|your)\s+)?"
    r"(?:(?:listing|provider|provider[- ]listing)?\s+drafts?|editor|portal|"
    r"workspace|it|here)\s*$",
    re.IGNORECASE,
)
STUDIO_DISTINCT_PRODUCT_ACTOR = re.compile(
    r"\b(?:API|application|client|server|system|"
    r"(?:art|audio|dance|design|film|music|photography|pottery|recording|sound|"
    r"yoga)\s+studio|"
    r"(?:account|buyer|client|customer|service)\s+portal|"
    r"customer(?:[- ]account|[- ]service)?\s+portal)\b",
    re.IGNORECASE,
)
STUDIO_LINK_DENIAL_PREFIX = re.compile(
    r"(?:"
    r"\b(?:avoid|do\s+not|don['’]t|must\s+not|never|should\s+not)\s+"
    r"(?:(?:follow|open|use|visit)\s+)?(?:the\s+)?|"
    r"\b(?:cannot|can['’]t|does\s+not|doesn['’]t|never)\s+"
    r"(?:allow|enable|let|permit|support)\w*\s+"
    r"(?:(?:customers?|providers?|users?)\s+)?(?:to\s+)?|"
    r"\b(?:blocks?|forbids?|prevents?|refuses?)\s+"
    r"(?:(?:customers?|providers?|users?)\s+)?(?:from\s+|to\s+)?|"
    r"\b(?:is|are|was|were)\s+not\s+(?:(?:currently|now)\s+)?"
    r"(?:(?:available|hosted|located)\s+)?(?:at|on|through|via)\s+|"
    r"\b(?:deprecated|invalid|obsolete|retired|unsafe)\s+"
    r")$",
    re.IGNORECASE,
)
STUDIO_CURRENT_REACTIVATION = re.compile(
    r"(?:"
    r"\b(?:and|but|however|then|yet)\s*,?\s+"
    r"|[.!?;:]\s*(?:(?:however|nevertheless|nonetheless|still|yet)\s*,?\s*)?"
    r"|"
    r"[,—–-]\s*(?:(?:archived|deprecated|historical|legacy|prototype|retired)"
    r"(?:\s+in\s+(?:19|20)\d{2})?\s*,\s*)?"
    r")"
    r"(?:(?:again|currently|now|presently|today)\s*,?\s*)?"
    r"(?:(?:Provider\s+Studio|it|this\s+(?:product|Studio))\s+)?"
    r"(?:"
    r"(?:is|remains?)\s+(?:(?:again|currently|now|presently|today)\s+)?"
    r"(?:active|available|current|live|operational|released)|"
    r"has\s+(?:(?:again|currently|now|since)\s+)?"
    r"(?:reactivated|relaunched|reopened|returned)|"
    r"(?:reactivated|relaunched|reopened|returned)\s+"
    r"(?:again|currently|now|presently|today)"
    r")\b",
    re.IGNORECASE,
)
STUDIO_GENERAL_CURRENT_RETURN = re.compile(
    r"(?:^|\b(?:and|but|however|nevertheless|nonetheless|then|yet)\b|"
    r"[.!?;:])\s*,?\s*(?:"
    r"(?:(?:now|today)\s+)?(?:Provider\s+Studio|the\s+Studio|it)\s+(?:"
    r"(?:is\s+)?back\s+online|came\s+back\s+online|resumed\s+(?:service|"
    r"operations?)|restored\s+operations?|(?:has\s+been\s+)?restored"
    r"(?:(?![.!?;]).){0,60}?\b(?:serving|available|operational)|"
    r"returned\s+to\s+(?:service|operations?)|"
    r"serves?\s+(?:customers?|providers?|users?)\s+again)|"
    r"(?:customers?|providers?|users?)\s+(?:can\s+)?"
    r"(?:access|enter|open|use|visit)"
    r"\s+(?:Provider\s+Studio|the\s+Studio|it)\s+again|"
    r"(?:now|today)\s+(?:Provider\s+Studio|the\s+Studio|it)\s+serves?\s+"
    r"(?:customers?|providers?|users?)\s+again"
    r")\b(?:(?![.!?;]).){0,40}?\b(?:again|currently|now|today)\b|"
    r"(?:^|\b(?:and|but|however|nevertheless|nonetheless|then|yet)\b|"
    r"[.!?;:])\s*,?\s*(?:now|today)\s+"
    r"(?:Provider\s+Studio|the\s+Studio|it)\s+serves?\s+"
    r"(?:customers?|providers?|users?)\s+again\b",
    re.IGNORECASE | re.DOTALL,
)
STUDIO_RESTORED_CURRENT_RETURN = re.compile(
    r"(?:^|\b(?:and|but|however|nevertheless|nonetheless|then|yet)\b|"
    r"[.!?;:])\s*,?\s*(?:Provider\s+Studio|the\s+Studio|it)\s+"
    r"(?:has\s+been|was)\s+restored\b(?:(?![.!?;]).){0,120}?\b(?:"
    r"active|available|currently|now|operational|serves?|services?|serving|today"
    r")\b",
    re.IGNORECASE | re.DOTALL,
)
STUDIO_DIRECT_CURRENT_LINK_SUFFIX = re.compile(
    r"^\s*(?:(?:Provider\s+Studio|it|this\s+(?:product|Studio))\s+)?(?:"
    r"(?:is|remains?)\s+(?:again|currently|now|presently|today)\s+"
    r"(?:active|available|current|live|operational|released)|"
    r"has\s+(?:(?:again|currently|now|since)\s+)?"
    r"(?:reactivated|relaunched|reopened|returned)"
    r")\b",
    re.IGNORECASE,
)
STUDIO_ADJACENT_CURRENT_REACTIVATION = re.compile(
    r"^\s*(?:(?:however|nevertheless|nonetheless|still|then)\s*,?\s*)?"
    r"(?:(?:again|currently|now|presently|today)\s*,?\s*)?"
    r"(?:Provider\s+Studio|it|the\s+Studio|this\s+(?:product|Studio))\s+"
    r"(?:"
    r"(?:is|remains?)\s+(?:(?:again|currently|now|presently|today)\s+)?"
    r"(?:active|available|current|live|operational|released)|"
    r"has\s+(?:(?:again|currently|now|since)\s+)?"
    r"(?:reactivated|relaunched|reopened|returned)|"
    r"(?:reactivated|relaunched|reopened|returned)\s+"
    r"(?:again|currently|now|presently|today)"
    r")\b",
    re.IGNORECASE,
)
STUDIO_CURRENT_PRODUCT_ASSERTION = re.compile(
    r"\bProvider\s+Studio\b(?:(?![.!?;]).){0,80}?\b"
    r"(?:is|remains?)\s+(?:(?:currently|now|presently|today)\s+)?"
    r"(?:active|available|current|live|operational|released)\b"
    r"(?:(?![.!?;]).){0,40}?"
    r"(?:\b(?:currently|now|presently|today)\b)?",
    re.IGNORECASE | re.DOTALL,
)
STUDIO_HISTORICAL_LINK_SUFFIX = re.compile(
    r"^\s*(?:[,—–-]\s*)?(?:"
    r"(?:was|were|is|are|became|remains?)\s+"
    r"(?:(?:an?|the)\s+)?(?:archived|deprecated|former|historical|legacy|"
    r"obsolete|prototype|retired|superseded)\b|"
    r"(?:served|operated|ran)\b(?:(?![.!?;]).){0,80}?\b"
    r"(?:former|historical|legacy|prototype|retired)\b|"
    r"(?:which|that)\s+(?:was|were|is|remains?)\s+"
    r"(?:(?:an?|the)\s+)?(?:archived|deprecated|former|historical|legacy|"
    r"obsolete|prototype|retired|superseded)\b|"
    r"(?:archived|deprecated|retired|superseded)\s+in\s+"
    r"(?:19|20)\d{2}\b"
    r")",
    re.IGNORECASE | re.DOTALL,
)
STUDIO_HISTORICAL_LIFECYCLE_SUFFIX = re.compile(
    r"^\s*(?:[,—–-]\s*)?(?:was|were)\s+"
    r"(?:(?:once|previously|then)\s+)?"
    r"(?:active|available|live|operational|publicly\s+available|reachable|released)\b"
    r"(?:(?![.!?;]).){0,100}?\b(?:"
    r"before(?:\s+it|\s+the\s+(?:product|Studio))?\s+"
    r"(?:(?:was|were|got)\s+)?(?!not\b|never\b)"
    r"(?:decommissioned|removed|retired|shut\s+down|sunset|withdrawn)|"
    r"before\s+being\s+(?!not\b|never\b)"
    r"(?:decommissioned|removed|retired|shut\s+down|sunset|withdrawn)|"
    r"(?:before|prior\s+to|until)\s+being\s+(?!not\b|never\b)"
    r"(?:decommissioned|removed|retired|shut\s+down|sunset|withdrawn)|"
    r"(?:before|prior\s+to|until)\s+"
    r"(?:it|the\s+(?:product|Studio))\s+(?:was|were|got)\s+"
    r"(?!not\b|never\b)"
    r"(?:decommissioned|removed|retired|shut\s+down|sunset|withdrawn)|"
    r"(?:before|prior\s+to|until)\s+(?:(?:its|the)\s+)?"
    r"(?:decommissioning|removal|retirement|shutdown|sunset|withdrawal)|"
    r"(?:and|but)\s+(?:(?:it|the\s+(?:product|Studio))\s+)?"
    r"(?:(?:was|were)\s+)?later\s+(?!not\b|never\b)"
    r"(?:decommissioned|removed|retired|shut\s+down|sunset|withdrawn)"
    r")\b",
    re.IGNORECASE | re.DOTALL,
)
STUDIO_HISTORICAL_RECORD_SUFFIX = re.compile(
    r"^\s*(?:[,—–-]\s*)?(?:"
    r"(?:went|became|stayed|remained|operated|ran|served|was|were)\b"
    r"(?:(?![.!?;]).){0,180}?\b(?:"
    r"decommissioned|removed|retired|shut\s+down|sunset|withdrawn|"
    r"decommissioning|removal|retirement|shutdown|sunset|withdrawal)\b|"
    r"(?:was|were)\s+(?:decommissioned|removed|retired|shut\s+down|sunset|"
    r"withdrawn)\b|"
    r"(?:(?:an?|the)\s+)?(?:archived|deprecated|former|historical|legacy|"
    r"obsolete|retired|superseded)\b"
    r"(?:(?![.!?;]).){0,80}?\b(?:beta\s+)?(?:interface|preview|prototype|"
    r"release|version|build|product)\b|"
    r"(?:which|that)\s+(?:was|were|is|remains?)\s+"
    r"(?:(?:an?|the)\s+)?(?:archived|deprecated|former|historical|legacy|"
    r"obsolete|retired|superseded)\b"
    r")",
    re.IGNORECASE | re.DOTALL,
)
STUDIO_HISTORICAL_DATE = re.compile(
    r"\b(?:in|during)\s+(?:19|20)\d{2}\b|"
    r"\bfrom\s+(?:19|20)\d{2}\s+(?:to|through|until|–|—|-)\s+"
    r"(?:19|20)\d{2}\b|"
    r"\bbetween\s+(?:19|20)\d{2}\s+and\s+(?:19|20)\d{2}\b",
    re.IGNORECASE,
)
STUDIO_HISTORICAL_PREDICATE = re.compile(
    r"\b(?:was|were|went|became|had(?:\s+been)?|used\s+to|formerly|"
    r"previously)\b|\b[a-z]+ed\b",
    re.IGNORECASE,
)
STUDIO_EXPLICIT_DESTINATION = re.compile(
    r"\bProvider\s+Studio\b(?:(?![.!?]).){0,100}?\b"
    r"(?:destination|URL|route|href)\b\s*(?:is|=|:)\s*"
    r"(?P<destination>\S+)",
    re.IGNORECASE | re.DOTALL,
)
STUDIO_RAW_DESTINATION_DENIAL = re.compile(
    r"\b(?:destination|href|link|route|URL)\s+(?:is|remains?)\s+"
    r"(?:explicitly\s+)?not\s+(?:(?:the|a)\s+)?(?:canonical\s+|current\s+|"
    r"live\s+)?(?:Provider\s+Studio\s+)?(?:destination|href|link|route|URL)\b|"
    r"\b(?:destination|href|link|route|URL)\s+(?:is|remains?)\s+"
    r"(?:deprecated|false|incorrect|invalid|obsolete|unsafe|wrong)\b"
    r"|\b(?:isn['’]t|aren['’]t|wasn['’]t|weren['’]t)\s+(?:the\s+)?"
    r"(?:canonical\s+|current\s+|live\s+)?(?:Provider\s+Studio\s+)?"
    r"(?:destination|href|link|route|URL)\b|"
    r"\b(?:is|remains?)\s+(?:explicitly\s+)?"
    r"(?:deprecated|false|incorrect|invalid|obsolete|unsafe|wrong)\b",
    re.IGNORECASE,
)
STUDIO_DOCUMENTATION_CONTEXT = re.compile(
    r"(?:"
    r"\bProvider\s+Studio\s+(?:documentation|docs?|guide|manual|reference|"
    r"examples?|test\s+fixtures?|archive)\b(?:(?![.!?]).){0,80}?"
    r"\b(?:is|are|lives?|resides?|exists?|can\s+be\s+found)\b"
    r"(?:(?![.!?]).){0,40}?\b(?:at|on|under)\b|"
    r"\b(?:documentation|docs?|guide|manual|reference|examples?|test\s+fixtures?|"
    r"archive)\s+(?:for|about|covering)\s+(?:the\s+)?Provider\s+Studio\b"
    r"(?:(?![.!?]).){0,80}?\b(?:is|are|lives?|resides?|exists?|"
    r"can\s+be\s+found)\b(?:(?![.!?]).){0,40}?\b(?:at|on|under)\b"
    r")",
    re.IGNORECASE | re.DOTALL,
)
STUDIO_DOCUMENTARY_LINK_PREFIX = re.compile(
    r"(?:\b(?:documentation|docs?|guide|manual|reference|examples?|"
    r"test\s+fixtures?|archive)\s+(?:for|about|covering|of)\s+(?:the\s+)?|"
    r"\b(?:(?:deployment|interface|migration|release)\s+)?"
    r"(?:archive|documentation|docs?|guide|manual|record|reference)\s+"
    r"(?:contains?|depicts?|documents?|preserves?|records?|shows?)\s+(?:the\s+)?)$",
    re.IGNORECASE,
)
STUDIO_DOCUMENTARY_LINK_SUFFIX = re.compile(
    r"^\s*(?:[,—–-]\s*)?(?:"
    r"(?:documentation|docs?|guide|manual|reference|examples?|"
    r"test\s+fixtures?|archive)\b|"
    r"interface\s+(?:documentation|docs?|guide|manual|reference|archive)\b|"
    r"as\s+(?:an?\s+|the\s+)?(?:archived|deprecated|historical|retired)\s+"
    r"(?:example|fixture|interface|record|reference)\b"
    r")",
    re.IGNORECASE,
)
STUDIO_DOCUMENTARY_CURRENT_VETO = re.compile(
    r"\b(?:current|live|production)\s+(?:app|application|destination|link|"
    r"console|editor|product|site|surface|URL|workspace)\b|"
    r"\b(?:access|enter|launch|open|use|visit)\b"
    r"(?:(?![.!?;]).){0,80}?\b(?:app|application|now|product|Studio|today)\b",
    re.IGNORECASE | re.DOTALL,
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

PUBLIC_WEB_DIRECT_ECONOMIC = {
    "public web claims booking, payment, settlement, or economic controls": re.compile(
        r"\b(?:the\s+)?(?:public\s+web|Stele\s+web|web\s+app|Provider\s+Studio)\b"
        r"(?:(?![.!?,;]|\b(?:and|or|but|however|yet|while|whereas|though)\b).)"
        r"{0,80}?\b(?:"
        r"(?:books|pays|settles)\b|"
        r"(?:manages|operates|holds|controls|administers|handles|processes|runs)\s+"
        r"(?:(?:an?|the)\s+)?escrow\b|"
        r"(?:can|does|now|currently|is\s+able\s+to)\s+(?!not\b)"
        r"(?:manage|operate|hold|control|administer|handle|process|run)\s+"
        r"(?:(?:an?|the)\s+)?escrow\b"
        r")|"
        r"\b(?:escrow|escrow\s+(?:management|operations?))\b"
        r"(?:(?![.!?]).){0,80}?\b(?:is|are|remains?)\s+"
        r"(?:(?:now|currently|already|presently)\s+)?"
        r"(?:managed|operated|held|controlled|administered|handled|processed|run)\s+"
        r"by\s+(?:the\s+)?Provider\s+Studio\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

CAPABILITY_META_SUFFIX = (
    r"(?!(?:(?:['’]s)?\s+|-)(?:absence|authority|ban|claim|count|description|"
    r"disclaimer|documentation|docs?|engine|"
    r"example|examples|guide|limit|manual|notice|policy|policies|prohibition|"
    r"prohibitions|provider|requirement|requirements|restriction|restrictions|"
    r"rule|rules|safeguard|safeguards|service|statement|tools?|warning|warnings)\b)"
)

HOSTED_TRANSACTION_ENABLED = {
    "hosted Stele MCP claims transaction capability": re.compile(
        r"\b(?:can|does|now|currently|is\s+able\s+to)\s+(?!not\b)"
        r"(?:create|build|construct|prepare|generate|originate|initiate|handle|"
        r"control|manage|process|sign|broadcast|submit|settle|execute|authorize|"
        r"approve|move|send|relay|forward)\w*\b"
        r"(?:(?![.!?]).){0,120}?\b"
        r"(?:transactions?|transaction\s+signatures?|payments?|settlements?|"
        r"transfers?|funds?|service\s+wallet|wallet\s+payloads?|payloads?)\b|"
        r"\b(?:is|remains?)\s+(?!not\b)"
        r"(?:(?:now|currently|actively|already|presently)\s+)?(?:"
        r"creating|building|constructing|preparing|generating|originating|"
        r"initiating|handling|controlling|managing|processing|signing|"
        r"broadcasting|submitting|settling|executing|authorizing|approving|"
        r"moving|sending|relaying|forwarding)\b"
        r"(?:(?![.!?]).){0,100}?\b(?:transactions?|payments?|settlements?|"
        r"transfers?|funds?|wallet\s+payloads?|payloads?)\b|"
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
        r"\b(?<!not\s)(?<!never\s)(?:creates|builds|constructs|prepares|"
        r"originates|initiates|signs|broadcasts|submits|settles|executes|"
        r"authorizes|approves|generates|handles|controls|manages|processes|moves)\b"
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
        rf"(?:signer|signing\s+(?:tools?|authority|service|engine|provider)|"
        rf"broadcast\s+tools?|signing|broadcast|submission|settlement|authorization|"
        rf"authority|capabilit(?:y|ies)|transaction\s+tools?)\b"
        rf"{CAPABILITY_META_SUFFIX}|"
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
        rf"capabilit(?:y|ies)|signer|transaction\s+tools?)\b"
        rf"{CAPABILITY_META_SUFFIX}|"
        r"\b(?:is|remains?)\s+(?!not\b)(?:directly\s+)?"
        r"(?:responsible\s+for|in\s+charge\s+of)\s+"
        r"(?:transaction\s+|wallet\s+)?(?:signing|broadcast|submission|"
        r"settlement|authorization)\b|"
        r"\b(?:has|holds|keeps|stores|retains|maintains)\s+access\s+to\s+"
        r"(?:wallet\s+)?(?:secrets?|seed\s+phrases?|recovery\s+phrases?|"
        r"private\s+keys?)\b|"
        r"\b(?<!not\s)(?<!never\s)(?<!will\s)(?<!could\s)(?<!would\s)"
        r"(?<!may\s)(?<!might\s)(?<!to\s)(?<!or\s)"
        r"(?!(?:describes?|discusses?|displays?|documents?|mentions?|prohibits?|"
        r"reports?|restricts?|warns?)\b)"
        r"(?!transactions?\b|signatures?\b|signers?\b|capabilit(?:y|ies)\b|"
        r"keys?\b|authority\b|custody\b)"
        r"[a-z][a-z-]{2,}(?:s|es)\b"
        r"(?:(?![.!?;|]|\b(?:no|not|never|zero|cannot|without|could|would|will|may|"
        r"might|future|retired|former|previous|legacy|off|gated|unavailable)\b|"
        r"n['’]t).){0,100}?\b(?:"
        r"signed\s+transactions?|transaction\s+(?:signatures?|signers?|tools?|"
        r"capabilit(?:y|ies)|authorization|submission|signing|broadcast|settlement)|"
        r"signing\s+(?:authority|keys?|capabilit(?:y|ies))|private\s+keys?|"
        r"wallet\s+custody"
        rf")\b{CAPABILITY_META_SUFFIX}",
        re.IGNORECASE | re.DOTALL,
    ),
}

TRANSACTION_TOOL_COUNT = re.compile(
    rf"\b(?:has|holds|keeps|uses|adds|exposes?|offers?|provides?|includes?|"
    rf"ships?\s+with)\s+"
    rf"(?:(?:(?![.!?;]).){{0,80}}?\b(?:and|plus|alongside)\s+)?"
    rf"(?:(?:exactly|only)\s+)?(?P<count>{COUNT_TOKEN})\s+"
    rf"(?:transaction|signing|broadcast|"
    rf"submission|settlement|payment|economic(?:-write)?)\s+tools?\b"
    rf"{CAPABILITY_META_SUFFIX}",
    re.IGNORECASE,
)
TRANSACTION_TOOL_DESCRIPTOR = re.compile(
    r"\b(?:transaction|signing|broadcast|submission|settlement|payment|"
    r"economic(?:-write)?)\b",
    re.IGNORECASE,
)

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
        r"(?:(?!\bno\b|[.!?]).){0,140}?\b(?:transaction|signing|broadcast)\s+"
        r"(?:tools?|endpoints?|capabilit(?:y|ies))\b|"
        r"\badds?\s+(?:an?\s+)?(?:transaction|signing|broadcast)\s+"
        r"(?:tools?|endpoints?|capabilit(?:y|ies))\b",
        re.IGNORECASE | re.DOTALL,
    ),
}

NEGATED_AUXILIARY = (
    r"(?:cannot|can\s+not|can['’]t|does\s+not|doesn['’]t|never)"
)
NEGATED_COPULA = (
    r"(?:(?:is|remains?)\s+(?:not|never|no\s+longer)|isn['’]t)"
)
TRANSACTION_ACTION = (
    r"(?:create|build|construct|prepare|generate|originate|initiate|handle|control|"
    r"manage|process|sign|broadcast|submit|authorize|approve|execute|settle|move|"
    r"send|relay|forward|hold|keep|store|retain|maintain)\w*"
)
TRANSACTION_ACTION_GERUND = (
    r"(?:creating|building|constructing|preparing|generating|originating|initiating|"
    r"handling|controlling|managing|processing|(?:transaction\s+)?signing|"
    r"broadcasting|submitting|"
    r"authorizing|approving|executing|settling|moving|sending|relaying|forwarding|"
    r"holding|keeping|storing|retaining|maintaining)"
)
TRANSACTION_OBJECT = (
    rf"(?:transactions?|payments?|transfers?|private\s+keys?|wallet\s+secrets?|"
    rf"seed\s+phrases?|signing\s+authority|wallet\s+payloads?|payloads?)\b"
    rf"{CAPABILITY_META_SUFFIX}"
)

EXACT_PROVIDER_DRAFT_TOOL_TRANSACTION = re.compile(
    rf"(?:"
    rf"{CANONICAL_PROVIDER_DRAFT_TOOL}(?:(?![.!?;]).){{0,120}}?\b"
    rf"{TRANSACTION_ACTION}\b(?:(?![.!?;]).){{0,100}}?\b{TRANSACTION_OBJECT}|"
    rf"{TRANSACTION_OBJECT}\s+(?:can|may)\s+be\s+"
    rf"(?:created|built|constructed|prepared|generated|originated|initiated|"
    rf"handled|controlled|managed|processed|signed|broadcast|submitted|settled|"
    rf"executed|authorized|approved|moved|sent|relayed|forwarded)\s+"
    rf"(?:by|through|via|with)\s+(?:the\s+)?{CANONICAL_PROVIDER_DRAFT_TOOL}"
    rf")",
    re.IGNORECASE | re.DOTALL,
)

EXACT_PROVIDER_DRAFT_TOOL_TRANSACTION_NOMINAL = re.compile(
    rf"(?:"
    rf"{CANONICAL_PROVIDER_DRAFT_TOOL}(?:(?![.!?;]).){{0,120}}?\b"
    rf"(?:provides?|offers?|supports?|enables?|exposes?|includes?|has|holds?|"
    rf"allows?|permits?)\s+"
    rf"(?:(?:the|an?)\s+)?(?:transaction\s+)?(?:signer|signing\s+(?:authority|"
    rf"capability|service|tooling)|signing|broadcast|submission|settlement|"
    rf"broadcast\s+(?:capability|service|tooling)|"
    rf"transaction\s+(?:creation|preparation|signing|broadcast|submission|"
    rf"settlement|execution|authorization)\s+(?:capability|service|tooling))\b|"
    rf"\b(?:transaction\s+(?:creation|preparation|generation|origination|"
    rf"initiation|handling|control|management|processing|signing|broadcast|"
    rf"submission|settlement|execution|authorization|approval)|"
    rf"(?:signing|broadcast|submission|settlement|execution|authorization)\s+of\s+"
    rf"transactions?)\s+(?:is|remains?)\s+"
    rf"(?:(?:now|currently|presently)\s+)?(?:available|enabled|supported|provided|"
    rf"offered|exposed|included|possible)\s+(?:by|from|through|via|with)\s+(?:the\s+)?"
    rf"{CANONICAL_PROVIDER_DRAFT_TOOL}"
    rf")",
    re.IGNORECASE | re.DOTALL,
)
TRANSACTION_ABSENCE_TARGET = (
    rf"(?:signing\s+(?:authority|capabilit(?:y|ies)|tools?|endpoints?|tooling)|"
    rf"(?:transaction|signing|broadcast|submission|settlement|payment|"
    rf"economic(?:-write)?)\s+(?:tools?|endpoints?|capabilit(?:y|ies)|tooling)|"
    rf"(?:transaction|signing|broadcast|submission|settlement)\s+functionality|signer|"
    rf"private\s+keys?|wallet\s+secrets?|seed\s+phrases?)\b"
    rf"{CAPABILITY_META_SUFFIX}"
)

HOSTED_DOUBLE_NEGATION_ENABLED = {
    "hosted Stele MCP claims transaction capability": re.compile(
        rf"\b(?:"
        rf"{NEGATED_AUXILIARY}\s+(?:fails?|refuses?)\s+to\s+"
        rf"{TRANSACTION_ACTION}\b(?:(?![.!?]).){{0,100}}?\b{TRANSACTION_OBJECT}|"
        rf"{NEGATED_AUXILIARY}\s+lacks?\s+(?:an?\s+)?"
        rf"{TRANSACTION_ABSENCE_TARGET}|"
        rf"(?:fails?|refuses?)\s+to\s+(?:lack|be\s+(?:without|devoid\s+of))\s+"
        rf"(?:an?\s+)?{TRANSACTION_ABSENCE_TARGET}|"
        rf"{NEGATED_AUXILIARY}\s+(?:be\s+)?"
        rf"(?:characteri[sz]ed|described|regarded|represented|said)\s+as\s+"
        rf"(?:having|holding|possessing|providing|offering|exposing)\s+"
        rf"(?:no|zero)\s+{TRANSACTION_ABSENCE_TARGET}|"
        rf"{NEGATED_AUXILIARY}\s+(?:be\s+)?(?:said|considered|described)\s+to\s+"
        rf"(?:lack|be\s+(?:without|devoid\s+of))\s+(?:an?\s+)?"
        rf"{TRANSACTION_ABSENCE_TARGET}|"
        rf"(?:cannot|can\s+not|can['’]t|does\s+not|doesn['’]t)\s+not\s+"
        rf"{TRANSACTION_ACTION}\b(?:(?![.!?]).){{0,100}}?\b{TRANSACTION_OBJECT}|"
        rf"{NEGATED_AUXILIARY}\s+avoids?\s+{TRANSACTION_ACTION_GERUND}\b"
        rf"(?:(?![.!?]).){{0,100}}?\b{TRANSACTION_OBJECT}|"
        rf"{NEGATED_AUXILIARY}\s+avoids?\s+(?:transaction\s+)?"
        rf"(?:signing|broadcast|submission|settlement|authorization)\b"
        rf"{CAPABILITY_META_SUFFIX}|"
        rf"{NEGATED_COPULA}\s+(?:lacking|without|devoid\s+of)\s+(?:an?\s+)?"
        rf"{TRANSACTION_ABSENCE_TARGET}|"
        rf"{NEGATED_COPULA}\s+(?:unable\s+to|incapable\s+of)\s+"
        rf"{TRANSACTION_ACTION}\b(?:(?![.!?]).){{0,100}}?\b{TRANSACTION_OBJECT}"
        rf")",
        re.IGNORECASE | re.DOTALL,
    ),
}

TRANSACTION_ABSENCE_CHAIN_OPERATOR = (
    rf"(?:{NEGATED_AUXILIARY}\s+|"
    rf"(?:fails?|refuses?)\s+(?:not\s+)?to\s+|"
    rf"not\s+to\s+)"
)
HOSTED_TRANSACTION_ABSENCE_PARITY = {
    "hosted Stele MCP claims transaction capability": re.compile(
        rf"\b(?:{TRANSACTION_ABSENCE_CHAIN_OPERATOR}){{1,6}}(?:"
        rf"lacks?\s+(?:an?\s+)?{TRANSACTION_ABSENCE_TARGET}|"
        rf"be\s+(?:without|devoid\s+of)\s+(?:an?\s+)?"
        rf"{TRANSACTION_ABSENCE_TARGET}|"
        rf"(?:have|hold|possess)\s+(?:no|zero)\s+"
        rf"{TRANSACTION_ABSENCE_TARGET}"
        rf")",
        re.IGNORECASE | re.DOTALL,
    )
}

HOSTED_TYPED_TRANSACTION_ABSENCE_DENIAL = {
    "hosted Stele MCP claims transaction capability": re.compile(
        rf"\b(?:"
        rf"(?:cannot|can\s+not|can['’]t|does\s+not|doesn['’]t|never)\s+"
        rf"(?:have|holds?|keeps?|uses?|adds?|exposes?|offers?|provides?|includes?|"
        rf"ships?\s+with)\s+"
        rf"(?:(?:exactly|only)\s+)?(?:zero|0|no)\s+"
        rf"(?:transaction|signing|broadcast|submission|settlement|payment|"
        rf"economic(?:-write)?)\s+tools?\b{CAPABILITY_META_SUFFIX}|"
        rf"(?:has|holds|keeps|uses|adds|exposes?|offers?|provides?|includes?|"
        rf"ships?\s+with)\s+(?:a\s+)?(?:not\s+(?:zero|0)|non[- ]?zero|positive)\s+"
        rf"(?:number\s+of\s+)?(?:transaction|signing|broadcast|submission|"
        rf"settlement|payment|economic(?:-write)?)\s+tools?\b{CAPABILITY_META_SUFFIX}|"
        rf"(?:transaction|signing|broadcast|submission|settlement|payment|"
        rf"economic(?:-write)?)\s+tool\s+count\s*(?:is|=|:)\s*"
        rf"(?:not\s+(?:zero|0)|non[- ]?zero|positive)\b"
        rf")",
        re.IGNORECASE | re.DOTALL,
    ),
}

HOSTED_STRONG_NEGATION_ENABLED = {
    "hosted Stele MCP claims transaction capability": re.compile(
        rf"\b(?:"
        rf"(?:(?:is|remains?)\s+(?:not|never|no\s+longer|"
        rf"by\s+no\s+means)\s+|isn['’]t\s+)"
        rf"(?:barred|blocked|forbidden|prevented|prohibited|restricted)\s+"
        rf"(?:from\s+)?{TRANSACTION_ACTION}\b"
        rf"(?:(?![.!?;]).){{0,100}}?\b{TRANSACTION_OBJECT}|"
        rf"(?:(?:is|remains?)\s+(?:not|never|no\s+longer|"
        rf"by\s+no\s+means)\s+|isn['’]t\s+)"
        rf"(?:barred|blocked|forbidden|prevented|prohibited|restricted)\s+"
        rf"(?:from\s+)?(?:transaction\s+)?(?:signing|broadcast|submission|"
        rf"settlement|authorization)\b{CAPABILITY_META_SUFFIX}|"
        rf"(?:is\s+|remains?\s+)?(?:by\s+no\s+means|in\s+no\s+way)\s+"
        rf"(?:lacking|without|lacks?|is\s+without|remains?\s+without)\s+"
        rf"(?:an?\s+)?"
        rf"{TRANSACTION_ABSENCE_TARGET}|"
        rf"(?:transaction\s+(?:signing|broadcast|submission|settlement|"
        rf"authorization)|signing\s+(?:authority|capabilit(?:y|ies)|tools?)|"
        rf"(?:transaction|signing|broadcast|submission|settlement)\s+"
        rf"(?:tools?|endpoints?))\s+(?:(?:is|are|remains?)\s+"
        rf"(?:not|never|no\s+longer)\s+|isn['’]t\s+|aren['’]t\s+)absent\b|"
        rf"(?:nothing|no\s+(?:rule|policy|restriction|prohibition))\s+"
        rf"(?:bars?|blocks?|forbids?|prevents?|prohibits?|restricts?)\s+"
        rf"(?:it|the\s+(?:service|MCP))\s+from\s+{TRANSACTION_ACTION}\b"
        rf"(?:(?![.!?;]).){{0,100}}?\b{TRANSACTION_OBJECT}|"
        rf"(?:has|faces|is\s+under)\s+no\s+(?:ban|bar|block|prohibition|"
        rf"restriction)\s+(?:against|on)\s+(?:transaction\s+)?"
        rf"(?:signing|broadcast|submission|settlement|authorization)\b"
        rf")",
        re.IGNORECASE | re.DOTALL,
    ),
}

HOSTED_TYPED_TRANSACTION_POSITIVE = {
    "hosted Stele MCP claims transaction capability": re.compile(
        rf"\b(?:"
        rf"(?:has|holds?|keeps?|uses?|adds?|exposes?|offers?|provides?|includes?|"
        rf"ships?\s+with)\s+(?:"
        rf"(?:>|greater\s+than|more\s+than)\s*0|"
        rf"(?:at\s+least|no\s+fewer\s+than|minimum\s+of)\s+(?:one|1)|"
        rf"(?:one|two|1|2|(?:an?\s+)?pair\s+of)"
        rf")\s+(?:transaction|signing|broadcast|submission|settlement|payment|"
        rf"economic(?:-write)?)\s+(?:tools?|endpoints?|capabilit(?:y|ies))\b"
        rf"{CAPABILITY_META_SUFFIX}|"
        rf"(?:transaction|signing|broadcast|submission|settlement|payment|"
        rf"economic(?:-write)?)\s+(?:tool|endpoint|capability)\s+count\s*"
        rf"(?:"
        rf"(?:is|=|:)?\s*(?:>|greater\s+than|more\s+than)\s*(?:zero|0)\b|"
        rf"(?:exceeds?|surpasses?)\s+(?:zero|0)\b"
        rf")|"
        rf"(?:transaction|signing|broadcast|submission|settlement|payment|"
        rf"economic(?:-write)?)\s+(?:tool|endpoint|capability)\s+count\s*"
        rf"(?:is|=|:)?\s*(?:at\s+least|no\s+fewer\s+than|minimum\s+of)?\s*"
        rf"(?:one|two|1|2)\b"
        rf")",
        re.IGNORECASE | re.DOTALL,
    ),
}

TRANSACTION_ZERO_UPPER_BOUND = re.compile(
    rf"\b(?:"
    rf"(?:fewer|less)\s+than\s+(?:one|1)|"
    rf"(?:at\s+most|no\s+more\s+than|up\s+to|a\s+maximum\s+of|"
    rf"maximum\s+of)\s+(?:zero|0)"
    rf")\s+(?:transaction|signing|broadcast|submission|settlement|payment|"
    rf"economic(?:-write)?)\s+(?:tools?|endpoints?|capabilit(?:y|ies))\b",
    re.IGNORECASE,
)
HOSTED_ZERO_BOUND_COORDINATED_POSITIVE = {
    "hosted Stele MCP claims transaction capability": re.compile(
        rf"{TRANSACTION_ZERO_UPPER_BOUND.pattern}"
        rf"\s*(?:,?\s*(?:and|but|plus)|alongside|as\s+well\s+as)\s+"
        rf"(?!(?:no|not|zero)\b)(?:an?\s+)?{TRANSACTION_ABSENCE_TARGET}",
        re.IGNORECASE | re.DOTALL,
    )
}

DOUBLE_NEGATION_CONTRADICTIONS = {
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
    "Stele catalog denies zero published services; expected zero": re.compile(
        r"\b(?:Stele|the\s+(?:public\s+)?catalog)\b(?:(?![.!?]).){0,100}?\b"
        r"(?:does\s+not|doesn['’]t|cannot)\s+(?:have|contain|report|show)\s+"
        r"zero\s+published\s+services?\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "Stele catalog denies zero listings; expected zero": re.compile(
        rf"(?:"
        rf"\bthere\s+(?:(?:is|are)\s+(?:not|no\s+longer)|isn['’]t|aren['’]t)\s+"
        rf"zero\s+{CATALOG_ITEM_NOUN}\b\s+{CATALOG_LOCATION}|"
        rf"\b(?:the\s+)?(?:public|Stele)\s+catalog\b{CATALOG_META_SUFFIX}"
        rf"(?:(?![.!?]).){{0,80}}?\b(?:does\s+not|doesn['’]t|cannot)\s+"
        rf"(?:have|contain|report|show)\s+zero\s+{CATALOG_ITEM_NOUN}\b"
        rf")",
        re.IGNORECASE,
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


NONCURRENT_GATE_EVENT = (
    r"(?:(?:an?|the)\s+)?(?:[a-z][a-z-]*\s+){0,3}"
    r"(?:activation|release|review|version|phase|build)"
)
CLAIM_NONCURRENT = re.compile(
    r"\b(?:future|retired|former|previous|legacy|historical|historically|"
    r"archived|deprecated|decommissioned|prototype|previously|formerly)\b|"
    r"\b(?:in|during|as\s+of)\s+(?!2026\b)\d{4}\b|"
    r"\b(?:starting|beginning)\s+in\s+(?!2026\b)\d{4}\b|"
    r"\bscheduled\s+for\s+(?!2026\b)\d{4}\b|"
    r"\buntil\s+(?:19\d{2}|20(?:0\d|1\d|2[0-5]))\b|"
    r"\bthrough\s+(?:19\d{2}|20(?:0\d|1\d|2[0-5]))\b|"
    r"\b(?:will|could|would|may|might)\b|"
    r"\b(?:next|upcoming|later|subsequent)\s+"
    r"(?:release|version|phase|build)\b|"
    r"\b(?:was|were)\b|"
    r"\b(?:Stele|MCP|web|Studio|wallet|catalog|it|they)\s+used\s+to\b|"
    rf"\bonly\s+after\s+{NONCURRENT_GATE_EVENT}\b|"
    rf"\bafter\s+{NONCURRENT_GATE_EVENT}\b",
    re.IGNORECASE,
)
CLAIM_HYPOTHETICAL_PREFIX = re.compile(
    r"^\s*[\"'“‘(\[]*\s*(?:(?:(?:release|security|deployment)\s+)?"
    r"(?:warning|caution)\s*(?::|[—–-])\s*)?(?:if|unless)\b",
    re.IGNORECASE,
)
CLAIM_DOCUMENTARY_PREFIX = re.compile(
    r"^\s*[\"'“‘(\[]*\s*(?:archived?\s+)?(?:counterexample|example|fixture|"
    r"historical\s+simulation|hypothetical|mockup|sample|simulation|test\s+case|"
    r"warning)\s*(?::|[—–-])\s*",
    re.IGNORECASE,
)
CLAIM_ARCHIVED_DOCUMENTATION_PREFIX = re.compile(
    r"^\s*[\"'“‘(\[]*\s*(?:according\s+to\s+)?(?:(?:the|an?)\s+)?"
    r"archived\s+(?:(?:audit|deployment|release|security)\s+)?"
    r"(?:assessment|documentation|docs?|example|fixture|manual|record|release|"
    r"report|review|sample|simulation|snapshot|test)\b"
    r"(?:(?![,;.!?]).){0,100}?\b"
    r"(?:contained|described|depicted|documented|linked|listed|recorded|said|"
    r"say|says|showed|shows|used)\b",
    re.IGNORECASE | re.DOTALL,
)
CLAIM_ARCHIVED_ATTRIBUTION_PREFIX = re.compile(
    r"^\s*[\"'“‘(\[]*\s*according\s+to\s+(?:(?:the|an?)\s+)?"
    r"archived\s+(?:(?:audit|deployment|release|security)\s+)?"
    r"(?:assessment|documentation|docs?|manual|record|report|review|snapshot)"
    r"\b(?:(?![,;.!?]).){0,100},\s*",
    re.IGNORECASE | re.DOTALL,
)
INTRODUCTORY_NONCURRENT_SCOPE = re.compile(
    r"^\s*(?:only\s+)?(?:"
    r"(?:in|during|as\s+of)\s+(?!2026\b)\d{4}\b|"
    r"(?:starting|beginning)\s+in\s+(?!2026\b)\d{4}\b|"
    r"scheduled\s+for\s+(?!2026\b)\d{4}\b|"
    r"until\s+(?:19\d{2}|20(?:0\d|1\d|2[0-5]))\b|"
    r"through\s+(?:19\d{2}|20(?:0\d|1\d|2[0-5]))\b|"
    r"(?:in|for|during|at)\b"
    r"(?:(?![,;.!?]).){0,100}\b(?:future|next|upcoming|later|subsequent|"
    r"retired|former|legacy|historical|prototype)\b|"
    r"(?:the\s+)?(?:next|upcoming|later|subsequent)\s+"
    r"(?:release|version|phase|build)\b|"
    r"(?:when|once)\b(?:(?![,;.!?]).){0,100}\b"
    r"(?:future|activation|release)\b|"
    r"(?:after|upon)\b(?:(?![,;.!?]).){0,100}\b"
    r"(?:future|retired|former|legacy|historical|prototype|activation|release|review)\b"
    r")(?:(?![,;.!?]).){0,60},\s*$",
    re.IGNORECASE | re.DOTALL,
)
CLAIM_NONCURRENT_SUFFIX = re.compile(
    r"^\s*,?\s*(?:(?:but|and)\s+)?(?:"
    r"(?:was|were)\s+(?:(?:an?|the)\s+)?"
    r"(?:(?:retired|former|legacy|historical|unreleased)\s+)?"
    r"(?:prototype|preview|experiment|mockup|simulation|version|release)\b|"
    rf"only\s+after\s+{NONCURRENT_GATE_EVENT}\b|"
    rf"after\s+{NONCURRENT_GATE_EVENT}\b|"
    r"(?:only\s+)?(?:in|for)\s+(?:(?:an?|the)\s+)?(?:"
    r"(?:future|next|upcoming|later|subsequent)\s+(?:release|version|phase|build)|"
    r"(?:retired|former|legacy|historical)\s+(?:prototype|release|version|build)|"
    r"prototype|future)\b|"
    r"(?:when|once)\s+(?:(?:an?|the)\s+)?"
    r"(?:future|next|upcoming|later|subsequent)\s+(?:release|version|phase|build)\b"
    r")",
    re.IGNORECASE,
)
CLAIM_DENIAL = re.compile(
    r"\b(?:no|not|never|cannot|neither|nor|lack(?:s|ing)?|refuses?|blocks?|bars?|"
    r"fails?|rejects?|forbids?|prevents?|den(?:y|ies|ied|ying)|"
    r"disavow(?:s|ed|ing)?|unable|incapable|"
    r"unavailable|gated|off|empty|"
    r"false|invalid|incorrect|wrong|misleading|obsolete|avoids?|unsafe|untrue|"
    r"deprecated|disabled|inactive|closed|blocked)\b|"
    r"n['’]t\b",
    re.IGNORECASE,
)
ABSENCE_DENIAL = re.compile(r"\b(?:devoid\s+of|without|zero)\b", re.IGNORECASE)
COUNT_DENIAL_PREFIX = re.compile(
    r"(?:\b(?:no|not|never|neither|nor)\s+|n['’]t\s+|"
    r"\b(?:rather\s+than|instead\s+of)\s+)$",
    re.IGNORECASE,
)
COUNT_ABSENCE_PREFIX = re.compile(r"\bwithout\s+$", re.IGNORECASE)

ASSERTION_FINITE_LEAD = (
    r"(?:am|is|are|has|have|does|do|can|"
    r"holds?|keeps?|stores?|retains?|maintains?|possess(?:es)?|owns?|"
    r"signs?|broadcasts?|submits?|settles?|executes?|authorizes?|approves?|"
    r"generates?|handles?|manages?|processes?|relays?|forwards?|"
    r"collects?|accepts?|takes?|charges?|bills?|transfers?|moves?|debits?|"
    r"withdraws?|operates?|runs?|performs?|conducts?|publishes?|lists?|"
    r"lacks?|refuses?|rejects?|blocks?|bars?|fails?|denies?|forbids?|prevents?|"
    r"creates?|builds?|constructs?|originates?|initiates?|prepares?|controls?|"
    r"accesses?|reads?|fetches?|retrieves?|loads?|views?|inspects?|queries?|"
    r"updates?|edits?|deletes?|writes?|hosts?|houses?|carries?|integrates?|"
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
    r"builds|constructs|originates|initiates|prepares|controls|accesses|reads|"
    r"fetches|retrieves|loads|views|inspects|queries|updates|edits|deletes|writes|"
    r"hosts|houses|carries|integrates|authors|produces|"
    r"sends|doubles|serves|functions|works|ships|launches|bundles|embeds|"
    r"includes|contains|confirms|proves|verifies|validates|authenticates|"
    r"certifies|attests|identifies|provides|exposes|offers|supports|enables|"
    r"adds|opens|uses|visits|open|use|visit)"
)
ASSERTION_SUBJECT = (
    r"(?:(?:the|an?)\s+)?(?:"
    r"Hosted\s+(?:Stele\s+)?MCP|local\s+(?:Stele\s+)?MCP|"
    r"Provider\s+Studio|public\s+web|Stele\s+web|web\s+app|"
    r"Desktop\s+Wallet|desktop\s+wallet|Mobile\s+Wallet|mobile\s+wallet|"
    r"Browser\s+Wallet|"
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
    r"(?:is|are|was|were|remains?)\s+(?:explicitly\s+)?not\s+(?:the\s+)?"
    r"(?:current|live|canonical)\s+(?:product\s+)?(?:destination|URL|link)|"
    r"(?:should|must)\s+not\s+be\s+used|"
    r"must\s+be\s+(?:removed|rejected|ignored)|"
    r"should\s+be\s+(?:removed|rejected|ignored)|"
    r"(?:would|will)\s+(?:be|constitute|indicate|signal)\s+"
    r"(?:(?:an?|the)\s+)?(?:critical\s+|security\s+)?"
    r"(?:defect|bug|error|violation|regression|incident|vulnerability|problem)"
    r")\b",
    re.IGNORECASE,
)
QUOTED_ASSERTION_REJECTION_TAIL = re.compile(
    r"^\s*[.,;:—–-]?\s*(?:(?:and|but)\s+)?"
    r"(?:"
    r"(?:(?:it|this\s+(?:document|note|report|text|warning)|"
    r"the\s+(?:document|note|report|text|warning))\s+)?"
    r"(?:explicitly\s+)?"
    r"(?:denies?|disputes?|rejects?|refutes?)\s+"
    r"(?:them\b|"
    r"(?:(?:that|this|these|those)\s+(?:quoted\s+)?|"
    r"(?:both|all)\s+(?:of\s+the\s+)?(?:quoted\s+)?|"
    r"the\s+(?:quoted\s+)?)"
    r"(?:claims?|assertions?|statements?|descriptions?)\b)|"
    r"(?:is|are|was|were|remains?|as)\s+(?:not\s+true|false|incorrect|"
    r"invalid|misleading|untrue|wrong)\b|"
    r"as\s+(?:an?\s+)?(?:false|incorrect|invalid|misleading|untrue|wrong)\s+"
    r"(?:claim|description|assertion|sentence|statement)s?\b|"
    r"(?:(?:is|are|was|were|remains?)\s+)?(?:an?\s+)?"
    r"(?:false|incorrect|invalid|misleading|untrue|wrong)\s+"
    r"(?:claim|description|assertion|sentence|statement)s?\b"
    r")",
    re.IGNORECASE,
)
QUOTED_ASSERTION_REJECTION_PREFIX = re.compile(
    r"(?:^|[.!?;]\s*)"
    r"(?:(?:the\s+)?(?:audit|document|note|report|review|reviewer|text|warning)\s+|"
    r"(?:it|they)\s+)?"
    r"(?:(?:clearly|directly|explicitly)\s+)?"
    r"(?:denies?|disputes?|rejects?|refutes?)\s*"
    r"(?:(?:that|this|these|those|the)\s+)?"
    r"(?:(?:following|quoted)\s+)?"
    r"(?:(?:claims?|assertions?|statements?|descriptions?)\s*)?"
    r"(?:(?:that|saying)\s*|:\s*)?$|"
    r"(?:^|[.!?;]\s*)(?:the\s+)?"
    r"(?:denied|disputed|rejected|refuted)\s+"
    r"(?:claims?|assertions?|statements?|descriptions?)\s*"
    r"(?:(?:reads?|says?)\s*|:\s*)?$",
    re.IGNORECASE,
)
NEGATED_QUOTED_REJECTION_FRAME = re.compile(
    r"\b(?:does|did|has|have|had)\s+not\s+(?:call|describe|identify|label|"
    r"mark|say|state)\b|"
    r"\b(?:isn['’]t|aren['’]t|wasn['’]t|weren['’]t)\s+"
    r"(?:calling|describing|identifying|labelling|marking|saying|stating)\b|"
    r"\b(?:doesn['’]t|didn['’]t|hasn['’]t|haven['’]t|hadn['’]t)\s+"
    r"(?:call|describe|identify|label|mark|say|state)\b|"
    r"\bnever\s+(?:called|described|identified|labelled|marked|said|stated)\b|"
    r"^\s*no\s+(?:assessor|audit|auditor|document|note|report|review|reviewer|"
    r"text|warning)\b"
    r"(?:(?![.!?;]).){0,100}?\b(?:calls?|describes?|identifies?|labels?|marks?|"
    r"says?|states?)\b",
    re.IGNORECASE | re.DOTALL,
)
QUOTED_REJECTION_REVERSAL = re.compile(
    r"\b(?:but|however|nevertheless|nonetheless|yet)\b"
    r"(?:(?![.!?;]).){0,80}?\b(?:actually\s+)?(?:accurate|correct|true|valid)\b",
    re.IGNORECASE | re.DOTALL,
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
RELATIVE_NEGATIVE_MODIFIER = re.compile(
    rf"\b(?:that|which|who)\b(?:(?![,;.!?]).){{0,120}}?"
    r"\b(?:has|have|had)\s+no\b(?:(?![,;.!?]).){0,120}?"
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


def quoted_assertion_is_explicitly_rejected(
    text: str, offset: int, end: int
) -> bool:
    """Bind every claim inside a quotation to a rejection after its close."""

    line_start = text.rfind("\n", 0, offset) + 1
    line_end = text.find("\n", end)
    if line_end < 0:
        line_end = len(text)
    candidates: list[tuple[int, int]] = []
    for opening_mark, closing_mark in (("\"", "\""), ("“", "”"), ("‘", "’")):
        opening = text.rfind(opening_mark, line_start, offset + 1)
        if opening < 0:
            continue
        closing = text.find(closing_mark, max(end, opening + 1), line_end)
        if closing >= 0:
            candidates.append((opening, closing))
    if not candidates:
        return False
    opening, closing = max(candidates, key=lambda bounds: bounds[0])
    frame = text[line_start:opening]
    tail = text[closing + 1 : line_end]
    if NEGATED_QUOTED_REJECTION_FRAME.search(frame):
        return False
    if QUOTED_REJECTION_REVERSAL.search(tail):
        return False
    if QUOTED_ASSERTION_REJECTION_PREFIX.search(frame):
        return True
    return bool(QUOTED_ASSERTION_REJECTION_TAIL.match(tail))


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
        or quoted_assertion_is_explicitly_rejected(
            text, offset, relation_end
        )
    )


def claim_is_quoted_nonassertion(
    text: str, offset: int, end: int | None = None
) -> bool:
    """Recognize quoted examples and archived simulations as non-current prose."""

    relation_end = end if end is not None else offset + 1
    sentence_start, sentence_end = claim_scope_bounds(text, offset)
    sentence = text[sentence_start:sentence_end]
    local_offset = offset - sentence_start
    local_end = relation_end - sentence_start

    opening_positions = [sentence.rfind(mark, 0, local_offset + 1) for mark in ('"', "“", "‘")]
    opening = max(opening_positions)
    if opening >= 0:
        closing_positions = [
            position
            for mark in ('"', "”", "’")
            if (position := sentence.find(mark, local_end)) >= 0
        ]
        if closing_positions:
            closing = min(closing_positions)
            before = sentence[:opening]
            after = sentence[closing + 1 :]
            documentary_intro = re.search(
                r"\b(?:archive(?:d)?|documentation|docs?|example|fixture|manual|"
                r"mockup|sample|simulation|test)\b(?:(?![.!?;]).){0,100}?\b"
                r"(?:contains?|depicts?|documents?|quotes?|records?|says?|shows?)\b",
                before,
                re.IGNORECASE,
            )
            documentary_suffix = re.match(
                r"^\s*(?:is|was|remains?|serves?\s+as|appears?\s+as|"
                r"illustrates?)\s+(?:an?\s+|the\s+)?(?:archived\s+)?"
                r"(?:counterexample|example|fixture|hypothetical|mockup|sample|"
                r"simulation|test\s+case)\b",
                after,
                re.IGNORECASE,
            )
            if documentary_intro or documentary_suffix:
                return True

    prefix = sentence[:local_offset]
    return bool(
        re.match(
            r"^\s*(?:in|within|for|during)\s+(?:an?\s+|the\s+)?"
            r"(?:archived?|documentation|example|fixture|historical|hypothetical|"
            r"mock|sample|simulation|test)\b(?:(?![,;.!?]).){0,100},\s*$",
            prefix,
            re.IGNORECASE | re.DOTALL,
        )
    )


def claim_is_noncurrent(text: str, offset: int, end: int | None = None) -> bool:
    relation_end = end if end is not None else offset + 1
    sentence_start, _ = claim_scope_bounds(text, offset)
    assertion_start, assertion_end = claim_assertion_bounds(
        text, offset, relation_end
    )
    prefix = claim_relation_scope(text, offset, relation_end)
    prefix = PARENTHETICAL_TEMPORAL.sub(" ", prefix)
    prefix = RELATIVE_TEMPORAL.sub(" ", prefix)
    introduction = text[sentence_start:assertion_start]
    return bool(
        CLAIM_NONCURRENT.search(prefix)
        or CLAIM_HYPOTHETICAL_PREFIX.search(prefix)
        or CLAIM_DOCUMENTARY_PREFIX.search(prefix)
        or CLAIM_DOCUMENTARY_PREFIX.match(introduction)
        or CLAIM_ARCHIVED_DOCUMENTATION_PREFIX.search(prefix)
        or CLAIM_ARCHIVED_DOCUMENTATION_PREFIX.match(introduction)
        or CLAIM_ARCHIVED_ATTRIBUTION_PREFIX.search(prefix)
        or CLAIM_ARCHIVED_ATTRIBUTION_PREFIX.match(introduction)
        or INTRODUCTORY_NONCURRENT_SCOPE.match(introduction)
        or CLAIM_NONCURRENT_SUFFIX.match(text[relation_end:assertion_end])
        or claim_is_quoted_nonassertion(text, offset, relation_end)
    )


def provider_capability_claim_is_noncurrent(
    text: str, offset: int, end: int | None = None
) -> bool:
    """Treat permission/current-time modals as live while retaining time gates."""

    relation_end = end if end is not None else offset + 1
    sentence_start, _ = claim_scope_bounds(text, offset)
    assertion_start, assertion_end = claim_assertion_bounds(
        text, offset, relation_end
    )
    prefix = claim_relation_scope(text, offset, relation_end)
    prefix = PARENTHETICAL_TEMPORAL.sub(" ", prefix)
    prefix = RELATIVE_TEMPORAL.sub(" ", prefix)
    assertion = text[assertion_start:assertion_end]
    permission_modals = (
        r"\b(?:may|could|would|will|might)\b"
        if re.search(r"\b(?:now|currently|today|presently)\b", assertion, re.IGNORECASE)
        else r"\bmay\b"
    )
    prefix = re.sub(permission_modals, " ", prefix, flags=re.IGNORECASE)
    introduction = text[sentence_start:assertion_start]
    return bool(
        CLAIM_NONCURRENT.search(prefix)
        or CLAIM_HYPOTHETICAL_PREFIX.search(prefix)
        or CLAIM_DOCUMENTARY_PREFIX.search(prefix)
        or CLAIM_DOCUMENTARY_PREFIX.match(introduction)
        or CLAIM_ARCHIVED_DOCUMENTATION_PREFIX.search(prefix)
        or CLAIM_ARCHIVED_DOCUMENTATION_PREFIX.match(introduction)
        or CLAIM_ARCHIVED_ATTRIBUTION_PREFIX.search(prefix)
        or CLAIM_ARCHIVED_ATTRIBUTION_PREFIX.match(introduction)
        or INTRODUCTORY_NONCURRENT_SCOPE.match(introduction)
        or CLAIM_NONCURRENT_SUFFIX.match(text[relation_end:assertion_end])
        or claim_is_quoted_nonassertion(text, offset, relation_end)
    )


def provider_capability_claim_is_current_semantic(
    text: str, offset: int, end: int | None = None
) -> bool:
    return not provider_capability_claim_is_noncurrent(
        text, offset, end
    ) and not claim_is_explicitly_rejected(text, offset, end)


def provider_capability_claim_is_current_affirmative(
    text: str, offset: int, end: int | None = None
) -> bool:
    return not provider_capability_claim_is_noncurrent(
        text, offset, end
    ) and not claim_is_denied(text, offset, end)


def provider_draft_claim_is_tools_list_gated(
    text: str, offset: int, end: int | None = None
) -> bool:
    """Require an exact-name positive ``tools/list`` condition for hosted create."""

    relation_end = end if end is not None else offset + 1
    # Markdown source wraps prose across physical lines. Bound the logical
    # sentence by punctuation/row separators so a harmless line wrap cannot
    # split the exact tool name from its tools/list condition.
    prior_boundaries = [text.rfind(marker, 0, offset) for marker in (".", "!", "?", ";", "|")]
    paragraph_start = text.rfind("\n\n", 0, offset)
    prior_boundaries.append(paragraph_start + 1 if paragraph_start >= 0 else -1)
    sentence_start = max(prior_boundaries) + 1
    following = [
        position
        for marker in (".", "!", "?", ";", "|")
        if (position := text.find(marker, offset)) >= 0
    ]
    paragraph_end = text.find("\n\n", offset)
    if paragraph_end >= 0:
        following.append(paragraph_end)
    sentence_end = min(following, default=len(text))
    sentence = text[sentence_start:sentence_end]
    if PROVIDER_DRAFT_TOOL_UNLESS_ABSENT_GATE.search(sentence):
        return True
    if PROVIDER_DRAFT_TOOL_REQUIRED_PRESENCE_GATE.search(sentence):
        return True
    if PROVIDER_DRAFT_TOOL_LIST_BYPASS.search(sentence):
        return False
    if PROVIDER_DRAFT_TOOL_POSITIVE_LIST_GATE.search(sentence):
        return True
    if PROVIDER_DRAFT_TOOL_WHEN_LISTED_GATE.search(sentence):
        return True

    # Permit a concise anaphoric "when listed" immediately after the exact
    # positive gate, but never let a generic tools/list authority anchor mask
    # an unconditional capability claim.
    assertion = text[sentence_start : min(sentence_end, relation_end + 220)]
    if not re.search(r"\bwhen\s+listed\b", assertion, re.IGNORECASE):
        return False
    prior = text[max(0, sentence_start - 360) : sentence_start]
    return bool(
        PROVIDER_DRAFT_TOOL_POSITIVE_LIST_GATE.search(prior)
        or (
            re.search(CANONICAL_PROVIDER_DRAFT_TOOL_GATE, prior, re.IGNORECASE)
            and re.search(AUTHENTICATED_TOOLS_LIST, prior, re.IGNORECASE)
            and re.search(r"\bonly\s+when\b", prior, re.IGNORECASE)
            and not PROVIDER_DRAFT_TOOL_LIST_BYPASS.search(prior)
        )
    )


def claim_is_denied(text: str, offset: int, end: int | None = None) -> bool:
    if claim_is_explicitly_rejected(text, offset, end):
        return True
    scope = claim_relation_scope(text, offset, end)
    scope = INCIDENTAL_NEGATIVE_MODIFIER.sub(" ", scope)
    scope = RELATIVE_NEGATIVE_MODIFIER.sub(" ", scope)
    if re.search(r"\bneither\b(?:(?![.!?]).){0,160}?\bnor\b", scope, re.I):
        return True
    return sum(1 for _ in CLAIM_DENIAL.finditer(scope)) % 2 == 1


def claim_has_affirmative_negation_parity(
    text: str, offset: int, end: int | None = None
) -> bool:
    """Evaluate claims whose grammar deliberately encodes an absence denial."""

    if claim_is_noncurrent(text, offset, end) or claim_is_explicitly_rejected(
        text, offset, end
    ):
        return False
    scope = claim_relation_scope(text, offset, end)
    scope = INCIDENTAL_NEGATIVE_MODIFIER.sub(" ", scope)
    scope = RELATIVE_NEGATIVE_MODIFIER.sub(" ", scope)
    denials = sum(1 for _ in CLAIM_DENIAL.finditer(scope))
    denials += sum(1 for _ in ABSENCE_DENIAL.finditer(scope))
    return denials % 2 == 0


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
    """Normalize rendered, visible prose before checking required anchors."""
    rendered = rendered_markdown(text)
    material = "\n".join(
        (rendered.prose, *(link.destination for link in rendered.links))
    )
    return " ".join(material.casefold().split())


def status_prose(text: str) -> str:
    """Blank non-prose Markdown while preserving offsets and line numbers."""

    def blank(match: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    visible_source = re.sub(r"<!--.*?-->", blank, text, flags=re.DOTALL)
    visible_source = re.sub(
        r"(?ms)^(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^(?P=fence)[ \t]*$",
        blank,
        visible_source,
    )
    return re.sub(
        r"(?m)^>\s?",
        lambda match: " " * len(match.group(0)),
        visible_source,
    )


def count_value(token: str) -> int:
    folded = token.casefold()
    return int(folded) if folded.isdigit() else COUNT_VALUES[folded]


@dataclass(frozen=True)
class TypedToolCount:
    start: int
    end: int
    value: int
    exact: bool
    qualifier: str
    ordinal_total: bool = False


TOOL_ORDINAL_VALUES = {
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}


def typed_tool_counts(text: str, start: int, end: int) -> list[TypedToolCount]:
    """Parse typed tool counts, including aggregates and multiplicative units."""

    atoms: list[TypedToolCount] = []
    for match in TOOL_TYPED_COUNT.finditer(text, start, end):
        if TOOL_COUNT_META_DESCRIPTOR.search(match.group(0)):
            continue
        qualifier = " ".join(
            (
                match.group("qualifier")
                or match.group("post_qualifier")
                or ""
            ).casefold().split()
        )
        exact = qualifier in {"", "exactly", "only", "a total of", "an total of", "total of"}
        atom_start = match.start()
        range_prefix_text = text[max(start, match.start() - 48) : match.start()]
        range_prefix = re.search(
            rf"(?:\bbetween\s+{TOOL_COUNT_TOKEN}\s+and\s+|"
            rf"\b{TOOL_COUNT_TOKEN}\s+(?:or|to|through)\s+|"
            rf"\b{TOOL_COUNT_TOKEN}\s*[-–—]\s*)$",
            range_prefix_text,
            re.IGNORECASE,
        )
        if range_prefix:
            atom_start = max(start, match.start() - 48) + range_prefix.start()
            qualifier = "range"
            exact = False
        ordinal_total = False
        if match.group("math_left"):
            left = count_value(match.group("math_left"))
            right = count_value(match.group("math_right"))
            value = (
                left + right
                if match.group("math_operator") == "+"
                else left * right
            )
        elif match.group("compound_unit"):
            multiplier = count_value(match.group("compound_multiplier") or "one")
            unit = match.group("compound_unit").casefold().removesuffix("s")
            value = multiplier * COUNT_VALUES[unit]
        elif match.group("ordinal"):
            value = TOOL_ORDINAL_VALUES[match.group("ordinal").casefold()]
            ordinal_total = True
        else:
            value = count_value(match.group("plain"))
        atoms.append(
            TypedToolCount(
                start=atom_start,
                end=match.end(),
                value=value,
                exact=exact,
                qualifier=qualifier,
                ordinal_total=ordinal_total,
            )
        )

    aggregates: list[TypedToolCount] = []
    index = 0
    while index < len(atoms):
        aggregate = atoms[index]
        index += 1
        while index < len(atoms) and TOOL_COUNT_CONNECTOR.fullmatch(
            text[aggregate.end : atoms[index].start]
        ):
            following = atoms[index]
            if following.ordinal_total:
                value = max(aggregate.value, following.value)
                ordinal_total = True
            elif aggregate.ordinal_total:
                value = aggregate.value + following.value
                ordinal_total = True
            else:
                value = aggregate.value + following.value
                ordinal_total = False
            aggregate = TypedToolCount(
                start=aggregate.start,
                end=following.end,
                value=value,
                exact=aggregate.exact and following.exact,
                qualifier=aggregate.qualifier or following.qualifier,
                ordinal_total=ordinal_total,
            )
            index += 1
        aggregates.append(aggregate)
    return aggregates


def catalog_count_value(token: str) -> int:
    """Resolve plain and multiplicative catalog counts such as ``two pairs``."""
    folded = " ".join(token.casefold().split())
    compound = re.fullmatch(
        rf"(?P<multiplier>{TOOL_COUNT_TOKEN})\s+"
        r"(?P<unit>pairs?|couples?|trios?|dozens?)",
        folded,
        re.IGNORECASE,
    )
    if not compound:
        return count_value(folded)
    unit = compound.group("unit").removesuffix("s")
    return count_value(compound.group("multiplier")) * COUNT_VALUES[unit]


def rich_catalog_count_value(phrase: str) -> tuple[int, str]:
    """Resolve qualified, set-based, and symbolic catalog counts."""

    folded = " ".join(phrase.casefold().split())
    qualifier_match = re.match(rf"(?P<qualifier>{CATALOG_RICH_QUALIFIER})\s+", folded)
    qualifier = ""
    if qualifier_match:
        qualifier = qualifier_match.group("qualifier")
        folded = folded[qualifier_match.end() :]

    def bare_count_value(token: str) -> int:
        bare = re.sub(r"^(?:an?|the)\s+", "", token.strip())
        return catalog_count_value(bare)

    between_range = re.fullmatch(
        rf"between\s+(?P<lower>{CATALOG_ARTICLED_COUNT})\s+and\s+"
        rf"(?P<upper>{CATALOG_ARTICLED_COUNT})",
        folded,
    )
    inline_range = re.fullmatch(
        rf"(?P<lower>{CATALOG_ARTICLED_COUNT})\s+"
        rf"(?:to|through|or|[-–—])\s+"
        rf"(?P<upper>{CATALOG_ARTICLED_COUNT})",
        folded,
    )
    range_match = between_range or inline_range
    if range_match:
        value = min(
            bare_count_value(range_match.group("lower")),
            bare_count_value(range_match.group("upper")),
        )
        qualifier = qualifier or "range starting at"
        return value, qualifier

    post_bound = re.fullmatch(
        rf"(?P<count>{CATALOG_ARTICLED_COUNT})\s+"
        rf"(?P<qualifier>or\s+(?:more|fewer|less))",
        folded,
    )
    if post_bound:
        return (
            bare_count_value(post_bound.group("count")),
            qualifier or post_bound.group("qualifier"),
        )

    multiplication = re.fullmatch(
        rf"(?P<left>{TOOL_COUNT_TOKEN})\s*(?:x|×|\*)\s*"
        rf"(?P<right>{TOOL_COUNT_TOKEN})",
        folded,
    )
    if multiplication:
        value = count_value(multiplication.group("left")) * count_value(
            multiplication.group("right")
        )
    else:
        word_multiplier = re.fullmatch(
            rf"(?P<multiplier>twice|thrice)\s+"
            rf"(?P<count>{CATALOG_ARTICLED_COUNT})",
            folded,
        )
        if word_multiplier:
            multiplier = 2 if word_multiplier.group("multiplier") == "twice" else 3
            return multiplier * bare_count_value(word_multiplier.group("count")), qualifier

        grouped = re.fullmatch(
            rf"(?P<outer>{TOOL_COUNT_TOKEN})\s+"
            rf"(?:sets?|groups?|batches?)\s+of\s+"
            rf"(?P<inner>{TOOL_COUNT_TOKEN})",
            folded,
        )
        grouped_each = re.fullmatch(
            rf"(?P<outer>{TOOL_COUNT_TOKEN})\s+"
            rf"(?:sets?|groups?|batches?)\s*,?\s+each\s+"
            rf"(?:with|containing|holding)\s+(?P<inner>{TOOL_COUNT_TOKEN})",
            folded,
        )
        grouped = grouped or grouped_each
        if grouped:
            value = count_value(grouped.group("outer")) * count_value(
                grouped.group("inner")
            )
        else:
            if re.fullmatch(r"half\s+(?:a\s+)?dozen", folded):
                return 6, qualifier

            additive = re.fullmatch(
                rf"{CATALOG_ARTICLED_COUNT}(?:\s+(?:and|plus)\s+"
                rf"{CATALOG_ARTICLED_COUNT})+",
                folded,
            )
            if additive:
                atoms = re.split(r"\s+(?:and|plus)\s+", folded)
                return sum(bare_count_value(atom) for atom in atoms), qualifier

            single_set = re.fullmatch(
                rf"(?:an?\s+)?(?:sets?|groups?|batches?)\s+of\s+"
                rf"(?P<inner>{TOOL_COUNT_TOKEN})",
                folded,
            )
            value = (
                count_value(single_set.group("inner"))
                if single_set
                else bare_count_value(folded)
            )

    return value, qualifier


def named_capability_items(inventory: str) -> tuple[str, ...]:
    """Split a current named capability inventory without crossing into clauses."""

    if NAMED_CAPABILITY_META_LEAD.match(inventory):
        return ()
    pieces = re.split(
        r"\s*,\s*(?:(?:and|plus)\s+)?|"
        r"\s+(?:and|as\s+well\s+as|plus)\s+",
        inventory,
        flags=re.IGNORECASE,
    )
    items: list[str] = []
    for piece in pieces:
        item = re.sub(r"^\s*(?:also|both|either)\s+", "", piece, flags=re.I)
        item = item.strip(" ,:—–-")
        if (
            not item
            or NAMED_CAPABILITY_DENIED_ITEM.match(item)
            or NAMED_CAPABILITY_MODIFIER_ITEM.match(item)
        ):
            continue
        if NAMED_CAPABILITY_FINITE_CLAUSE.search(item):
            continue
        if len(re.findall(r"[A-Za-z0-9]+", item)) > 12:
            continue
        items.append(item)
    return tuple(items)


def named_catalog_inventory_count(inventory: str) -> int:
    """Count named live catalog items while preserving zero-compatible bounds."""

    if CATALOG_ZERO_COMPATIBLE_NAMED_BOUND.search(
        inventory
    ) or CATALOG_COUNTED_INVENTORY_LEAD.match(inventory):
        return 0
    if re.match(r"^\s*(?:neither|no|not|nothing|without|zero)\b", inventory, re.I):
        return 0
    pieces = re.split(
        r"\s*,\s*(?:(?:and|or|plus)\s+)?|"
        r"\s+(?:and|as\s+well\s+as|or|plus)\s+",
        inventory,
        flags=re.IGNORECASE,
    )
    count = 0
    for piece in pieces:
        item = piece.strip(" ,:—–-")
        if not item or re.match(
            r"^\s*(?:neither|no|not|nothing|without|zero)\b", item, re.I
        ):
            continue
        if CATALOG_NAMED_META_ITEM.search(item):
            continue
        if NAMED_CAPABILITY_FINITE_CLAUSE.search(item):
            continue
        if CATALOG_NAMED_ITEM_PHRASE.search(item):
            count += 1
    if count:
        return count
    if not CATALOG_NAMED_META_ITEM.search(inventory):
        shared = CATALOG_SHARED_NOUN_COORDINATION.search(inventory)
        if shared:
            return 2
    return 0


def role_wallet_is_anaphoric_to_surface(scope: str) -> bool:
    """Return true when a later role wallet refers back to the MCP surface."""
    assignments: list[tuple[re.Match[str], set[str]]] = []
    for assignment_pattern in (
        HOSTED_ROLE_ASSIGNMENT,
        HOSTED_ROLE_DUTY_ASSIGNMENT,
        HOSTED_ROLE_CAPACITY_ASSIGNMENT,
        HOSTED_ROLE_DUTY_OF_ASSIGNMENT,
    ):
        for match in assignment_pattern.finditer(scope):
            before_assignment = scope[: match.start()]
            if MCP_CLAIM_HARD_BOUNDARY.search(
                before_assignment
            ) and not HOSTED_ANAPHORIC_REFERENCE.search(before_assignment):
                continue
            phrase = match.group("role_phrase").casefold()
            roles = {phrase, *phrase.split()}
            assignments.append((match, roles))
    if not assignments:
        return False
    for pattern in (
        ROLE_WALLET_REFERENCE,
        ROLE_QUALIFIED_WALLET_REFERENCE,
        ROLE_SIGNER_REFERENCE,
    ):
        for match in pattern.finditer(scope):
            prefix = scope[max(0, match.start() - 40) : match.start()]
            suffix = scope[match.end() : match.end() + 100]
            if DISTINCT_ACTOR_PREFIX.search(prefix) or DISTINCT_ACTOR_SUFFIX.match(
                suffix
            ):
                continue
            referenced_role = match.group("role").casefold()
            for assignment, assigned_roles in assignments:
                if assignment.end() > match.start() or referenced_role not in assigned_roles:
                    continue
                intervening = scope[assignment.end() : match.start()]
                if INTERVENING_ROLE_ACTOR.search(intervening):
                    continue
                return True
    for match in GENERIC_ROLE_SIGNER_REFERENCE.finditer(scope):
        prefix = scope[max(0, match.start() - 60) : match.start()]
        suffix = scope[match.end() : match.end() + 100]
        if DISTINCT_ACTOR_PREFIX.search(prefix) or DISTINCT_ACTOR_SUFFIX.match(suffix):
            continue
        if any(assignment.end() <= match.start() for assignment, _ in assignments):
            return True
    return False


def published_service_count_is_catalog_attributed(
    text: str, claim: re.Match[str]
) -> bool:
    """Keep a generic count from inheriting Stele context across another actor."""
    assertion_start, assertion_end = claim_assertion_bounds(
        text, claim.start(), claim.end()
    )
    before = text[assertion_start : claim.start()]
    after = text[claim.end() : assertion_end]
    reverse = CATALOG_PUBLISHED_REVERSE_LOCATION.match(after)
    if reverse:
        return True
    surfaces = list(CATALOG_COUNT_SURFACE.finditer(before))
    if not surfaces:
        if not CATALOG_COUNT_ANAPHORIC_PREFIX.match(before):
            return False
        prior_scope = text[max(0, assertion_start - 240) : assertion_start]
        prior_surfaces = list(CATALOG_COUNT_SURFACE.finditer(prior_scope))
        if not prior_surfaces:
            return False
        return not INTERVENING_UNRELATED_ASSERTION_SUBJECT.search(
            prior_scope[prior_surfaces[-1].end() :]
        )
    intervening = before[surfaces[-1].end() :]
    return not INTERVENING_UNRELATED_ASSERTION_SUBJECT.search(intervening)


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


def provider_studio_link_is_documentary(link: RenderedLink) -> bool:
    """Distinguish a product destination from documentation about the product."""

    context = link.context or link.label
    label = " ".join(unescape(link.label).split())
    if STUDIO_DOCUMENTARY_CURRENT_VETO.search(label):
        return False
    if re.search(
        r"\b(?:documentation|docs?|guide|manual|reference|examples?|"
        r"test\s+fixtures?|archive)\b",
        label,
        re.IGNORECASE,
    ):
        return True
    offset = min(max(0, link.context_offset), len(context))
    start, end = claim_assertion_bounds(context, offset, offset + len(label))
    assertion = context[start:end]
    label_end = min(offset + len(label), len(context))
    if STUDIO_DOCUMENTARY_CURRENT_VETO.search(assertion):
        return False
    return bool(
        STUDIO_DOCUMENTATION_CONTEXT.search(assertion)
        or STUDIO_DOCUMENTARY_LINK_PREFIX.search(context[start:offset])
        or STUDIO_DOCUMENTARY_LINK_SUFFIX.match(context[label_end:end])
    )


def provider_studio_action_label(
    label: str, scope: str, offset: int | None = None
) -> bool:
    """Bind an actionable draft-link label to Provider Studio in its assertion."""

    explicit = STUDIO_DRAFT_ACTION_LABEL.search(label)
    contextual = STUDIO_CONTEXTUAL_DRAFT_ACTION_LABEL.search(label)
    if not explicit and not contextual:
        return False
    label_offset = offset
    if label_offset is None:
        label_offset = scope.find(label)
        if label_offset < 0:
            label_offset = len(scope)
    sentence_start, sentence_end = claim_scope_bounds(scope, label_offset)
    local = scope[sentence_start:sentence_end]
    if not provider_studio_context_reaches_offset(scope, label_offset):
        return False
    return bool(explicit or STUDIO_PROVIDER_ACTOR_CONTEXT.search(local))


def provider_studio_context_reaches_offset(scope: str, offset: int) -> bool:
    """Keep a Studio product relation from crossing into another actor's clause."""

    sentence_start, sentence_end = claim_scope_bounds(scope, offset)
    prefix = scope[sentence_start:offset]
    providers = list(re.finditer(r"\bProvider\s+Studio\b", prefix, re.IGNORECASE))
    if providers:
        return not INTERVENING_UNRELATED_ASSERTION_SUBJECT.search(
            prefix[providers[-1].end() :]
        )
    suffix = scope[offset:sentence_end]
    following = re.search(r"\bProvider\s+Studio\b", suffix, re.IGNORECASE)
    if not following:
        return False
    return not INTERVENING_UNRELATED_ASSERTION_SUBJECT.search(
        suffix[: following.start()]
    )


def adjacent_clause_after(scope: str, end: int) -> str:
    """Return only the structurally adjacent clause after a sentence boundary."""

    cursor = end
    while cursor < len(scope) and scope[cursor] in " \t\r\n.!?;:|":
        cursor += 1
    if cursor >= len(scope):
        return ""
    start, adjacent_end = claim_scope_bounds(scope, cursor)
    return scope[max(start, cursor):adjacent_end]


def provider_studio_link_is_reactivated(
    context: str, label_end: int, sentence_end: int
) -> bool:
    """Bind current return language only within this or the next actor-local clause."""

    suffix = context[label_end:sentence_end]
    if STUDIO_DIRECT_CURRENT_LINK_SUFFIX.match(suffix):
        return True
    same_clause = STUDIO_CURRENT_REACTIVATION.search(suffix)
    if same_clause and not INTERVENING_UNRELATED_ASSERTION_SUBJECT.search(
        suffix[: same_clause.start()]
    ):
        return True
    general_return = STUDIO_GENERAL_CURRENT_RETURN.search(suffix)
    if general_return and not INTERVENING_UNRELATED_ASSERTION_SUBJECT.search(
        suffix[: general_return.start()]
    ):
        return True
    restored_return = STUDIO_RESTORED_CURRENT_RETURN.search(suffix)
    if restored_return and not INTERVENING_UNRELATED_ASSERTION_SUBJECT.search(
        suffix[: restored_return.start()]
    ):
        return True
    if INTERVENING_UNRELATED_ASSERTION_SUBJECT.search(suffix):
        return False
    adjacent = adjacent_clause_after(context, sentence_end)
    return bool(
        STUDIO_ADJACENT_CURRENT_REACTIVATION.match(adjacent)
        or STUDIO_GENERAL_CURRENT_RETURN.match(adjacent)
        or STUDIO_RESTORED_CURRENT_RETURN.match(adjacent)
    )


def provider_studio_link_is_historical(
    context: str, offset: int, label_end: int
) -> bool:
    """Classify the complete actor-local proposition containing a Studio link."""

    assertion_start, assertion_end = claim_assertion_bounds(
        context, offset, label_end
    )
    assertion = context[assertion_start:assertion_end]
    if re.search(
        r"\b(?:formerly|previously|had(?:\s+been)?|used\s+to)\b",
        assertion,
        re.IGNORECASE,
    ):
        return True
    return bool(
        STUDIO_HISTORICAL_DATE.search(assertion)
        and STUDIO_HISTORICAL_PREDICATE.search(assertion)
    )


def prior_current_studio_assertion_reaches_link(context: str, offset: int) -> bool:
    """Bind a generic Studio action to a nearby actor-local current assertion."""

    prefix_start = max(0, offset - 360)
    prefix = context[prefix_start:offset]
    currents = list(STUDIO_CURRENT_PRODUCT_ASSERTION.finditer(prefix))
    if not currents:
        return False
    current = currents[-1]
    absolute_start = prefix_start + current.start()
    absolute_end = prefix_start + current.end()
    if not claim_is_current_affirmative(context, absolute_start, absolute_end):
        return False
    intervening = context[absolute_end:offset]
    return not (
        INTERVENING_UNRELATED_ASSERTION_SUBJECT.search(intervening)
        or STUDIO_DISTINCT_PRODUCT_ACTOR.search(intervening)
        or claim_is_explicitly_rejected(
            context, absolute_start, absolute_end
        )
    )


def provider_studio_link_is_current_product(link: RenderedLink) -> bool:
    """Return whether a rendered link is an actionable current Studio link."""

    if provider_studio_link_is_documentary(link):
        return False
    context = link.context or link.label
    label = " ".join(unescape(link.label).split())
    structural_studio = bool(
        re.search(
            r"\bProvider\s+Studio\b",
            link.structural_context,
            re.IGNORECASE,
        )
    )
    offset = min(max(0, link.context_offset), len(context))
    label_end = offset + len(label)
    sentence_start, sentence_end = claim_scope_bounds(context, offset)
    suffix = context[label_end:sentence_end]
    reactivated = provider_studio_link_is_reactivated(
        context, label_end, sentence_end
    )
    structural_noncurrent = bool(
        CLAIM_NONCURRENT.search(link.structural_context)
    )
    block_context = context
    if link.structural_context and context.startswith(
        f"{link.structural_context}: "
    ):
        block_context = context[len(link.structural_context) + 2 :]
    structural_current_override = bool(
        structural_noncurrent
        and re.search(
        r"\b(?:again|currently|now|presently|today)\b|"
        r"\b(?:is|remains?)\s+(?:active|available|current|live|operational|"
        r"released)\b",
        block_context,
        re.IGNORECASE,
        )
    )
    if structural_current_override:
        structural_noncurrent = False
        reactivated = True
    historical_suffix = STUDIO_HISTORICAL_LINK_SUFFIX.match(
        suffix
    )
    historical_lifecycle = STUDIO_HISTORICAL_LIFECYCLE_SUFFIX.match(
        suffix
    )
    historical_record = STUDIO_HISTORICAL_RECORD_SUFFIX.match(suffix)
    if historical_record and re.search(
        r"\b(?:not|never)\b(?:(?![.!?;]).){0,40}?\b(?:decommissioned|removed|"
        r"retired|shut\s+down|sunset|withdrawn|decommissioning|removal|"
        r"retirement|shutdown|withdrawal)\b",
        historical_record.group(0),
        re.IGNORECASE | re.DOTALL,
    ):
        historical_record = None
    historical_assertion = provider_studio_link_is_historical(
        context, offset, label_end
    )
    if (
        claim_is_noncurrent(context, offset, label_end)
        or historical_suffix
        or historical_lifecycle
        or historical_record
        or historical_assertion
        or structural_noncurrent
    ) and not reactivated:
        return False
    if claim_is_explicitly_rejected(
        context, offset, label_end
    ) or STUDIO_LINK_DENIAL_PREFIX.search(context[sentence_start:offset]):
        return False
    if re.search(r"\bProvider\s+Studio\b", label, re.IGNORECASE):
        return True
    if re.fullmatch(r"Studio", label, re.IGNORECASE) and re.search(
        r"\bprovider(?:-listing)?\s+drafts?\b", context, re.IGNORECASE
    ):
        return True
    if re.fullmatch(
        r"(?:https?://)?stele\.monolythium\.com/studio/?", label, re.IGNORECASE
    ):
        return True
    if provider_studio_action_label(label, context, offset):
        return True
    if structural_studio and (
        STUDIO_DRAFT_ACTION_LABEL.search(label)
        or STUDIO_CONTEXTUAL_DRAFT_ACTION_LABEL.search(label)
    ):
        return True
    if STUDIO_GENERIC_PRODUCT_ACTION_LABEL.fullmatch(label) and (
        provider_studio_context_reaches_offset(context, offset)
        or prior_current_studio_assertion_reaches_link(context, offset)
        or structural_studio
    ):
        return True
    if STUDIO_CONTEXTUAL_PRODUCT_ACTION_LABEL.fullmatch(label) and (
        provider_studio_context_reaches_offset(context, offset)
        or prior_current_studio_assertion_reaches_link(context, offset)
        or structural_studio
    ):
        return True
    label_offset = offset
    nearby = context[
        max(sentence_start, label_offset - 180) : min(
            sentence_end, label_offset + len(label) + 180
        )
    ]
    return bool(
        provider_studio_context_reaches_offset(context, offset)
        and STUDIO_PRODUCT_ACTION.search(nearby)
    )


def has_canonical_provider_studio_link(text: str) -> bool:
    """Require a visible, resolved canonical Studio product link."""

    return any(
        link.destination == CANONICAL_STUDIO_URL
        and provider_studio_link_is_current_product(link)
        for link in rendered_markdown(text).links
    )


def provider_studio_url_violations(text: str) -> list[int]:
    """Reject current product destinations that are not the exact public Studio URL."""

    def current_product_scope(
        offset: int,
        end: int,
        destination_span: tuple[int, int] | None = None,
    ) -> tuple[str, bool, bool]:
        scope = claim_assertion_scope(text, offset, end)
        if STUDIO_RAW_DESTINATION_DENIAL.search(scope):
            return scope, False, False
        masked = text
        if destination_span is not None:
            mask_start, mask_end = destination_span
            masked = (
                f"{text[:mask_start]}"
                f"{'x' * (mask_end - mask_start)}"
                f"{text[mask_end:]}"
            )
        if claim_is_noncurrent(masked, offset, end) or claim_is_denied(
            masked, offset, end
        ):
            return scope, False, False
        if STUDIO_DOCUMENTATION_CONTEXT.search(scope):
            return scope, False, False
        provider_context = provider_studio_context_reaches_offset(text, offset)
        studio_draft_context = bool(
            re.search(r"\bStudio\b", scope, re.IGNORECASE)
            and re.search(
                r"\bprovider(?:-listing)?\s+drafts?\b", scope, re.IGNORECASE
            )
        )
        return scope, provider_context or studio_draft_context, True

    def product_label(label: str, scope: str) -> bool:
        if re.search(r"\b(?:documentation|docs?|guide|reference)\b", label, re.I):
            return False
        if re.search(r"\bProvider\s+Studio\b", label, re.IGNORECASE):
            return True
        if provider_studio_action_label(label, scope):
            return True
        if STUDIO_GENERIC_PRODUCT_ACTION_LABEL.fullmatch(label) and re.search(
            r"\bProvider\s+Studio\b", scope, re.IGNORECASE
        ):
            return True
        return bool(
            re.fullmatch(r"\s*Studio\s*", label, re.IGNORECASE)
            and re.search(r"\bprovider(?:-listing)?\s+drafts?\b", scope, re.I)
        )

    violations: list[int] = [
        0
        for link in rendered_markdown(text).links
        if provider_studio_link_is_current_product(link)
        and link.destination != CANONICAL_STUDIO_URL
    ]
    linked_spans: list[tuple[int, int]] = []
    html_closing_tag_spans = [
        match.span() for match in HTML_CLOSING_TAG.finditer(text)
    ]
    for match in HTML_ANCHOR_LINK.finditer(text):
        group = (
            "quoted_destination"
            if match.group("quoted_destination") is not None
            else "bare_destination"
        )
        linked_spans.append(match.span(group))
        label = unescape(HTML_TAG.sub(" ", match.group("label")))
        paragraph_start = text.rfind("\n\n", 0, match.start())
        paragraph_start = paragraph_start + 2 if paragraph_start >= 0 else 0
        paragraph_end = text.find("\n\n", match.end())
        if paragraph_end < 0:
            paragraph_end = len(text)
        scope = text[paragraph_start:paragraph_end]
        rendered_scope = rendered_markdown(scope)
        current = any(
            rendered_link.label == " ".join(label.split())
            and provider_studio_link_is_current_product(rendered_link)
            for rendered_link in rendered_scope.links
        )
        opening_tag = match.group(0).split(">", 1)[0]
        destination = match.group(group)
        if current and (
            len(HTML_HREF_ATTRIBUTE.findall(opening_tag)) != 1
            or destination != CANONICAL_STUDIO_URL
        ):
            violations.append(match.start(group))

    for match in MARKDOWN_INLINE_LINK.finditer(text):
        linked_spans.append(match.span("destination"))

    reference_definitions: dict[str, list[str]] = {}
    for definition in MARKDOWN_REFERENCE_DEFINITION.finditer(text):
        reference = " ".join(definition.group("reference").casefold().split())
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
        reference_label = match.group("reference") or match.group("label")
        reference = " ".join(reference_label.casefold().split())
        destinations = reference_definitions.get(reference, [])
        # A uniquely resolved reference is dispositioned by the rendered-link
        # classifier above. This raw pass exists only for unresolved or
        # ambiguous references that the renderer cannot classify reliably.
        if len(destinations) != 1:
            violations.append(match.start())

    for match in MARKDOWN_SHORTCUT_REFERENCE_LINK.finditer(text):
        reference = " ".join(match.group("label").casefold().split())
        destinations = reference_definitions.get(reference)
        if destinations is None:
            continue
        scope, relevant_scope, current = current_product_scope(
            match.start(), match.end()
        )
        if not current:
            continue
        relevant = product_label(match.group("label"), scope) or (
            relevant_scope and bool(STUDIO_PRODUCT_ACTION.search(scope))
        )
        if relevant and len(destinations) != 1:
            violations.append(match.start())

    for match in STUDIO_EXPLICIT_DESTINATION.finditer(text):
        destination = match.group("destination")
        mask_span = (
            match.span("destination")
            if STUDIO_RAW_DESTINATION.fullmatch(destination.rstrip(".,;:"))
            else None
        )
        _, _, current = current_product_scope(
            match.start(),
            match.end(),
            mask_span,
        )
        if not current:
            continue
        if destination.startswith("["):
            continue
        candidate = destination.strip("<>\"'").rstrip(".,;:")
        if candidate != CANONICAL_STUDIO_URL:
            violations.append(match.start("destination"))

    for match in STUDIO_RAW_DESTINATION.finditer(text):
        if any(start <= match.start() < end for start, end in linked_spans):
            continue
        if any(
            start <= match.start() < end
            for start, end in html_closing_tag_spans
        ):
            continue
        candidate = match.group("destination").rstrip(".,;:")
        scope, relevant_scope, current = current_product_scope(
            match.start(),
            match.end(),
            match.span("destination"),
        )
        if not current:
            continue
        parsed = urlsplit(candidate)
        decoded_path = decoded_url_path(parsed.path).casefold()
        stele_host = (parsed.hostname or "").casefold() == "stele.monolythium.com"
        studio_like = stele_host and decoded_path.startswith(("/studio", "/provider"))
        html_anchor_attribute = bool(
            HTML_HREF_DESTINATION_PREFIX.search(
                text[max(0, match.start() - 320) : match.start()]
            )
        )
        actionable = relevant_scope and bool(
            STUDIO_PRODUCT_ACTION.search(scope)
            or re.search(r"\bProvider\s+Studio\s*:\s*#", scope, re.IGNORECASE)
            or html_anchor_attribute
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
        # A typed zero such as "zero transaction tools" describes the absence
        # of a forbidden subtype, not the size of the complete MCP surface.
        typed_count_prefix = prose[max(0, claim.start() - 32) : claim.start()]
        if TRANSACTION_TOOL_DESCRIPTOR.search(claim.group(0)) or re.search(
            r"\b(?:transaction|signing|broadcast|submission|settlement|payment|"
            r"economic(?:-write)?)\s+$",
            typed_count_prefix,
            re.IGNORECASE,
        ):
            return
        if claim_is_noncurrent(prose, claim.start(), claim.end()):
            return
        if kind == "hosted":
            if claim_is_current_semantic(prose, claim.start(), claim.end()):
                contradictions.append((claim.start(), HOSTED_DYNAMIC_INVENTORY_ERROR))
            return
        if claim_is_denied(
            prose, claim.start(), claim.end()
        ) or count_claim_is_denied(prose, claim.start()):
            return
        expected = 3
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

    def record_typed_tool_count(kind: str, claim: TypedToolCount) -> None:
        semantic_no_qualifier = claim.qualifier in {
            "no fewer than",
            "no less than",
            "no more than",
        }
        if claim_is_noncurrent(prose, claim.start, claim.end):
            return
        if kind == "hosted":
            if claim_is_current_semantic(prose, claim.start, claim.end):
                contradictions.append((claim.start, HOSTED_DYNAMIC_INVENTORY_ERROR))
            return
        if (
            not semantic_no_qualifier
            and claim_is_denied(prose, claim.start, claim.end)
        ) or (
            not semantic_no_qualifier
            and count_claim_is_denied(prose, claim.start)
        ):
            return
        expected = 3
        if claim.value != expected or not claim.exact:
            qualified = f"{claim.qualifier} " if claim.qualifier else ""
            contradictions.append(
                (
                    claim.start,
                    f"{kind} Stele MCP claims {qualified}{claim.value} tools; "
                    f"expected exactly {expected}",
                )
            )

    def mcp_claim_is_attributed(surface: re.Match[str], claim_start: int) -> bool:
        assertion_start, _ = claim_assertion_bounds(
            prose, surface.start(), surface.end()
        )
        if MCP_META_OBJECT_PREFIX.search(prose[assertion_start : surface.start()]):
            return False
        if claim_start <= surface.end():
            return True
        between = prose[surface.end() : claim_start]
        if MCP_META_OBJECT_AFTER_SURFACE.match(between):
            return False
        if re.fullmatch(r"\s*\|\s*", between):
            return claim_is_current_semantic(prose, surface.start(), surface.end())
        if EXPLICITLY_DISTINCT_WALLET_SUBJECT.search(between):
            return False
        if NESTED_UNRELATED_ASSERTION_SUBJECT.search(between):
            return False
        if MCP_COUNT_ANAPHORIC_PREDICATE.search(between):
            return claim_is_current_semantic(prose, surface.start(), surface.end())
        anaphor = HOSTED_ANAPHORIC_REFERENCE.search(between)
        if anaphor:
            if INTERVENING_UNRELATED_ASSERTION_SUBJECT.search(
                between[: anaphor.start()]
            ):
                return False
            return claim_is_current_semantic(prose, surface.start(), surface.end())
        if role_wallet_is_anaphoric_to_surface(between):
            return claim_is_current_semantic(prose, surface.start(), surface.end())
        return not (
            MCP_CLAIM_HARD_BOUNDARY.search(between)
            or INTERVENING_UNRELATED_ASSERTION_SUBJECT.search(between)
        )

    surfaces = list(STELE_MCP_SURFACE.finditer(prose))
    for index, surface in enumerate(surfaces):
        kind = "hosted" if surface.group("hosted") else "local"
        next_surface = (
            surfaces[index + 1].start() if index + 1 < len(surfaces) else len(prose)
        )
        segment_end = min(next_surface, surface.end() + 600)
        for claim in typed_tool_counts(prose, surface.end(), segment_end):
            if not mcp_claim_is_attributed(surface, claim.start):
                continue
            between = prose[surface.end() : claim.start]
            typed_phrase = prose[claim.start : claim.end]
            if UNRELATED_TOOL_COUNT_SUBJECT.search(
                prose[surface.end() : claim.end]
            ) or TOOL_COUNT_META_CONTEXT.search(between):
                continue
            # Typed transaction counts describe a prohibited subtype, not the
            # complete surface. They are evaluated by the parity gate below.
            if TRANSACTION_TOOL_DESCRIPTOR.search(typed_phrase):
                continue
            record_typed_tool_count(kind, claim)
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
        expected_count = 3
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
            if not claim_is_current_semantic(prose, claim.start(), claim.end()):
                continue
            if kind == "hosted":
                contradictions.append((claim.start(), HOSTED_DYNAMIC_INVENTORY_ERROR))
            elif count_value(count_token) == expected_count:
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
            if (
                kind == "local"
                and exception
                and count_value(exception.group("count")) == expected_count
            ):
                continue
            if claim_is_current_semantic(prose, claim.start(), claim.end()):
                label = (
                    HOSTED_DYNAMIC_INVENTORY_ERROR
                    if kind == "hosted"
                    else f"{kind} Stele MCP denies its required {expected_count}-tool surface"
                )
                contradictions.append((claim.start(), label))

        if kind == "hosted":
            for claim in HOSTED_ORDINAL_TOOL_ABSENCE_AFTER_SURFACE.finditer(
                prose, surface.end(), segment_end
            ):
                if UNRELATED_TOOL_COUNT_SUBJECT.search(
                    prose[surface.end() : claim.end()]
                ):
                    continue
                if not mcp_claim_is_attributed(surface, claim.start()):
                    continue
                if claim_is_current_semantic(prose, claim.start(), claim.end()):
                    contradictions.append(
                        (claim.start(), HOSTED_DYNAMIC_INVENTORY_ERROR)
                    )

        if kind == "hosted":
            segment = prose[surface.start() : segment_end]
            for claim in HOSTED_PROVIDER_DRAFT_CREATE_CAPABILITY.finditer(segment):
                offset = surface.start() + claim.start()
                claim_end = surface.start() + claim.end()
                if not mcp_claim_is_attributed(surface, offset):
                    continue
                if provider_capability_claim_is_current_affirmative(
                    prose, offset, claim_end
                ) and not provider_draft_claim_is_tools_list_gated(
                    prose, offset, claim_end
                ):
                    contradictions.append(
                        (offset, HOSTED_PROVIDER_DRAFT_CONDITIONAL_ERROR)
                    )
            for claim in HOSTED_PROVIDER_DRAFT_NAMED_TOOL_CLAIM.finditer(segment):
                offset = surface.start() + claim.start()
                claim_end = surface.start() + claim.end()
                if not mcp_claim_is_attributed(surface, offset):
                    continue
                if not provider_capability_claim_is_current_affirmative(
                    prose, offset, claim_end
                ):
                    continue
                if claim.group("name") != CANONICAL_PROVIDER_DRAFT_TOOL_NAME:
                    contradictions.append(
                        (offset, HOSTED_PROVIDER_DRAFT_LOOKALIKE_ERROR)
                    )
                elif not provider_draft_claim_is_tools_list_gated(
                    prose, offset, claim_end
                ):
                    contradictions.append(
                        (offset, HOSTED_PROVIDER_DRAFT_CONDITIONAL_ERROR)
                    )
            for claim in MCP_NAMED_CAPABILITY_CLAIM.finditer(segment):
                offset = surface.start() + claim.start()
                if not mcp_claim_is_attributed(surface, offset):
                    continue
                predicate_end = surface.start() + claim.start("inventory")
                if not claim_is_current_affirmative(
                    prose, offset, predicate_end
                ):
                    continue
                items = named_capability_items(claim.group("inventory"))
                if len(items) > 2:
                    contradictions.append(
                        (
                            offset,
                            f"hosted Stele MCP presents {len(items)} unconditional named "
                            "capabilities; authenticated tools/list is authoritative",
                        )
                    )
            for claim in TRANSACTION_TOOL_COUNT.finditer(segment):
                offset = surface.start() + claim.start()
                if not mcp_claim_is_attributed(surface, offset):
                    continue
                # "without a transaction tool" is an ordinary absence claim. A
                # double-negative form is handled explicitly below by
                # HOSTED_DOUBLE_NEGATION_ENABLED instead of treating the typed count
                # as an affirmative capability on its own.
                if COUNT_ABSENCE_PREFIX.search(prose[max(0, offset - 32) : offset]):
                    continue
                if count_value(claim.group("count")) > 0 and claim_is_current_affirmative(
                    prose, offset, surface.start() + claim.end()
                ):
                    contradictions.append(
                        (offset, "hosted Stele MCP claims transaction capability")
                    )
            for label, pattern in HOSTED_TRANSACTION_ENABLED.items():
                for match in pattern.finditer(segment):
                    offset = surface.start() + match.start()
                    if not mcp_claim_is_attributed(surface, offset):
                        continue
                    if TRANSACTION_ZERO_UPPER_BOUND.search(match.group(0)):
                        continue
                    if claim_is_current_affirmative(
                        prose, offset, surface.start() + match.end()
                    ):
                        contradictions.append((offset, label))
            for label, pattern in HOSTED_DOUBLE_NEGATION_ENABLED.items():
                for match in pattern.finditer(segment):
                    offset = surface.start() + match.start()
                    if not mcp_claim_is_attributed(surface, offset):
                        continue
                    if claim_has_affirmative_negation_parity(
                        prose, offset, surface.start() + match.end()
                    ):
                        contradictions.append((offset, label))
            for label, pattern in HOSTED_TRANSACTION_ABSENCE_PARITY.items():
                for match in pattern.finditer(segment):
                    offset = surface.start() + match.start()
                    if not mcp_claim_is_attributed(surface, offset):
                        continue
                    if claim_has_affirmative_negation_parity(
                        prose, offset, surface.start() + match.end()
                    ):
                        contradictions.append((offset, label))
            for label, pattern in HOSTED_TYPED_TRANSACTION_ABSENCE_DENIAL.items():
                for match in pattern.finditer(segment):
                    offset = surface.start() + match.start()
                    if not mcp_claim_is_attributed(surface, offset):
                        continue
                    if claim_is_current_semantic(
                        prose, offset, surface.start() + match.end()
                    ):
                        contradictions.append((offset, label))
            for patterns in (
                HOSTED_STRONG_NEGATION_ENABLED,
                HOSTED_TYPED_TRANSACTION_POSITIVE,
                HOSTED_ZERO_BOUND_COORDINATED_POSITIVE,
            ):
                for label, pattern in patterns.items():
                    for match in pattern.finditer(segment):
                        offset = surface.start() + match.start()
                        if not mcp_claim_is_attributed(surface, offset):
                            continue
                        if claim_is_current_semantic(
                            prose, offset, surface.start() + match.end()
                        ):
                            contradictions.append((offset, label))
            for label, pattern in HOSTED_PROVIDER_DRAFT_AUTHORITY.items():
                for match in pattern.finditer(segment):
                    offset = surface.start() + match.start()
                    if not mcp_claim_is_attributed(surface, offset):
                        continue
                    if provider_capability_claim_is_current_affirmative(
                        prose, offset, surface.start() + match.end()
                    ):
                        contradictions.append((offset, label))

        if kind == "local":
            segment = prose[surface.start() : segment_end]
            for label, pattern in LOCAL_TRANSACTION_ENABLED.items():
                for match in pattern.finditer(segment):
                    offset = surface.start() + match.start()
                    if not mcp_claim_is_attributed(surface, offset):
                        continue
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

    for claim in HOSTED_REVERSE_TOOL_ABSENCE.finditer(prose):
        if claim_is_current_semantic(prose, claim.start(), claim.end()):
            contradictions.append((claim.start(), HOSTED_DYNAMIC_INVENTORY_ERROR))

    for claim in HOSTED_PROVIDER_DRAFT_REVERSE_CREATE.finditer(prose):
        if provider_capability_claim_is_current_affirmative(
            prose, claim.start(), claim.end()
        ) and not provider_draft_claim_is_tools_list_gated(
            prose, claim.start(), claim.end()
        ):
            contradictions.append(
                (claim.start(), HOSTED_PROVIDER_DRAFT_CONDITIONAL_ERROR)
            )

    for claim in HOSTED_PROVIDER_DRAFT_REVERSE_AUTHORITY.finditer(prose):
        if provider_capability_claim_is_current_affirmative(
            prose, claim.start(), claim.end()
        ):
            contradictions.append(
                (claim.start(), "hosted MCP claims provider-listing draft authority")
            )

    for claim in HOSTED_PROVIDER_DRAFT_NAMED_TOOL_REVERSE.finditer(prose):
        if not provider_capability_claim_is_current_affirmative(
            prose, claim.start(), claim.end()
        ):
            continue
        if claim.group("name") != CANONICAL_PROVIDER_DRAFT_TOOL_NAME:
            contradictions.append(
                (claim.start(), HOSTED_PROVIDER_DRAFT_LOOKALIKE_ERROR)
            )
        elif not provider_draft_claim_is_tools_list_gated(
            prose, claim.start(), claim.end()
        ):
            contradictions.append(
                (claim.start(), HOSTED_PROVIDER_DRAFT_CONDITIONAL_ERROR)
            )

    for claim in PROVIDER_DRAFT_NAMED_TOOL_AVAILABILITY.finditer(prose):
        current = (
            provider_capability_claim_is_current_semantic(
                prose, claim.start(), claim.end()
            )
            if PROVIDER_DRAFT_TOOL_LIST_BYPASS.search(
                claim_scope(prose, claim.start())
            )
            else provider_capability_claim_is_current_affirmative(
                prose, claim.start(), claim.end()
            )
        )
        if current and not provider_draft_claim_is_tools_list_gated(
            prose, claim.start(), claim.end()
        ):
            contradictions.append(
                (claim.start(), HOSTED_PROVIDER_DRAFT_CONDITIONAL_ERROR)
            )

    for claim in PROVIDER_DRAFT_NAMED_TOOL_INVOCATION.finditer(prose):
        if not provider_capability_claim_is_current_affirmative(
            prose, claim.start(), claim.end()
        ):
            continue
        if claim.group("name") != CANONICAL_PROVIDER_DRAFT_TOOL_NAME:
            contradictions.append(
                (claim.start(), HOSTED_PROVIDER_DRAFT_LOOKALIKE_ERROR)
            )
        elif not provider_draft_claim_is_tools_list_gated(
            prose, claim.start(), claim.end()
        ):
            contradictions.append(
                (claim.start(), HOSTED_PROVIDER_DRAFT_CONDITIONAL_ERROR)
            )

    for claim in EXACT_PROVIDER_DRAFT_TOOL_CREATE.finditer(prose):
        if provider_capability_claim_is_current_affirmative(
            prose, claim.start(), claim.end()
        ) and not provider_draft_claim_is_tools_list_gated(
            prose, claim.start(), claim.end()
        ):
            contradictions.append(
                (claim.start(), HOSTED_PROVIDER_DRAFT_CONDITIONAL_ERROR)
            )

    for claim in EXACT_PROVIDER_DRAFT_TOOL_AUTHORITY.finditer(prose):
        if provider_capability_claim_is_current_affirmative(
            prose, claim.start(), claim.end()
        ):
            contradictions.append(
                (claim.start(), "hosted MCP claims provider-listing draft authority")
            )

    for pattern in (
        EXACT_PROVIDER_DRAFT_TOOL_TRANSACTION,
        EXACT_PROVIDER_DRAFT_TOOL_TRANSACTION_NOMINAL,
    ):
        for claim in pattern.finditer(prose):
            if provider_capability_claim_is_current_affirmative(
                prose, claim.start(), claim.end()
            ):
                contradictions.append(
                    (claim.start(), "hosted Stele MCP claims transaction capability")
                )

    for match in EXACT_PROVIDER_DRAFT_TOOL_ANAPHOR.finditer(prose):
        claim_start = match.start("claim")
        claim_end = match.end("claim")
        if not provider_capability_claim_is_current_affirmative(
            prose, claim_start, claim_end
        ):
            continue
        action = match.group("action").casefold()
        target = match.group("target").casefold()
        if "draft" in target and action.startswith(
            ("creat", "prepar", "author", "generat", "produc")
        ):
            if not provider_draft_claim_is_tools_list_gated(
                prose, claim_start, claim_end
            ):
                contradictions.append(
                    (claim_start, HOSTED_PROVIDER_DRAFT_CONDITIONAL_ERROR)
                )
        elif "draft" in target:
            contradictions.append(
                (claim_start, "hosted MCP claims provider-listing draft authority")
            )
        else:
            contradictions.append(
                (claim_start, "hosted Stele MCP claims transaction capability")
            )

    for label, pattern in HOSTED_PROVIDER_DRAFT_UNCONDITIONAL.items():
        for claim in pattern.finditer(prose):
            if provider_capability_claim_is_current_affirmative(
                prose, claim.start(), claim.end()
            ) and not provider_draft_claim_is_tools_list_gated(
                prose, claim.start(), claim.end()
            ):
                contradictions.append((claim.start(), label))

    for claim in typed_tool_counts(prose, 0, len(prose)):
        surface = MCP_AFTER_TYPED_COUNT.match(prose[claim.end : claim.end + 100])
        if not surface:
            continue
        surface_end = claim.end + surface.end()
        if re.match(
            r"^\s+(?:documentation|docs?|examples?|fixtures?|mockups?|samples?|"
            r"SDK|test\s+(?:fixture|harness|case|server))\b",
            prose[surface_end : surface_end + 100],
            re.IGNORECASE,
        ):
            continue
        prefix = prose[max(0, claim.start - 52) : claim.start]
        if TRANSACTION_TOOL_DESCRIPTOR.search(
            f"{prefix} {prose[claim.start:claim.end]}"
        ):
            continue
        kind = "hosted" if surface.group("hosted") else "local"
        record_typed_tool_count(
            kind,
            TypedToolCount(
                start=claim.start,
                end=surface_end,
                value=claim.value,
                exact=claim.exact,
                qualifier=claim.qualifier,
                ordinal_total=claim.ordinal_total,
            ),
        )

    for claim in PUBLISHED_SERVICE_COUNT.finditer(prose):
        lower_prefix_start = max(0, claim.start() - 48)
        lower_bound = PUBLISHED_SERVICE_LOWER_BOUND_PREFIX.search(
            prose[lower_prefix_start : claim.start()]
        )
        polarity_prose = prose
        if lower_bound:
            qualifier_start = lower_prefix_start + lower_bound.start("qualifier")
            qualifier_end = lower_prefix_start + lower_bound.end("qualifier")
            polarity_prose = (
                prose[:qualifier_start]
                + " " * (qualifier_end - qualifier_start)
                + prose[qualifier_end:]
            )
        if claim_is_noncurrent(
            prose, claim.start(), claim.end()
        ) or (
            claim_is_denied(polarity_prose, claim.start(), claim.end())
            or count_claim_is_denied(polarity_prose, claim.start())
        ) or not published_service_count_is_catalog_attributed(prose, claim):
            continue
        actual = count_value(claim.group("count"))
        if actual != 0:
            qualifier = (
                " ".join(lower_bound.group("qualifier").casefold().split()) + " "
                if lower_bound
                else ""
            )
            contradictions.append(
                (
                    claim.start(),
                    f"Stele catalog claims {qualifier}{actual} published services; "
                    f"expected zero",
                )
            )

    for claim in CATALOG_ITEM_COUNT.finditer(prose):
        qualifier = (
            claim.group("forward_qualifier")
            or claim.group("reverse_qualifier")
            or claim.group("existential_qualifier")
            or claim.group("location_qualifier")
            or claim.group("location_reverse_qualifier")
            or ""
        ).casefold()
        if claim_is_noncurrent(
            prose, claim.start(), claim.end()
        ) or (
            qualifier not in {"no fewer than", "no less than"}
            and claim_is_denied(prose, claim.start(), claim.end())
        ):
            continue
        count_token = (
            claim.group("forward_count")
            or claim.group("reverse_count")
            or claim.group("existential_count")
            or claim.group("location_count")
            or claim.group("location_reverse_count")
        )
        actual = catalog_count_value(count_token)
        if actual != 0:
            qualified = f"{qualifier} " if qualifier else ""
            contradictions.append(
                (
                    claim.start(),
                    f"Stele catalog claims {qualified}{actual} listings; expected zero",
                )
            )

    for pattern in CATALOG_RICH_COUNT_PATTERNS:
        for claim in pattern.finditer(prose):
            phrase = claim.group("count_phrase")
            actual, qualifier = rich_catalog_count_value(phrase)
            if claim_is_noncurrent(
                prose, claim.start(), claim.end()
            ) or (
                qualifier not in {"no fewer than", "no less than"}
                and claim_is_denied(prose, claim.start(), claim.end())
            ):
                continue
            upper_bound_only = qualifier in {
                "at most",
                "up to",
                "or fewer",
                "or less",
                "a maximum of",
                "an maximum of",
                "maximum of",
            }
            lower_bound_nonzero = qualifier == "more than" and actual == 0
            if (actual > 0 or lower_bound_nonzero) and not upper_bound_only:
                qualified = f"{qualifier} " if qualifier else ""
                contradictions.append(
                    (
                        claim.start(),
                        f"Stele catalog claims {qualified}{actual} listings; expected zero",
                    )
                )

    for claim in CATALOG_NAMED_INVENTORY_CLAIM.finditer(prose):
        predicate_end = claim.start("inventory")
        if not claim_is_current_affirmative(
            prose, claim.start(), predicate_end
        ):
            continue
        actual = named_catalog_inventory_count(claim.group("inventory"))
        if actual > 0:
            contradictions.append(
                (
                    claim.start(),
                    f"Stele catalog names {actual} live inventory items; expected zero",
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
        (PROVIDER_DRAFT_CREATE_AFFIRMATIVE_CONTRADICTIONS, "affirmative"),
        (PROVIDER_DRAFT_CREATE_SEMANTICS, "semantic"),
        (IDENTITY_OVERCLAIMS, "affirmative"),
        (IDENTITY_REVERSE_OVERCLAIMS, "affirmative"),
        (IDENTITY_NAMED_OVERCLAIMS, "affirmative"),
        (DESKTOP_STELE_EMBEDDING, "affirmative"),
        (STALE_ECONOMIC_PREVIEW, "affirmative"),
        (PUBLIC_WEB_FORBIDDEN_CAPABILITIES, "affirmative"),
        (PUBLIC_WEB_DIRECT_ECONOMIC, "affirmative"),
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
        transition = re.compile(
            rf"\b{capability}\b(?:(?![.!?]).){{0,90}}?\b"
            rf"{CAPABILITY_TRANSITION_RELATION}\b",
            re.IGNORECASE | re.DOTALL,
        )
        for pattern in (forward, reverse, negated_disabled, transition):
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
        visible_source = status_prose(text)
        for label, pattern in FORBIDDEN.items():
            match = pattern.search(visible_source)
            if match:
                line = visible_source.count("\n", 0, match.start()) + 1
                failures.append(f"{path.relative_to(ROOT)}:{line}: {label}")
        folded = folded_prose(visible_source)
        for phrase in REQUIRED:
            if phrase.casefold() not in folded:
                failures.append(
                    f"{path.relative_to(ROOT)}: missing capability anchor {phrase!r}"
                )

    for path in STELE_STATUS_DOCUMENTS:
        text = path.read_text(encoding="utf-8")
        visible_source = status_prose(text)
        if not has_canonical_provider_studio_link(visible_source):
            failures.append(
                f"{path.relative_to(ROOT)}: missing exact Provider Studio Markdown destination "
                f"{CANONICAL_STUDIO_MARKDOWN_DESTINATION!r}; missing visible canonical "
                f"Provider Studio link {CANONICAL_STUDIO_URL!r}"
            )
        for label, pattern in STALE_STELE_DEPLOYMENT.items():
            match = pattern.search(visible_source)
            if match:
                line = visible_source.count("\n", 0, match.start()) + 1
                failures.append(f"{path.relative_to(ROOT)}:{line}: {label}")
        for offset, label in stele_status_contradictions(visible_source):
            line = visible_source.count("\n", 0, offset) + 1
            failures.append(f"{path.relative_to(ROOT)}:{line}: {label}")
        for match in HOSTED_FIXED_INVENTORY_CLAIM.finditer(visible_source):
            if TRANSACTION_TOOL_DESCRIPTOR.search(match.group(0)):
                continue
            if UNRELATED_TOOL_COUNT_SUBJECT.search(match.group(0)):
                continue
            assertion_start, _ = claim_assertion_bounds(
                visible_source, match.start(), match.end()
            )
            prefix = visible_source[assertion_start : match.start()]
            if MCP_META_OBJECT_PREFIX.search(prefix) or TOOL_COUNT_META_CONTEXT.search(
                prefix
            ):
                continue
            if claim_is_current_affirmative(
                visible_source, match.start(), match.end()
            ):
                line = visible_source.count("\n", 0, match.start()) + 1
                failures.append(
                    f"{path.relative_to(ROOT)}:{line}: hosted Stele MCP presents a fixed "
                    "tool inventory; authenticated tools/list is authoritative"
                )
        folded = folded_prose(visible_source)
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
