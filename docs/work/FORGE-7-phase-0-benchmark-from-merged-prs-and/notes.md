# FORGE-7 notes

## Amendment 1 (2026-10-19): solver is Codex CLI, not Claude Code

**Why:** the owner has an OpenAI API key and no Anthropic key. The spec (approved 2026-10-18) named Claude Code as the
thin-integration solver. Claude Code via the owner's Claude subscription was considered and rejected: it would put the
owner's account login inside solver containers and share usage limits with the agents building forge.

**What changed:** R9 names Codex CLI (`codex exec`), keeps the solver interface open for Claude Code; R8 computes cost
from reported tokens and a versioned price table (Codex reports tokens, not dollars); NFR reproducibility records the
solver CLI and price-table version; the spend-cap assumption names the OpenAI key. Plan T8/T9 and the run paragraph
follow (per-task ceiling enforced by the runner from the token stream, since Codex has no spend flag).

**Fidelity note:** the owner's repositories were built with Claude Code. Codex reads `AGENTS.md`, which points to the
factory skills as files, so the method is available to it, but this is the same method through a different agent. The
Phase 0 report states it.

**Approval:** spec re-approval and plan approval by the non-author agent (antigravity) under FORGE-10 rule 7.
