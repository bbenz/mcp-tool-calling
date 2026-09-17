"""The web front end reports decisions; it must never make one.

These tests pin three things: the page cannot become a way to reach something
the operator scripts would not let you reach, the scenario listing cannot drift
from what a run actually claims, and the reset endpoint stays shut.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from refund_demo.briefings import ABOUT, BRIEFINGS
from refund_demo.config import get_settings
from refund_demo.scenarios import CLAIMS, SCENARIOS
from refund_demo.web.app import PAGE, app


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


def test_services_reports_where_it_is_running(client, monkeypatch):
    """The page's service URLs are loopback everywhere; this is what disambiguates them."""
    from refund_demo import runtime

    runtime.describe.cache_clear()
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
    monkeypatch.setenv("POD_NAME", "refund-demo-7c9f")
    try:
        body = client.get("/api/services").json()
        assert set(body) == {"services", "runtime"}
        assert set(body["services"]) == {"devidp", "mcp-a", "mcp-b", "upstream"}
        assert body["runtime"]["platform"] == "kubernetes"
        assert "refund-demo-7c9f" in body["runtime"]["detail"]
        assert body["runtime"]["loopback_note"]
    finally:
        runtime.describe.cache_clear()


def test_the_page_has_somewhere_to_put_the_runtime_badge_and_note(client):
    """Guards the two element ids the services() poll writes into."""
    body = client.get("/").text
    assert 'id="env"' in body
    assert 'id="loopback"' in body


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


# --- the gate must fail closed where it has a public address ---------------
#
# A missing or mis-keyed Secret used to remove authentication entirely, with
# the pod still reporting healthy and nothing in the logs to say so.

def test_no_key_still_means_no_gate_on_a_local_run(monkeypatch, fresh_settings, client):
    monkeypatch.delenv("WEB_ACCESS_KEY", raising=False)
    monkeypatch.delenv("WEB_REQUIRE_ACCESS_KEY", raising=False)
    get_settings.cache_clear()
    assert client.get("/api/scenarios").status_code == 200


def test_a_public_deployment_without_a_key_refuses_to_serve(monkeypatch, fresh_settings, client):
    monkeypatch.delenv("WEB_ACCESS_KEY", raising=False)
    monkeypatch.setenv("WEB_REQUIRE_ACCESS_KEY", "1")
    get_settings.cache_clear()
    for path in ("/", "/api/scenarios", "/api/ledger", "/api/audit", "/api/services"):
        assert client.get(path).status_code == 503, path


def test_health_answers_even_when_the_gate_is_refusing(monkeypatch, fresh_settings, client):
    """Probes must not be taken down by an operator configuration error."""
    monkeypatch.delenv("WEB_ACCESS_KEY", raising=False)
    monkeypatch.setenv("WEB_REQUIRE_ACCESS_KEY", "1")
    get_settings.cache_clear()
    assert client.get("/health").status_code == 200


def test_a_wrong_key_is_still_401_not_503(monkeypatch, fresh_settings, client):
    monkeypatch.setenv("WEB_ACCESS_KEY", "correct-horse")
    monkeypatch.setenv("WEB_REQUIRE_ACCESS_KEY", "1")
    get_settings.cache_clear()
    assert client.get("/api/scenarios?k=wrong").status_code == 401
    assert client.get("/api/scenarios?k=correct-horse").status_code == 200
    assert client.get("/api/scenarios", headers={"X-Demo-Key": "correct-horse"}).status_code == 200


# ---------------------------------------------------------------------------
# Briefings
#
# The page is read without narration at least as often as with it, so the
# explanatory text is part of the demo rather than decoration around it. These
# pin the two ways it could silently rot: a scenario added without a briefing,
# and a briefing left behind for a scenario that no longer exists.
# ---------------------------------------------------------------------------


def test_every_scenario_can_explain_itself():
    assert set(BRIEFINGS) == set(SCENARIOS)


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_a_briefing_answers_all_three_questions(name):
    # Separate floors: an expectation can be legitimately terse, an explanation
    # of why it matters cannot. Both floors have already caught real thinness.
    floors = {"sends": 60, "expects": 60, "why": 120}
    brief = BRIEFINGS[name]
    for field, floor in floors.items():
        assert brief[field].strip(), f"{name} has no {field}"
        assert len(brief[field]) > floor, f"{name}.{field} is too thin to be useful"


def test_the_api_serves_the_briefing_with_each_scenario(client):
    listed = client.get("/api/scenarios").json()
    assert len(listed) == len(SCENARIOS)
    for item in listed:
        assert item["sends"] and item["expects"] and item["why"], item["name"]
        assert item["claim"] == CLAIMS[item["name"]]


def test_the_page_carries_the_about_expander_and_the_scenario_expanders(client):
    body = client.get("/").text
    assert "<!--ABOUT-->" not in body, "the About placeholder was never substituted"
    assert "About this demo" in body
    for key in ("what", "how", "watch", "not"):
        # A distinctive fragment, so a rewrite that empties the text is caught.
        assert ABOUT[key][:40] in body, key
    assert "<details" in body and "toggleAll" in body


def test_run_output_is_still_escaped_even_though_briefings_are_not():
    """Briefings are authored here and contain markup on purpose.

    Scenario *results* are not authored here -- they carry reason codes and
    upstream text -- so show() must keep escaping them. If this ever inverts,
    the page starts rendering whatever an error message contains.
    """
    page = PAGE
    assert "esc(String(v))" in page, "result values are no longer escaped"
    assert "${s.sends}" in page and "${esc(s.sends)}" not in page