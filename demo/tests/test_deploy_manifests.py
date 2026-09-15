"""The three deployment paths have to describe the same demo.

There are now three ways to run this: the operator scripts on a laptop, five
containers under Compose, and one pod on AKS. Each one restates the topology in
a different language, which is exactly the kind of triplication that rots. A
mismatch would not fail loudly -- it would surface on stage as a service that
answers on a laptop and 502s in the cluster.

So these tests treat the topology as the fact and the three files as claims
about it, and fail when the claims disagree.
"""

from __future__ import annotations

import os
import re

import pytest

yaml = pytest.importorskip("yaml")

DEMO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K8S = os.path.join(DEMO, "k8s")
COMPOSE_PATH = os.path.join(DEMO, "docker", "docker-compose.yml")
DOCKERFILE_PATH = os.path.join(DEMO, "docker", "Dockerfile")

NAMESPACE = "refund-demo"

# The topology, stated once. Everything below is checked against this.
TOPOLOGY = {
    "devidp": ("refund_demo.devidp.server", 8800),
    "upstream": ("refund_demo.upstream_api.app", 8803),
    "mcp-a": ("refund_demo.mcp_server.app", 8801),
    "mcp-b": ("refund_demo.resource_b.app", 8802),
    "web": ("refund_demo.web.app", 8080),
}


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def compose():
    return _load(COMPOSE_PATH)


@pytest.fixture(scope="module")
def deployment():
    return _load(os.path.join(K8S, "deployment.yaml"))


@pytest.fixture(scope="module")
def containers(deployment):
    return {c["name"]: c for c in deployment["spec"]["template"]["spec"]["containers"]}


# --- the topology is the same in all three places -------------------------

def test_compose_defines_exactly_the_five_services(compose):
    assert set(compose["services"]) == set(TOPOLOGY)


def test_kubernetes_defines_exactly_the_five_containers(containers):
    assert set(containers) == set(TOPOLOGY)


@pytest.mark.parametrize("name", sorted(TOPOLOGY))
def test_compose_runs_the_expected_module(compose, name):
    module, _ = TOPOLOGY[name]
    assert compose["services"][name]["command"] == ["python", "-m", module]


@pytest.mark.parametrize("name", sorted(TOPOLOGY))
def test_kubernetes_runs_the_expected_module(containers, name):
    module, _ = TOPOLOGY[name]
    assert containers[name]["command"] == ["python", "-m", module]


@pytest.mark.parametrize("name", sorted(TOPOLOGY))
def test_kubernetes_container_exposes_the_expected_port(containers, name):
    _, port = TOPOLOGY[name]
    assert [p["containerPort"] for p in containers[name]["ports"]] == [port]


@pytest.mark.parametrize("name", sorted(TOPOLOGY))
def test_probes_target_that_same_port(containers, name):
    """A probe pointed at the wrong port reads as a crashloop, not a typo."""
    _, port = TOPOLOGY[name]
    for probe in ("readinessProbe", "livenessProbe"):
        http = containers[name][probe]["httpGet"]
        assert http["port"] == port
        assert http["path"] == "/health"


# --- SQLite means one writer, and the manifests have to say so ------------

def test_deployment_is_a_single_replica(deployment):
    assert deployment["spec"]["replicas"] == 1


def test_deployment_recreates_rather_than_rolls(deployment):
    """A rolling update would briefly point two pods at one ledger volume."""
    assert deployment["spec"]["strategy"]["type"] == "Recreate"


# --- the state directory has to be shared, and it has to be the right one -

def test_every_container_mounts_the_shared_state_directory(containers):
    for name, container in containers.items():
        paths = {m["mountPath"]: m["name"] for m in container["volumeMounts"]}
        assert paths.get("/app/.local") == "state", name


def test_compose_shares_one_state_volume(compose):
    for name, service in compose["services"].items():
        mounts = service.get("volumes") or []
        assert any(str(m).endswith(":/app/.local") for m in mounts), name


def test_state_volume_is_declared(deployment, compose):
    volumes = {v["name"] for v in deployment["spec"]["template"]["spec"]["volumes"]}
    assert {"state", "tmp"} <= volumes
    assert "demo-state" in (compose.get("volumes") or {})


# --- devidp binds loopback by default; containers must override it --------

def test_containers_override_the_bind_host(compose):
    for name, service in compose["services"].items():
        assert service["environment"]["BIND_HOST"] == "0.0.0.0", name


def test_kubernetes_overrides_the_bind_host():
    data = _load(os.path.join(K8S, "configmap.yaml"))["data"]
    assert data["BIND_HOST"] == "0.0.0.0"


def test_dockerfile_defaults_the_bind_host():
    text = open(DOCKERFILE_PATH, encoding="utf-8").read()
    assert "BIND_HOST=0.0.0.0" in text


# --- security posture -----------------------------------------------------

def test_reset_stays_off_in_both_container_paths(compose):
    assert compose["services"]["web"]["environment"]["WEB_ALLOW_RESET"] == "0"
    data = _load(os.path.join(K8S, "configmap.yaml"))["data"]
    assert data["WEB_ALLOW_RESET"] == "0"


def test_containers_are_hardened(containers):
    for name, container in containers.items():
        sc = container["securityContext"]
        assert sc["allowPrivilegeEscalation"] is False, name
        assert sc["readOnlyRootFilesystem"] is True, name
        assert sc["capabilities"]["drop"] == ["ALL"], name


