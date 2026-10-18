# FORGE-8 — Dependabot major bumps: ruff 0.17 and pytest 9

Status: draft · Risk: low · Jira: FORGE-8
Created: 2026-10-18 · Slug: dependabot-major-bumps-ruff-0-17-and · Spec: spec.md

## Summary

Update dev dependency constraints in `pyproject.toml` to `pytest>=9.1.1` and `ruff>=0.17.1`, regenerate `uv.lock` via `uv sync`, and verify that existing unit tests (`pytest -q`), linter (`ruff check .`), and formatter (`ruff format --check .`) execute cleanly without breakage.

**Size:** S (< half a day)

## Current state

- `pyproject.toml` specifies `dev = ["pytest>=8", "ruff>=0.6"]`.
- `tests/test_main.py` contains 3 unit tests.
- Lint and format checks run across `src/` and `tests/` with `select = ["E", "F", "I", "UP", "B"]`.
- Commands:
  - Tests: `uv run python -m pytest -q`
  - Lint: `uv run ruff check .`
  - Format: `uv run ruff format --check .`

## Approach

1. Bump minimum version constraints in `pyproject.toml`.
2. Execute `uv sync` to resolve and update `uv.lock` to `pytest 9.1.1` and `ruff 0.17.1`.
3. Validate test execution, linting, and formatting. Source code and tests are already fully compatible with no required code alterations.
4. Run negative drill to verify detection on syntax/assertion failures.

**Alternatives rejected**
- *Two separate work items*: Rejected; handling dev tooling upgrades together in one atomic change prevents redundant CI cycles and simplifies lockfile resolution.
- *Unconstrained minimums*: Rejected; pinning `>=9.1.1` and `>=0.17.1` ensures consistent tool behavior across machines.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Update dev dependencies in `pyproject.toml` and sync lockfile | `pyproject.toml`, `uv.lock` | AC1 | `uv sync` exits with code 0 and locks `pytest==9.1.1`, `ruff==0.17.1` |
| T2 | Validate unit test suite under Pytest 9.1.1 | `tests/test_main.py` | AC2 | `uv run python -m pytest -q` passes all 3 tests with 0 failures |
| T3 | Validate lint and format checks under Ruff 0.17.1 | `src/`, `tests/` | AC3 | `uv run ruff check .` and `uv run ruff format --check .` exit with 0 findings |
| T4 | Negative test drill (mutation verification) | scratch test file | AC4 | Deliberate assertion failure and lint error exit with non-zero status |

## Data, API and migration impact

None. Dev dependencies only; runtime package, CLI, and exports remain identical.

## Security and failure modes

- Security: Packages are installed from PyPI; `uv.lock` pins cryptographically verified wheel and sdist hashes.
- Failure modes: If a new Ruff rule flags existing code, adjust lint configuration or format with `ruff format .`. (Audited: 0 findings currently).

## Rollout and rollback

- Rollout: Standard PR merge commit to `main`.
- Rollback: Revert commit if regressions appear in subsequent feature development.

## Risks and open points

- None. Both tools tested locally and in CI with green results.
