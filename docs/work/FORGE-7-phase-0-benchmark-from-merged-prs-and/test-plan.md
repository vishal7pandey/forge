# FORGE-7 — Test plan: Phase 0 benchmark from merged PRs and thin-integration baseline run

Status: draft · Risk: medium · Jira: FORGE-7

Test framework and conventions found: pytest (`[tool.pytest.ini_options]` in `pyproject.toml`, `testpaths = ["tests"]`,
`pythonpath = ["src"]`), tests in `tests/` named `test_*.py`, no fixtures yet beyond the template. Run all:
`uv run python -m pytest -q` (pytest.exe is blocked on this machine). Lint: `uv run ruff check .`,
`uv run ruff format --check .`. Baseline on 2026-10-19: 3 passed, lint clean. New tests live in `tests/bench/`; external
edges are faked (fixture git repository built in `tmp_path`, `FixturePrSource`, `LocalExecutor`, `ScriptedSolver`), so no
network, Docker or money is needed for PR A.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | integration | tests/bench/test_mine.py::test_mine_yields_only_source_and_test_pr | fixture with 3 merged PRs (source+tests, docs-only, Dependabot) -> 1 candidate, base = merge's first parent, solution = merge SHA, holdout = `["tests/test_mul.py"]` | PR touching only test files -> no candidate (no source change) | Dependabot author `app/dependabot` -> excluded even if it touches source and tests | planned |
| AC2 | unit | tests/bench/test_statement.py::test_statement_prefers_spec, ::test_statement_pr_body_has_no_diff_lines, ::test_statement_uses_jira_override | PR carrying `docs/work/X-1-a/spec.md` -> statement = spec text, source `spec` | override file present and no spec -> source `jira`; empty PR body -> title only | PR body with a pasted hunk (`@@ -1 +1 @@`, `+    return a * b`) -> those lines removed, ordinary `- bullet` lines kept, source `pr` | planned |
| AC3 | integration | tests/bench/test_validate.py::test_valid_candidate_kept_with_regression_set, ::test_excluded_no_fail_to_pass, ::test_excluded_solution_fails | mul PR -> kept, regression set contains `tests/test_basic.py::test_add` and not the holdout | flaky oracle (result differs between the two runs) -> `flaky` | holdout passes on base -> `no_fail_to_pass`; holdout fails on solution -> `solution_fails` | planned |
| AC4 | unit | tests/bench/test_model.py::test_manifest_hash_stable_and_sensitive | same tasks in different order -> same version hash | one task -> stable 64-hex hash | one statement changed by one character -> different hash | planned |
| AC5 | integration | tests/bench/test_environment.py::test_env_has_no_holdout_and_no_credentials | prepared task dir lacks holdout files, `git remote -v` prints nothing | key not configured -> env holds no credential-like name at all | host env with `GITHUB_TOKEN`, `AWS_SECRET_ACCESS_KEY` set -> neither reaches the task env; only `OPENAI_API_KEY` matches the credential pattern | planned |
| AC6 | integration | tests/bench/test_score.py::test_original_patch_resolves, ::test_empty_patch_unresolved, ::test_regression_break_unresolved_names_test | scripted solver applies the PR's source patch -> `resolved` | empty patch -> `unresolved` | patch that adds `mul` but breaks `add` -> `unresolved`, detail names `tests/test_basic.py::test_add` | planned |
| AC7 | integration | tests/bench/test_score.py::test_touched_tests_flag | scripted patch editing `tests/test_basic.py` -> `touched_tests: true` | patch touching only `src/` -> `false` | patch deleting a test file -> `true` | planned |
| AC8 | unit | tests/bench/test_runner.py::test_cap_stops_new_tasks, ::test_resume_skips_scored_tasks | cap 1.00, ceiling 0.40, recorded 0.70 -> no solver call, remaining tasks `budget_exceeded` with cost 0 | recorded 0.60 -> exactly one more task starts (0.60 + 0.40 = 1.00 is allowed) | cap 0 -> nothing starts | planned |
| AC9 | unit | tests/bench/test_metrics.py::test_metrics_after_scripted_run | 4 results, 2 resolved -> `baseline.tasks_run: 4`, `resolved_rate: 0.5`, file parses as YAML/JSON | 0 resolved -> `cost_per_resolved_usd: null` | `budget_exceeded` rows are not counted in `tasks_run` | planned |
| AC10 | manual | (PR B) one real Codex CLI run on one task on GitHub Actions | outcome other than `error`, cost > 0 recorded | n/a: single run by design | missing `OPENAI_API_KEY` -> runner exits before starting with a clear message (unit test in PR B) | planned |
| AC11 | manual | (PR B) `bench/README.md` exclusion table and `bench/taskset-v1.json` | >= 30 validated tasks across >= 4 repositories | exactly 30 -> passes | < 30 -> report states it, owner decides on another repository | planned |

## Regression risk

Only new code under `src/forge/bench/` and `tests/bench/`; `src/forge/main.py` and `tests/test_main.py` are untouched and
must stay green. No dependency changes in PR A.

## Untestable AC

None.

## Manual checks

- AC10 and AC11 are PR B and need a paid run and real repositories; their steps and results are recorded here when
  PR B runs. Everything else is automated.

## Audit (after implementation)

Pending: filled in audit mode after PR A's code is written.
