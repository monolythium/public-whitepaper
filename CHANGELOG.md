# Changelog

Release history of the Monolythium public whitepaper.

> **v6 reconciliation — 2026-07-05.** The v5.0/v5.1 entries below describe several constructions that
> have since changed with the Monolythium v2 (LythiumDAG-BFT) re-genesis. The whitepaper and lightpaper
> texts have been corrected in place (see the "v6 reconciliation" note at the head of each); a full v6
> edition will re-scope the surrounding narrative. In summary, relative to v5.1:
>
> - **Cross-chain interop is now an external-provider integration, not an in-tree bridge.** The in-tree
>   bridge stack — on-chain bridge proof verifier, route/fee/insurance scaffolding, and build feature —
>   was removed; the chain no longer verifies bridge proofs on-chain. Interop is delivered through an
>   external interop provider (evaluation in progress; described vendor-neutrally).
> - **The application-layer Groth16-BN254 / SP1 zero-knowledge verifier is disabled at genesis** — the
>   direction is a post-quantum FRI/STARK verifier that ships gated off until ready. Consensus finality
>   is pure ML-DSA-65 and never depended on it.
> - **The encrypted mempool ("LythiumSeal") was removed** — v2 runs a plaintext mempool and addresses
>   ordering fairness at the DAG-consensus layer; the threshold-decryption sealing design was dropped.
> - **DVT uses a per-operator ML-DSA-65 multisig** (a 7-of-10 bitmap of independent operator
>   signatures), not FROST/DKG/threshold-shared keys.
> - **Cross-cluster finality quorum is count-based, not stake-weighted, and block rewards are
>   service-weighted, not stake-weighted** — stake sets only top-100 admission rank.
> - **Confidential (amount-hidden) value transfer, the on-chain prover / GPU proof market, and
>   service-tier oracle-feed payments are gated off at genesis** and are not live; stealth-address
>   recipient privacy and privacy policy are live.
> - **Wallet recovery uses a standard BIP-39 → ML-DSA-65 mnemonic** (the PQM-1 format was dropped).
> - **The SLH-DSA hash-based emergency-backup key and the in-protocol emergency-key registry / algorithm
>   rotation were removed.** The chain is ML-DSA-65-only at launch; the advertised break-glass was audited as
>   inoperative and taken out. Post-quantum crypto agility (a cross-family backup primitive plus an
>   in-protocol rotation path) is deferred to a future genesis. The emergency freeze (a global, time-bounded
>   pause) is a separate mechanism and is unaffected.

## v5.0 — May 2026

First public-facing release.

A condensed lightpaper companion (`monolythium-lightpaper-v5.0.md`, ~7,000 words) accompanies the whitepaper, covering the thesis, the first commercial wedge, composition with the major agent-payment standards, the five refusals, the six design positions, the eight agent-commerce primitives, tokenomics, threat model, and honest limitations.

### Formats

Both documents ship in three formats:

- **Markdown** (`.md`) — canonical source.
- **Web** (`.html`) — self-contained branded page in the Monolythium theme; IBM Plex Sans/Mono embedded; no external network calls.
- **PDF** (`.pdf`) — print-ready A4, derived from the same HTML.

Whitepaper PDF: 81 pages. Lightpaper PDF: 34 pages.

### Thesis and positioning

- Settlement-layer thesis for the autonomous economy.
- A first commercial wedge stated explicitly: agent escrow, spending policy, and reputation as the trust layer behind paid APIs and services.
- Composition with the major open agent-payment standards — x402, AP2, ACP, MCP, Visa Intelligent Commerce, Mastercard Agent Pay — as the chain-anchored settlement, policy, escrow, identity, and reputation layer those rails leave open.
- Five refusals: no on-chain governance, no perpetuals or margin, no EVM execution, no fungibility between public and private denominations, no bundled AI model.
- Bifurcated denomination — public and private LYTH are structurally non-fungible.
- Cluster marketplace with distributed validator technology — 100 clusters × 10 operators (7 active + 3 standby), per-operator multi-cluster caps.
- Forking as the explicitly documented path of dissent.

