import pytest

from forge.bench.environment import prepare_task_env
from forge.bench.executor import LocalExecutor
from forge.bench.mine import mine
from forge.bench.model import Outcome
from forge.bench.score import score
from forge.bench.solvers import ScriptedSolver, solution_patch
from forge.bench.validate import validate

from .conftest import CALC_BASE


@pytest.fixture(scope="module")
def mul_task(fixture_repo, tmp_path_factory):
    cand = mine([fixture_repo.prs["mul"]], fixture_repo.store)[0]
    return validate(cand, fixture_repo.store, LocalExecutor(), tmp_path_factory.mktemp("v"))


def _attempt(fixture_repo, task, tmp_path, solver):
    ex = LocalExecutor()
    env = prepare_task_env(task, fixture_repo.store, ex, tmp_path)
    solver.solve(task, env, ex, timeout=60)
    return score(task, env, fixture_repo.store, ex)


def test_original_patch_resolves(fixture_repo, mul_task, tmp_path):
    solver = ScriptedSolver(patch_for=lambda t: solution_patch(t, fixture_repo.store))
    result = _attempt(fixture_repo, mul_task, tmp_path, solver)
    assert result.outcome is Outcome.RESOLVED, result.detail
    assert result.touched_tests is False


def test_empty_patch_unresolved(fixture_repo, mul_task, tmp_path):
    result = _attempt(fixture_repo, mul_task, tmp_path, ScriptedSolver())
    assert result.outcome is Outcome.UNRESOLVED
    assert "oracle failed" in result.detail


def _mul_but_break_add(task_dir):
    broken = CALC_BASE.replace("a + b", "a - b") + "\n\ndef mul(a, b):\n    return a * b\n"
    (task_dir / "src" / "calc.py").write_text(broken, encoding="utf-8", newline="\n")


def test_regression_break_unresolved_names_test(fixture_repo, mul_task, tmp_path):
    result = _attempt(fixture_repo, mul_task, tmp_path, ScriptedSolver(edit=_mul_but_break_add))
    assert result.outcome is Outcome.UNRESOLVED
    assert "regression broken: tests/test_basic.py::test_add" in result.detail
    assert "oracle failed" not in result.detail


def test_touched_tests_flag(fixture_repo, mul_task, tmp_path):
    def edit_test(task_dir):
        p = task_dir / "tests" / "test_basic.py"
        p.write_text(p.read_text(encoding="utf-8") + "# edited\n", encoding="utf-8")

    def delete_test(task_dir):
        (task_dir / "tests" / "test_basic.py").unlink()

    src_only = ScriptedSolver(patch_for=lambda t: solution_patch(t, fixture_repo.store))
    assert _attempt(fixture_repo, mul_task, tmp_path / "a", src_only).touched_tests is False
    edited = _attempt(fixture_repo, mul_task, tmp_path / "b", ScriptedSolver(edit=edit_test))
    assert edited.touched_tests is True
    deleted = _attempt(fixture_repo, mul_task, tmp_path / "c", ScriptedSolver(edit=delete_test))
    assert deleted.touched_tests is True
