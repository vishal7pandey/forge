"""Task statements: what the solver is told, without leaking the solution or the holdout."""

from __future__ import annotations

import re
from pathlib import Path

from forge.bench.model import Candidate, PrInfo
from forge.bench.repo import GitRepoStore

_SPEC_RE = re.compile(r"^docs/work/[^/]+/spec\.md$")
_DIFF_MARKERS = ("@@", "diff --git", "+++ ", "--- ", "index ")
_FENCE_RE = re.compile(r"^\s*```")


def strip_diff(text: str, diff: str) -> str:
    """Remove pasted diff content from PR text.

    Drops fenced blocks labelled diff/patch, hunk and file headers, and any line identical to an
    added or removed line of the PR's own diff. Ordinary Markdown bullets ("- item") are kept unless
    they literally appear in the diff.
    """
    diff_lines = {
        line
        for line in diff.splitlines()
        if line[:1] in "+-" and not line.startswith(("+++", "---")) and line[1:].strip()
    }
    out: list[str] = []
    in_diff_fence = False
    for line in text.splitlines():
        if _FENCE_RE.match(line):
            label = line.strip().strip("`").strip().lower()
            if in_diff_fence:
                in_diff_fence = False
                continue
            if label in ("diff", "patch"):
                in_diff_fence = True
                continue
        if in_diff_fence:
            continue
        if line.startswith(_DIFF_MARKERS) or line in diff_lines:
            continue
        out.append(line)
    return "\n".join(out).strip()


def build_statement(
    pr: PrInfo, candidate: Candidate, store: GitRepoStore, overrides: Path | None = None
) -> tuple[str, str]:
    """(statement, source), source being `spec`, `jira` or `pr`."""
    for path in pr.files:
        if _SPEC_RE.match(path):
            text = store.read_file(pr.repo, candidate.solution_sha, path)
            if text and text.strip():
                return text.strip(), "spec"
    if overrides is not None:
        f = Path(overrides) / f"{candidate.task_id}.md"
        if f.is_file():
            return f.read_text(encoding="utf-8").strip(), "jira"
    diff = store.diff(pr.repo, candidate.base_sha, candidate.solution_sha)
    body = strip_diff(pr.body, diff)
    text = pr.title.strip() + ("\n\n" + body if body else "")
    return text, "pr"
