import importlib
from pathlib import Path

import pytest

import jira_dashboard

SUBPACKAGES = ["models", "services", "integrations", "config", "utils", "ui"]


@pytest.mark.parametrize("name", SUBPACKAGES)
def test_subpackage_importable(name: str) -> None:
    assert importlib.import_module(f"jira_dashboard.{name}")


@pytest.mark.parametrize("name", ["skills", "agents", "workflows", "database"])
def test_future_packages_not_created_yet(name: str) -> None:
    package_dir = Path(jira_dashboard.__file__).parent
    assert not (package_dir / name).exists()


def test_main_exits_with_the_ui_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("jira_dashboard.ui.app.run", lambda: 7)
    with pytest.raises(SystemExit) as exc:
        jira_dashboard.main()
    assert exc.value.code == 7
