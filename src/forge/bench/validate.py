"""Validation: keep a candidate only if its holdout fails on base and passes on the solution."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, replace
from pathlib import Path

from forge.bench.executor import ExecResult, Executor, minimal_env
from forge.bench.model import Candidate, Exclusion, ExclusionReason, Task
from forge.bench.repo import GitRepoStore

JUNIT_NAME = ".forge-junit.xml"


@dataclass(frozen=True)
class RepoProfile:
    """How to install and test a repository inside its working copy."""

    test: tuple[str, ...] = (sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider")
    install: tuple[str, ...] | None = None
    timeout: float = 600.0
    env: dict[str, str] = field(default_factory=dict)


def junit_passed(xml_text: str) -> list[str]:
    """Node ids of passed test cases in a pytest xunit1 report."""
    passed = []
    for case in ET.fromstring(xml_text).iter("testcase"):
        if any(child.tag in ("failure", "error", "skipped") for child in case):
            continue
        file = (case.get("file") or "").replace("\\", "/")
        name = case.get("name") or ""
        classname = case.get("classname") or ""
        module = file[:-3].replace("/", ".") if file.endswith(".py") else ""
        cls = classname[len(module) + 1 :] if module and classname.startswith(module + ".") else ""
        parts = [file] + ([*cls.split(".")] if cls else []) + [name]
        passed.append("::".join(parts))
    return passed


def _run(executor: Executor, profile: RepoProfile, cwd: Path, args: tuple[str, ...], network=False):
    return executor.run(
        [*profile.test, *args],
        cwd,
        minimal_env(profile.env),
        network=network,
        timeout=profile.timeout,
    )


def _install(executor: Executor, profile: RepoProfile, cwd: Path) -> ExecResult | None:
    if not profile.install:
        return None
    return executor.run(
        list(profile.install), cwd, minimal_env(profile.env), network=True, timeout=profile.timeout
    )


def regression_set(executor, profile, cwd: Path, holdout: tuple[str, ...]) -> tuple[str, ...]:
    """Tests outside the holdout that pass on this working copy."""
    _run(executor, profile, cwd, (f"--junitxml={JUNIT_NAME}", "-o", "junit_family=xunit1"))
    report = cwd / JUNIT_NAME
    if not report.exists():
        return ()
    ids = junit_passed(report.read_text(encoding="utf-8"))
    report.unlink()
    return tuple(sorted(i for i in ids if i.split("::", 1)[0] not in holdout))


def write_holdout(store: GitRepoStore, c: Candidate, dest: Path, holdout: tuple[str, ...]) -> None:
    for path in holdout:
        text = store.read_file(c.repo, c.solution_sha, path)
        target = dest / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text or "", encoding="utf-8", newline="")


def validate(
    c: Candidate,
    store: GitRepoStore,
    executor: Executor,
    workdir: Path,
    profile: RepoProfile | None = None,
) -> Task | Exclusion:
    profile = profile or RepoProfile()
    holdout = tuple(p for p in c.holdout if store.read_file(c.repo, c.solution_sha, p) is not None)
    if not holdout:
        return Exclusion(c.task_id, ExclusionReason.NO_TESTS_FOUND, "no holdout file at solution")

    base = store.checkout(c.repo, c.base_sha, Path(workdir) / "base")
    inst = _install(executor, profile, base)
    if inst is not None and not inst.ok:
        return Exclusion(c.task_id, ExclusionReason.ENV_UNREPRODUCIBLE, inst.stderr[-500:])
    regression = regression_set(executor, profile, base, holdout)

    write_holdout(store, c, base, holdout)
    first, second = (_run(executor, profile, base, holdout) for _ in range(2))
    if first.ok != second.ok:
        return Exclusion(c.task_id, ExclusionReason.FLAKY, "oracle differs between runs on base")
    if first.ok:
        return Exclusion(c.task_id, ExclusionReason.NO_FAIL_TO_PASS, "holdout passes on base")

    sol = store.checkout(c.repo, c.solution_sha, Path(workdir) / "solution")
    inst = _install(executor, profile, sol)
    if inst is not None and not inst.ok:
        return Exclusion(c.task_id, ExclusionReason.ENV_UNREPRODUCIBLE, inst.stderr[-500:])
    first, second = (_run(executor, profile, sol, holdout) for _ in range(2))
    if first.ok != second.ok:
        return Exclusion(c.task_id, ExclusionReason.FLAKY, "oracle differs on solution")
    if not first.ok:
        if _run(executor, profile, sol, holdout, network=True).ok:
            return Exclusion(c.task_id, ExclusionReason.NEEDS_NETWORK, "passes only with network")
        return Exclusion(c.task_id, ExclusionReason.SOLUTION_FAILS, first.stdout[-500:])

    return Task.from_candidate(replace(c, holdout=holdout), regression)
