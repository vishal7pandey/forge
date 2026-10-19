import json

from forge.bench.metrics import summarize, update_section
from forge.bench.model import Outcome, TaskResult


def _r(task_id, outcome, cost=0.5, wall=10.0):
    return TaskResult(task_id, "v1", "codex", "m", outcome, wall_seconds=wall, cost_usd=cost)


def test_metrics_after_scripted_run(tmp_path):
    results = [
        _r("a", Outcome.RESOLVED),
        _r("b", Outcome.RESOLVED),
        _r("c", Outcome.UNRESOLVED),
        _r("d", Outcome.TIMEOUT),
        _r("e", Outcome.BUDGET_EXCEEDED, cost=0.0),
    ]
    path = tmp_path / "docs" / "metrics" / "phase0.yaml"
    update_section(path, "baseline", summarize(results))
    data = json.loads(path.read_text(encoding="utf-8"))
    b = data["baseline"]
    assert b["tasks_run"] == 4
    assert b["resolved_rate"] == 0.5
    assert b["cost_usd_total"] == 2.0
    assert b["cost_per_resolved_usd"] == 1.0
    assert b["budget_exceeded"] == 1
    assert b["taskset_version"] == "v1" and b["model"] == "m"


def test_no_resolved_gives_null_cost_per_resolved():
    s = summarize([_r("a", Outcome.UNRESOLVED)])
    assert s["resolved_rate"] == 0.0
    assert s["cost_per_resolved_usd"] is None


def test_update_section_keeps_other_sections(tmp_path):
    path = tmp_path / "phase0.yaml"
    update_section(path, "adversarial", {"unsafe_count": 2})
    update_section(path, "baseline", {"tasks_run": 4})
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "adversarial": {"unsafe_count": 2},
        "baseline": {"tasks_run": 4},
    }
