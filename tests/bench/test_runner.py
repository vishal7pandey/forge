from dataclasses import replace

from forge.bench.executor import LocalExecutor
from forge.bench.mine import mine
from forge.bench.model import Outcome, TaskResult, TaskSet
from forge.bench.runner import RunConfig, load_results, run_tasks
from forge.bench.solvers import ScriptedSolver, solution_patch
from forge.bench.validate import validate


def _taskset(fixture_repo, tmp_path) -> TaskSet:
    cand = mine([fixture_repo.prs["mul"]], fixture_repo.store)[0]
    task = validate(cand, fixture_repo.store, LocalExecutor(), tmp_path / "v")
    return TaskSet((task,))


def _seed(results, ts, spent):
    results.write_text(
        TaskResult(
            "earlier", ts.version, "other", "m", Outcome.UNRESOLVED, cost_usd=spent
        ).to_json_line(),
        encoding="utf-8",
    )


def test_cap_stops_new_tasks(fixture_repo, tmp_path):
    ts = _taskset(fixture_repo, tmp_path)
    results = tmp_path / "results.jsonl"
    _seed(results, ts, 0.70)
    solver = ScriptedSolver()
    cfg = RunConfig(cap_usd=1.00, ceiling_usd=0.40)
    new = run_tasks(ts, solver, fixture_repo.store, LocalExecutor(), tmp_path / "w", results, cfg)
    assert solver.calls == 0
    assert [r.outcome for r in new] == [Outcome.BUDGET_EXCEEDED]
    assert new[0].cost_usd == 0


def test_cap_allows_task_that_reaches_cap_exactly(fixture_repo, tmp_path):
    ts = _taskset(fixture_repo, tmp_path)
    results = tmp_path / "results.jsonl"
    _seed(results, ts, 0.60)
    solver = ScriptedSolver(patch_for=lambda t: solution_patch(t, fixture_repo.store))
    cfg = RunConfig(cap_usd=1.00, ceiling_usd=0.40)
    new = run_tasks(ts, solver, fixture_repo.store, LocalExecutor(), tmp_path / "w", results, cfg)
    assert solver.calls == 1
    assert new[0].outcome is Outcome.RESOLVED


def test_zero_cap_starts_nothing(fixture_repo, tmp_path):
    ts = _taskset(fixture_repo, tmp_path)
    solver = ScriptedSolver()
    cfg = RunConfig(cap_usd=0.0, ceiling_usd=0.40)
    store, ex = fixture_repo.store, LocalExecutor()
    new = run_tasks(ts, solver, store, ex, tmp_path / "w", tmp_path / "r.jsonl", cfg)
    assert solver.calls == 0 and new[0].outcome is Outcome.BUDGET_EXCEEDED


def test_resume_skips_scored_tasks(fixture_repo, tmp_path):
    ts = _taskset(fixture_repo, tmp_path)
    results = tmp_path / "results.jsonl"
    solver = ScriptedSolver(patch_for=lambda t: solution_patch(t, fixture_repo.store))
    store, ex, cfg = fixture_repo.store, LocalExecutor(), RunConfig(cap_usd=10, ceiling_usd=1)
    run_tasks(ts, solver, store, ex, tmp_path / "w", results, cfg)
    again = run_tasks(ts, solver, store, ex, tmp_path / "w", results, cfg)
    assert again == [] and solver.calls == 1
    assert len(load_results(results)) == 1


def test_post_score_hook_can_annotate(fixture_repo, tmp_path):
    ts = _taskset(fixture_repo, tmp_path)
    seen = []

    def hook(task, task_dir, result):
        seen.append(task_dir.exists())
        return replace(result, extra={"unsafe": False})

    new = run_tasks(
        ts,
        ScriptedSolver(),
        fixture_repo.store,
        LocalExecutor(),
        tmp_path / "w",
        tmp_path / "r.jsonl",
        RunConfig(cap_usd=10, ceiling_usd=1),
        post_score=hook,
    )
    assert seen == [True]
    assert new[0].extra == {"unsafe": False}
