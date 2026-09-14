"""Shared fixtures.

The unit tests here do not need the services running: they exercise the policy
engine and the token validator directly. The end-to-end tests do need them, and
skip themselves with a clear message when the services are down, so a partial
run never looks like a pass.
"""

from __future__ import annotations

import httpx
import pytest

from refund_demo import ledger
from refund_demo.config import get_settings


def _service_up(url: str) -> bool:
    try:
        return httpx.get(f"{url}/health", timeout=2.0).status_code == 200
    except httpx.HTTPError:
        return False


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture(scope="session")
def services(settings):
    required = {
        "devidp": settings.issuer,
        "mcp-a": settings.mcp_a_public_url,
        "mcp-b": settings.mcp_b_public_url,
        "upstream": settings.upstream_api_url,
    }
    down = [name for name, url in required.items() if not _service_up(url)]
    if down:
        pytest.skip(f"services not running: {', '.join(down)} (run scripts\\start-all.ps1)")
    return required


@pytest.fixture(scope="session", autouse=True)
def fresh_ledger():
    ledger.initialize()
    return ledger.ledger_fingerprint()