def test_pod_runs_as_a_non_root_user(deployment):
    sc = deployment["spec"]["template"]["spec"]["securityContext"]
    assert sc["runAsNonRoot"] is True
    assert sc["runAsUser"] == 10001
    # Without fsGroup the emptyDir lands root-owned and the app cannot write.
    assert sc["fsGroup"] == 10001


def test_every_container_is_bounded(containers):
    for name, container in containers.items():
        resources = container["resources"]
        assert resources["requests"]["cpu"] and resources["requests"]["memory"], name
        assert resources["limits"]["cpu"] and resources["limits"]["memory"], name


def test_only_the_web_container_is_exposed():
    """devidp mints its own tokens. It must never get a public address."""
    service = _load(os.path.join(K8S, "service.yaml"))
    ports = service["spec"]["ports"]
    assert len(ports) == 1
    assert ports[0]["targetPort"] == TOPOLOGY["web"][1]


def test_service_selects_the_deployment(deployment):
    service = _load(os.path.join(K8S, "service.yaml"))
    labels = deployment["spec"]["template"]["metadata"]["labels"]
    for key, value in service["spec"]["selector"].items():
        assert labels.get(key) == value


def test_image_is_left_as_a_placeholder_for_the_deploy_script(containers):
    """A real registry baked in here would be someone else's registry."""
    assert {c["image"] for c in containers.values()} == {"IMAGE_PLACEHOLDER"}


def test_everything_lands_in_the_demo_namespace():
    for filename in ("configmap.yaml", "deployment.yaml", "service.yaml"):
        doc = _load(os.path.join(K8S, filename))
        assert doc["metadata"]["namespace"] == NAMESPACE, filename
    ns = _load(os.path.join(K8S, "namespace.yaml"))
    assert ns["metadata"]["name"] == NAMESPACE


def test_dockerignore_keeps_local_state_out_of_the_image():
    """The signing key lives in .local. It must not end up in a layer."""
    text = open(os.path.join(DEMO, ".dockerignore"), encoding="utf-8").read()
    for pattern in (".local/", ".venv/", "*.pem", "*.key"):
        assert pattern in text, pattern


def test_dockerfile_runs_as_a_non_root_uid():
    text = open(DOCKERFILE_PATH, encoding="utf-8").read()
    assert re.search(r"^USER demo$", text, re.MULTILINE)
    assert "--uid 10001" in text


def test_dockerfile_exposes_every_service_port():
    text = open(DOCKERFILE_PATH, encoding="utf-8").read()
    exposed = set()
    for line in text.splitlines():
        if line.startswith("EXPOSE"):
            exposed.update(int(p) for p in line.split()[1:])
    assert exposed == {port for _, port in TOPOLOGY.values()}


# --- regressions found by actually running the containers -----------------

# Windows-only distributions that have no Linux wheel. Pinning one of these
# without a marker builds fine on the laptop and fails the image build with
# "No matching distribution found".
WINDOWS_ONLY = ("pywin32", "pywinpty", "pyreadline3", "win32-setctime", "winkerberos")


def test_requirements_mark_windows_only_pins():
    """requirements.txt is frozen on Windows; Linux has to be able to read it."""
    path = os.path.join(DEMO, "requirements.txt")
    offenders = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = re.split(r"[=<>!~;\[]", line, 1)[0].strip().lower()
        if name in WINDOWS_ONLY and "sys_platform" not in line:
            offenders.append(line)
    assert not offenders, f"needs a ; sys_platform == \"win32\" marker: {offenders}"


def test_compose_allows_the_service_names_as_mcp_hosts(compose):
    """The MCP transport answers 421 unless the Host header is allowlisted.

    Inside Compose the Host header is the service name, not localhost.
    """
    allowed = compose["services"]["mcp-a"]["environment"]["MCP_ALLOWED_HOSTS"]
    entries = {e.strip() for e in allowed.split(",")}
    assert "mcp-a:*" in entries
    assert "mcp-b:*" in entries


def test_dns_rebinding_protection_stays_on_and_always_allows_loopback():
    from refund_demo.config import Settings

    settings = Settings(mcp_allowed_hosts="")
    plain = settings.transport_security()
    assert plain.enable_dns_rebinding_protection is True
    assert plain.allowed_hosts == ["127.0.0.1:*", "localhost:*", "[::1]:*"]


def test_extra_allowed_hosts_extend_rather_than_replace_loopback():
    from refund_demo.config import Settings

    extended = Settings(mcp_allowed_hosts="mcp-a:*, mcp-b:*, localhost:*").transport_security()
    assert extended.enable_dns_rebinding_protection is True
    # loopback survives, the extras are added, and nothing is duplicated
    assert extended.allowed_hosts == ["127.0.0.1:*", "localhost:*", "[::1]:*", "mcp-a:*", "mcp-b:*"]
    assert "http://mcp-a:*" in extended.allowed_origins


def test_both_mcp_servers_apply_the_transport_security_settings():
    """A bare streamable_http_app() silently allows only loopback Host headers."""
    for module in ("mcp_server", "resource_b"):
        path = os.path.join(DEMO, "src", "refund_demo", module, "app.py")
        text = open(path, encoding="utf-8").read()
        assert "streamable_http_app(transport_security=" in text, module

