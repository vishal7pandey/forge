"""Where commands run. LocalExecutor for offline tests; DockerExecutor (PR B) for real tasks."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

# Host variables a process needs to start at all (Windows needs SYSTEMROOT for Python). Nothing
# credential-like is ever on this list; credentials are added explicitly by the caller.
BASE_ENV_NAMES = ("PATH", "SYSTEMROOT", "COMSPEC", "PATHEXT", "HOME", "USERPROFILE", "TEMP", "TMP")


def minimal_env(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    env = {k: os.environ[k] for k in BASE_ENV_NAMES if k in os.environ}
    env.update(extra or {})
    return env


@dataclass(frozen=True)
class ExecResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


class Executor(Protocol):
    def run(
        self,
        cmd: Sequence[str],
        cwd: Path,
        env: Mapping[str, str],
        *,
        network: bool,
        timeout: float,
    ) -> ExecResult: ...


@dataclass
class LocalExecutor:
    """Runs on the host. It cannot switch the network off; it records the request instead."""

    calls: list[tuple[tuple[str, ...], bool]] = field(default_factory=list)

    def run(self, cmd, cwd, env, *, network, timeout):
        self.calls.append((tuple(cmd), network))
        try:
            p = subprocess.run(
                list(cmd),
                cwd=cwd,
                env=dict(env),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            return ExecResult(-1, _text(e.stdout), _text(e.stderr), timed_out=True)
        return ExecResult(p.returncode, p.stdout, p.stderr)


def _text(b: bytes | str | None) -> str:
    if b is None:
        return ""
    return b if isinstance(b, str) else b.decode("utf-8", errors="replace")
