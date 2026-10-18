---
purpose: "Find out, with measurements, whether a governed platform around coding agents produces safer changes than a thin integration of the same agents, at comparable correctness and cost, before building that platform. This is Phase 0 of the Forge design (ai-native-software-factory-design, doc 23), run by its owner as a learning lab."
mode: active
decision: D-001
done:
  - id: C1
    text: "A benchmark of at least 30 tasks mined from merged pull requests with tests, from the owner's repositories and two public ones, with the original tests held out as the oracle"
    check: {jira: FORGE-7}
  - id: C2
    text: "An adversarial set of 10 tasks, each with a deterministic detector for its unsafe outcome"
    check: {jira: FORGE-9}
  - id: C3
    text: "The thin integration has run every benchmark and adversarial task, with resolved rate, cost and wall time recorded per task"
    check: {metric: {file: docs/metrics/phase0.yaml, key: baseline.tasks_run, min: 40}}
  - id: C4
    text: "A Phase 0 report against hypotheses H1 to H3 of design doc 23 exists, with a proceed, narrow or stop decision record for the owner"
    check: {file: docs/phase0/report.md}
non_goals:
  - "Forge platform code beyond the benchmark runner and scorer: gateway, sandboxed runs, policy and check run wait for the Phase 0 decision (FORGE-4, FORGE-5, FORGE-6)"
  - "Validating enterprise demand, buyers or pricing; there are no customers or design partners in this build"
  - "Tuning the thin integration to win or lose: it runs as a team would use it, with the repository's own AGENTS.md and skills"
  - "Deploying anything, on Forge or on the benchmark repositories"
parked:
  - {item: "Slice 1 build (gateway, sandboxed run, policy, audit record, check run), pending the Phase 0 decision", jira: FORGE-1}
---
# Project charter

Forge implements the design in [ai-native-software-factory-design](https://github.com/vishal7pandey/ai-native-software-factory-design).
After an independent review (ANSFD-1), that design makes Phase 0 a **hard gate** (doc 23): the alternative to beat, the
thin integration of existing agents, is measured before any platform is built. This charter covers only that gate.

## Why only Phase 0

A charter that already lists the slice components would authorise the build-out the review warns against: a sophisticated
platform whose infrastructure hides whether it solves a real problem. Phase 0 can fail, and that is its value. The slice
(FORGE-1) is parked until the owner's decision on the report.

## The decision this charter ends with

The report (C4) states, per hypothesis in doc 23, the measured values and thresholds:

- **Stop** if the thin integration is already as safe on the adversarial set (H1 fails) and Forge's expected cost or
  correctness gap can't be closed (H2 or H3 fails): fold the benchmark and adversarial set into the AI Software Factory.
- **Narrow** if only the safety case holds: build the safety wrapper only.
- **Proceed** otherwise: a charter amendment adds the slice criteria (gateway, sandboxed run, policy and audit record,
  check run, and the slice exit bar of doc 19).

Phase 0 measures the baseline only; Forge's own numbers on H1 to H3 come from the slice, against this baseline. The
proceed decision is therefore a bet that the baseline leaves room (unsafe actions on the adversarial set, a correctness
or review-effort gap), not proof that Forge closes it.

## Maintenance mode

When every done criterion is met the project enters maintenance mode (`mode: maintenance`, approved through a new
charter decision). In maintenance mode only security and dependency updates are made, through the findings and
dependency loops (`factory-findings`, `factory-dependencies`). Any other change needs a charter amendment: a new
charter decision the owner accepts. `factory feature start` warns, but does not block, so the owner can proceed
deliberately.
