"""Where the demo says it is running.

Every service URL in this demo is loopback in every environment, so the only
thing separating "this is the cluster" from "this is your laptop" on a
projector is what these functions report.
"""

from __future__ import annotations

import pytest

from refund_demo import runtime


@pytest.fixture(autouse=True)
def _clear_cache():
    runtime.describe.cache_clear()
    yield
    runtime.describe.cache_clear()


@pytest.fixture
def not_a_container(monkeypatch):
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
    monkeypatch.setattr(runtime, "_in_container", lambda: False)


def test_a_laptop_reports_local(not_a_container):
    info = runtime.describe()
    assert info["platform"] == "local"
    assert info["label"] == "Local"


def test_a_pod_reports_kubernetes_with_its_pod_and_node(monkeypatch):
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
    monkeypatch.setenv("POD_NAME", "refund-demo-7c9f")
    monkeypatch.setenv("NODE_NAME", "aks-nodepool1-42")
    info = runtime.describe()
    assert info["platform"] == "kubernetes"
    assert info["label"] == "Kubernetes"
    assert "refund-demo-7c9f" in info["detail"]
    # The node is long enough to push the zoom controls off a projector, so it
    # belongs in the tooltip rather than the badge.
    assert "aks-nodepool1-42" not in info["detail"]
    assert "refund-demo-7c9f" in info["full"]
    assert "aks-nodepool1-42" in info["full"]


def test_kubernetes_is_reported_even_without_the_downward_api(monkeypatch):
    """The manifests supply POD_NAME/NODE_NAME, but a hand-applied pod may not."""
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
    monkeypatch.delenv("POD_NAME", raising=False)
    monkeypatch.delenv("NODE_NAME", raising=False)
    info = runtime.describe()
    assert info["platform"] == "kubernetes"
    assert info["detail"], "must still say something rather than render an empty badge"
    assert info["full"], "an empty tooltip would render as a bare attribute"


def test_kubernetes_wins_over_the_container_check(monkeypatch):
    """A pod is also a container; it must not be labelled Compose."""
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
    monkeypatch.setattr(runtime, "_in_container", lambda: True)
    assert runtime.describe()["platform"] == "kubernetes"


def test_compose_reports_compose(monkeypatch):
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
    monkeypatch.setattr(runtime, "_in_container", lambda: True)
    assert runtime.describe()["platform"] == "compose"


def test_every_platform_explains_why_the_urls_are_loopback(monkeypatch):
    """The note is the point: it is what stops 'localhost' reading as 'laptop'."""
    cases = [
        ({"KUBERNETES_SERVICE_HOST": "10.0.0.1"}, False),
        ({}, True),
        ({}, False),
    ]
    for env, container in cases:
        runtime.describe.cache_clear()
        monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        monkeypatch.setattr(runtime, "_in_container", lambda c=container: c)
        info = runtime.describe()
        assert info["loopback_note"], f"{info['platform']} has no explanation"


def test_the_kubernetes_note_says_only_web_is_exposed(monkeypatch):
    """If this stops being true, the note becomes a false claim about exposure."""
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
    note = runtime.describe()["loopback_note"]
    assert "web" in note and "Service" in note
    assert "mcp-a" in note
