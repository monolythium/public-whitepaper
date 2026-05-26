# Changelog

Release history of the Monolythium public whitepaper.

## v5.0 — May 2026

First public-facing release.

A condensed lightpaper companion (`monolythium-lightpaper-v5.0.md`, ~7,000 words) accompanies the whitepaper, covering the thesis, the first commercial wedge, composition with the major agent-payment standards, the five refusals, the six design positions, the eight agent-commerce primitives, tokenomics, threat model, and honest limitations.

### Thesis and positioning

- Settlement-layer thesis for the autonomous economy.
- A first commercial wedge stated explicitly: agent escrow, spending policy, and reputation as the trust layer behind paid APIs and services.
- Composition with the major open agent-payment standards — x402, AP2, ACP, MCP, Visa Intelligent Commerce, Mastercard Agent Pay — as the chain-anchored settlement, policy, escrow, identity, and reputation layer those rails leave open.
- Five refusals: no on-chain governance, no perpetuals or margin, no EVM execution, no fungibility between public and private denominations, no bundled AI model.
- Bifurcated denomination — public and private LYTH are structurally non-fungible.
- Cluster marketplace with distributed validator technology — 100 clusters × 10 operators (7 active + 3 standby), per-operator multi-cluster caps.
- Forking as the explicitly documented path of dissent.

### Cryptography and identity

- Post-quantum cryptography end-to-end: ML-DSA-65 user signatures, ML-KEM-768 key encapsulation, SLH-DSA emergency backup, Ferveo threshold-DKE encrypted mempool, FRI/STARK-based zero-knowledge proofs.
- Two-tier finality: anchor-level (3–5s) via BLS12-381 aggregate; quantum-attested checkpoint every 100 anchors via ML-DSA-65.
- Starfish-C consensus — leaderless DAG-BFT with deterministic linearization, succinct equivocation proofs, and threshold-VRF leader selection.
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

- Bridges and the liquidity edge — IBC, zero-knowledge and light-client bridges, cross-chain swaps, route-specific cooldowns and drain caps.
- Hardware sovereignty — Monarch OS substrate with TPM-measured boot, immutable image, kernel-attack-surface hardening, continuous on-chain PCR attestation, network and geographic diversity scoring.
- Threat model — surface-by-surface blast-radius separation, including encrypted-mempool and threshold-VRF MEV bounds.
- Recovery posture — emergency-key registry with SLH-DSA backup, scoped and time-bounded emergency-freeze mechanism, multisig treasury, recovery runbooks.

License: CC BY-SA 4.0 on the whitepaper text.
