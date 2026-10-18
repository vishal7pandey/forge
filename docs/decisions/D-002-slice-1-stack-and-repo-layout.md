---
id: D-002
type: design
title: Slice 1 stack and repo layout
status: accepted
jira: FORGE-3
proposed_by: agent
proposed_at: '2026-10-18'
options:
- text: One Python package for the slice (src/forge/<component>), split later behind
    the published interfaces
  recommended: true
- text: Multi-language monorepo now (Go services, Python agent, Next.js web, shared
    contracts)
decision: One Python package for the slice (src/forge/<component>), split later behind
  the published interfaces
by: Vishal Pandey (delegated to agent)
at: '2026-10-18'
delegated: true
note: Owner tried to accept on 2026-10-18 (answer mistyped), then transferred ownership
  and stewardship of forge to the agents the same day; recorded under that delegation.
---
# Slice 1 stack and repo layout

## Context

The design (`01-architecture-overview.md`) names Python plus Go, with a Next.js web app, and I suggested a multi-language
layout for this repo. Before FORGE-4 is planned, the stack must be fixed, because it decides the package layout, CI and
tooling. Ticket FORGE-3.

## Evidence

- The factory supports `python` fully; `node` is partial and `go` is not supported (`docs/SUPPORT.md` in the factory):
  a Go service would get a placeholder CI.
- Everything the slice reuses has a first-class Python SDK: LiteLLM (gateway providers), Temporal (durable execution),
  Claude Agent SDK and OpenAI Agents SDK (runtimes), OPA via its REST API or the `regorus` engine, Sigstore (signing).
- The slice's web surface is a minimal run view (design `22`, Slice 1 table); it can be server-rendered for now.
- Go's advantages in the design (latency, static binaries for the CLI and gateway) matter at scale and in customer
  installs, neither of which is in the charter.

## Options

1. **One Python package.** `src/forge/{gateway,harness,sandbox,policy,evidence,bench}` with the interfaces from the design
   (gateway client, runtime adapter, sandbox adapter) as the seams. Full factory CI from day one. Splitting a component
   into its own service or language later means re-implementing behind an interface that already has tests.
2. **Multi-language monorepo now.** Matches the long-term design; costs a Go and Node toolchain, hand-written CI for both,
   and cross-language contracts before there is a second consumer of any of them.

## Recommendation

Option 1: it keeps the slice inside what the factory supports today and defers the language split until a measured
need (latency, distribution) appears.