### Cryptography and identity

- Post-quantum cryptography: ML-DSA-65 user and consensus signatures, ML-KEM-768 key encapsulation, and SLH-DSA emergency backup. Zero-knowledge proofs use SP1 zkVM + Groth16-BN254 on the gated application surface (classical; FRI/STARK is the long-horizon goal, not the shipped verifier). The no_classical_in_protocol lint is green and hard-fails the build: there is no classical signature acceptance path in the protocol. _(Superseded — the SLH-DSA emergency backup was removed; the chain is ML-DSA-65-only and crypto agility is deferred to a future genesis. See the v6 reconciliation note at the head of this changelog.)_
- Single-tier post-quantum finality: a per-operator ML-DSA-65 bitmap-multisig quorum certificate (any seven of a cluster's ten operators' individual signatures form the certificate), with roughly four-to-eight-second anchor finality.
- Starfish-C consensus: DAG-BFT with deterministic linearization, succinct equivocation proofs, and a post-quantum leader-seed beacon (a domain-separated, chain-id-bound BLAKE3 hash of the ML-DSA-65 quorum certificate that finalizes each anchor).
- Identity primitives: 20-byte BLAKE3-derived addresses, bech32m display with per-type human-readable prefix discriminator, standard 24-word BIP-39 mnemonic backup (seed re-derived for ML-DSA-65), hierarchical on-chain name registry.

### Execution and economics

- Execution model: Rust-first contracts compiled to deterministic RISC-V; native modules for hot paths; MRC-20/721/1155/4626 and native smart-account standards.
- Tokenomics: 100M LYTH initial supply, 8% inflation cap, liquid bonding, distributed delegation protocol with per-wallet caps tightening as the network matures.
- Allocation framework — seven-category split anchored on the 32,781,503.90 LYTH community-obligations pre-allocation, with foundation treasury reserve, ecosystem grants, vested core-contributor allocation, public sale and community access programs, operator incentives, and liquidity provision.
- Token utility and value capture across consensus, network, service-tier, registry, application, and delegation economics — LYTH-denominated gas, fee burn, service-tier payments, registry bonds, name-registry fees, and order-book fees.
- Canonical-LYTH disambiguation: only LYTH on Monolythium L1 is the official token; tokens by the same name on other networks are unaffiliated unless explicitly listed on the canonical-tokens page.

### Operations and primitives

- Eight agent-commerce primitives: attestation, consent, issuer registry, discovery, reputation, availability, escrow + arbiter, spending policy.
- Cluster operations — distributed validator technology, standby capacity, GPU prover service tier separation, service-tier revenue direct to operators.
- Privacy cordon — native caller-origin enforcement of denomination non-fungibility.

### Bridges, hardware, and resilience

- Bridges and the liquidity edge — zero-knowledge and light-client bridges, cross-chain swaps, route-specific cooldowns and drain caps. _(Superseded — the in-tree bridge stack was removed; interop is now an external-provider integration. See the v6 reconciliation note at the head of this changelog.)_
- Hardware sovereignty — Monarch OS substrate with TPM-measured boot, immutable image, kernel-attack-surface hardening, continuous on-chain PCR attestation, network and geographic diversity scoring.
- Threat model: surface-by-surface blast-radius separation, including post-quantum-leader-seed-beacon MEV bounds.
- Recovery posture — emergency-key registry with SLH-DSA backup, scoped and time-bounded emergency-freeze mechanism, multisig treasury, recovery runbooks. _(Superseded — the emergency-key registry and its SLH-DSA backup were removed; a break-day migration is handled by the emergency freeze plus a coordinated hard fork, with crypto agility deferred to a future genesis. See the v6 reconciliation note at the head of this changelog.)_

License: CC BY-SA 4.0 on the whitepaper text.
