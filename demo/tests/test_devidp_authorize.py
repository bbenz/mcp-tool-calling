"""The /authorize endpoint hands out authorization codes, so it has to be picky.

Two defects lived here. Neither was reachable from the internet in the shipped
topology -- devidp is never published by the Service -- but both are the exact
class of bug this talk is about, and a demo that argues for careful
authorization should not contain them.
"""

from __future__ import annotations

import urllib.parse

import pytest
from starlette.testclient import TestClient

from refund_demo.devidp.server import app

BASE = {
    "response_type": "code",
    "client_id": "copilot-demo-client",
    "redirect_uri": "http://localhost:7777/callback",
    "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
    "code_challenge_method": "S256",
    "resource": "api://refund-mcp-a",
    "scope": "Refunds.Read",
}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _authorize(client, **overrides):
    params = {**BASE, **overrides}
    return client.get(f"/authorize?{urllib.parse.urlencode(params)}", follow_redirects=False)


def test_the_login_page_renders_for_a_valid_request(client):
    response = _authorize(client)
    assert response.status_code == 200
    assert "Sign in as" in response.text


@pytest.mark.parametrize(
    "hostile",
    [
        "https://attacker.example/callback",
        "http://attacker.example/callback",
        "http://localhost.attacker.example/callback",
        "//attacker.example/callback",
        "javascript:alert(1)",
    ],
)
def test_an_unregistered_redirect_uri_is_refused(client, hostile):
    """Otherwise /authorize is a code exfiltration primitive for any host."""
    response = _authorize(client, redirect_uri=hostile, employee="sam.agent")
    assert response.status_code != 302
    assert "attacker.example" not in response.headers.get("location", "")


def test_a_loopback_redirect_uri_still_works(client):
    """RFC 8252: native clients get loopback callbacks on an arbitrary port."""
    response = _authorize(client, redirect_uri="http://127.0.0.1:9999/cb", employee="sam.agent")
    assert response.status_code == 302
    assert response.headers["location"].startswith("http://127.0.0.1:9999/cb?")
    assert "code=" in response.headers["location"]


@pytest.mark.parametrize("field", ["client_id", "scope", "resource"])
def test_query_parameters_are_escaped_into_the_login_page(client, field):
    """These three are interpolated into HTML; unescaped they are reflected XSS."""
    response = _authorize(client, **{field: "<script>alert(1)</script>"})
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;" in response.text
