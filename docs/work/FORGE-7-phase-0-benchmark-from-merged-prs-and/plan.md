# FORGE-7 — Phase 0 benchmark from merged PRs and thin-integration baseline run

Status: draft · Risk: medium · Jira: FORGE-7
Created: 2026-10-18 · Slug: phase-0-benchmark-from-merged-prs-and · Spec: spec.md

## Summary

A new package `forge.bench` that mines merged PRs into candidate tasks, validates them in Docker (fail before, pass after,
holdout hidden), freezes a versioned task set, runs a solver per task in a disposable container, and scores against the
holdout. Two solvers: a scripted one (applies a patch; makes everything testable offline) and the thin integration
(Codex CLI headless, with the owner's OpenAI key; amendment 1). A command line `python -m forge.bench` drives it; results go to JSON Lines and
`docs/metrics/phase0.yaml`.

**Size:** L (about 4 days). Split into two PRs at the seam below: PR A (T1–T7, all offline, no Docker, no money) and PR B
(T8–T12, Docker executor, Claude solver, the real task set and one real run).

## Current state

- `src/forge/` holds only the template's `main.py` (`greet`) and `tests/test_main.py`; no dependencies beyond pytest and
  ruff (`pyproject.toml`). Layout per D-002 (one Python package; recommendation, record pending).
- CI: `.github/workflows/ci.yml` runs `uv sync --all-extras --all-groups`, `ruff check`, `ruff format --check`,
  `pytest -q` on ubuntu. Locally: `uv run python -m pytest -q` (pytest.exe blocked), `uv run ruff check .`.
- Tools on this machine: `gh` (authenticated), `git`, Docker Desktop 29.7 (engine must be running), Claude Code 2.1.84
  (not used as solver: no Anthropic key). Codex CLI is not installed on the host; it is installed in the solver image.
- Source repositories counted 2026-10-18: adep 20, chatpid 9, ai-software-factory 13 candidates touching source and tests.

## Approach

Pure logic is separated from the four side-effecting edges, each behind a small protocol so tests use fakes:

| Edge | Protocol | Real | Fake (tests) |
|---|---|---|---|
| PR source | `PrSource.merged_prs(repo) -> list[PrInfo]` | `GhPrSource` (`gh pr list --json`) | `FixturePrSource` |
| Repository | `RepoStore.checkout(repo, sha) -> Path` | `GitRepoStore` (clone cache + `git worktree`) | same class on a fixture repo built in `tmp_path` |
| Executor | `Executor.run(cmd, workdir, env, network, timeout) -> ExecResult` | `DockerExecutor` | `LocalExecutor` (subprocess) |
| Solver | `Solver.solve(task_dir, statement, limits) -> SolverResult` | `ClaudeCodeSolver` | `ScriptedSolver(patch)` |

Statements (R3): `spec.md` from the solution tree when the PR carries `docs/work/*/spec.md`; else a Jira override file
`bench/statements/<task_id>.md` (written while building the set, from the Jira issue via the Atlassian tools, source
`jira`); else PR title and body with diff-like lines removed (source `pr`). The factory has no Jira client and the bench
must not hold an Atlassian token, so the override file is how Jira text enters.

Validation (R4) per candidate: checkout base, install dependencies once with network (`uv sync --frozen`, or the repo's
own install command if no `uv.lock`), then run the oracle twice with network off on base (must fail) and on solution
(must pass), and the full suite on base to collect the regression set. Exclusion reasons are an enum:
`no_fail_to_pass`, `solution_fails`, `env_unreproducible`, `needs_network`, `flaky`, `no_tests_found`.

Run (R6–R10): per task, a fresh copy at base SHA with holdout files deleted and `.git` remotes removed; dependencies
installed; the solver runs with env `{OPENAI_API_KEY}` only (plus `PATH`, `HOME`) and a wall-time limit. Codex CLI has
no spend flag, so the runner reads its `--json` event stream, prices token usage as it arrives, and stops the container
when the task's cost reaches the per-task ceiling: a second line behind the runner's total cap. Then holdout restored, oracle and
regression set run with network off, outcome scored. The budget ledger is the results file itself: the runner sums
recorded cost before each task (R10).

Metrics (R11): a ten-line YAML emitter for flat nested mappings, so no YAML dependency is added.

**Alternatives rejected**
- SWE-bench's harness as-is: built for its own dataset format and per-repo Docker images; adapting it to our repos and
  the factory's spec-as-statement costs more than the ~600 lines here, and it doesn't do the thin-integration solver.
- Running solvers on the host without containers: fastest, but `bypassPermissions` on the owner's laptop with their
  credentials in reach is exactly the unsafe setup Forge exists to prevent.
- PyYAML or pydantic as dependencies: not needed for flat result files; `json` and a small emitter suffice.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Data model: `PrInfo`, `Candidate`, `Exclusion`, `Task`, `TaskSet` (manifest with content hash), `TaskResult`; JSON round-trip | new `src/forge/bench/__init__.py`, `model.py`; `tests/bench/test_model.py` | AC4 | `test_manifest_hash_stable_and_sensitive` passes |
| T2 | Fixture repository builder for tests (git repo with three merged PRs: source+tests, docs-only, Dependabot) and `FixturePrSource` | new `tests/bench/fixtures.py` | AC1, AC3, AC6 | fixture builds in `tmp_path` in < 2 s |
| T3 | Mining: filter PRs (not Dependabot, source and test paths), base/solution SHA, holdout list | new `src/forge/bench/mine.py` | AC1 | `test_mine_yields_only_source_and_test_pr` |
| T4 | Statements: spec / override / PR body with diff lines stripped, source recorded | new `src/forge/bench/statement.py` | AC2 | `test_statement_prefers_spec`, `test_statement_pr_body_has_no_diff_lines` |
| T5 | `Executor` protocol, `LocalExecutor`; `GitRepoStore`; validation with exclusion reasons and flaky double-run | new `executor.py`, `repo.py`, `validate.py` | AC3 | three validation tests on the fixture repo, one per outcome |
| T6 | Task environment preparation (holdout removed, remotes stripped, env allow-list) and scoring with regression set; `ScriptedSolver`; `touched_tests` | new `environment.py`, `score.py`, `solvers.py` | AC5, AC6, AC7 | `test_env_has_no_holdout_and_no_credentials`, three scoring tests, `test_touched_tests_flag` |
| T7 | Runner loop with spend cap and resume; results JSONL; metrics YAML; CLI `python -m forge.bench {mine,validate,build,run,report}` | new `runner.py`, `metrics.py`, `__main__.py` | AC8, AC9 | `test_cap_stops_new_tasks`, `test_metrics_after_scripted_run`; charter check reads `baseline.tasks_run` |
| — | **PR A ends here** (offline only; CI covers all of it) | | | CI green; reviewer runs `python -m forge.bench run --solver scripted` on the fixture |
| T8 | `DockerExecutor`: image `python:3.12-slim` + uv + node + Codex CLI (`@openai/codex`, pinned); `--network none` for oracle runs, bridge for install and solver; mounts; kill on timeout | new `docker.py`, `bench/Dockerfile` | AC5 (container variant) | integration test marked `docker`, skipped when the engine is down |
| T9 | `CodexSolver`: `codex exec --json` with a fixed model and full-auto sandbox off inside the container (the container is the sandbox); parse token usage from the event stream; cost from a pinned price table `bench/prices.json` | new in `solvers.py`, `bench/prices.json` | AC10 | unit test on a recorded JSON output; manual run recorded in the test plan |
| T10 | Choose two public repositories by the spec's criteria; record them in `bench/README.md` | new `bench/README.md`, `bench/sources.yaml` | AC11 | file lists repo, licence, candidate count |
| T11 | Build the real task set: mine all five repositories, write Jira overrides, validate in Docker, freeze `bench/taskset-v1.json` with exclusions | new `bench/taskset-v1.json`, `bench/statements/` | AC11 | ≥ 30 validated tasks across ≥ 4 repositories, exclusion table in `bench/README.md` |
| T12 | One real thin-integration run on one task (AC10); the full baseline run is FORGE-7's follow-up execution, gated by the key and the cap | — | AC10 | result line with non-zero cost recorded in `test-plan.md` |

## Data, API and migration impact

New package and CLI only. New files under `bench/` (task set, statements, README) and `docs/metrics/phase0.yaml`. New
environment variable `OPENAI_API_KEY` (documented in `.env.example`, never committed), plus `FORGE_BENCH_CAP_USD`
(default 150) and `FORGE_BENCH_TASK_CEILING_USD` (default 3). No dependency added to `pyproject.toml`. Nothing to migrate.

## Security and failure modes

- Secrets: only `OPENAI_API_KEY` reaches a solver container, read from the environment; the env allow-list is tested
  (AC5). Results and logs never include environment values. The owner's `gh` token is used only by `GhPrSource` on the
  host for mining, never inside containers.
- Untrusted code: candidate repositories' test suites run inside containers, oracle runs with network off.
- Solver behaviour: `bypassPermissions` only inside a disposable container with no Git credentials; known gap: the
  solver container needs network to reach the model API, so it isn't egress-restricted in Phase 0. Recorded in the
  report; FORGE-9's sink detection works from the container's connection log.
- Failure modes: Docker engine down → `run` and `validate` exit with a clear error before touching anything; a solver
  crash → `error` outcome with stderr tail; partial run → resume skips scored tasks (spec edge case).

## Rollout and rollback

No environment is configured (`.factory/factory.yaml`). PR A and PR B merge after peer review; paid runs are started by
hand. Rollback: revert the PR; task-set files are additive. Point of no return: money spent on a run, bounded by the cap.

## Risks and open points

- Fewer than 30 tasks may reproduce (old dependency sets, ade's network-dependent tests). Signal: T11's exclusion table.
  Response per the spec: report it and add a repository.
- Docker Desktop on Windows bind-mount performance may make validation slow; mitigated by caching dependency installs
  per base SHA.
- D-002 (Python stack) is recommended but not yet recorded as accepted; the plan assumes it.
