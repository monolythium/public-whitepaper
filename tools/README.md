# tools/

Builder for the branded web (HTML) and PDF artifacts that ship alongside each markdown release.

## What it does

Reads each markdown source under `2026/may/` and emits a self-contained `.html` (Monolythium theme, IBM Plex Sans + Mono embedded as base64) and a print-ready A4 `.pdf` (derived from the same HTML via WeasyPrint's `@media print` rules) next to the source.

## Quick start

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/requirements.txt
python tools/build.py
```

The build first runs `tools/check_truth.py`, which fails closed if public copy regresses to presenting
the target agent-commerce suite, spending-policy/USDC agent-payment routes, Stele-in-desktop, current
economic fees, a third hosted MCP tool, or a transaction-capable MCP as shipped. It also rejects stale
Stele hostname-reservation or unavailable-deployment language. Every public status surface must preserve
the dated live-preview link, zero-service catalog, Browser Wallet v0.4.5 prerelease label, exact hosted
and local MCP tool counts, public-web inspect-only draft boundary, published-listing prerequisite, and
the economic-write, transaction-signing, and mainnet-off gates. Correct anchors do not mask conflicting
copy: nonzero inventory, wrong tool counts, a transaction-capable local MCP, public-web draft creation,
draft preparation without a listing, or an enabled gated capability each fail the build. It can be run
directly without the rendering dependencies:

```bash
python tools/check_truth.py
python -m unittest discover -s tools -p 'test_*.py'
```

After rendering, `tools/check_public_boundary.py` inspects the candidate file set and compressed PDF
streams. It rejects unpublished markers, local filesystem paths, draft/private directories, disguised
office containers, office files, and every PDF not explicitly allowlisted. The two release PDFs are the
only current allowlist entries. Run it directly with:

```bash
python tools/check_public_boundary.py
```

The PDF renderer resolves cross-document annotations against the public GitHub repository. It must not
use a checkout directory as its base URL: doing so embeds a local `file:` annotation and makes the PDF
bytes depend on the build path.

Secret checks use the standard Gitleaks rules. `.gitleaksignore` contains two exact historical finding
fingerprints for the same prose-only false positive: a sentence naming Argon2id and XChaCha20-Poly1305
as encrypted-keystore algorithms. The entries do not suppress a file, commit, rule, or future finding.

```bash
gitleaks dir --redact .
gitleaks git --redact --log-opts=--all
```

System libraries WeasyPrint needs (Debian / Ubuntu):

```bash
sudo apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
    libffi-dev libcairo2 fonts-liberation
```

The script writes outputs **in place** next to each markdown source. Review the diff and commit the regenerated files.

## Layout

```
tools/
├── README.md            — this file
├── build.py             — the HTML/PDF generator
├── check_public_boundary.py — public-only path/content/artifact gate (standard library only)
├── check_truth.py       — public capability-boundary regression gate (standard library only)
├── requirements.txt     — pinned Python deps
└── fonts/               — bundled IBM Plex woff2 (OFL 1.1)
    ├── ibm-plex-sans-latin-{400,500,600,700}-normal.woff2
    ├── ibm-plex-mono-latin-{400,500}-normal.woff2
    ├── OFL-IBM-Plex-Sans.txt
    └── OFL-IBM-Plex-Mono.txt
```

## Brand

The output mirrors the `monolythium` theme used on monolythium.com:

- Canvas `#0d0e18` with a subtle indigo/violet radial bloom on the web view.
- Indigo accent `#6366F1`, hover-violet `#8B5CF6` on h3 and links.
- IBM Plex Sans for body, IBM Plex Mono for caps and code.
- Glass-card cover with a gradient rule across the top.
- Print version flattens the glass effect (WeasyPrint does not support `backdrop-filter`) but preserves the palette, typography, and gradient bloom on the cover.

## Adding a new release

1. Add the markdown source under `2026/<month>/your-doc-v6.0.md`.
2. Add a new `Doc(...)` row to the `DOCS` list in `build.py` pointing at it.
3. Run `python tools/build.py`.
4. Commit the new `.md`, `.html`, and `.pdf`.

## Font licensing

IBM Plex Sans and IBM Plex Mono are licensed under the SIL Open Font License 1.1. The full license text is included in `tools/fonts/OFL-IBM-Plex-Sans.txt` and `tools/fonts/OFL-IBM-Plex-Mono.txt`. The fonts are redistributed here under those terms.
