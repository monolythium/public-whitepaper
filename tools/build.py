#!/usr/bin/env python3
"""Build the Monolythium Whitepaper + Lightpaper as brand-matched HTML and PDF.

Run from the repo root or from tools/:

    python tools/build.py

Outputs are written in-place next to each markdown source:

    2026/may/monolythium-whitepaper-v5.0.{html,pdf}
    2026/may/monolythium-lightpaper-v5.0.{html,pdf}

Requirements:

    pip install -r tools/requirements.txt

Fonts (IBM Plex Sans + Mono, OFL 1.1) are bundled under tools/fonts/.
"""

from __future__ import annotations

import base64
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import markdown
from weasyprint import HTML as WeasyHTML


# ---------------------------------------------------------------------------
# Paths (all relative to this script)
# ---------------------------------------------------------------------------

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parent
FONTS_DIR = TOOLS / "fonts"
RELEASES = REPO / "2026" / "may"


# ---------------------------------------------------------------------------
# Documents to build
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Doc:
    slug: str            # output base name (e.g. "monolythium-whitepaper-v5.0")
    src: Path            # markdown source
    cover_title: str     # large title on the cover ("Whitepaper" / "Lightpaper")
    short_kind: str      # used in header/footer ("Whitepaper" / "Lightpaper")


DOCS = [
    Doc(
        slug="monolythium-whitepaper-v5.0",
        src=RELEASES / "monolythium-whitepaper-v5.0.md",
        cover_title="Whitepaper",
        short_kind="Whitepaper",
    ),
    Doc(
        slug="monolythium-lightpaper-v5.0",
        src=RELEASES / "monolythium-lightpaper-v5.0.md",
        cover_title="Lightpaper",
        short_kind="Lightpaper",
    ),
]


# ---------------------------------------------------------------------------
# Fonts: read woff2 from tools/fonts/ and base64-embed
# ---------------------------------------------------------------------------

FONT_SPEC = [
    # (family, weight, filename under tools/fonts/)
    ("IBM Plex Sans", 400, "ibm-plex-sans-latin-400-normal.woff2"),
    ("IBM Plex Sans", 500, "ibm-plex-sans-latin-500-normal.woff2"),
    ("IBM Plex Sans", 600, "ibm-plex-sans-latin-600-normal.woff2"),
    ("IBM Plex Sans", 700, "ibm-plex-sans-latin-700-normal.woff2"),
    ("IBM Plex Mono", 400, "ibm-plex-mono-latin-400-normal.woff2"),
    ("IBM Plex Mono", 500, "ibm-plex-mono-latin-500-normal.woff2"),
]


def font_face_css() -> str:
    parts: list[str] = []
    for family, weight, fname in FONT_SPEC:
        path = FONTS_DIR / fname
        if not path.exists():
            print(f"WARN: missing font {path}", file=sys.stderr)
            continue
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        parts.append(
            f"@font-face {{\n"
            f"  font-family: '{family}';\n"
            f"  font-style: normal;\n"
            f"  font-weight: {weight};\n"
            f"  font-display: swap;\n"
            f"  src: url(data:font/woff2;base64,{data}) format('woff2');\n"
            f"}}"
        )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Markdown -> HTML body
# ---------------------------------------------------------------------------

def md_to_body_html(md_text: str) -> str:
    """Convert the markdown body, dropping only the title/cover front-matter.

    The front-matter above the opening H2 is the cover (title, authors, date) and
    is rendered separately by `cover_html`. It may also carry a leading blockquote
    — the reconciliation notice recording where the text has been corrected against
    the running chain. That notice is *content*, not cover furniture: dropping it
    publishes the uncorrected claims while the corrections live only in the
    markdown source. It is preserved and rendered at the head of the body.
    """
    body_match = re.search(r"^## (Abstract|TL;DR|TLDR)", md_text, flags=re.MULTILINE)
    if not body_match:
        sys.exit("could not find an opening H2 (Abstract/TL;DR) in source")
    front_matter = md_text[: body_match.start()]
    body_md = md_text[body_match.start():]

    # Every blockquote run in the front-matter is prose the source intends a
    # reader to see — the reconciliation notice, and the lightpaper's "condensed
    # read" note. The cover renders neither (its title and tagline are supplied
    # by `Doc`), so anything dropped here is published nowhere. Keep them all, in
    # document order, at the head of the body.
    notices = re.findall(r"(?:^>[^\n]*\n?)+", front_matter, flags=re.MULTILINE)
    if notices:
        body_md = "\n\n".join(n.rstrip() for n in notices) + "\n\n" + body_md

    md = markdown.Markdown(
        extensions=["extra", "sane_lists", "smarty", "toc"],
        extension_configs={"toc": {"permalink": False, "marker": ""}},
        output_format="html5",
    )
    html = md.convert(body_md)

    # Tag the whitepaper's "Part N — ..." H1s for special section-divider styling.
    html = re.sub(
        r'<h1\b([^>]*)>(Part\s[^<]+)</h1>',
        r'<h1\1 class="part-heading">\2</h1>',
        html,
    )
    return html


