"""Command line: `python -m forge.bench {mine,validate,run,report}`."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from forge.bench.executor import LocalExecutor
from forge.bench.metrics import summarize, update_section
from forge.bench.mine import GhPrSource, mine
from forge.bench.model import Candidate, Task, TaskSet
from forge.bench.repo import GitRepoStore
from forge.bench.runner import RunConfig, load_results, run_tasks
from forge.bench.solvers import ScriptedSolver, solution_patch
from forge.bench.statement import build_statement
from forge.bench.validate import validate

DEFAULT_CACHE = Path.home() / ".cache" / "forge" / "repos"


def _store(args) -> GitRepoStore:
    store = GitRepoStore(Path(args.cache))
    for spec in args.repo_url or []:
        name, _, url = spec.partition("=")
        store.register(name, url)
    return store


def cmd_mine(args) -> int:
    store = _store(args)
    out = []
    for repo in args.repo:
        prs = {p.number: p for p in GhPrSource(limit=args.limit).merged_prs(repo)}
        for c in mine(prs.values(), store):
            text, source = build_statement(prs[c.pr_number], c, store, args.overrides)
            out.append({**asdict(c), "statement": text, "statement_source": source})
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"mine: {len(out)} candidate(s) -> {args.out}")
    return 0


def cmd_validate(args) -> int:
    store = _store(args)
    tasks, exclusions = [], []
    for i, d in enumerate(json.loads(Path(args.candidates).read_text(encoding="utf-8"))):
        c = Candidate(**{**d, "holdout": tuple(d["holdout"])})
        r = validate(c, store, LocalExecutor(), Path(args.workdir) / f"v{i}")
        (tasks if isinstance(r, Task) else exclusions).append(r)
    ts = TaskSet(tuple(tasks), tuple(exclusions))
    Path(args.out).write_text(ts.to_json(), encoding="utf-8")
    print(f"validate: {len(tasks)} task(s), {len(exclusions)} excluded -> {args.out}")
    return 0


def cmd_run(args) -> int:
    store = _store(args)
    ts = TaskSet.from_json(Path(args.taskset).read_text(encoding="utf-8"))
    if args.solver == "scripted-solution":
        solver = ScriptedSolver(patch_for=lambda t: solution_patch(t, store))
    elif args.solver == "scripted-empty":
        solver = ScriptedSolver()
    else:
        print(f"unknown solver {args.solver!r}", file=sys.stderr)
        return 2
    cfg = RunConfig(cap_usd=args.cap, ceiling_usd=args.ceiling, force=args.force)
    new = run_tasks(ts, solver, store, LocalExecutor(), Path(args.workdir), Path(args.results), cfg)
    print(f"run: {len(new)} result(s) -> {args.results}")
    return 0


def cmd_report(args) -> int:
    results = load_results(Path(args.results))
    values = summarize(results)
    update_section(Path(args.metrics), args.section, values)
    print(json.dumps(values, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m forge.bench")
    p.add_argument("--cache", default=str(DEFAULT_CACHE), help="bare clone cache")
    p.add_argument("--repo-url", action="append", help="owner/name=url override (tests, mirrors)")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("mine", help="candidates from merged PRs (uses gh)")
    m.add_argument("--repo", action="append", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--overrides", type=Path, help="dir of <task_id>.md statements from Jira")
    m.add_argument("--limit", type=int, default=300)
    m.set_defaults(func=cmd_mine)

    v = sub.add_parser("validate", help="candidates -> versioned task set")
    v.add_argument("--candidates", required=True)
    v.add_argument("--out", required=True)
    v.add_argument("--workdir", required=True)
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("run", help="run a solver over a task set")
    r.add_argument("--taskset", required=True)
    r.add_argument("--solver", required=True, help="scripted-solution | scripted-empty")
    r.add_argument("--results", required=True)
    r.add_argument("--workdir", required=True)
    r.add_argument("--cap", type=float, default=RunConfig().cap_usd)
    r.add_argument("--ceiling", type=float, default=RunConfig().ceiling_usd)
    r.add_argument("--force", action="store_true")
    r.set_defaults(func=cmd_run)

    rep = sub.add_parser("report", help="results -> metrics section")
    rep.add_argument("--results", required=True)
    rep.add_argument("--metrics", default="docs/metrics/phase0.yaml")
    rep.add_argument("--section", default="baseline")
    rep.set_defaults(func=cmd_report)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
