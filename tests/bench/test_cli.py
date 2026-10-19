"""End to end through the command line, offline: validate -> run (scripted) -> report."""

import json
from dataclasses import asdict

from forge.bench.__main__ import main
from forge.bench.mine import mine

from .conftest import REPO


def test_cli_validate_run_report(fixture_repo, tmp_path):
    cands = mine([fixture_repo.prs[k] for k in ("mul", "already")], fixture_repo.store)
    cand_file = tmp_path / "candidates.json"
    cand_file.write_text(json.dumps([asdict(c) for c in cands]), encoding="utf-8")
    common = ["--cache", str(tmp_path / "cache"), "--repo-url", f"{REPO}={fixture_repo.path}"]

    ts_file, results = tmp_path / "taskset.json", tmp_path / "results.jsonl"
    assert main([*common, "validate", "--candidates", str(cand_file), "--out", str(ts_file),
                 "--workdir", str(tmp_path / "v")]) == 0  # fmt: skip
    ts = json.loads(ts_file.read_text(encoding="utf-8"))
    assert [t["task_id"] for t in ts["tasks"]] == ["calc-1"]
    assert [e["reason"] for e in ts["exclusions"]] == ["no_fail_to_pass"]

    assert main([*common, "run", "--taskset", str(ts_file), "--solver", "scripted-solution",
                 "--results", str(results), "--workdir", str(tmp_path / "w")]) == 0  # fmt: skip
    metrics = tmp_path / "phase0.yaml"
    assert main([*common, "report", "--results", str(results), "--metrics", str(metrics)]) == 0
    baseline = json.loads(metrics.read_text(encoding="utf-8"))["baseline"]
    assert baseline["tasks_run"] == 1 and baseline["resolved_rate"] == 1.0
