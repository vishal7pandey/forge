import pytest

from forge.bench.environment import credential_names, prepare_task_env
from forge.bench.executor import LocalExecutor
from forge.bench.mine import mine
from forge.bench.repo import git
from forge.bench.validate import validate


@pytest.fixture(scope="module")
def mul_task(fixture_repo, tmp_path_factory):
    cand = mine([fixture_repo.prs["mul"]], fixture_repo.store)[0]
    return validate(cand, fixture_repo.store, LocalExecutor(), tmp_path_factory.mktemp("v"))


def test_env_has_no_holdout_and_no_credentials(fixture_repo, mul_task, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_should_not_leak")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "should_not_leak")
    env = prepare_task_env(
        mul_task,
        fixture_repo.store,
        LocalExecutor(),
        tmp_path,
        model_key=("OPENAI_API_KEY", "sk-test"),
    )
    for path in mul_task.holdout:
        assert not (env.dir / path).exists()
    assert (env.dir / "src" / "calc.py").exists()
    assert git("remote", "-v", cwd=env.dir).strip() == ""
    assert credential_names(env.env) == ["OPENAI_API_KEY"]
    assert "GITHUB_TOKEN" not in env.env and "AWS_SECRET_ACCESS_KEY" not in env.env


def test_env_without_model_key_holds_no_credentials(fixture_repo, mul_task, tmp_path):
    env = prepare_task_env(mul_task, fixture_repo.store, LocalExecutor(), tmp_path)
    assert credential_names(env.env) == []
