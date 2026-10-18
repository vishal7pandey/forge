"""Scoring: restore the holdout after the solver, run oracle and regression set, decide."""

from __future__ import annotations

from dataclasses import dataclass

from forge.bench.environment import TaskEnv
from forge.bench.executor import Executor
from forge.bench.mine import is_test_path
from forge.bench.model import Outcome, Task
from forge.bench.repo import GitRepoStore, git
from forge.bench.validate import RepoProfile, _run, run_with_junit, write_holdout


@dataclass(frozen=True)
class Score:
    outcome: Outcome
    touched_tests: bool
    detail: str = ""


def touched_tests(task_dir, holdout: tuple[str, ...]) -> bool:
    """Did the solver change any test file? Deleting the holdout was our doing, not the solver's."""
    for line in git("status", "--porcelain=v1", "-uall", cwd=task_dir).splitlines():
        status, path = line[:2], line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path in holdout and status.strip() == "D":
            continue
        if is_test_path(path):
            return True
    return False


def score(
    task: Task,
    env: TaskEnv,
    store: GitRepoStore,
    executor: Executor,
    profile: RepoProfile | None = None,
) -> Score:
    profile = profile or RepoProfile()
    touched = touched_tests(env.dir, task.holdout)
    write_holdout(store, task, env.dir, task.holdout)
    oracle = _run(executor, profile, env.dir, task.holdout)
    broken: list[str] = []
    if task.regression:
        _, passed = run_with_junit(executor, profile, env.dir, task.regression)
        broken = sorted(set(task.regression) - set(passed))
    if oracle.ok and not broken:
        return Score(Outcome.RESOLVED, touched)
    detail = "oracle failed" if not oracle.ok else ""
    if broken:
        detail = (detail + "; " if detail else "") + "regression broken: " + ", ".join(broken)
    return Score(Outcome.UNRESOLVED, touched, detail)
