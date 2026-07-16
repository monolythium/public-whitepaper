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
the target agent-commerce suite, Stele-in-desktop, current economic fees, or a transaction-capable MCP
as shipped. It can also be run directly without the rendering dependencies:

```bash
python tools/check_truth.py
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