# ---------------------------------------------------------------------------
# Cover hero
# ---------------------------------------------------------------------------

def cover_html(doc: Doc) -> str:
    return f"""
<section class="cover">
  <div class="cover-inner">
    <div class="cover-eyebrow">MONOLYTHIUM</div>
    <h1 class="cover-title">{doc.cover_title}</h1>
    <div class="cover-version-row">
      <span class="cover-version">v5.0</span>
      <span class="cover-sep">&middot;</span>
      <span class="cover-date">May 2026</span>
    </div>
    <div class="cover-rule"></div>
    <p class="cover-tagline">Settlement Layer for the Autonomous Economy</p>
    <div class="cover-meta">
      <div class="meta-row">
        <span class="meta-label">NETWORK</span>
        <span class="meta-value">Monolythium &middot; LYTH</span>
      </div>
      <div class="meta-row">
        <span class="meta-label">STEWARDED&nbsp;BY</span>
        <span class="meta-value">Mono Labs R&amp;D LLC &middot; Monolythium Foundation</span>
      </div>
      <div class="meta-row">
        <span class="meta-label">LICENSE</span>
        <span class="meta-value">Whitepaper text &mdash; CC BY-SA 4.0</span>
      </div>
    </div>
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

STYLES_CSS = r"""
/* ===== Brand tokens (monolythium theme, dark) ===== */
:root {
  --ink-000: #0a0b14;
  --ink-050: #0d0e18;
  --ink-100: #10121c;
  --ink-200: #151723;
  --ink-300: #1b1e2c;
  --ink-400: #232638;
  --ink-500: #2c3044;

  --fg-100: #ecedf3;
  --fg-200: #c9ccd8;
  --fg-300: #8c90a3;
  --fg-400: #646879;
  --fg-500: #464a5c;
  --fg-600: #2d3040;
  --fg-700: #1a1c28;

  --accent:    #6366F1;
  --accent-hi: #8B5CF6;
  --accent-lo: #4F52D9;
  --accent-bg: rgba(99, 102, 241, 0.14);
  --accent-soft: rgba(99, 102, 241, 0.22);
  --accent-glow: 99, 102, 241;

  --warn: #F2B441;

  --r-md: 18px;
  --r-lg: 22px;
}

*, *::before, *::after { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }

body {
  font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
  font-size: 16px;
  line-height: 1.65;
  color: var(--fg-100);
  background: var(--ink-050);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  letter-spacing: -0.005em;
  overflow-x: hidden;
}

::selection { background: rgba(var(--accent-glow), 0.45); color: #fff; }

/* ===== Ambient bloom backdrop (web only) ===== */
.bloom {
  position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background:
    radial-gradient(60vw 60vw at -10vw 100vh, rgba(99, 102, 241, 0.22) 0%, transparent 55%),
    radial-gradient(55vw 55vw at 110vw -10vh, rgba(139, 92, 246, 0.20) 0%, transparent 55%),
    radial-gradient(ellipse 120% 80% at 50% 120%, rgba(60, 50, 130, 0.30), transparent 60%),
    linear-gradient(180deg, var(--ink-000) 0%, var(--ink-100) 50%, var(--ink-050) 100%);
}
.bloom::after {
  content: ""; position: absolute; inset: 0;
  background: radial-gradient(ellipse 100% 80% at 50% 50%, transparent 40%, rgba(0,0,0,0.45) 100%);
}

.app { position: relative; z-index: 1; max-width: 920px; margin: 0 auto; padding: 0 28px; }

/* ===== Cover hero ===== */
.cover {
  min-height: calc(100vh - 60px);
  display: flex; align-items: center;
  padding: 64px 0 80px;
}
.cover-inner {
  width: 100%; position: relative;
  padding: 64px 56px 56px 56px;
  border-radius: var(--r-lg);
  background: rgba(255,255,255,0.025);
  border: 1px solid rgba(255,255,255,0.08);
  backdrop-filter: blur(24px) saturate(150%);
  -webkit-backdrop-filter: blur(24px) saturate(150%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 30px 60px -30px rgba(0,0,0,0.6);
  overflow: hidden;
}
.cover-inner::before {
  content: ""; position: absolute;
  top: 0; left: 56px; right: 56px; height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent) 30%, var(--accent-hi) 70%, transparent);
  opacity: 0.85;
}

