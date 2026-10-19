"""Aggregates for the Phase 0 report and the charter's metric checks.

`docs/metrics/phase0.yaml` is written as JSON, which is valid YAML, so the charter check (a YAML
reader) can read it and the benchmark needs no YAML dependency. Each producer owns one top-level
section (`baseline` here; `adversarial` for FORGE-9) and updates only that section.
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Iterable
from pathlib import Path

from forge.bench.model import ATTEMPTED, Outcome, TaskResult


def summarize(results: Iterable[TaskResult]) -> dict:
    rows = list(results)
    attempted = [r for r in rows if r.outcome in ATTEMPTED]
    resolved = sum(1 for r in attempted if r.outcome is Outcome.RESOLVED)
    cost = round(sum(r.cost_usd for r in attempted), 4)
    return {
        "tasks_run": len(attempted),
        "resolved": resolved,
        "resolved_rate": round(resolved / len(attempted), 4) if attempted else None,
        "cost_usd_total": cost,
        "cost_per_resolved_usd": round(cost / resolved, 4) if resolved else None,
        "wall_seconds_median": (
            round(statistics.median(r.wall_seconds for r in attempted), 1) if attempted else None
        ),
        "budget_exceeded": sum(1 for r in rows if r.outcome is Outcome.BUDGET_EXCEEDED),
        "touched_tests": sum(1 for r in attempted if r.touched_tests),
        "taskset_version": _single(r.taskset_version for r in rows),
        "solver": _single(r.solver for r in rows),
        "model": _single(r.model for r in rows),
    }


def _single(values: Iterable[str]) -> str | None:
    distinct = sorted(set(values))
    return distinct[0] if len(distinct) == 1 else (",".join(distinct) or None)


def update_section(path: Path, name: str, values: dict) -> dict:
    """Replace one top-level section of the metrics file, keeping the others."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    data[name] = values
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    return data
