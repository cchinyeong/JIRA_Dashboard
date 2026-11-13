import logging
from dataclasses import dataclass

import httpx
from pydantic import SecretStr

from jira_dashboard.config import Settings
from jira_dashboard.integrations.jira_http import JiraApiError, JiraHttp
from jira_dashboard.utils.redaction import register_secret

logger = logging.getLogger(__name__)

OK = "ok"
REJECTED = "rejected"
UNREACHABLE = "unreachable"
CERTIFICATE = "certificate"
OTHER = "other"


@dataclass(frozen=True, slots=True)
class ConnectionResult:
    ok: bool
    kind: str
    message: str
    user: str | None = None


def _plain(exc: JiraApiError) -> ConnectionResult:
    if exc.kind == "auth":
        return ConnectionResult(
            False,
            REJECTED,
            "Jira did not accept the token. Check that it is correct, has not expired and "
            "belongs to an account that can read the CAE project.",
        )
    if exc.kind == "tls":
        return ConnectionResult(
            False,
            CERTIFICATE,
            "The Jira certificate is not trusted by Windows. Install the corporate CA or "
            "check the VPN.",
        )
    if exc.kind in ("connection", "timeout"):
        return ConnectionResult(
            False,
            UNREACHABLE,
            "Cannot reach this address. Check the address and the VPN.",
        )
    return ConnectionResult(False, OTHER, f"Jira answered unexpectedly: {exc}")


def check_connection(
    settings: Settings,
    address: str,
    token: SecretStr,
    transport: httpx.BaseTransport | None = None,
) -> ConnectionResult:
    """One read-only request (GET /myself) with the given address and token; saves nothing."""
    register_secret(token.get_secret_value())
    candidate = settings.model_copy(
        update={"jira": settings.jira.model_copy(update={"base_url": address})}
    )
    http = JiraHttp(candidate, token, transport=transport, sleep=lambda _seconds: None)
    try:
        me = http.get_myself()
    except JiraApiError as exc:
        logger.info("Connection test failed (%s)", exc.kind)
        return _plain(exc)
    except Exception:
        logger.exception("Unexpected error during the connection test")
        return ConnectionResult(
            False, OTHER, "The test failed unexpectedly. See the log for details."
        )
    finally:
        http.close()
    name = me.get("displayName") or me.get("name") or "an unnamed account"
    logger.info("Connection test succeeded")
    return ConnectionResult(True, OK, f"Connected as {name}.", name)
