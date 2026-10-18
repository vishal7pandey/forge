---
id: D-001
type: charter
title: Approve the Forge Phase 0 charter
status: proposed
jira: FORGE-2
proposed_by: agent
proposed_at: '2026-10-18'
options:
- text: Approve the Phase 0 charter in docs/PROJECT.md as written
  recommended: true
- text: Replace it with a full Slice 1 charter (gateway, sandboxed run, policy, check run, benchmark, exit bar)
decision: null
by: null
at: null
delegated: false
subject: docs/PROJECT.md
---
# Approve the Forge Phase 0 charter

## Context

Forge has no approved definition of done. FORGE-2 asks for one. A first draft covered the whole of Slice 1; after the
independent design review (ANSFD-1, design doc 23) the recommendation changed: charter only the Phase 0 gate, which
measures the thin integration of existing agents before any platform is built.

## Evidence

- Design doc 23 (hypotheses H1 to H4, stop, narrow and proceed criteria) and doc 19 (Phase 0 as a hard gate).
- Tickets: FORGE-7 (benchmark and baseline run), FORGE-9 (adversarial set). FORGE-4, FORGE-5, FORGE-6 (slice) are parked
  under FORGE-1 until the decision.
- The FORGE-4 gateway spec is written (PR #5) and stays as a draft; nothing of it is built under this charter.

## Options

1. **Phase 0 charter (C1 to C4).** Weeks, not months. Ends in a proceed, narrow or stop decision with numbers. If it says
   proceed, a charter amendment adds the slice.
2. **Full Slice 1 charter.** Builds gateway, sandboxed run, policy and check run alongside the benchmark. Faster to a
   working platform if the hypothesis holds; months of work wasted if it doesn't, and the review's main finding is ignored.

## Recommendation

Option 1: the review's central point is that the build must be able to fail cheaply first, and only Phase 0 can.
