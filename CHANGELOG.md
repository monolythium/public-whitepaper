# Changelog

Release history of the Monolythium public whitepaper.

> **Erratum — v2 (LythiumDAG-BFT) testnet status.** Two constructions noted in the v5.0/v5.1 entries
> below have changed with the Monolythium v2 re-genesis and no longer describe the running chain.
> (1) **The encrypted mempool ("LythiumSeal") has been removed** —
> v2 runs a plaintext mempool and addresses ordering fairness at the DAG-consensus layer; the cluster
> ML-KEM / Shamir / threshold-reveal sealing scheme is no longer part of the protocol. (2) **The
> application-layer Groth16-BN254 zero-knowledge verifier is disabled at genesis** — the direction is a
> post-quantum recursive-STARK verifier that ships gated off until ready. Consensus finality remains
> pure ML-DSA-65 and never depended on either. See the erratum at the head of the whitepaper and
> lightpaper; a full v6 edition will re-scope the text.

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

- Post-quantum cryptography: ML-DSA-65 user and consensus signatures, ML-KEM-768 key encapsulation, SLH-DSA emergency backup, and an optional LythiumSeal post-quantum encrypted-mempool sealing path (cluster ML-KEM-768 + GF(256) Shamir t-of-n + committing AEAD), research-stage and unaudited. Zero-knowledge proofs use SP1 zkVM + Groth16-BN254 on the gated application surface (classical; FRI/STARK is the long-horizon goal, not the shipped verifier). The chain does not yet claim a classical-free protocol: the no_classical_in_protocol lint is not yet green, so quantum claims state the surface they cover.
- Single-tier post-quantum finality: a per-operator ML-DSA-65 bitmap-multisig quorum certificate (no BLS aggregate; any seven of a cluster's ten operators' individual signatures form the certificate), with roughly four-to-eight-second anchor finality.
- Starfish-C consensus: DAG-BFT with deterministic linearization, succinct equivocation proofs, and a post-quantum leader-seed beacon (a hash of the ML-DSA-65 quorum certificate) that replaces the legacy threshold-BLS beacon.
- Identity primitives: 20-byte BLAKE3-derived addresses, bech32m display with per-type human-readable prefix discriminator, PQM-1 24-word mnemonic backup, hierarchical on-chain name registry.

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

- Bridges and the liquidity edge — zero-knowledge and light-client bridges, cross-chain swaps, route-specific cooldowns and drain caps.
- Hardware sovereignty — Monarch OS substrate with TPM-measured boot, immutable image, kernel-attack-surface hardening, continuous on-chain PCR attestation, network and geographic diversity scoring.
- Threat model: surface-by-surface blast-radius separation, including optional-encrypted-mempool and post-quantum-leader-seed-beacon MEV bounds.
- Recovery posture — emergency-key registry with SLH-DSA backup, scoped and time-bounded emergency-freeze mechanism, multisig treasury, recovery runbooks.

License: CC BY-SA 4.0 on the whitepaper text.
