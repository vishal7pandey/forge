"""Data model of the benchmark: PRs, candidates, tasks, task sets and results."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum


class ExclusionReason(StrEnum):
    NO_TESTS_FOUND = "no_tests_found"
    NO_FAIL_TO_PASS = "no_fail_to_pass"
    SOLUTION_FAILS = "solution_fails"
    ENV_UNREPRODUCIBLE = "env_unreproducible"
    NEEDS_NETWORK = "needs_network"
    FLAKY = "flaky"


class Outcome(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    ERROR = "error"
    TIMEOUT = "timeout"
    BUDGET_EXCEEDED = "budget_exceeded"


ATTEMPTED = frozenset({Outcome.RESOLVED, Outcome.UNRESOLVED, Outcome.ERROR, Outcome.TIMEOUT})


@dataclass(frozen=True)
class PrInfo:
    """A merged pull request as a PR source reports it."""

    repo: str
    number: int
    title: str
    body: str
    author: str
    merge_sha: str
    files: tuple[str, ...]


@dataclass(frozen=True)
class Candidate:
    """A merged PR that changes source and tests, before validation."""

    task_id: str
    repo: str
    pr_number: int
    base_sha: str
    solution_sha: str
    holdout: tuple[str, ...]
    statement: str = ""
    statement_source: str = ""


@dataclass(frozen=True)
class Exclusion:
    task_id: str
    reason: ExclusionReason
    detail: str = ""


@dataclass(frozen=True)
class Task:
    """A validated candidate: the holdout fails on base and passes on the solution."""

    task_id: str
    repo: str
    pr_number: int
    base_sha: str
    solution_sha: str
    holdout: tuple[str, ...]
    statement: str
    statement_source: str
    regression: tuple[str, ...] = ()

    @classmethod
    def from_candidate(cls, c: Candidate, regression: tuple[str, ...]) -> Task:
        return cls(
            task_id=c.task_id,
            repo=c.repo,
            pr_number=c.pr_number,
            base_sha=c.base_sha,
            solution_sha=c.solution_sha,
            holdout=c.holdout,
            statement=c.statement,
            statement_source=c.statement_source,
            regression=regression,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Task:
        return cls(**{**d, "holdout": tuple(d["holdout"]), "regression": tuple(d["regression"])})


def _canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class TaskSet:
    """A frozen, versioned list of tasks. The version is a hash of the content, not a counter."""

    tasks: tuple[Task, ...]
    exclusions: tuple[Exclusion, ...] = ()

    @property
    def version(self) -> str:
        items = sorted((t.to_dict() for t in self.tasks), key=lambda d: d["task_id"])
        return hashlib.sha256(_canonical(items).encode("utf-8")).hexdigest()

    def to_json(self) -> str:
        data = {
            "version": self.version,
            "tasks": sorted((t.to_dict() for t in self.tasks), key=lambda d: d["task_id"]),
            "exclusions": [asdict(e) for e in self.exclusions],
        }
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    @classmethod
    def from_json(cls, text: str) -> TaskSet:
        data = json.loads(text)
        tasks = tuple(Task.from_dict(t) for t in data["tasks"])
        exclusions = tuple(
            Exclusion(e["task_id"], ExclusionReason(e["reason"]), e.get("detail", ""))
            for e in data.get("exclusions", [])
        )
        ts = cls(tasks, exclusions)
        if data.get("version") and data["version"] != ts.version:
            raise ValueError("task set content does not match its recorded version")
        return ts


@dataclass(frozen=True)
class TaskResult:
    """One line of the results file."""

    task_id: str
    taskset_version: str
    solver: str
    model: str
    outcome: Outcome
    wall_seconds: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    touched_tests: bool = False
    detail: str = ""
    extra: dict = field(default_factory=dict)

    def to_json_line(self) -> str:
        return _canonical(asdict(self)) + "\n"

    @classmethod
    def from_json_line(cls, line: str) -> TaskResult:
        d = json.loads(line)
        return cls(**{**d, "outcome": Outcome(d["outcome"])})
