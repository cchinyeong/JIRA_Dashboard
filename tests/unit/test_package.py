import importlib

import pytest

import jira_dashboard

SUBPACKAGES = ["models", "services", "integrations", "config", "utils"]


@pytest.mark.parametrize("name", SUBPACKAGES)
def test_subpackage_importable(name: str) -> None:
    assert importlib.import_module(f"jira_dashboard.{name}")


def test_main_runs(capsys: pytest.CaptureFixture[str]) -> None:
    jira_dashboard.main()
    assert capsys.readouterr().out.strip() == "jira-dashboard"
