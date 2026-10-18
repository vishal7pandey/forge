from dataclasses import replace

from forge.bench.mine import mine
from forge.bench.statement import build_statement, strip_diff


def _mul(fixture_repo):
    pr = fixture_repo.prs["mul"]
    return pr, mine([pr], fixture_repo.store)[0]


class _SpecStore:
    """Wraps the fixture store so a spec.md exists at the solution SHA."""

    def __init__(self, store, spec_text):
        self._store, self._spec = store, spec_text

    def read_file(self, repo, sha, path):
        return self._spec if path.endswith("spec.md") else self._store.read_file(repo, sha, path)

    def diff(self, *a, **k):
        return self._store.diff(*a, **k)


def test_statement_prefers_spec(fixture_repo, tmp_path):
    pr, cand = _mul(fixture_repo)
    pr = replace(pr, files=pr.files + ("docs/work/X-1-add-mul/spec.md",))
    (tmp_path / f"{cand.task_id}.md").write_text("from jira", encoding="utf-8")
    store = _SpecStore(fixture_repo.store, "# X-1 Add mul\n\nR1. The system multiplies.\n")
    text, source = build_statement(pr, cand, store, overrides=tmp_path)
    assert source == "spec"
    assert text == "# X-1 Add mul\n\nR1. The system multiplies."


def test_statement_uses_jira_override(fixture_repo, tmp_path):
    pr, cand = _mul(fixture_repo)
    (tmp_path / f"{cand.task_id}.md").write_text("  Ticket text from Jira.\n", encoding="utf-8")
    assert build_statement(pr, cand, fixture_repo.store, overrides=tmp_path) == (
        "Ticket text from Jira.",
        "jira",
    )


def test_statement_pr_body_has_no_diff_lines(fixture_repo):
    pr, cand = _mul(fixture_repo)
    body = (
        "Adds multiplication.\n\n"
        "- keeps add unchanged\n"
        "@@ -1,2 +1,5 @@\n"
        "+def mul(a, b):\n"
        "+    return a * b\n"
        "```diff\n"
        "-old line\n"
        "+new line\n"
        "```\n"
        "Done."
    )
    text, source = build_statement(replace(pr, body=body), cand, fixture_repo.store)
    assert source == "pr"
    lines = text.splitlines()
    assert lines[0] == "PR 1"
    assert "- keeps add unchanged" in lines
    assert "Done." in lines
    for leaked in ("@@ -1,2 +1,5 @@", "+def mul(a, b):", "+    return a * b", "-old line"):
        assert leaked not in lines


def test_statement_empty_body_is_title_only(fixture_repo):
    pr, cand = _mul(fixture_repo)
    assert build_statement(replace(pr, body=""), cand, fixture_repo.store) == ("PR 1", "pr")


def test_strip_diff_keeps_bullets_not_in_diff():
    assert strip_diff("- a bullet\n+ also text", "+other\n") == "- a bullet\n+ also text"
