---
id: D-001
type: charter
title: Approve the Forge Slice 1 charter
status: proposed
jira: FORGE-2
proposed_by: agent
proposed_at: '2026-10-18'
options:
- text: Approve the charter in docs/PROJECT.md as written
  recommended: true
- text: Approve a smaller charter with C1 to C3 only (no benchmark, no exit bar)
decision: null
by: null
at: null
delegated: false
subject: docs/PROJECT.md
---
# Approve the Forge Slice 1 charter

## Context

Forge has no approved definition of done. Without one, scope only grows (the factory's charter rule). FORGE-2 asks for a
charter covering Slice 1 of the design (`19-roadmap.md`, Phase S): ticket to verified pull request.

## Evidence

- Slice scope and exit bar: design `19-roadmap.md`; components in `02`, `04`, `08`, `09`, `11`, `12`, `22`.
- No design partners exist, so the design's Phase 0 cannot run as written; the charter substitutes a public-repository
  benchmark (FORGE-7) and says so.
- Tickets: FORGE-4 (gateway), FORGE-5 (sandboxed run), FORGE-6 (policy, evidence, check run), FORGE-7 (benchmark).

## Options

1. **As written (C1 to C6).** Builds the whole slice and measures it. Months of work; the benchmark makes the result
   honest, and C5 and C6 give a clear stop.
2. **Smaller (C1 to C3).** A working governed run that opens a PR, without measuring quality or cost. Faster, but it
   proves the plumbing, not the value, which is what the design's own warning was about.

## Recommendation

Option 1: without C4 to C6 the slice can't fail, so it can't tell you anything.
