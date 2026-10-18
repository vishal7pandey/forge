"""Git access for the benchmark: cached bare clones, file reads at a SHA, disposable checkouts."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


def git(*args: str, cwd: Path | None = None, check: bool = True) -> str:
    """Run git and return stdout. Raises GitError with git's stderr on failure."""
    proc = subprocess.run(
        ["git", "-c", "core.autocrlf=false", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


class GitRepoStore:
    """Bare clones under `cache_root`, one per repository, refreshed on demand."""

    def __init__(self, cache_root: Path) -> None:
        self.cache_root = Path(cache_root)
        self._urls: dict[str, str] = {}

    def register(self, repo: str, url: str) -> None:
        self._urls[repo] = url

    def _dir(self, repo: str) -> Path:
        return self.cache_root / repo.replace("/", "__")

    def ensure(self, repo: str) -> Path:
        d = self._dir(repo)
        if not d.exists():
            url = self._urls.get(repo, f"https://github.com/{repo}.git")
            d.parent.mkdir(parents=True, exist_ok=True)
            git("clone", "--quiet", "--bare", url, str(d))
        return d

    def parent(self, repo: str, sha: str) -> str:
        return git("rev-parse", f"{sha}^1", cwd=self.ensure(repo)).strip()

    def read_file(self, repo: str, sha: str, path: str) -> str | None:
        out = subprocess.run(
            ["git", "show", f"{sha}:{path}"],
            cwd=self.ensure(repo),
            capture_output=True,
        )
        if out.returncode != 0:
            return None
        return out.stdout.decode("utf-8", errors="replace")

    def changed_files(self, repo: str, base: str, solution: str) -> list[str]:
        out = git("diff", "--name-only", base, solution, cwd=self.ensure(repo))
        return [line for line in out.splitlines() if line]

    def diff(self, repo: str, base: str, solution: str, exclude: tuple[str, ...] = ()) -> str:
        """Unified diff from base to solution, optionally without some paths."""
        specs = ["--", "."] + [f":(exclude){p}" for p in exclude]
        return git("diff", "--binary", base, solution, *specs, cwd=self.ensure(repo))

    def checkout(self, repo: str, sha: str, dest: Path) -> Path:
        """A fresh working copy at `sha` with no remotes."""
        dest = Path(dest)
        if dest.exists():
            shutil.rmtree(dest)
        git("clone", "--quiet", "--no-hardlinks", str(self.ensure(repo)), str(dest))
        git("checkout", "--quiet", "--detach", sha, cwd=dest)
        for remote in git("remote", cwd=dest).split():
            git("remote", "remove", remote, cwd=dest)
        return dest
