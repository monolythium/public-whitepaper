# Monolythium Public Whitepaper

The public-facing whitepaper for Monolythium — a Layer 1 blockchain designed as a settlement layer for the autonomous economy.

## Latest

**Monolythium Whitepaper v5.0 — May 2026** &nbsp;·&nbsp; [Markdown](2026/may/monolythium-whitepaper-v5.0.md) &nbsp;·&nbsp; [Web](2026/may/monolythium-whitepaper-v5.0.html) &nbsp;·&nbsp; [PDF](2026/may/monolythium-whitepaper-v5.0.pdf)

Settlement Layer for the Autonomous Economy. Rust/RISC-V execution, post-quantum accounts, native MRC asset and market modules, cluster-marketplace operations with distributed validator technology, bifurcated public/private denomination, and the eight agent-commerce primitives. ~21,000 words / 81 pages.

**Monolythium Lightpaper v5.0 — May 2026** &nbsp;·&nbsp; [Markdown](2026/may/monolythium-lightpaper-v5.0.md) &nbsp;·&nbsp; [Web](2026/may/monolythium-lightpaper-v5.0.html) &nbsp;·&nbsp; [PDF](2026/may/monolythium-lightpaper-v5.0.pdf)

A condensed, ten-minute read of the whitepaper. Covers the thesis, the first commercial wedge, composition with the major agent-payment standards, the five refusals, the six design positions, the eight agent-commerce primitives, tokenomics, threat model, and limitations. ~7,000 words / 34 pages.

## Formats

Every release ships in three formats:

- **Markdown** — canonical source, easy to read on any device, easy to diff.
- **Web (HTML)** — self-contained branded page with the site's typography and palette; embeds its own fonts, no external network calls.
- **PDF** — print-ready A4, derived from the same HTML, with chapter headers, page numbers, and proper paged-media typography.

## Structure

```text
public-whitepaper/
├── README.md            — this file
├── LICENSE.md           — CC BY-SA 4.0 (whitepaper text)
├── CHANGELOG.md         — release history
└── 2026/
    └── may/
        ├── monolythium-whitepaper-v5.0.md
        ├── monolythium-whitepaper-v5.0.html
        ├── monolythium-whitepaper-v5.0.pdf
        ├── monolythium-lightpaper-v5.0.md
        ├── monolythium-lightpaper-v5.0.html
        └── monolythium-lightpaper-v5.0.pdf
```

Each release is dated and lives under its own folder. The newest release is linked above.

## License

The whitepaper text is published under the **Creative Commons Attribution-ShareAlike 4.0 International License** (CC BY-SA 4.0). See [`LICENSE.md`](LICENSE.md) for the full terms.

Attribution string:

> *Monolythium Whitepaper, v5.0 (May 2026), Mono Labs R&D LLC, licensed under CC BY-SA 4.0.*

The Monolythium protocol source code is licensed separately under the Business Source License 1.1 (with a four-year commercial restriction window converting to a permissive license). Selected execution crates ship under MIT.

## About the project

Monolythium is developed by **Mono Labs R&D LLC** (San Francisco, California) and stewarded by the **Monolythium Foundation** (Cayman Islands). The two entities are independent, with separate governance and separate roles in the protocol's operation.
