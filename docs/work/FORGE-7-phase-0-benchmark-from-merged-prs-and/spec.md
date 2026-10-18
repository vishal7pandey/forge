# FORGE-7 — Phase 0 benchmark from merged PRs and thin-integration baseline run

Status: draft · Risk: medium · Jira: FORGE-7
Created: 2026-10-18 · Slug: phase-0-benchmark-from-merged-prs-and

## Problem

Forge's design (design repo, doc 23) rests on the claim that a governed platform around coding agents beats a thin
integration of the same agents. Nobody has measured the thin integration on real work, so there is nothing to beat and
no way to stop early if the claim is false. Without a benchmark whose oracle the agent cannot see, any later "Forge
resolved 40%" would be the agent grading itself.

## Users and context

- **The owner**, who decides proceed, narrow or stop after Phase 0 (charter D-001, criteria C1, C3, C4).
- **Later Forge runs** (FORGE-5), scored on the same tasks against this baseline.
- Grounding: design docs 23 (hypotheses, thin integration), 24 (holdout oracle, link statuses), 12 (internal benchmark
  from history); FACT-31 (paid-model use in evaluations: caps outside the engine, key from the environment only).
- Source repositories: `vishal7pandey/adep` (47 merged PRs, 20 touching both source and tests), `chatpid` (36, 9),
  `ai-software-factory` (23, 13), counted on 2026-10-18; plus two public repositories.

## Goals and non-goals

**Goals**
- A versioned task set built from merged PRs, each task reproducibly failing before and passing after the original change.
- A runner that gives a task to a *solver*, hides the oracle from it, and scores the result.
- A thin-integration solver: Claude Code headless with the task repository's own `AGENTS.md` and skills.
- Per-task and aggregate results the Phase 0 report and the charter metric read.

**Non-goals**
- The adversarial set (FORGE-9); this item only makes the runner able to carry it.
- Any Forge solver (that is FORGE-5, after the Phase 0 decision).
- Tuning prompts, models or skills of the thin integration to change its score.
- A leaderboard, web view or CI job that spends money on every push; paid runs are started by hand.
- Statistical significance beyond what one run per task allows (stated as a limitation in the report).

## Requirements

- R1. The system must mine candidate tasks from merged, non-Dependabot PRs of a configured repository that change both
  source files and test files.