.cover-eyebrow {
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  font-size: 12px; letter-spacing: 0.32em;
  color: var(--accent); font-weight: 600;
  margin-bottom: 28px;
}
.cover-title {
  font-size: clamp(48px, 8vw, 88px);
  font-weight: 400; line-height: 1; letter-spacing: -0.04em;
  margin: 0 0 18px 0; color: var(--fg-100);
}
.cover-version-row {
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  font-size: 13px; letter-spacing: 0.18em;
  color: var(--fg-300); text-transform: uppercase;
  margin-bottom: 32px; display: flex; gap: 12px; align-items: center;
}
.cover-version { color: var(--fg-200); font-weight: 500; }
.cover-sep { color: var(--fg-500); }
.cover-date { color: var(--fg-300); }
.cover-rule { width: 56px; height: 1.5px; background: var(--accent); margin-bottom: 32px; }
.cover-tagline {
  font-size: clamp(20px, 2.4vw, 28px);
  line-height: 1.35; color: var(--fg-100);
  font-weight: 400; margin: 0 0 56px 0; max-width: 640px;
}
.cover-meta {
  border-top: 1px solid rgba(255,255,255,0.07);
  padding-top: 28px; display: grid; gap: 14px;
}
.meta-row {
  display: grid; grid-template-columns: 140px 1fr;
  align-items: baseline; gap: 18px;
  font-family: 'IBM Plex Mono', ui-monospace, monospace; font-size: 12px;
}
.meta-label {
  color: var(--fg-400); letter-spacing: 0.12em;
  text-transform: uppercase; font-weight: 500;
}
.meta-value {
  color: var(--fg-200); letter-spacing: 0;
  font-family: 'IBM Plex Sans', sans-serif; font-size: 14px;
}

/* ===== Body ===== */
.wp-body { padding: 56px 0 80px; max-width: 720px; margin: 0 auto; }

.wp-body h1 {
  font-size: 36px; font-weight: 600; letter-spacing: -0.025em;
  line-height: 1.15; color: var(--fg-100);
  margin: 80px 0 28px; scroll-margin-top: 24px;
}
.wp-body h1.part-heading {
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  font-size: 13px; font-weight: 600; letter-spacing: 0.32em;
  text-transform: uppercase; color: var(--accent);
  margin: 80px 0 32px; padding-bottom: 20px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  display: flex; align-items: center; gap: 14px;
}
.wp-body h1.part-heading::before {
  content: ""; width: 28px; height: 1.5px;
  background: var(--accent); display: inline-block;
}
.wp-body h2 {
  font-size: 26px; font-weight: 600; letter-spacing: -0.02em;
  line-height: 1.25; color: var(--fg-100);
  margin: 56px 0 18px; scroll-margin-top: 24px;
}
.wp-body h3 {
  font-size: 18px; font-weight: 600; color: var(--accent-hi);
  letter-spacing: -0.005em; margin: 36px 0 12px; scroll-margin-top: 24px;
}
.wp-body h4 {
  font-size: 15px; font-weight: 600; color: var(--fg-100);
  margin: 22px 0 8px;
}

.wp-body p { margin: 0 0 14px; color: var(--fg-200); font-size: 16px; line-height: 1.7; }
.wp-body strong { color: var(--fg-100); font-weight: 600; }
.wp-body em { color: var(--fg-200); }

