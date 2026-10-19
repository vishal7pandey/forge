"""The run loop: one solver over a task set, under a hard total spend cap, resumable."""

from __future__ import annotations

import os
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from forge.bench.environment import TaskEnvError, prepare_task_env
from forge.bench.executor import Executor
from forge.bench.model import Outcome, Task, TaskResult, TaskSet
from forge.bench.repo import GitRepoStore
from forge.bench.score import score
from forge.bench.solvers import Solver
from forge.bench.validate import RepoProfile

PostScore = Callable[[Task, Path, TaskResult], TaskResult]


@dataclass(frozen=True)
class RunConfig:
    """Spend limits. The cap counts every cost already recorded in the results file."""

    cap_usd: float = float(os.environ.get("FORGE_BENCH_CAP_USD", "150"))
    ceiling_usd: float = float(os.environ.get("FORGE_BENCH_TASK_CEILING_USD", "3"))
    timeout: float = 1800.0
    force: bool = False
    model_key: tuple[str, str] | None = None


def load_results(path: Path) -> list[TaskResult]:
    path = Path(path)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [TaskResult.from_json_line(line) for line in lines if line.strip()]


def _append(path: Path, result: TaskResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(result.to_json_line())


def run_tasks(
    taskset: TaskSet,
    solver: Solver,
    store: GitRepoStore,
    executor: Executor,
    workdir: Path,
    results_path: Path,
    config: RunConfig | None = None,
    profile: RepoProfile | None = None,
    post_score: PostScore | None = None,
) -> list[TaskResult]:
    """Run `solver` on every task not yet scored for this task set, solver and model.

    Before each task the runner checks recorded spend plus the per-task ceiling against the cap
    and records `budget_exceeded` instead of starting the task when it would go over (R10).
    """
    config = config or RunConfig()
    results_path = Path(results_path)
    existing = load_results(results_path)
    version = taskset.version
    done = {
        r.task_id
        for r in existing
        if r.taskset_version == version
        and r.solver == solver.name
        and r.model == solver.model
        and r.outcome is not Outcome.BUDGET_EXCEEDED
    }
    spent = sum(r.cost_usd for r in existing)
    new: list[TaskResult] = []
    for task in sorted(taskset.tasks, key=lambda t: t.task_id):
        if task.task_id in done and not config.force:
            continue
        base = TaskResult(task.task_id, version, solver.name, solver.model, Outcome.ERROR)
        if spent + config.ceiling_usd > config.cap_usd + 1e-9:
            limits = f"ceiling {config.ceiling_usd:.2f} > cap {config.cap_usd:.2f}"
            result = replace(
                base, outcome=Outcome.BUDGET_EXCEEDED, detail=f"spent {spent:.2f} + {limits}"
            )
            _append(results_path, result)
            new.append(result)
            continue
        result = _attempt(task, base, solver, store, executor, Path(workdir), config, profile)
        if post_score is not None and result.outcome is not Outcome.ERROR:
            result = post_score(task, Path(workdir) / task.task_id / "task", result)
        shutil.rmtree(Path(workdir) / task.task_id, ignore_errors=True)
        _append(results_path, result)
        new.append(result)
        spent += result.cost_usd
    return new


def _attempt(task, base, solver, store, executor, workdir, config, profile) -> TaskResult:
    start = time.monotonic()
    try:
        env = prepare_task_env(
            task, store, executor, workdir / task.task_id, profile, config.model_key
        )
    except TaskEnvError as e:
        return replace(base, detail=str(e)[:500])
    sr = solver.solve(task, env, executor, config.timeout)
    common = {
        "tokens_in": sr.tokens_in,
        "tokens_out": sr.tokens_out,
        "cost_usd": sr.cost_usd,
    }
    if sr.timed_out:
        wall = time.monotonic() - start
        return replace(base, outcome=Outcome.TIMEOUT, wall_seconds=wall, **common)
    s = score(task, env, store, executor, profile)
    return replace(
        base,
        outcome=s.outcome,
        wall_seconds=time.monotonic() - start,
        touched_tests=s.touched_tests,
        detail=s.detail or sr.detail,
        **common,
    )
