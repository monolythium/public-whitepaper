# Monolythium Lightpaper

## v5.0 — May 2026

**Settlement Layer for the Autonomous Economy**

**Network:** Monolythium · Native token: LYTH
**Whitepaper text license:** Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
**Source code license:** Business Source License 1.1 (with permissive conversion); selected execution crates ship under MIT.

> *A condensed, ten-minute read of the [Monolythium Whitepaper v5.0](monolythium-whitepaper-v5.0.md). For implementation detail, threat model, and full citations, see the whitepaper.*

---

> **v6 reconciliation — updated 2026-07-16.** This text has a set of factual corrections applied so
> that it matches the running Monolythium v2 chain (LythiumDAG-BFT) as of the **v0.4.0 re-genesis of
> 2026-07-07**. The affected sections have been rewritten in place; a full v6 edition will re-scope the
> surrounding narrative. What changed, and why:
>
> 1. **Cross-chain interop is now an external-provider integration, not an in-tree bridge.** The entire
>    in-tree bridge stack — the on-chain bridge proof verifier, the route/fee/insurance scaffolding, and
>    the associated build feature — has been **removed**. The chain no longer verifies bridge proofs
>    on-chain; interoperability is delivered by integrating an **external interop provider** (evaluation
>    in progress; described vendor-neutrally). This moves the highest-risk surface out of consensus and
>    lets interop evolve without a re-genesis.
> 2. **The application-layer Groth16-BN254 / SP1 zero-knowledge verifier is disabled at genesis.** The
>    intended direction is a post-quantum FRI/STARK verifier that ships **gated off** until ready.
>    Consensus finality is pure ML-DSA-65 and never depended on it.
> 3. **The encrypted mempool ("LythiumSeal") has been removed.** v2 runs a **plaintext** mempool;
>    ordering fairness is handled at the DAG-consensus layer. The threshold-decryption design was dropped.
> 4. **DVT uses a per-operator ML-DSA-65 multisig, not shared or threshold keys.** Each operator signs
>    with its own independent key; a cluster certificate is a 7-of-10 bitmap of those raw signatures.
> 5. **Cross-cluster finality quorum is count-based, not stake-weighted.** Clusters carry equal weight;
>    stake sets only top-100 admission rank.
> 6. **Rewards are service-weighted, not stake-weighted.** A cluster's share of the reward pool is set by
>    proven services (archive, GPU proving, RPC, indexing, geo/client diversity), not by delegated stake;
>    stake's only role is top-100 admission rank. This supersedes the earlier "quadratic reward curve"
>    wording.
> 7. **Confidential (amount-hidden) value transfer was removed from the protocol and is not live.**
>    Stealth-address recipient privacy and privacy policy remain in the v0.4.0 protocol, but the earlier
>    Ristretto/Pedersen + Bulletproofs value path was deleted after audit; any replacement is a future
>    post-quantum design, not a gated switch.
> 8. **The on-chain prover / GPU proof market and service-tier oracle-feed payments are gated off at
>    genesis** and are not reachable in the public v0.4.0 protocol.
> 9. **Wallet recovery uses a standard 24-word BIP-39 mnemonic** re-derived for ML-DSA-65 as
>    `mldsa_seed = SHAKE256("monolythium.mldsa65.v1" || bip39_pbkdf2_seed(mnemonic, ""))[0:32]`; the
>    earlier "PQM-1" format was dropped and any PQM-1 scheme described below is **superseded**.
> 10. **The registered v0.4.0 development-network topology is a 4×10 DVT fleet** (four clusters of ten
>     operator identities, 7-of-10 each) plus two relay identities. Registration does not prove current
>     participation or liveness; see the dated degraded-status observation below.
> 11. **The SLH-DSA emergency-backup key, emergency-key registry, and on-chain algorithm rotation were
>     removed.** The chain is ML-DSA-65-only. A second-family backup and in-protocol rotation require a
>     future genesis; the separate time-bounded emergency freeze does not rotate user keys.
> 12. **The classical signature code has been removed from the implementation**, not merely refused at
>     admission. ML-DSA-65 was always the only algorithm accepted at transaction admission, but the
>     implementation still carried secp256k1, Ed25519 and WebAuthn P-256 behind a build flag, plus a
>     classical/post-quantum **hybrid** construction and a wallet-side key-import path for them. None of
>     it could produce a transaction the chain would accept. It is now deleted, and those wire tags are
>     permanently retired. The claims below ("no classical signature acceptance path", "no classical
>     fallback", no hybrid) are therefore now true of the code and not only of the admission gate. One
>     classical dependency remains: the peer-to-peer transport's node-identity keys, which authenticate
>     network connections and never consensus or state.
> 13. **The peer-to-peer handshake is not "Noise XX", and the argument against hybrid signatures was
>     unsound.** The operator-to-operator handshake is a **self-contained KEM-Noise IK-style
>     construction of our own**, not a stock Noise pattern, and it has **not yet had an independent
>     cryptographic review** (a tracked gate before mainnet). The case against hybrid also mis-stated
>     itself — it defined hybrid as accepting *either* signature but argued against a scheme requiring
>     *both*. The conclusion (pure post-quantum, no hybrid) is unchanged; see whitepaper §7 and §12.3
>     for the corrected reasoning.
> 14. **Agent commerce remains a target architecture.** Service listings, availability, escrow,
>     arbitration, bilateral reputation, protocol spending policy, economic runbooks, and autonomous
>     signing are not activated on the current public development network. The methods and state
>     machines below are design requirements, not a current ABI.
> 15. **Stele's product architecture is standalone web, not a desktop-wallet feature.** As of
>     2026-07-16, the public preview is live at
>     [stele.monolythium.com](https://stele.monolythium.com) with zero published services. Browser Wallet
>     v0.4.5 is a prerelease and owns identity proof; Stele's hosted services never receive wallet
>     secrets. Hosted Stele MCP is keyless and exposes exactly two OAuth-protected tools: public catalog
>     search and bounded, non-economic booking-draft preparation. The isolated local Stele MCP exposes
>     exactly three read/status tools and no transaction tool. Economic writes, transaction signing, and
>     mainnet remain off. The current product line retires embedded Stele, but legacy or unreconciled
>     desktop builds may retain a gated historical surface until reviewed removal and migration are
>     released. Provider publication, E2EE rooms, settlement, disputes, and reviews remain gated.
>
> **Dated network-status note — 2026-07-16.** The registered v0.4.0 development-network endpoint was
> reachable but stalled at height 74,907 with latest timestamp 2026-07-08T22:39:05Z during repeated
> checks. Treat it as degraded/stale, not as production settlement or network-liveness evidence.

## TL;DR

Monolythium is a Layer 1 blockchain designed as the **settlement layer for the autonomous economy** — a future in which humans, companies, AI agents, machines, and software services transact directly on open rails.

The chain is **not EVM-compatible at execution**. Its target architecture is connected at the liquidity edge through separately released external-provider or issuer integrations and is designed to compose **underneath** major agent-payment standards. Those commerce and interop paths are not current integration claims.

Six positions define the design:

1. **Post-quantum accounts by default**, with no classical signature acceptance path.
2. **Rust-first smart contracts** compiled to a deterministic RISC-V execution target.
3. **Native modules** for tokens, NFTs, and markets, with payments and agent commerce as separately activated target modules.
4. **Bifurcated denomination** that separates monetary privacy from commerce so the chain cannot be used as a fungible-anonymous-payment rail.
5. **Cluster marketplace** that turns validator operation into a public, competitive market with distributed validator technology.
6. **No on-chain governance and no perpetual futures**, so the surface that can be captured, gamed, or weaponised is smaller.

The chain is useful even if the agent economy grows slowly. Native tokens, spot markets, post-quantum identity, external-provider interop, and the bifurcated denomination are valuable on their own. The bet is asymmetric: a strong fit for the autonomous-economy case, a strong general-purpose settlement chain in the meantime.

---

## 1. The Thesis

Most production blockchains today are honestly named **trading chains**. They optimize for swap latency, perpetuals throughput, and high-frequency fee surfaces. Trading is fine; trading is not what the next ten years of digital economic activity will primarily look like.

The next ten years are **agentic**. An AI agent that pays for inference, hires a contractor, buys data, settles an invoice, escrows funds against a deliverable, subscribes to compute, or pays another agent for a service is not science fiction — each of those actions is technically possible today. What is missing is open, neutral, enforceable rails on which to settle them.

Today, an agent that wants to spend money does so through an account it shares with its user inside a closed AI platform, through a payment-processor account leased by the user, or through a custodial wallet rented from a single exchange. Each rail is **owned**. The agent is rentable. The identity is rentable. The reputation accrued through years of work is rentable. If the platform changes its terms, the agent's economic life resets.

Monolythium exists to provide a different option — programmable, auditable, permissionless, interop-connected, post-quantum, and structurally hostile to use cases that combine anonymous payment with anonymous service discovery.

The audience the chain is built for, in plain terms: **anyone who needs a delegated software entity to act with bounded authority across providers and jurisdictions on rails the principal controls.** That includes AI agents — but also fintech automations, organizational treasury policies, vendor pipelines, and routine machine-to-machine commerce. The chain is the same chain it would be if no agent ever showed up. The user is different.

> *The moment an AI assistant can say, "Send me 50 USDC to complete this task," the agent-commerce era has started.* Monolythium is designing user-controlled rails for that future; current Stele MCP surfaces do not hold a wallet or sign a transaction.

---

## 2. The First Wedge

A settlement layer for the autonomous economy is the long horizon. The first commercial wedge is narrower.

**The planned wedge is agent escrow, spending policy, and reputation as the trust layer behind paid APIs and services.**

The market is already converging on standardised payment handshakes for agents. x402 (Coinbase) shipped in 2025; AP2 (Google) launched the same year; Stripe and OpenAI released the Agentic Commerce Protocol; AWS Bedrock AgentCore added native stablecoin payment rails; Visa and Mastercard both announced agent-payment programs. These standards solve the payment **handshake** — how an agent discovers a paid endpoint, presents payment, and receives a response.

They do not solve four problems that are unavoidable once agents operate against more than trivial workflows:

- **Enforceable principal-level spending policy** — caps, allow-lists, time-of-day rules, expiry, revocation — that the agent itself cannot bypass.
- **Escrow with counter-offer flow and pluggable arbiters** for deliverable-against-payment work.
- **Portable cross-platform reputation tied to the agent identity** that survives a switch of model provider, runtime, or wallet.
- **Chain-anchored consent records** the principal can revoke instantly, leaving in-flight commitments grandfathered.

The target architecture assigns those four capabilities to versioned native or indexed surfaces. They are not activated public-network deliverables.

---

## 3. Target Composition with Agent-Payment Standards

The following table describes possible roles after the exact protocol, asset, SDK, wallet, privacy, and connector contracts are released. It is not a current integration list.

| Layer | Standard | Possible role after activation |
|---|---|---|
| HTTP payment handshake | **x402** (Coinbase, x402 Foundation) | Could bind settlement to versioned receipts, escrow, and reputation |
| Agent intent mandate | **AP2** (Google, open) | Could bind a mandate to principal-controlled consent and policy |
| Checkout flow | **ACP** (Stripe, OpenAI) | Could bind checkout output to settlement and dispute state |
| Tool / connector boundary | **MCP** (Model Context Protocol) | Could expose released discovery or approval workflows; signing requires a separate local design and explicit authority |
| Card-issuer agent flows | **Visa Intelligent Commerce, Mastercard Agent Pay** | Could add portable identity and receipts behind issuer-controlled flows |

The intended composition is one-directional: the external rail would handle its own handshake while an activated Monolythium surface could add policy, escrow, dispute, reputation, and settlement.

### Illustrative future example — x402 + Monolythium

1. An assistant could receive an `HTTP 402` response and prepare a bounded request.
2. A future wallet could compare it with a released principal-owned policy.
3. Only under explicit authority could the wallet sign a typed transaction referencing the external payment identifier.
4. An activated protocol would reject policy violations at admission.
5. A released receiver could wait for observed finality before serving the response.
6. A released escrow protocol could permit a dispute tied to the finalized receipt.

This scenario does not assert a current x402 receiver, stablecoin route, settlement-time SLA, `pay_vendor` ABI, or transaction-capable MCP tool.

---

## 4. What Monolythium Refuses

A chain's identity is shaped at least as much by what it refuses to do as by what it does. Five refusals define Monolythium.

### 4.1 No on-chain governance

No governance token. No on-chain proposal contract. No protocol-level voting mechanism. No on-chain treasury voting. No signaling extrinsic that pretends to be governance.

A decade of L1 experiments has produced four consistent governance failure modes — capture by large holders, vote-buying markets, low-turnout theatre, and a direct control surface for attackers who obtain a quorum. The chain rejects all four by **not having the mechanism**. Direction is set by accountable maintainers in public; operators choose whether to run new node software; the legitimate path of dissent is forking.

### 4.2 No perpetual futures or margin

Spot markets, yes. Perpetual futures, on-chain leverage, and margin trading, no — not on mainnet, not as a mintable asset class, not as a planned addition. Once a chain becomes a perpetuals venue, the design pressure on every other surface bends toward the perpetuals product. The chain pays the simplification — smaller audit surface, cleaner identity — to keep the design focused on settlement.

### 4.3 No EVM execution

Monolythium is **not EVM-compatible at execution**. EVM bytecode does not run on the chain; Solidity is not the default developer model; ERC conventions are not the protocol standards.

The chain is **EVM-connected at the liquidity edge** — value moves in and out through an external interop provider and issuer-supported integrations, rather than an in-tree cross-chain bridge. Once value arrives, it settles through Mono-native standards on a Rust/RISC-V execution layer.

### 4.4 No fungibility between public and private money

The design separates **public** and **private** LYTH and forbids a reverse private-to-public crossing. The confidential value path that would create and move amount-hidden private LYTH was removed after audit, so it is not usable today. Any replacement must preserve the rule that private-denominated value cannot enter contracts, markets, interop, delegation, or a future discovery registry. See §9.

### 4.5 No bundled AI model

The chain does not bundle a specific AI model with the protocol. The target agent identity is provider-independent, and future economic action schemas would be typed and wallet-visible rather than treated as AI prompts. Those schemas are not activated today.

---

## 5. Six Design Positions

The chain's identity is the product of the six commitments below. Each is structural, not parameterised.

### 5.1 Post-quantum accounts by default

ML-DSA-65 (NIST FIPS 204, Dilithium Level 3) is the only signature primitive accepted at transaction admission. No classical fallback. No hybrid mode. No ECDSA acceptance path "for compatibility." Every account signs every transaction with a post-quantum primitive from the chain's first block.

Hybrid is rejected for three reasons. If consensus accepts **either** signature, the scheme is only as strong as its weakest component — a quantum adversary forges the classical half and the post-quantum half is never examined. If consensus requires **both**, the post-quantum primitive is already carrying the whole quantum defense alone, and the classical half hedges the opposite risk (a classical break of the lattice assumption), which Monolythium answers with process — emergency freeze plus a coordinated migration — rather than a second signature on every transaction forever. Hybrid also creates audit ambiguity and downgrade-attack surface, and it postpones the migration twice (once now, once later) instead of doing it once at genesis when there is no installed base of classical-only wallets to support.

The cost of pure post-quantum is signature size — ML-DSA-65 signatures are ~3,309 bytes versus ECDSA's 64 bytes. The cost is real and paid in storage and bandwidth. The alternative is paying the migration cost twice.

| Layer | Primitive | Use |
|---|---|---|
| User signatures | **ML-DSA-65** (FIPS 204) | Every user-signed transaction |
| Crypto-agility backup | **Future genesis; primitive not selected** | The removed SLH-DSA registry is not available; a second-family design requires independent review |
| Key encapsulation | **ML-KEM-768** (FIPS 203) | Peer-to-peer handshakes (a KEM-Noise IK-style construction of our own, pending cryptographer review), RPC TLS, stealth-address derivation |
| Consensus signatures | **ML-DSA-65** (FIPS 204) | Per-operator vertex signatures; cluster 7-of-10 quorum is a bitmap multisig of independent operator signatures |
| Zero-knowledge verification (gated off) | **Post-quantum FRI/STARK — intended direction** | Application-layer proof verification is **disabled at genesis**; the earlier SP1 zkVM + Groth16-BN254 verifier is not enabled. Consensus finality is pure ML-DSA-65 and never depended on it |
| Hash | **BLAKE3** | State-tree leaves, Merkle commitments, address derivation |

### 5.2 Post-quantum finality

The chain delivers a single, post-quantum finality tier, with no classical fast-path and no separate checkpoint tier:

- **Anchor-level finality** (roughly four to eight seconds, ML-DSA-65). Each operator signs its cluster's vertex with its own ML-DSA-65 key; the cluster's 7-of-10 quorum certificate is a bitmap multisig of those independent operator signatures. Used for everyday transfers, application interactions, mempool admission, and equally for external interop attestations, exchange listings, and high-value cross-chain settlement.

Because every anchor is already finalized under post-quantum signatures, there is no quantum-forgeable tier to outrun: an attacker who cannot forge ML-DSA-65 cannot forge an anchor. Integrations wanting deeper economic finality wait for more confirmations, not for a separate signature tier.

### 5.3 Rust on RISC-V

The execution layer has three tiers:

1. **Native protocol modules** for activated hot and security-critical primitives; agent-commerce registries and spending policy remain separately gated target modules.
2. **Rust/RISC-V contracts** for application-specific programmable logic.
3. **zkVM-proven computation** *(gated off at genesis)* — a future application-layer verifier for high-cost off-chain verification and, when armed, verified-matching swaps and zkML; not reachable today, and cross-chain interop runs through an external provider (§11), not in-tree bridge proofs.

Why this combination:

- **Rust** provides strong compiler feedback, ergonomic testing and fuzzing, and better alignment with AI-assisted development than Solidity. The Rust ecosystem has fifteen years of training data; Solidity does not.
- **RISC-V** is open, simple, portable, deterministic, and aligned with the zero-knowledge proving ecosystem. The chain rides that convergence rather than fighting it.
- **Native modules** mean common asset and market logic is audited once at the protocol level. Applications compose against audited primitives rather than reimplementing them.
- **Cleaner audit surface** because the heaviest financial logic lives in the well-audited core, not in thousands of independent contracts.

### 5.4 Native modules and MRC standards

Instead of asking every application to rebuild core financial primitives as arbitrary smart contracts, the chain provides audited native modules and Mono-native standards.

| Ethereum convention | Monolythium target |
|---|---|
| ERC-20 | **MRC-20** fungible tokens |
| ERC-721 | **MRC-721** non-fungible tokens |
| ERC-1155 | **MRC-1155** multi-assets |
| ERC-4626 | **MRC-4626** vaults |
| ERC-1271 / ERC-4337 patterns | Native smart-account and policy-account standards |
| Solidity marketplace contracts | Native marketplace modules and Rust/RISC-V contracts |
| Contract-based AMMs and order books | Native spot-market modules with contract hooks |

Wallets and explorers display MRC assets as **first-class assets**, not as arbitrary contract calls. When a user receives an MRC-721, the wallet knows it is an NFT with a typed schema, not an opaque series of bytes that might or might not implement an interface correctly.

### 5.5 Cluster marketplace

Monolythium does not have validators in the traditional single-operator sense. It has **clusters**: 7-of-10 operator-threshold groups that produce one logical cluster vertex per cluster, per consensus round. At target scale, **100 clusters × 10 operators = 1,000 operator positions** (700 active + 300 standby).

Cluster membership is a **public market**. Operators publish their node attestation (hardware class, network metadata, geographic claim, uptime, service-tier capacity), and clusters compose themselves from operators offering complementary skills — a bare-metal operator in one region for throughput, a cloud operator in a second for diversity, a home operator in a third for jurisdiction, a GPU-equipped operator for the prover service tier, an archive-capable operator for RPC.

Stakers see all of this through wallet and explorer surfaces and delegate accordingly. The "best validator" is not picked by social reputation; it is composed in public by people reading the same data the chain reads.

The cluster model gives the chain three structural advantages over single-operator designs:

- **Operator-level fault tolerance** — a single operator's outage does not stop the cluster (7-of-10 threshold, three operator failures tolerated).
- **Operator diversity** — operators within a cluster can be in different regions, on different network providers, on different hardware classes, and under different jurisdictions.
- **Operator markets** — operator capacity is a public market; reputation accrues to the operator identity over time and is not owned by any single venue.

A hard per-operator multi-cluster cap prevents a successful operator from reproducing single-operator centralisation across the cluster set.

### 5.6 Bifurcated denomination

The target design makes public and private LYTH non-fungible and permits no private-to-public crossing. Stealth-address recipient privacy and privacy-policy code remain in v0.4.0; the confidential value path—public→private creation, amount-hidden transfer, and burn—was **removed**, not merely gated. See §8.

---

## 6. Target Agent-Commerce Architecture

This section condenses a future design. The current public development network does not expose these eight primitives as an executable suite. Names, state machines, method vocabulary, fees, events, and layer assignments below are requirements—not a current ABI.

| # | Primitive | Target layer | Intended purpose |
|---|---|---|---|
| 1 | `attestation` | Target native module | Signed-hash + typed-schema registry |
| 2 | `consent` | Target native module | Principal-signed records with revocation |
| 3 | `issuer-registry` | Target native module | Permissionless credential-issuer registry |
| 4 | `discovery` | Target native module | Permissionless service-listing registry |
| 5 | `reputation` | Target indexer view | Multi-dimensional aggregation over finalized events |
| 6 | `availability` | Target native module | Availability state for domain registries |
| 7 | `escrow + arbiter-registry` | Target native modules | Escrow, counter-offer, and arbitration |
| 8 | `spending-policy` | Target consensus module | Per-account constraints enforced at admission |

In the design, only `spending-policy` would consume the consensus path; reputation would remain an indexer view. Neither statement implies current deployment.

Two primitives are worth calling out:

The **escrow target** uses an `Open → Negotiating(round_n) → Accepted → InProgress → Submitted → Released | Disputed` state machine. Exact transitions and arbitration contracts require a versioned protocol release.

The **spending-policy target** requires admission-time enforcement so the delegated agent cannot opt out. No current public RPC offers that policy surface.

### Runbooks

The target requires **typed, versioned, wallet-visible actions** rather than free-text RPC. Provisional names include `pay_vendor`, `open_escrow`, `release_escrow`, `refund_payment`, `book_service`, `place_trade`, `set_spending_policy`, `revoke_agent_permission`, `verify_receipt`, and `rate_vendor`.

These are not current SDK methods or MCP transaction tools. The intended safety property is that a released wallet and activated protocol validate the same schema while the user retains authority.

### Stele boundary

Stele's release architecture is a standalone public web product. As of 2026-07-16, the public preview is live at [stele.monolythium.com](https://stele.monolythium.com) with zero published services. Browser Wallet v0.4.5 is a prerelease; it owns identity proof, while Stele's hosted services never receive wallet secrets. Hosted Stele MCP is keyless and exposes exactly two OAuth-protected tools: public catalog search and bounded, non-economic booking-draft preparation. The isolated local Stele MCP exposes exactly three read/status tools and no transaction tool. Neither MCP holds a wallet, signs, broadcasts, or settles. Economic writes, transaction signing, and mainnet remain off. Provider publication, E2EE rooms, settlement, disputes, and reviews remain separately gated. The target desktop product line retires the Stele marketplace surface; legacy or unreconciled desktop builds may retain a gated historical surface until reviewed removal and migration are released.

---

## 7. Identity: Addresses, Mnemonics, and Names

### Bech32m-only display

User-facing addresses are displayed in **bech32m** format only. Hex `0x...` display is not the canonical surface. The `mono` human-readable prefix and bech32m checksum make Monolythium addresses visually unmistakable from any other chain's `0x...` format, providing format-as-safety against cross-chain address confusion at exchange listings, bridge UIs, and partner integrations.

Per-type prefixes signal the address's role at a glance:

| Prefix | Address class |
|---|---|
| `mono1...` | Standard user account |
| `monos1...` | Stake / delegation account |
| `monoc1...` | Contract account |
| `monok1...` | Cluster account |
| `monom1...` | Native module account |
| `monox1...` | External-interop (bridge) account |

### Wallet recovery — PQM-1 removed

PQM-1 and its algorithm-tagged seed layout must not be used. The canonical mnemonic input is a standard 24-word BIP-39 phrase re-derived for ML-DSA-65 as `mldsa_seed = SHAKE256("monolythium.mldsa65.v1" || bip39_pbkdf2_seed(mnemonic, ""))[0:32]`.

The browser wallet uses an Argon2id/XChaCha20-Poly1305 encrypted vault in extension-local storage. That is not a generic OS-keychain or biometric guarantee, and network selection does not change derivation. Cross-client recovery—especially with the desktop wallet—must be tested before compatibility is claimed. Stele and hosted MCP never receive a mnemonic.

### LYTH name registry

A hierarchical, on-chain name registry maps human-readable names to addresses. Lowercase ASCII letters, digits, and hyphens; no mixed case, no Unicode confusables. Names live under the `.mono` namespace and resolve to five structural categories: a bare `<name>.mono` is a human/personal account, an agent registers beneath its human principal as `<name>.agent.<human>.mono`, and clusters, contracts, and protocol entities take `<name>.cluster.mono`, `<name>.contract.mono`, and `<name>.system.mono` (the system category is foundation-only). U-curve pricing discourages both squatting (short names cost more) and clutter (long names pay a small administrative fee). Transfer is propose-accept with a 24-hour acceptance window. Reserved prefixes prevent collisions with bech32m HRPs and `0x` strings.

A person is addressed as `alex-rivera.mono`, their agent as `support-bot.agent.alex-rivera.mono`, and a cluster as `northstar.cluster.mono`. The bech32m address remains the canonical underlying identifier; the name is a human-readable alias.

---

## 8. Bifurcated Denomination — Privacy Without Contamination

> **Design-status boundary.** The confidential value implementation was deleted after audit. This section preserves the required cordon and one-way economic design for a future post-quantum replacement; it does not describe usable amount-hidden value today.

Privacy on a public ledger has, over the last several years, been on a steady regulatory collision course. The two historical trajectories are visible:

- A chain with **fungible** shielded and transparent denominations gets delisted by major exchanges because shielded-to-transparent flow contaminates the entire public denomination. Fungibility breaks the audit story for everyone.
- A chain with a **single private-by-default** denomination gets delisted because there is no public denomination to clear. The audit story is "we cannot tell you anything."

Both trajectories converge on the same outcome. Monolythium's bifurcation is a third option that has not been deployed at scale.

### How bifurcation works

The target protocol enforces non-fungibility at the consensus layer with separate public and private state. A native **caller-origin cordon** prevents public modules from receiving private-denominated value and prevents private state in a public contract context. Stealth-address recipient privacy and privacy-policy code remain in v0.4.0; confidential amount transfer does not.

Any future **crossing** must conserve value exactly once and omit a reverse instruction. The removed construction cannot be re-armed; a replacement requires a post-quantum design, conservation proof, independent audit, and separate activation.

### What this gives a regulator or an exchange

The **public denomination** is fully auditable. Public activity is transparent and traceable by the analytics tooling that already exists for other transparent chains. A KYC-supervised exchange can custody public LYTH with the same audit posture as any other transparent asset.

The **private denomination** is opaque by design. The protocol does not pretend otherwise. An exchange may refuse private deposits, require a proof-of-crossing, or accept them at a higher KYC tier. The chain does not constrain the choice; the chain provides the structural separation that makes the choice coherent.

### Side effect — structurally hostile to illicit commerce

The target cordon forbids private-denominated value from any future discovery, escrow, or dispute module. Public Stele catalog data is transparent and non-economic; it is not an activated on-chain discovery registry.

> *Monolythium separates monetary privacy from commerce. The private denomination supports peer-to-peer transfers only — it cannot pay for services, interact with smart contracts, or trade. The public denomination supports full commerce and is fully transparent and analyzable.*

---

## 9. Consensus — Starfish-C

The consensus engine is **Starfish-C**, a DAG-BFT protocol with:

- **Four-second deterministic finality** under partial synchrony (four to eight seconds typical, with an outer bound of about twelve seconds under degraded networking before view-change).
- **Deterministic linearization** of the DAG — two honest clusters starting from the same DAG state derive byte-identical block sequences.
- **Bounded reorg** capped by protocol parameter; an adversary cannot force a deeper reorg without controlling more than f Byzantine clusters.
- **Post-quantum leader-seed beacon**: wave leadership derives from a domain-separated, chain-id-bound BLAKE3 hash of the ML-DSA-65 quorum certificate that already finalizes each anchor, so every cluster derives the same leader and an adversary cannot grind it (the certificate is post-quantum and agreed before the next leader is known).
- **100% slash + permanent operator exile** on equivocation. The slash is exemplary, not merely punitive; a protocol that destroys the equivocating operator's stake and bars them forever does not need to tolerate equivocation.

The user-facing finality unit is the **anchor**. Multiple internal layers exist — vertex (cluster's signed round payload), wave (round of vertex production), anchor (deterministic linearization point), and block (preserved only for EVM-style RPC compatibility such as `eth_blockNumber`).

The mempool is plaintext: a transaction body is visible from the moment it enters the mempool until anchor inclusion, and the protocol does not seal or encrypt mempool contents. Transaction-ordering fairness is addressed at the DAG-consensus layer rather than through mempool encryption — ordering follows the deterministic DAG linearization, not a single sequencer's discretion, so a plaintext order is sequenced by consensus rules rather than by privileged pre-inclusion reads.

---

## 10. Tokenomics

> **Design-status boundary.** The values below record the v5 tokenomics charter. Unless independently observable from finalized chain state, they are target parameters—not proof of current balances, rewards, bonds, vesting, sale terms, yield, or holder rights. The stale RPC observed on 2026-07-16 is not evidence of current economic operation. Agent-commerce fees, registry bonds, service-tier payments, and delegation economics remain separately gated.

### 10.1 Supply

- **Initial supply.** 100,000,000 LYTH at genesis.
- **Annual inflation cap.** 8% — a protocol-layer hard cap. Lifting it requires a coordinated hard fork.
- **Treasury funding.** Pre-funded from the genesis reserve; no inflation tap. Treasury draws on the reserve and on buyback-burn yield over time.

The supply structure is constitutional. The inflation cap, the treasury's funding mechanism, and the basic distribution rules are not changeable through any in-protocol process.

### 10.2 Allocation

| # | Category | LYTH | Share |
|---|---|---:|---:|
| 1 | Community obligations (pre-allocated genesis balances) | 32,781,503.90 | 32.78% |
| 2 | Foundation treasury reserve | 15,000,000 | 15.00% |
| 3 | Ecosystem & grants | 15,000,000 | 15.00% |
| 4 | Core contributors (vested) | 13,000,000 | 13.00% |
| 5 | Public sale & community access programs | 12,000,000 | 12.00% |
| 6 | Operator incentives & community programs | 7,218,496.10 | 7.22% |
| 7 | Liquidity provision & integration support | 5,000,000 | 5.00% |
| | **Total** | **100,000,000.00** | **100.00%** |

Category 1 is a frozen ledger of 732 historical community-cohort entries pre-allocated as on-chain genesis balances. No claim flow is required; each entry resolves directly to a balance on the holder's chain address.

Category 4 vests on a 12-month cliff with 48-month linear vest.

### 10.3 Utility — LYTH at every layer

LYTH accrues utility across the entire chain surface, not only at the gas layer:

- **Consensus.** Each active operator position requires a 5,000 LYTH self-bond; standbys bond at the same level. Equivocation slashing burns the entire bond.
- **Network.** Every transaction pays gas in LYTH, including transactions moving stablecoins, MRC assets, or NFTs. A portion of every transaction's gas is burned.
- **Service tiers.** The target model denominates released RPC and archival service contracts in LYTH. This is not proof of a paid public endpoint. GPU prover and oracle-feed payment paths remain gated.
- **Interop.** Cross-chain interop runs through an external interop provider rather than an in-tree bridge, so the protocol no longer charges in-protocol bridge-route fees or runs bridge insurance and reserve programs; value arriving through the provider still pays LYTH gas once it transacts on-chain.
- **Registries.** Future discovery, issuer, and arbiter registries may use published LYTH-denominated anti-spam terms; those §6 paths are not activated.
- **Markets.** Native order-book maker/taker fees pay in LYTH or in the asset traded (with a LYTH-denominated discount path).
- **Agent commerce.** If §6 is activated, its versioned fee and settlement contracts may use LYTH; no current fee or settlement path is asserted.

The target economic thesis is that activity in other assets would still require LYTH-denominated protocol resources. It is not a current API-payment or service-yield claim.

### 10.4 Liquid bonding and distributed delegation

Monolythium's staking model is **liquid bonding**: stakers retain custody of their LYTH at all times. There is no staking contract to send funds to. There is **zero unbonding period** for delegators. A delegator can exit a delegation instantly. Slashing applies to operator self-bonds, not to delegators.

The core anti-capture mechanism is the **per-wallet delegation cap**: any single wallet can delegate at most X% of its total LYTH holdings to any single cluster. The cap binds on **capital**, not on wallet count, so an adversary splitting capital across many wallets gains no advantage.

| Network condition | Per-cluster cap | Minimum diversification |
|---|---|---|
| Early operating set | 50% | 2 clusters |
| Growing operating set | 25% | 4 clusters |
| Mature operating set | 15% | 7 clusters |
| Steady-state operating set | 10% | 10 clusters |

Tightening is triggered by sustained network conditions (number of independent clusters, geographic distribution, operator entropy), not by calendar dates and not by any in-protocol vote. Modifying the schedule requires a coordinated hard fork.

The cap composes with a **service-weighted reward layer**: a cluster's share of the cluster reward pool is set by the **proven useful services it provides** — archive serving, GPU proving, public RPC, indexing, and geo/client diversity — not by how much stake is delegated to it. Stake sets only a cluster's rank for top-100 active-set admission; once admitted, clusters vote with equal weight and earn strictly in proportion to proven service, so two clusters with equal service earn equal pots regardless of stake. Decentralization is the highest-yield strategy at every margin — the way to earn more is to serve more, not to accumulate stake.

### 10.5 The four-button autovote

The v5 design proposes an **Intelligent Autovote** wallet surface with four named modes. It is a UX target, not a current shipped-feature claim:

- **Max Yield** — allocate to highest-APR clusters consistent with the per-cluster cap.
- **Max Diversity** — spread across as many independent clusters as the current cap allows.
- **Max Decentralization** — actively route stake away from clusters with high correlated-preference or geographic concentration scores.
- **Custom** — manual per-cluster allocation, with the cap enforced at submission time.

---

## 11. Interop and the Liquidity Edge

Monolythium needs liquidity but does not need EVM execution to get it — and it no longer ships an **in-tree bridge** to get it either. The entire in-tree bridge stack — the on-chain bridge proof verifier, the route/fee/insurance scaffolding, and the associated build feature — has been **removed** from the protocol. The chain does not verify bridge proofs on-chain.

Cross-chain interoperability is instead delivered by integrating an **external interop provider** (evaluation in progress; described here vendor-neutrally). Running the chain's own bridge verifier in-tree concentrated the highest-risk, audit-heavy surface inside consensus; moving interop to an external provider takes that surface out of the core, lets interop evolve without a re-genesis, and keeps the base layer post-quantum and lean. The liquidity strategy is now two layers:

1. **External interop-provider integration** for moving major external assets in and out — verification, routing, and settlement of the cross-chain leg are the provider's responsibility, not the protocol's.
2. **Issuer-supported native assets** where the network earns enough adoption to justify direct issuer integrations.

**Wrapped assets are labeled honestly.** An asset that arrives through the external interop provider is not the same as a native issuer-minted asset. Wallets and explorers surface the provider, route, trust model, and any provider-side risk metadata, and mark clearly which assets are native and which arrived through an external provider.

> The goal is not to hide interop risk; the goal is to make interop risk legible.

Because the chain does not itself verify the cross-chain leg, the trust model for any incoming bridged asset is the **external provider's** trust model — any drain caps, circuit breakers, cooldowns, or route verification are provider properties surfaced to the user as provider metadata, not guarantees enforced by Monolythium consensus. The retired `0x1008` bridge precompile is a fail-closed tombstone; the node refuses to boot any milestone that would attempt to activate it.

---

## 12. Hardware Sovereignty — Monarch OS

Production operators run on **Monarch OS** — an immutable substrate built on a minimal Linux base, hardened for institutional security and designed for permissionless accessibility. A home operator with a recent gaming PC runs on the same substrate a co-located bare-metal operator runs.

- **Immutable signed image.** No package manager. No SSH. No interactive shell. The system is purpose-built for operator workloads.
- **Verified rooted filesystem.** Every block of the filesystem is verified against a signed Merkle root at read time.
- **TPM 2.0 measured boot.** Boot-sequence hash measurements are extended into TPM PCRs. The system can prove what it booted via TPM PCR quotes.
- **TPM-sealed operator signing key.** An operator's ML-DSA-65 consensus signing key is sealed against the local TPM. Opening the chassis or modifying firmware breaks the seal and forces re-onboarding.
- **No userspace foothold for kernel exploits.** A modern class of kernel local-privilege-escalation bugs requires a local non-privileged userspace foothold; Monarch OS structurally denies that foothold.
- **Aggressively trimmed kernel.** The userspace cryptographic kernel API is disabled at kernel-config level — all crypto runs in-process via Rust libraries, not via kernel crypto sockets. The entire class of kernel-CVE attacks against userspace crypto APIs is closed off going forward.

Operators publish **TPM PCR quotes** every epoch to the on-chain node registry. A change in PCR values that is not preceded by a coordinated upgrade announcement is treated as an anomaly. The chain stores the attestation; explorers display it; cluster members verify against expected values. It becomes cryptographically observable when a corporate hypervisor or unauthorized management layer is introduced underneath a Monarch node.

Network-level and geographic diversity scoring is layered on top — distinct IP per operator, on-chain ASN recording, geographic claims cross-checked against IP geolocation and latency triangulation, hosting class derived from PCR patterns. Diverse clusters earn delegator preference; concentrated clusters lose it.

---

## 13. Recovery Posture

The audited SLH-DSA backup, emergency-key registry, and on-chain user-key rotation were removed as inoperative. The v0.4.0 protocol is ML-DSA-65-only. A second-family backup and protocol rotation path are future-genesis work requiring independent cryptographic review; no user should believe a backup key is registered today. A break-day migration therefore depends on the separate time-bounded emergency freeze plus a coordinated hard fork, with public operational playbooks required before mainnet.

### Emergency freeze — scope and limits

A multi-signature Foundation key with a declared signer set and ratification window can pause transaction admission during a confirmed cryptographic-primitive break or a confirmed adversarial fork. (Cross-chain interop runs through an external provider outside consensus, so pausing a compromised interop route is the provider's control surface, not a Monolythium freeze action.) The freeze is **not** for routine upgrades, parameter changes, protocol-direction decisions, asset confiscation, ongoing supervision, or censorship of specific accounts.

It is a circuit breaker — a documented, accountable, time-bounded path through a worst-case event, instead of relying on improvisation under duress. The chain's no-governance design (§4.1) and the freeze mechanism are compatible exactly because the freeze is scoped to events with clear, observable triggers, not to ongoing decisions about how the protocol should evolve.

---

## 14. Threat Model in One Page

Monolythium's threat model assumes some operators are Byzantine, external interop is an active attack surface, private keys can be stolen, governance can be socially engineered (which is one reason the chain has none), and cryptographic primitives may eventually fail. The defensive posture is **separation of blast radius** — different surfaces have different protection budgets, and a failure at one surface should not compromise another.

| Surface | Primary protection | Failure scope |
|---|---|---|
| Consensus | Cluster threshold + equivocation slash + DAG-BFT mathematics | Halts safety; protocol rejects equivocating operators and degrades gracefully |
| User signatures | ML-DSA-65 only; future crypto agility requires a new genesis | A primitive break has no current on-chain per-user rotation path; emergency response is freeze plus coordinated hard fork |
| Interop (external provider) | Cross-chain verification and routing run with an external interop provider, outside consensus; wallets surface the provider's trust model and risk metadata | Interop failure bounded to the provider and the assets that transited it; consensus and native accounts unaffected — the chain neither verifies nor custodies the cross-chain leg |
| Mempool | Plaintext mempool; transaction-ordering fairness handled at the DAG-consensus layer | Transactions are visible before inclusion; ordering follows deterministic DAG linearization rather than a single sequencer's discretion |
| Application contracts | Audit + native modules + sandbox boundaries | Contract bug damages the contract's users; native modules and consensus layer insulated |
| Hardware | TPM PCR attestation + immutable substrate + diversity scoring | Compromised operator detectable through PCR drift; concentrated hosting class detectable through diversity scoring |
| Recovery | Time-bounded emergency freeze + coordinated hard fork | No current emergency-key registry or frozen-account claim ABI exists |

**What the chain does not promise**: that operators will not be compromised, that an external interop provider will never be exploited, that smart contracts will not have bugs, that cryptography will work forever, or that no user will lose funds to social engineering. Honesty about limits is part of the threat model — a chain that claims invulnerability is a chain whose users are unprepared when invulnerability fails.

### MEV

MEV is bounded structurally by the chain's design. A post-quantum leader-seed beacon, derived from a domain-separated, chain-id-bound BLAKE3 hash of the ML-DSA-65 quorum certificate the quorum already committed before the next leader is known, forecloses leader-grinding through block-content selection. The native order book settles deterministically against the consensus order rather than against a single sequencer's discretion, so order-book MEV games are bounded by the DAG linearization. The mempool is plaintext, so the chain does not claim MEV is zero — some backrunning of public events and inter-market arbitrage exists wherever transactions are visible — but the leaderless DAG ordering and deterministic order book remove the sequencer-discretion and leader-grinding categories.

---

## 15. Market Positioning

Monolythium does not have a perfect mirror competitor. Its differentiated combination is:

- AI-agent settlement as a primary category;
- Rust/RISC-V-native execution from the base layer;
- post-quantum accounts as default, not optional;
- native MRC token, NFT, and market modules, plus a target agent-commerce architecture;
- external interop-provider liquidity rather than EVM execution compatibility;
- no on-chain governance;
- no mainnet perpetuals;
- structurally non-fungible public/private denomination;
- a public cluster marketplace with distributed validator technology;
- a lean, post-quantum core that keeps cross-chain interop (external provider) and application-layer zero-knowledge verification (a post-quantum FRI/STARK verifier, gated off) out of consensus;
- target composition with major agent-payment standards after compatible integrations are released.

For agent commerce, neutrality matters because agents transact across companies, model providers, wallets, jurisdictions, and service providers. Monolythium's target is such a neutral substrate; the current capability boundary above must not be mistaken for delivery of that target.

---

## 16. Honest Limitations

The chain's direction is a strategic bet. The risks are real and named.

- Some developers will not migrate from Solidity to Rust.
- Liquidity may arrive more slowly without direct EVM compatibility.
- Wallets and explorers require more custom work than they would on an EVM chain.
- Native MRC standards must earn trust before they reach ubiquity comparable to ERC standards.
- Rust/RISC-V contract tooling must be excellent — anything less than excellent loses to a familiar EVM environment.
- Interop depends on an external provider; the security and availability of cross-chain movement is bounded by that provider's trust model and is not verified by Monolythium consensus. A post-quantum application-layer zero-knowledge verifier (FRI/STARK) is still ahead and ships gated off.
- The market for agent commerce may take longer to mature than expected.
- Post-quantum signatures are larger than classical signatures, raising storage and bandwidth costs. This is most visible in consensus: each anchor's quorum certificates carry raw per-operator ML-DSA-65 signatures (3,309 bytes each, seven per 7-of-10 cluster), so a certificate grows linearly with the number of voting clusters. This is a deliberate cost of post-quantum, stateless consensus, not an oversight.
- Distributed validator technology has not been deployed at the chain's target scale in a leaderless DAG-BFT configuration; the operational learning is ahead, not behind.
- The bifurcated denomination is structurally hostile to certain user expectations from existing privacy chains; users coming from those chains will find the constraints unusual.
- The composition stance depends on the major agent-payment standards remaining open and composable. A standard that closes its integration surface would constrain the wedge for that particular rail.

These are not footnotes. They are the cost of choosing a distinct category. The counter-risk is also real: becoming another EVM-compatible chain may make adoption easier at first but leave the project buried under stronger incumbents, deeper liquidity, and thousands of similar competitors. The chain accepts the harder path because the easier path leads to a category in which it is already too late to win.

---

## 17. What Success Looks Like

Monolythium succeeds if it becomes a credible settlement layer for AI agents acting on behalf of human or organizational principals, human-to-agent commerce, agent-to-agent commerce, payments, token and NFT issuance, spot markets, cross-chain swaps, safer cross-chain interop through external providers, and long-lived post-quantum digital identities.

Structural success indicators independent of any single market hype cycle:

- the number of independent clusters and the geographic and ASN distribution of their operators;
- the depth of the discovery registry and the number of legitimate providers it hosts;
- the volume of escrowed agent-to-agent and human-to-agent transactions;
- the share of cross-chain volume moving through proof-verified external-provider routes versus trusted-multisig routes;
- the volume of agent-payment-standard composition (x402, AP2, ACP, MCP) settling against Monolythium spending policies and escrows;
- the diversity of MRC asset issuers;
- the survival of agent identities across model providers — the structural portability of reputation.

A network that scores well on these is a network that has delivered what the design promised. A network that scores well on token price alone has not.

---

## 18. Closing

Monolythium is a deliberate break from the default Layer-1 playbook.

It does not try to win by becoming a slightly faster EVM chain. It chooses Rust on a deterministic RISC-V target, post-quantum accounts as default, native asset standards, native markets, a target agent-commerce architecture, external-provider interop, a lean post-quantum core, a structurally separated privacy design, a public cluster marketplace, and a smaller protocol surface.

It aims to compose underneath major agent-payment standards rather than fight them, after the chain-anchored policy, escrow, identity, and reputation surfaces are activated.

That choice is harder. It means more tooling, more education, and a slower path to existing Solidity liquidity. It also gives the chain a clearer identity and a stronger foundation for the workloads it expects to serve.

The thesis is straightforward: the next major settlement layer will not be the chain that copies Ethereum most closely. It will be the chain that gives new economic actors — autonomous agents, organizations delegating to software, services that want neutral cross-platform rails — safer rails to transact across applications, markets, and jurisdictions.

---

## Read Further

This lightpaper distils the reconciled [Monolythium Whitepaper v5.1 text](monolythium-whitepaper-v5.0.md). For design detail, threat model, cryptographic specifications, consensus mathematics, cluster operations, recovery posture, and citations, the whitepaper is the canonical reference. Neither document is an API reference or proof of current network liveness.

---

## Entities

Monolythium is operated and stewarded by two entities:

- **Mono Labs R&D LLC** — the operating company, based in San Francisco, California. Mono Labs R&D LLC develops the Monolythium protocol, operates the reference client and SDK, and is the seller of record for the LYTH token in jurisdictions where a seller of record is required.
- **Monolythium Foundation** — the protocol steward, based in the Cayman Islands. The removed emergency-key registry is not among its current protocol functions. Any treasury, name-reserve, or emergency-freeze authority must be verified against separately published, current artifacts rather than inferred from this historical v5 design.

The two entities are independent, with separate governance, separate financial accounts, and separate roles in the protocol's operation.

---

## License

The text of this lightpaper is licensed under the **Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0)**, the same license as the whitepaper it summarises.

Attribution string:

> *Monolythium Lightpaper, v5.0 (May 2026), Mono Labs R&D LLC, licensed under CC BY-SA 4.0.*

The Monolythium protocol source code is licensed separately under the Business Source License 1.1, with a four-year commercial restriction window before automatic conversion to a permissive license. Selected execution crates ship under MIT.

---

*End of Monolythium Lightpaper v5.0.*