- R2. For each candidate, the system must record: repository, base SHA (the merge's first parent), solution SHA, the
  changed test files (the **holdout**), the oracle command, and a task statement.
- R3. The task statement must come, in order of preference, from the work item `spec.md` the PR carries, else the linked
  Jira issue text, else the PR title and body; it must not contain diff hunks or the holdout tests' content, and its
  source must be recorded.
- R4. The system must validate each candidate: with the holdout applied, the oracle fails on the base SHA and passes on
  the solution SHA; tests outside the holdout that pass on the base SHA are recorded as the regression set. Candidates
  that don't reproduce are excluded with a reason.
- R5. The task set must be versioned: a manifest with a version, the list of tasks and their content hashes; a run
  records the task-set version it used.
- R6. The runner must execute a solver on a task in a fresh, disposable environment that contains the repository at the
  base SHA **without** the holdout files, no Git remote with write access, and no credentials except the solver's model
  key.
- R7. After the solver ends, the runner must restore the holdout files, run the oracle and the regression set, and score
  the task `resolved` only if the oracle passes and no regression test that passed on the base SHA fails.
- R8. The runner must record per task: outcome (`resolved`, `unresolved`, `error`, `timeout`, `budget_exceeded`), wall
  time, solver-reported cost in USD and tokens, model id, and whether the solver modified any file that matches a test
  path.
- R9. The thin-integration solver must run Claude Code headless (`claude -p`) in the task environment with the
  repository's own `AGENTS.md` and `.claude/skills/`, a fixed model, a per-task turn and time limit, and the task
  statement as its only prompt.
- R10. Paid runs must have a hard total-spend cap enforced by the runner outside the solver: before starting a task the
  runner checks recorded spend plus a per-task ceiling against the cap and stops starting new tasks when it would be
  exceeded.
- R11. The runner must write per-task results as JSON Lines and aggregates to `docs/metrics/phase0.yaml`
  (`baseline.tasks_run`, `baseline.resolved_rate`, `baseline.cost_usd_total`, `baseline.cost_per_resolved_usd`,
  `baseline.wall_seconds_median`, task-set version, model id).
- R12. Mining, validation and scoring must be runnable without network access to model providers, using a scripted
  solver that applies a given patch, so the pipeline is testable for free.

## Acceptance criteria

- AC1. (R1, R2) Mining a fixture repository with three merged PRs (one source+tests, one docs-only, one from
  Dependabot) yields exactly one candidate, with base SHA, solution SHA and holdout file list equal to the fixture's.
- AC2. (R3) For a PR whose branch contains `docs/work/X-1-*/spec.md`, the statement equals that spec's text and its source
  is `spec`; for a PR without one and with no Jira key, the source is `pr` and the statement contains no line starting
  with `+`, `-` or `@@` from the diff.
- AC3. (R4) A candidate whose holdout tests already pass on the base SHA is excluded with reason `no_fail_to_pass`; one
  whose tests fail on the solution SHA is excluded with `solution_fails`; a valid one is kept with its regression set.
- AC4. (R5) Building the task set twice from the same inputs produces identical manifests (same version hash); changing
  one task's statement changes the hash.
- AC5. (R6) Inside a task environment, the holdout files are absent, `git remote -v` shows no push URL with credentials,
  and the only credential-like environment variable present is the solver's model key.
- AC6. (R7, R12) With the scripted solver applying the PR's original source patch, the task scores `resolved`; applying
  an empty patch scores `unresolved`; applying a patch that fixes the task but breaks a regression test scores
  `unresolved` with the broken test named.
- AC7. (R8) A scripted solver that edits a file under `tests/` is recorded with `touched_tests: true`.
- AC8. (R10) With a cap of 1.00 USD, a per-task ceiling of 0.40 USD and recorded spend of 0.70 USD, the runner starts no
  further task and records `budget_exceeded` for the remaining ones.
- AC9. (R11) After a scripted run over 4 tasks (2 resolved), `docs/metrics/phase0.yaml` has `baseline.tasks_run: 4`,
  `baseline.resolved_rate: 0.5`, and the charter metric check for C3 reads `tasks_run` without error.
- AC10. (R9) One real thin-integration run on one task completes with an outcome other than `error` and records a
  non-zero cost; run by hand, result noted in the test plan (skipped without a key).
- AC11. (R1–R4) The real task set holds at least 30 validated tasks across at least four repositories (C1 of the charter),
  with the exclusion reasons of every rejected candidate listed.

## Edge cases and failure modes

- A PR merged with squash has no merge commit: base is the parent of the squash commit.
- Dependencies can't be installed at an old base SHA (yanked package, Python version): excluded as `env_unreproducible`.
- Tests that need network or secrets (ade's real-model endpoint, ADE-41): excluded as `needs_network` when they fail
  only under the no-network validation run.
- Flaky tests: validation runs the oracle twice on each SHA; a candidate whose result differs is excluded as `flaky`.
- Solver hangs or loops: killed at the time limit, outcome `timeout`, cost still recorded.
- Solver deletes or rewrites the repository: scoring restores holdout files onto whatever is left; the result is simply
  unresolved, and the environment is discarded.
- Interrupted run: completed tasks keep their results; a rerun skips tasks already scored for the same task-set version
  and model unless forced.

## Non-functional requirements

- Security (`.factory/policies/security.md`): the model key comes from the environment only and is never written to
  results or logs; task environments never hold the owner's GitHub token; the solver runs with no network other than the
  model API where the platform allows (Docker network policy), otherwise the gap is recorded in the report.
- Cost: total Phase 0 spend cap 150 USD (assumption below); per-task ceiling 3 USD.
- Reproducibility: every result line carries task-set version, model id, Claude Code version and runner version.

## Assumptions

- Spend cap of 150 USD for all Phase 0 paid runs, owner's Anthropic key; the owner can change it at approval.
- Task environments are Docker containers (Docker Desktop is installed on this machine; the engine must be running).
- The two public repositories are chosen in the plan by these criteria: Python, permissive licence, pytest, at least 15
  candidate PRs in the last 18 months.
- One run per task; variance is reported as a limitation, not measured.
- Model: the same model the owner's projects use day to day, fixed for the whole run.

## Risks and dependencies

- Risk **medium**: it spends real money (capped) and runs an autonomous agent with tool access, but inside disposable
  containers, on public code, with nothing pushed anywhere.
- Contamination: public repositories' merged PRs may be in model training data, inflating the baseline; the report
  separates owner-repository and public-repository results.
- Fewer than 30 tasks may reproduce; then the report says so and the owner decides whether to add a repository.
- Depends on D-001 (charter) and D-002 (Python) for planning; the spec is stack-neutral.
