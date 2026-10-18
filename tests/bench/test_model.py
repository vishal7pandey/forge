import pytest

from forge.bench.model import Exclusion, ExclusionReason, Outcome, Task, TaskResult, TaskSet


def _task(task_id: str, statement: str = "Add mul") -> Task:
    return Task(
        task_id=task_id,
        repo="o/r",
        pr_number=1,
        base_sha="a" * 40,
        solution_sha="b" * 40,
        holdout=("tests/test_mul.py",),
        statement=statement,
        statement_source="pr",
        regression=("tests/test_basic.py::test_add",),
    )


def test_manifest_hash_stable_and_sensitive():
    one = TaskSet((_task("r-1"), _task("r-2")))
    reordered = TaskSet((_task("r-2"), _task("r-1")))
    assert one.version == reordered.version
    assert len(one.version) == 64 and all(c in "0123456789abcdef" for c in one.version)

    changed = TaskSet((_task("r-1", statement="Add mul!"), _task("r-2")))
    assert changed.version != one.version


def test_single_task_hash_is_stable():
    assert TaskSet((_task("r-1"),)).version == TaskSet((_task("r-1"),)).version


def test_task_set_json_round_trip():
    ts = TaskSet((_task("r-1"),), (Exclusion("r-9", ExclusionReason.FLAKY, "differs"),))
    back = TaskSet.from_json(ts.to_json())
    assert back == ts
    assert back.version == ts.version


def test_task_set_rejects_tampered_content():
    text = TaskSet((_task("r-1"),)).to_json().replace("Add mul", "Add div")
    with pytest.raises(ValueError, match="does not match"):
        TaskSet.from_json(text)


def test_result_json_line_round_trip():
    r = TaskResult("r-1", "v", "scripted", "none", Outcome.RESOLVED, cost_usd=0.25)
    assert TaskResult.from_json_line(r.to_json_line()) == r
