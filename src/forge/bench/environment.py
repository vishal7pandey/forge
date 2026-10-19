"""The task environment a solver sees: base SHA, holdout removed, no remotes, minimal env."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from forge.bench.executor import Executor, minimal_env
from forge.bench.model import Task
from forge.bench.repo import GitRepoStore
from forge.bench.validate import RepoProfile

CREDENTIAL_NAME = re.compile(r"TOKEN|SECRET|PASSW|API_?KEY|_KEY$|CREDENTIAL|AUTH", re.IGNORECASE)


@dataclass(frozen=True)
class TaskEnv:
    dir: Path
    env: dict[str, str]


class TaskEnvError(RuntimeError):
    """The task environment could not be prepared (for example, dependencies don't install)."""


def credential_names(env: dict[str, str]) -> list[str]:
    return sorted(k for k in env if CREDENTIAL_NAME.search(k))


def prepare_task_env(
    task: Task,
    store: GitRepoStore,
    executor: Executor,
    workdir: Path,
    profile: RepoProfile | None = None,
    model_key: tuple[str, str] | None = None,
) -> TaskEnv:
    """A fresh copy of the repository at the base SHA, ready for a solver.

    The holdout files are deleted, Git remotes are removed (no push target, no credentials in
    URLs), dependencies are installed, and the environment holds only the variables a process needs
    to start plus the solver's model key, if given as (name, value).
    """
    profile = profile or RepoProfile()
    d = store.checkout(task.repo, task.base_sha, Path(workdir) / "task")
    for path in task.holdout:
        (d / path).unlink(missing_ok=True)
    env = minimal_env(profile.env)
    if profile.install:
        r = executor.run(list(profile.install), d, env, network=True, timeout=profile.timeout)
        if not r.ok:
            raise TaskEnvError(f"install failed: {r.stderr[-500:]}")
    if model_key is not None:
        env[model_key[0]] = model_key[1]
    return TaskEnv(d, env)
