"""Solvers: what attempts a task. ScriptedSolver here; CodexSolver arrives in PR B (T9)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from forge.bench.environment import TaskEnv
from forge.bench.executor import Executor
from forge.bench.model import Task
from forge.bench.repo import GitRepoStore, git


@dataclass(frozen=True)
class SolverResult:
    exit_code: int = 0
    timed_out: bool = False
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    detail: str = ""


class Solver(Protocol):
    name: str
    model: str

    def solve(
        self, task: Task, env: TaskEnv, executor: Executor, timeout: float
    ) -> SolverResult: ...


def solution_patch(task: Task, store: GitRepoStore) -> str:
    """The original PR's change without its test files: what a perfect solver would write."""
    return store.diff(task.repo, task.base_sha, task.solution_sha, exclude=task.holdout)


class ScriptedSolver:
    """Applies a given patch, or runs a given edit function, at no cost. For tests and dry runs."""

    name = "scripted"
    model = "none"

    def __init__(
        self,
        patch_for: Callable[[Task], str] | None = None,
        edit: Callable[[Path], None] | None = None,
        cost_usd: float = 0.0,
    ) -> None:
        self.patch_for = patch_for
        self.edit = edit
        self.cost_usd = cost_usd
        self.calls = 0

    def solve(self, task, env, executor, timeout):
        self.calls += 1
        if self.edit is not None:
            self.edit(env.dir)
        patch = self.patch_for(task) if self.patch_for else ""
        if patch:
            patch_file = env.dir.parent / f"{task.task_id}.patch"
            patch_file.write_text(patch, encoding="utf-8", newline="")
            git("apply", "--whitespace=nowarn", str(patch_file), cwd=env.dir)
            patch_file.unlink()
        return SolverResult(cost_usd=self.cost_usd)
