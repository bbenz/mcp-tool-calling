"""The web front end reports decisions; it must never make one.

These tests pin three things: the page cannot become a way to reach something
the operator scripts would not let you reach, the scenario listing cannot drift
from what a run actually claims, and the reset endpoint stays shut.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from refund_demo.config import get_settings
from refund_demo.scenarios import CLAIMS, SCENARIOS
from refund_demo.web.app import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def fresh_settings():
    """Settings are cached; tests that change the environment must clear it."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_health_is_cheap_and_does_not_require_the_other_services(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "web"}


def test_the_page_renders_without_any_external_resource(client):
    """Stage requirement: this has to work with the Wi-Fi switched off."""
    body = client.get("/").text
    assert body.startswith("<!doctype html>")
    for marker in ("//cdn.", "https://unpkg", "https://cdnjs", "<script src="):
        assert marker not in body, f"page reaches out to {marker}"


def test_every_scenario_is_listed_with_the_claim_it_will_report(client):
    listed = client.get("/api/scenarios").json()
    assert len(listed) == len(SCENARIOS)
    assert {item["name"] for item in listed} == set(SCENARIOS)
    assert all(item["claim"] for item in listed), "a scenario is listed with no claim"


def test_the_listing_cannot_drift_from_the_scenarios():
    assert set(CLAIMS) == set(SCENARIOS)


def test_an_unknown_scenario_is_a_404_not_a_500(client):
    assert client.post("/api/scenarios/not-a-scenario/run").status_code == 404


def test_reset_over_http_is_refused_by_default(client, fresh_settings):
    response = client.post("/api/reset")
    assert response.status_code == 403
    assert "WEB_ALLOW_RESET" in response.json()["detail"]


def test_reset_stays_refused_in_entra_mode_even_when_enabled(monkeypatch, fresh_settings):
    monkeypatch.setenv("WEB_ALLOW_RESET", "1")
    monkeypatch.setenv("AUTH_MODE", "entra")
    monkeypatch.delenv("ALLOW_RESET", raising=False)
    get_settings.cache_clear()
    with TestClient(app) as client:
        response = client.post("/api/reset")
    assert response.status_code == 403
    assert "entra" in response.json()["error"]


def test_the_access_key_gate_blocks_every_data_route(monkeypatch, fresh_settings):
    monkeypatch.setenv("WEB_ACCESS_KEY", "s3cret")
    get_settings.cache_clear()
    with TestClient(app) as client:
        assert client.get("/").status_code == 401
        for path in ("/api/scenarios", "/api/ledger", "/api/audit", "/api/services"):
            assert client.get(path).status_code == 401, f"{path} was not gated"
        assert client.post("/api/scenarios/no-token/run").status_code == 401
        # health stays open so Kubernetes probes still work
        assert client.get("/health").status_code == 200
        # and the key lets you back in, by query string or by header
        assert client.get("/api/scenarios?k=s3cret").status_code == 200
        assert client.get("/api/scenarios", headers={"x-demo-key": "s3cret"}).status_code == 200


def test_the_ledger_endpoint_exposes_the_digest_and_no_secrets(client):
    body = client.get("/api/ledger").json()
    assert len(body["fingerprint"]["digest"]) == 64
    assert isinstance(body["orders"], list) and body["orders"]
    serialized = str(body)
    for forbidden in ("Bearer ", "access_token", "client_secret", "private_key"):
        assert forbidden not in serialized


def test_the_audit_endpoint_honours_last_and_survives_a_bad_value(client):
    assert client.get("/api/audit?last=3").status_code == 200
    assert client.get("/api/audit?last=not-a-number").status_code == 200
    assert client.get("/api/audit?last=-5").status_code == 200


def test_a_scenario_runs_end_to_end_through_the_web_api(client, services):
    body = client.post("/api/scenarios/wrong-audience/run").json()
    assert body["passed"] is True
    assert body["ledger_changed"] is False
    assert body["claim"] == CLAIMS["wrong-audience"]
