---
purpose: "Forge turns a ticket into a pull request that a governed AI agent wrote in a sandbox, under policy and a budget, with verification published by the platform and a signed evidence bundle. This build proves Slice 1 of the design in ai-native-software-factory-design, for its owner as a learning lab, before anything else is added."
mode: active
decision: D-001
done:
  - id: C1
    text: "Every model call in Forge goes through the gateway with a model alias, a per-run budget cap and a usage ledger row"
    check: {work: FORGE-4}
  - id: C2
    text: "An implement-change agent run executes in an isolated sandbox with egress deny and opens a pull request on a target repository"
    check: {jira: FORGE-5}
  - id: C3
    text: "Each run records its policy decisions, produces a signed evidence bundle and publishes pass or fail only as a Forge check run"
    check: {jira: FORGE-6}
  - id: C4
    text: "An internal benchmark of tasks mined from merged pull requests of at least two public repositories runs in CI"
    check: {jira: FORGE-7}
  - id: C5
    text: "The benchmark resolved rate (hidden tests pass) reaches at least 0.3"
    check: {metric: {file: docs/metrics/slice1.yaml, key: benchmark.resolved_rate, min: 0.3}}
  - id: C6
    text: "The benchmark cost per resolved task is recorded and stays at or below 5 US dollars"
    check: {metric: {file: docs/metrics/slice1.yaml, key: benchmark.cost_per_resolved_usd, max: 5.0}}
non_goals:
  - "Multi-tenancy, SSO, BYOC or air-gapped deployment"
  - "A web application beyond a minimal run view; the Claude Code plugin, hooks and dispatch (Phase 1)"
  - "Autonomy above L2: agents open pull requests, humans review and merge"
  - "Deploying anything to production, on Forge or on target repositories"
  - "Go services, a marketplace, or any SDLC stage before implementation or after the pull request"
parked: []
---
# Project charter

Forge implements the design in [ai-native-software-factory-design](https://github.com/vishal7pandey/ai-native-software-factory-design),
starting with **Slice 1: ticket to verified pull request** (design `19-roadmap.md`, Phase S; Jira epic FORGE-1).

## Why these criteria

C1 to C4 are the slice's components, one ticket each. C5 and C6 are the slice exit bar. The design's exit bar is
"30% of eligible tickets produce a PR merged with no more than small edits" on design-partner repositories. This build has
no design partners, so Phase 0 (validation with partner teams) is replaced by a benchmark mined from public repositories
(FORGE-7), and "merged with small edits" by its closest offline proxy: the hidden tests of the original merged PR pass. That
proxy is weaker than real merges; the gap is accepted for a learning lab and named here so nobody reads C5 as more.

The 5 US dollar ceiling in C6 is a first guess, to be revised with data from the first benchmark run (a charter amendment).

## Maintenance mode

When every done criterion is met the project enters maintenance mode (`mode: maintenance`, approved through a new
charter decision). In maintenance mode only security and dependency updates are made, through the findings and
dependency loops (`factory-findings`, `factory-dependencies`). Any other change needs a charter amendment: a new
charter decision the owner accepts. `factory feature start` warns, but does not block, so the owner can proceed
deliberately.
