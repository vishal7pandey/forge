from dataclasses import dataclass, field

from forge.bench.executor import ExecResult, LocalExecutor
from forge.bench.mine import mine
from forge.bench.model import ExclusionReason, Task
from forge.bench.validate import junit_passed, validate


def _candidate(fixture_repo, key):
    return mine([fixture_repo.prs[key]], fixture_repo.store)[0]


def test_valid_candidate_kept_with_regression_set(fixture_repo, tmp_path):
    cand = _candidate(fixture_repo, "mul")
    result = validate(cand, fixture_repo.store, LocalExecutor(), tmp_path)
    assert isinstance(result, Task), result
    assert "tests/test_basic.py::test_add" in result.regression
    assert not any(r.startswith("tests/test_mul.py") for r in result.regression)


def test_excluded_no_fail_to_pass(fixture_repo, tmp_path):
    result = validate(
        _candidate(fixture_repo, "already"), fixture_repo.store, LocalExecutor(), tmp_path
    )
    assert result.reason is ExclusionReason.NO_FAIL_TO_PASS


def test_excluded_solution_fails(fixture_repo, tmp_path):
    result = validate(
        _candidate(fixture_repo, "broken"), fixture_repo.store, LocalExecutor(), tmp_path
    )
    assert result.reason is ExclusionReason.SOLUTION_FAILS


@dataclass
class FlakyExecutor:
    """Real execution, but the second oracle run on base reports the opposite result."""

    inner: LocalExecutor = field(default_factory=LocalExecutor)
    oracle_runs: int = 0

    def run(self, cmd, cwd, env, *, network, timeout):
        r = self.inner.run(cmd, cwd, env, network=network, timeout=timeout)
        if any(a.startswith("tests/test_mul.py") for a in cmd):
            self.oracle_runs += 1
            if self.oracle_runs == 2:
                return ExecResult(0 if r.returncode else 1, r.stdout, r.stderr)
        return r


def test_excluded_flaky(fixture_repo, tmp_path):
    cand = _candidate(fixture_repo, "mul")
    result = validate(cand, fixture_repo.store, FlakyExecutor(), tmp_path)
    assert result.reason is ExclusionReason.FLAKY


def test_junit_passed_builds_node_ids():
    xml = (
        '<testsuites><testsuite name="pytest">'
        '<testcase classname="tests.test_a" name="test_ok" file="tests/test_a.py"/>'
        '<testcase classname="tests.test_a.TestK" name="test_m[1]" file="tests/test_a.py"/>'
        '<testcase classname="tests.test_a" name="test_bad" file="tests/test_a.py">'
        '<failure message="x"/></testcase>'
        '<testcase classname="tests.test_a" name="test_skip" file="tests\\test_a.py">'
        "<skipped/></testcase>"
        "</testsuite></testsuites>"
    )
    assert junit_passed(xml) == ["tests/test_a.py::test_ok", "tests/test_a.py::TestK::test_m[1]"]
