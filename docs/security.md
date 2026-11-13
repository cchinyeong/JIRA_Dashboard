# Security

## Jira Personal Access Token (PAT)

1. In Jira on-prem, create a PAT (Profile > Personal Access Tokens). Prefer a dedicated account with the least permissions needed (read-only until write-back exists) and set an expiry.
2. Start the dashboard (`uv run jira-dashboard`). On first run the **Jira setup** dialog opens by itself; at any other time use **Jira setup…** on the toolbar. Enter the Jira address and paste the token (the field is masked), press **Test connection**, then **Save**.
   - The token goes only to Windows Credential Manager. It is never written to a file, shown or logged, and the dialog clears it after saving.
   - The address goes into `settings.local.toml` (only the `jira.base_url` line changes; the file holds no secrets).
   - If a token is already stored, leave the token field empty to keep it.
   - Test connection makes one read-only request (`GET /rest/api/2/myself`) and saves nothing.
3. Alternatively store it from a terminal (never in a file, source code or settings):

```powershell
uv run python -c "import getpass; from jira_dashboard.services.secrets import set_secret, JIRA_PAT; set_secret(JIRA_PAT, getpass.getpass('Jira PAT: '))"
```

4. Rotate by opening **Jira setup…** and saving the new token (or running the command above), and revoke the old one in Jira.
5. Remove it:

```powershell
uv run python -c "from jira_dashboard.services.secrets import delete_secret, JIRA_PAT; delete_secret(JIRA_PAT)"
```

Entries appear in Credential Manager under the name `jira-pat` for service `jira-dashboard`, and are encrypted per Windows user.

## Development-only environment fallback

Set `JIRA_DASHBOARD_ALLOW_ENV_SECRETS=1` and `JIRA_DASHBOARD_SECRET_JIRA_PAT=<token>` to read the PAT from the environment. It is used only when nothing is stored, logs a warning, and must not be used in production.

## Logging

`jira_dashboard.utils.logging.configure_logging(settings.logging)` writes to the console and a rotating `dashboard.log`. All handlers redact credentials:

- Every secret returned by `get_secret` is registered and masked exactly (primary defence).
- Patterns mask `Authorization` headers, `Bearer`/`Basic` values and `token`, `password`, `secret`, `api_key` pairs (second layer).

Redaction cannot recognise a secret that was never registered and has an unusual format, so never log request headers or raw credentials deliberately.

Retrieved secrets are `SecretStr` values: printing them shows `**********`; call `.get_secret_value()` only where the value is needed.

## Integration test

The real Credential Manager test is skipped by default:

```powershell
$env:JIRA_DASHBOARD_TEST_KEYRING = "1"; uv run pytest tests/integration
```