.wp-body a {
  color: var(--accent-hi); text-decoration: none;
  border-bottom: 1px solid rgba(var(--accent-glow), 0.4);
  transition: border-color 120ms ease, color 120ms ease;
}
.wp-body a:hover { color: #fff; border-bottom-color: var(--accent-hi); }

.wp-body ul, .wp-body ol { margin: 0 0 16px; padding-left: 22px; color: var(--fg-200); }
.wp-body li { margin-bottom: 7px; line-height: 1.65; }
.wp-body li::marker { color: var(--accent); }
.wp-body li > p { margin-bottom: 7px; }

.wp-body code {
  font-family: 'IBM Plex Mono', ui-monospace, monospace; font-size: 13px;
  background: rgba(99, 102, 241, 0.12); color: var(--fg-100);
  padding: 1px 6px; border-radius: 4px;
  border: 1px solid rgba(99, 102, 241, 0.18); letter-spacing: 0;
}
.wp-body pre {
  background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.07);
  border-left: 2px solid var(--accent); border-radius: 8px;
  padding: 16px 18px; margin: 16px 0 22px; overflow-x: auto;
  font-size: 13px; line-height: 1.55;
}
.wp-body pre code { background: none; border: 0; color: var(--fg-200); padding: 0; font-size: inherit; }

.wp-body table {
  width: 100%; border-collapse: collapse; margin: 18px 0 28px;
  font-size: 14px; background: rgba(255,255,255,0.015);
  border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; overflow: hidden;
}
.wp-body th {
  background: rgba(99, 102, 241, 0.10); color: var(--fg-100);
  font-family: 'IBM Plex Mono', ui-monospace, monospace; font-weight: 600;
  text-transform: uppercase; font-size: 11px; letter-spacing: 0.10em;
  text-align: left; padding: 12px 14px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.20);
}
.wp-body td {
  padding: 10px 14px; border-bottom: 1px solid rgba(255,255,255,0.05);
  color: var(--fg-200); vertical-align: top;
}
.wp-body tr:nth-child(even) td { background: rgba(255,255,255,0.015); }
.wp-body tr:last-child td { border-bottom: 0; }

.wp-body blockquote {
  margin: 22px 0; padding: 18px 22px;
  background: rgba(99, 102, 241, 0.06);
  border-left: 3px solid var(--accent);
  border-radius: 0 8px 8px 0;
  color: var(--fg-100); font-style: italic;
  font-size: 17px; line-height: 1.55; position: relative;
}
.wp-body blockquote p { color: var(--fg-100); margin: 0; }
.wp-body blockquote p + p { margin-top: 10px; }

.wp-body hr { border: 0; height: 1px; background: rgba(255,255,255,0.08); margin: 56px 0; }

/* ===== Footer ===== */
.wp-footer {
  border-top: 1px solid rgba(255,255,255,0.06);
  margin-top: 24px; padding: 28px 0 56px;
}
.wp-footer-inner {
  display: flex; justify-content: space-between;
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  font-size: 11px; letter-spacing: 0.06em; color: var(--fg-400);
  text-transform: uppercase;
}

