from forge.bench.mine import is_source_path, is_test_path, mine, parse_gh_prs

from .conftest import REPO


def test_mine_yields_only_source_and_test_pr(fixture_repo):
    prs = [fixture_repo.prs[k] for k in ("mul", "docs", "deps")]
    candidates = mine(prs, fixture_repo.store)

    assert len(candidates) == 1
    c = candidates[0]
    mul = fixture_repo.prs["mul"]
    assert c.task_id == "calc-1"
    assert c.solution_sha == mul.merge_sha
    assert c.base_sha == fixture_repo.store.parent(REPO, mul.merge_sha)
    assert c.base_sha != c.solution_sha
    assert c.holdout == ("tests/test_mul.py",)


def test_mine_skips_pr_touching_only_tests(fixture_repo):
    assert mine([fixture_repo.prs["testsonly"]], fixture_repo.store) == []


def test_mine_skips_dependabot_even_with_source_and_tests(fixture_repo):
    deps = fixture_repo.prs["deps"]
    assert any(is_source_path(p) for p in deps.files)
    assert any(is_test_path(p) for p in deps.files)
    assert mine([deps], fixture_repo.store) == []


def test_path_classification():
    assert is_test_path("tests/test_x.py")
    assert is_test_path("pkg/test_x.py")
    assert is_test_path("web/src/a.test.ts")
    assert not is_test_path("src/testing_utils_contest.py")
    assert is_source_path("src/calc.py")
    assert not is_source_path("README.md")


def test_parse_gh_prs_reads_merge_commit_and_files():
    gh = (
        '[{"number": 7, "title": "T", "body": null, "author": {"login": "alice"},'
        ' "files": [{"path": "src/a.py"}, {"path": "tests/test_a.py"}],'
        ' "mergeCommit": {"oid": "abc123"}},'
        ' {"number": 8, "title": "no merge", "body": "", "author": {"login": "x"},'
        ' "files": [], "mergeCommit": null}]'
    )
    prs = parse_gh_prs("o/r", gh)
    assert [p.number for p in prs] == [7]
    assert prs[0].merge_sha == "abc123"
    assert prs[0].files == ("src/a.py", "tests/test_a.py")
    assert prs[0].body == ""
