import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

import httpx

from jira_dashboard.config import Settings, get_settings
from jira_dashboard.integrations.jira_http import JiraApiError, JiraHttp, check_fields
from jira_dashboard.integrations.live_report import (
    EXPECTED_TYPES,
    TicketReport,
    analyse_ticket,
    format_report,
)
from jira_dashboard.integrations.live_sanitize import UserAliases, find_leaks, sanitize_issue
from jira_dashboard.services.secrets import JIRA_PAT, MissingSecretError, SecretStore, get_secret
from jira_dashboard.utils.redaction import redact

DEFAULT_OUTPUT = Path("tests/unit/fixtures/live")
FATAL_KINDS = {"auth", "tls", "connection", "timeout"}


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="live_check", description="Read-only check of real Jira tickets."
    )
    parser.add_argument("keys", nargs="*", default=list(EXPECTED_TYPES), help="ticket keys")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="fixture directory")
    return parser.parse_args(argv)


def _emit(text: str) -> None:
    print(redact(text))


def main(
    argv: Sequence[str] | None = None,
    *,
    settings: Settings | None = None,
    secret_store: SecretStore | None = None,
    transport: httpx.BaseTransport | None = None,
) -> int:
    args = _parse(argv)
    settings = settings or get_settings()

    if settings.jira.is_placeholder:
        _emit(
            "The Jira base URL is not configured. Set jira.base_url in settings.local.toml "
            "or JIRA_DASHBOARD_JIRA__BASE_URL."
        )
        return 1
    try:
        token = get_secret(JIRA_PAT, secret_store)
    except MissingSecretError:
        _emit("No Jira token is stored. Follow docs/security.md to store the PAT.")
        return 1

    probe = JiraHttp(settings, token, transport=transport)
    try:
        return _run(args, settings, probe, token.get_secret_value())
    finally:
        probe.close()


def _run(args: argparse.Namespace, settings: Settings, probe: JiraHttp, token: str) -> int:
    findings = []
    try:
        findings = check_fields(settings, probe.get_fields())
    except JiraApiError as exc:
        if exc.kind in FATAL_KINDS:
            _emit(f"Cannot continue: {exc}")
            return 1
        _emit(f"Field list not available: {exc}")

    reports: list[TicketReport] = []
    errors: dict[str, str] = {}
    sanitised: dict[str, dict] = {}
    users = UserAliases()
    for key in args.keys:
        try:
            raw = probe.get_issue(key)
        except JiraApiError as exc:
            errors[key] = str(exc)
            if exc.kind in FATAL_KINDS:
                break
            continue
        reports.append(analyse_ticket(raw, settings, EXPECTED_TYPES.get(key)))
        sanitised[key] = sanitize_issue(raw, settings, users)

    notes = _write_fixtures(args.output, sanitised, settings, token)
    _emit(format_report(reports, findings, errors, notes))
    leaked = any("not written" in note for note in notes)
    return 1 if errors or leaked else 0


def _write_fixtures(
    output: Path, sanitised: dict[str, dict], settings: Settings, token: str
) -> list[str]:
    if not sanitised:
        return ["No fixtures written."]
    texts = {key: json.dumps(payload, indent=2) + "\n" for key, payload in sanitised.items()}
    leaks = sorted(
        {
            leak
            for text in texts.values()
            for leak in find_leaks(text, settings.jira.base_url, token)
        }
    )
    if leaks:
        return [f"Fixtures not written: sanitised output still contains: {', '.join(leaks)}."]
    output.mkdir(parents=True, exist_ok=True)
    for key, text in texts.items():
        (output / f"{key}.json").write_text(text, encoding="utf-8")
    return [f"Sanitised fixtures written to {output}. Review them before committing."]


if __name__ == "__main__":
    sys.exit(main())
