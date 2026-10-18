# FORGE-8 — Test plan: Dependabot major bumps: ruff 0.17 and pytest 9

Status: draft · Risk: low · Jira: FORGE-8

Test framework and conventions found: Pytest 9.x, `tests/` directory, naming `test_*.py`, command: `uv run python -m pytest -q`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | integration | `uv sync` / `pyproject.toml` | `pytest>=9.1.1` and `ruff>=0.17.1` resolve cleanly | Lockfile resolves to exact latest audited versions | Incompatible constraint fails resolution | verified |
| AC2 | unit | `tests/test_main.py` | All 3 unit tests pass under Pytest 9.1.1 | Zero deprecation warnings in test fixtures | n/a: covered in AC4 | verified |
| AC3 | integration | `uv run ruff check .` & `uv run ruff format --check .` | Zero lint violations, 48 files correctly formatted | All rule sets (E, F, I, UP, B) pass | n/a: covered in AC4 | verified |
| AC4 | unit | Mutation drill (`tests/test_main.py`) | Broken assertion or lint error triggers non-zero exit | `assert False` exits with code 1 | Linter flags unused import with code 1 | verified |

## Regression risk

Zero regression risk to product code; existing tests and main entrypoint remain untouched.

## Untestable AC

None.

## Manual checks

None.

## Audit (after implementation)

- AC1 confirmed via `uv sync` output pinning `pytest==9.1.1` and `ruff==0.17.1`.
- AC2 confirmed via `uv run python -m pytest -q` output `3 passed in 0.23s`.
- AC3 confirmed via `uv run ruff check .` (All checks passed!) and `uv run ruff format --check .` (48 files already formatted).
- AC4 confirmed by injecting `assert False` and observing pytest fail with exit code 1.
