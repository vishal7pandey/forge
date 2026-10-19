"""A real git repository with merged PRs, built in tmp_path, standing in for GitHub."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from forge.bench.model import PrInfo
from forge.bench.repo import GitRepoStore, git

REPO = "acme/calc"

CALC_BASE = "def add(a, b):\n    return a + b\n"
TEST_BASIC = "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"
CONFTEST = (
    "import sys\nfrom pathlib import Path\n\n"
    "sys.path.insert(0, str(Path(__file__).parent / 'src'))\n"
)


@dataclass
class FixtureRepo:
    path: Path
    store: GitRepoStore
    prs: dict[str, PrInfo] = field(default_factory=dict)


class FixturePrSource:
    def __init__(self, prs: list[PrInfo]) -> None:
        self._prs = prs

    def merged_prs(self, repo: str) -> list[PrInfo]:
        return [p for p in self._prs if p.repo == repo]


def _g(path: Path, *args: str) -> str:
    return git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args, cwd=path)


def _write(root: Path, files: dict[str, str | None]) -> None:
    for rel, text in files.items():
        p = root / rel
        if text is None:
            p.unlink()
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")


def _merge_pr(fx: FixtureRepo, key: str, number: int, author: str, files: dict, body=""):
    root = fx.path
    branch = f"pr-{number}"
    _g(root, "checkout", "-q", "-b", branch, "main")
    _write(root, files)
    _g(root, "add", "-A")
    _g(root, "commit", "-q", "-m", f"PR {number}")
    _g(root, "checkout", "-q", "main")
    _g(root, "merge", "-q", "--no-ff", "-m", f"Merge pull request #{number}", branch)
    merge_sha = _g(root, "rev-parse", "HEAD").strip()
    changed = _g(root, "diff", "--name-only", "HEAD^1", "HEAD").split()
    fx.prs[key] = PrInfo(REPO, number, f"PR {number}", body, author, merge_sha, tuple(changed))


def build_fixture_repo(root: Path) -> FixtureRepo:
    """main with add(); then merged PRs:

    mul: source + new test (valid task); docs: README only; deps: Dependabot touching source and
    tests; already: new test of existing behaviour (passes on base); broken: test that fails on
    the solution too; testsonly: changes only a test file.
    """
    repo_dir = root / "origin"
    repo_dir.mkdir(parents=True)
    git("init", "-q", "-b", "main", cwd=repo_dir)
    _write(
        repo_dir,
        {"src/calc.py": CALC_BASE, "tests/test_basic.py": TEST_BASIC, "conftest.py": CONFTEST},
    )
    _g(repo_dir, "add", "-A")
    _g(repo_dir, "commit", "-q", "-m", "initial")
    store = GitRepoStore(root / "cache")
    store.register(REPO, str(repo_dir))
    fx = FixtureRepo(repo_dir, store)

    mul_src = CALC_BASE + "\n\ndef mul(a, b):\n    return a * b\n"
    mul_test = "from calc import mul\n\n\ndef test_mul():\n    assert mul(2, 3) == 6\n"
    _merge_pr(fx, "mul", 1, "alice", {"src/calc.py": mul_src, "tests/test_mul.py": mul_test})
    _merge_pr(fx, "docs", 2, "alice", {"README.md": "# calc\n"})
    _merge_pr(
        fx,
        "deps",
        3,
        "app/dependabot",
        {"src/calc.py": mul_src + "# bump\n", "tests/test_basic.py": TEST_BASIC + "# bump\n"},
    )
    already_test = "from calc import add\n\n\ndef test_add_zero():\n    assert add(0, 0) == 0\n"
    _merge_pr(
        fx,
        "already",
        4,
        "bob",
        {"src/calc.py": mul_src + "# bump\n# doc\n", "tests/test_add_zero.py": already_test},
    )
    broken_test = "from calc import mul\n\n\ndef test_mul_wrong():\n    assert mul(2, 3) == 7\n"
    _merge_pr(
        fx,
        "broken",
        5,
        "bob",
        {"src/calc.py": mul_src + "# bump\n# doc\n# x\n", "tests/test_wrong.py": broken_test},
    )
    _merge_pr(fx, "testsonly", 6, "bob", {"tests/test_basic.py": TEST_BASIC + "# note\n"})
    return fx


@pytest.fixture(scope="session")
def fixture_repo(tmp_path_factory: pytest.TempPathFactory) -> FixtureRepo:
    """Built once per session; tests must not modify `path` (checkouts go to their own tmp_path)."""
    return build_fixture_repo(tmp_path_factory.mktemp("fixture"))
