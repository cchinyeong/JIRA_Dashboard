# Live data check

A read-only command that fetches a few real tickets from the VE Jira, verifies the configured field IDs, saves sanitised copies as test fixtures and prints a report of how well the ticket mapper handles real data. It only sends GET requests and never changes Jira.

## Before you run it

1. Set the Jira base URL (HTTPS) in `settings.local.toml`:

```toml
[jira]
base_url = "https://your-jira-host"
```

2. Store a Personal Access Token in Windows Credential Manager (see [security.md](security.md)). Use a read-only account if possible.
3. Be on the network or VPN that reaches Jira. TLS verification stays on and uses the Windows certificate store, so the corporate CA is trusted without any extra setup.

## Run

```powershell
uv run python -m jira_dashboard.integrations.live_check
```

Default tickets are CAE-1513 (Epic), CAE-1558 (Risk), CAE-1592 (Issue) and CAE-1628 (Task). Pass other keys and a different output folder if needed:

```powershell
uv run python -m jira_dashboard.integrations.live_check CAE-1700 CAE-1701 --output tests/unit/fixtures/live
```

The exit status is 0 when every ticket was retrieved and 1 otherwise (including a blocked write).

## What you get

- **Field check:** each configured field ID is compared with Jira's field list (`ok`, `missing` or `name_mismatch`).
- **Per ticket:** whether the mapper handled it, and the kind, status, domain, request drivers, parent, estimates, requester found (yes/no), sprint state, the Epic Link value shape, the sprint format and the issue link texts seen. Free text such as summaries and sprint names is not printed.
- **Sanitised fixtures:** `tests/unit/fixtures/live/<KEY>.json`. Raw responses are never written to disk.

## How the sanitising works

Only an allow-list of structural fields is kept. People become `user-N`, summaries become `Sample ticket <KEY>`, and description panels keep only their titles (the requester panel keeps a placeholder name). Before anything is written, the output is scanned for the Jira host name, real e-mail addresses and the token; if any is found nothing is written.

## Review before committing

- Open each file in `tests/unit/fixtures/live/` and check that nothing identifies a person or project.
- Sprint names and component names are kept as they are; confirm they are acceptable to commit.
- Share the console report (it contains no free text) so the mapper can be corrected where real data differed.
