# DRAFT — MRV app-contract parity (not published)

> **Status: DRAFT. Do not publish.** This folder holds proposed editorial changes
> for a future whitepaper revision. It is **not** part of any released
> whitepaper. The canonical released text remains the dated files under
> `2026/may/`. Nothing here changes those files, the README "Latest" links, the
> CHANGELOG, or any PDF/HTML artifact. Publishing is a separate, deliberate step.

## What this is

The node is gaining application-contract parity work that activates at a
foundation-signed milestone height (referred to as **N**):

- three host-context syscalls — `block_timestamp`, `chain_id`, `call_value`;
- a synthesized rich receipt (`RiscvReceipt`) sidecar for bare deploys;
- hardened call-frame metering.

The deploy / call / constructor lane is already live and ungated; only the bits
above activate at N.

This draft proposes two whitepaper edits to keep §14 (Execution) and §4.3 (No EVM
execution) accurate once that work lands:

1. `14.2-host-syscall-abi-addition.md` — an addition to §14.2 documenting the
   three host-context syscalls as a consensus-fixed, deterministic extension.
2. `4.3-framing-reconcile.md` — a revised §4.3 that keeps the "no EVM bytecode"
   refusal while clarifying the chain provides an **EVM-equivalent host context**
   for ported application logic.

Both are written against the v5.1 text currently in
`2026/may/monolythium-whitepaper-v5.0.md` (header "v5.1 — June 2026").

## Editorial guardrails carried into these drafts

- Keep the determinism claim intact. `block_timestamp` exposes the
  consensus-fixed anchor timestamp, **not** a host wall clock; §14.1's "no wall
  clock" statement stays true.
- Keep the refusal. The chain still does not execute EVM bytecode and Solidity is
  still not the default model. "EVM-equivalent host context" describes the shape
  of block/call metadata exposed to ported app logic, never bytecode-level
  compatibility.
- No activation height is stated. Downstream learns activation through the
  `lyth_capabilities` `runtimeFeatures` gate `mrv_app_contract_parity`.