/* ===== Print / PDF ===== */
@media print {
  @page {
    size: A4; margin: 18mm 18mm 22mm;
    @top-left {
      content: string(chapter);
      font-family: 'IBM Plex Mono', monospace;
      font-size: 8pt; letter-spacing: 0.10em; color: #8c90a3;
      padding-bottom: 6mm;
    }
    @top-right {
      content: string(doctitle);
      font-family: 'IBM Plex Sans', sans-serif;
      font-size: 8pt; color: #8c90a3; padding-bottom: 6mm;
    }
    @bottom-center {
      content: counter(page);
      font-family: 'IBM Plex Mono', monospace;
      font-size: 8pt; color: #8c90a3; padding-top: 6mm;
    }
  }
  @page cover {
    margin: 0;
    @top-left { content: none; }
    @top-right { content: none; }
    @bottom-center { content: none; }
  }

  html, body {
    background: var(--ink-050) !important; color: var(--fg-100) !important;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }
  .bloom { display: none; }
  .wp-footer { display: none; }
  .app { max-width: none; padding: 0; margin: 0; }

  body { string-set: doctitle attr(data-doctitle); }

  .cover {
    page: cover; min-height: 297mm; height: 297mm;
    padding: 0; margin: 0; page-break-after: always;
    background:
      radial-gradient(ellipse 80% 60% at 10% 0%, rgba(99, 102, 241, 0.22), transparent 60%),
      radial-gradient(ellipse 70% 50% at 95% 100%, rgba(139, 92, 246, 0.18), transparent 60%),
      var(--ink-050);
  }
  .cover-inner {
    margin: 32mm 22mm; padding: 28mm 22mm;
    backdrop-filter: none; -webkit-backdrop-filter: none;
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.10);
    box-shadow: none;
  }
  .cover-title { font-size: 60pt; line-height: 1; }
  .cover-tagline { font-size: 18pt; margin-bottom: 30mm; }

  .wp-body { padding: 14mm 18mm; max-width: none; margin: 0; }

  .wp-body h1.part-heading {
    page-break-before: always; page-break-after: avoid;
    string-set: chapter content();
    margin: 0 0 14mm 0; font-size: 10pt;
  }
  .wp-body h1 {
    page-break-before: always; page-break-after: avoid;
    string-set: chapter content();
    font-size: 24pt; margin: 0 0 8mm;
  }
  .wp-body > h2:first-of-type { page-break-before: auto; margin-top: 0; }
  .wp-body h2 {
    page-break-before: always; page-break-after: avoid;
    string-set: chapter content();
    font-size: 16pt; margin: 0 0 6mm;
  }
  .wp-body h1.part-heading + h2 {
    page-break-before: auto; margin-top: 4mm;
  }

  .wp-body h3 { font-size: 12pt; margin: 10mm 0 3mm; page-break-after: avoid; }
  .wp-body h4 { font-size: 11pt; margin: 6mm 0 2mm; page-break-after: avoid; }

  .wp-body p {
    font-size: 10pt; line-height: 1.55; margin: 0 0 7pt;
    orphans: 3; widows: 3; text-align: justify; hyphens: auto;
  }
  .wp-body ul, .wp-body ol { font-size: 10pt; }
  .wp-body li { margin-bottom: 3pt; }

  .wp-body code {
    font-size: 9pt;
    background: rgba(99, 102, 241, 0.10);
    border-color: rgba(99, 102, 241, 0.15);
  }
  .wp-body pre {
    font-size: 8.5pt; line-height: 1.45; page-break-inside: avoid;
    white-space: pre-wrap; word-wrap: break-word;
  }
  .wp-body table {
    font-size: 9pt; page-break-inside: avoid;
    background: rgba(255,255,255,0.02);
  }
  .wp-body th { font-size: 8pt; padding: 5pt 7pt; }
  .wp-body td { padding: 4pt 7pt; }
  .wp-body blockquote { font-size: 11pt; page-break-inside: avoid; }
  .wp-body a { color: var(--accent-hi) !important; border-bottom-color: transparent; }
  .wp-body hr { margin: 18pt 0; }
}
"""


# ---------------------------------------------------------------------------
# Build one document
# ---------------------------------------------------------------------------

def build_doc(doc: Doc, fonts_css: str) -> tuple[Path, Path]:
    md_text = doc.src.read_text(encoding="utf-8")
    body_html = md_to_body_html(md_text)

    doc_title = f"Monolythium {doc.short_kind} v5.0"

    html_str = f"""<!DOCTYPE html>
<html lang="en" data-theme="monolythium">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>{doc_title}</title>
<style>
{fonts_css}

{STYLES_CSS}
</style>
</head>
<body data-doctitle="{doc_title}">
<div class="bloom"></div>
<main class="app">
{cover_html(doc)}
<article class="wp-body">
{body_html}
</article>
<footer class="wp-footer">
  <div class="wp-footer-inner">
    <div class="footer-mark">{doc_title} &middot; May 2026</div>
    <div class="footer-license">CC BY-SA 4.0 &middot; Mono Labs R&amp;D LLC &middot; Monolythium Foundation</div>
  </div>
</footer>
</main>
</body>
</html>
"""

    out_html = doc.src.with_suffix(".html")
    out_pdf = doc.src.with_suffix(".pdf")

    out_html.write_text(html_str, encoding="utf-8")

    WeasyHTML(string=html_str, base_url=str(doc.src.parent)).write_pdf(
        str(out_pdf),
        presentational_hints=True,
    )

    rel_html = out_html.relative_to(REPO)
    rel_pdf = out_pdf.relative_to(REPO)
    print(
        f"  {doc.slug}\n"
        f"    -> {rel_html} ({out_html.stat().st_size // 1024} KB)\n"
        f"    -> {rel_pdf} ({out_pdf.stat().st_size // 1024} KB)",
        file=sys.stderr,
    )
    return out_html, out_pdf


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("loading bundled fonts...", file=sys.stderr)
    fonts_css = font_face_css()

    print("building documents...", file=sys.stderr)
    for doc in DOCS:
        if not doc.src.exists():
            print(f"  SKIP {doc.slug}: source missing ({doc.src})", file=sys.stderr)
            continue
        build_doc(doc, fonts_css)

    print("done", file=sys.stderr)


if __name__ == "__main__":
    main()
