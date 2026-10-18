# FORGE-8 — Dependabot major bumps: ruff 0.17 and pytest 9

Status: draft · Risk: low · Jira: FORGE-8
Created: 2026-10-18 · Slug: dependabot-major-bumps-ruff-0-17-and

## Problem

Dependabot opened PR #2 (`ruff >= 0.17.1`) and PR #3 (`pytest >= 9.1.1`). Per `.factory/policies/dependencies.md`, `0.6 -> 0.17` (a `0.y` bump where `y` changes) and `8 -> 9` are classified as major version updates. Major updates cannot be merged automatically without a dedicated work item verifying test and linter compatibility across the repository.

## Users and context

- **Developers & Agents**: Running local development commands (`uv run python -m pytest -q`, `uv run ruff check .`).
- **CI Workflows**: Running automated lint and test suites (`.github/workflows/ci.yml`).
- Grounded in `.factory/policies/dependencies.md`, `pyproject.toml`, and open PRs #2 and #3.

## Goals and non-goals

**Goals**
- Update `pyproject.toml` to require `pytest>=9.1.1` and `ruff>=0.17.1`.
- Update `uv.lock` to lock these versions and verify compatibility.
- Ensure the full test suite and all linting/formatting checks pass cleanly.
- Provide the verified basis to close or supersede PRs #2 and #3.

**Non-goals**
- Adding any new runtime dependencies or altering `[project.dependencies]`.
- Changing existing Ruff lint rule configurations (`select = ["E", "F", "I", "UP", "B"]`) or line length.

## Requirements

- R1. `pyproject.toml` `dependency-groups.dev` must specify `pytest>=9.1.1` and `ruff>=0.17.1`.
- R2. `uv.lock` must resolve and lock `pytest` at 9.1.1 (or newer) and `ruff` at 0.17.1 (or newer).
- R3. The test suite must execute cleanly under `pytest 9.x` with exit code 0.
- R4. Lint and formatting checks must execute cleanly under `ruff 0.17.x` with exit code 0.

## Acceptance criteria

- AC1. (R1, R2) `pyproject.toml` specifies `pytest>=9.1.1` and `ruff>=0.17.1`, and `uv sync` resolves without conflicts.
- AC2. (R3) `uv run python -m pytest -q` passes all existing test cases without errors or deprecation breakages.
- AC3. (R4) `uv run ruff check .` and `uv run ruff format --check .` pass with zero findings.
- AC4. (R3, R4) A deliberate test failure or lint error produces a non-zero exit code under the upgraded tools.

## Edge cases and failure modes

- Deprecated Pytest hooks or config: verified against `[tool.pytest.ini_options]` in `pyproject.toml` (clean).
- New default Ruff lint rules in 0.17: verified with current rule selection (clean).

## Non-functional requirements

- Security: Zero open CVEs in updated packages; hashes pinned in `uv.lock`.
- Performance: Test execution and linting duration remain under 1 second locally.

## Assumptions

- Bundling the two dev-dependency major bumps into a single work item is low risk and minimizes CI churn.

## Risks and dependencies

- Risk is **low**: dev dependencies only, zero runtime exposure, immediately reversible.
- Dependencies: None.
