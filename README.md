# forge

Forge is an AI-native software factory platform: a control plane, LLM gateway, agent harness, policy, evidence and
FinOps for governed AI agents across the software delivery lifecycle.

Design, requirements and architecture: [ai-native-software-factory-design](https://github.com/vishal7pandey/ai-native-software-factory-design).
Work tracking: Jira project FORGE. Status: early, building Slice 1 (ticket to verified pull request).

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Test and lint

```bash
uv run pytest -q          # on machines where pytest.exe is blocked: uv run python -m pytest -q
uv run ruff check .
uv run ruff format --check .
```

## How work happens

Every change is a work item in `docs/work/` with a spec, plan and test plan, following the AI Software Factory method
(`AGENTS.md`). Owner decisions are records in `docs/decisions/`.

## License

[Apache-2.0](LICENSE)
