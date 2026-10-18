"""Mining: merged PRs that change both source and tests become candidate tasks."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Iterable
from typing import Protocol

from forge.bench.model import Candidate, PrInfo
from forge.bench.repo import GitRepoStore

SOURCE_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx")
_TEST_RE = re.compile(r"(^|/)tests?/|(^|/)test_[^/]*\.py$|_test\.py$|\.test\.(ts|tsx|js|jsx)$")


def is_test_path(path: str) -> bool:
    return bool(_TEST_RE.search(path))


def is_source_path(path: str) -> bool:
    return path.endswith(SOURCE_SUFFIXES) and not is_test_path(path)


def is_dependabot(author: str) -> bool:
    return "dependabot" in author.lower()


def task_id_for(repo: str, number: int) -> str:
    return f"{repo.split('/')[-1]}-{number}"


class PrSource(Protocol):
    def merged_prs(self, repo: str) -> list[PrInfo]: ...


class GhPrSource:
    """Merged PRs through the GitHub CLI (`gh`), which uses the owner's own login."""

    FIELDS = "number,title,body,author,files,mergeCommit"

    def __init__(self, limit: int = 300) -> None:
        self.limit = limit

    def merged_prs(self, repo: str) -> list[PrInfo]:
        out = subprocess.run(
            ["gh", "pr", "list", "-R", repo, "--state", "merged", "--limit", str(self.limit)]
            + ["--json", self.FIELDS],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        ).stdout
        return parse_gh_prs(repo, out)


def parse_gh_prs(repo: str, gh_json: str) -> list[PrInfo]:
    prs = []
    for p in json.loads(gh_json):
        merge = (p.get("mergeCommit") or {}).get("oid")
        if not merge:
            continue
        prs.append(
            PrInfo(
                repo=repo,
                number=int(p["number"]),
                title=p.get("title") or "",
                body=p.get("body") or "",
                author=(p.get("author") or {}).get("login", ""),
                merge_sha=merge,
                files=tuple(f["path"] for f in p.get("files") or []),
            )
        )
    return prs


def mine(prs: Iterable[PrInfo], store: GitRepoStore) -> list[Candidate]:
    """Candidates from merged, non-Dependabot PRs that change source files and test files."""
    candidates = []
    for pr in prs:
        if is_dependabot(pr.author):
            continue
        tests = tuple(
            sorted(p for p in pr.files if is_test_path(p) and p.endswith(SOURCE_SUFFIXES))
        )
        if not tests or not any(is_source_path(p) for p in pr.files):
            continue
        candidates.append(
            Candidate(
                task_id=task_id_for(pr.repo, pr.number),
                repo=pr.repo,
                pr_number=pr.number,
                base_sha=store.parent(pr.repo, pr.merge_sha),
                solution_sha=pr.merge_sha,
                holdout=tests,
            )
        )
    return candidates
