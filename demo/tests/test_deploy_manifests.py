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
    """A probe pointed at the wrong port reads as a crashloop, not a typo.

    Only `web` binds the pod IP, so only `web` can answer a kubelet httpGet.
    The other four bind loopback and are probed with curl from inside the pod.
    """
    _, port = TOPOLOGY[name]
    for probe in ("readinessProbe", "livenessProbe"):
        spec = containers[name][probe]
        if name == "web":
            assert spec["httpGet"]["port"] == port
            assert spec["httpGet"]["path"] == "/health"
        else:
            command = spec["exec"]["command"]
            assert command[0] == "curl"
            assert f"http://localhost:{port}/health" in command


def _env_of(container) -> dict:
    return {e["name"]: e.get("value") for e in container.get("env", [])}


@pytest.mark.parametrize("name", sorted(set(TOPOLOGY) - {"web"}))
def test_internal_containers_bind_loopback_only(containers, name):
    """Five containers share one network namespace; only web faces the Service.

    A blanket BIND_HOST=0.0.0.0 put the dev issuer -- which mints a token for
    any audience, to anyone who asks -- on the pod IP, reachable from every
    other pod in the cluster.
    """
    assert _env_of(containers[name])["BIND_HOST"] == "127.0.0.1"


def test_web_container_binds_all_interfaces(containers):
    assert _env_of(containers["web"])["BIND_HOST"] == "0.0.0.0"


def test_the_public_deployment_requires_an_access_key(containers):
    """An absent Secret must fail closed, not silently remove authentication."""
    assert _env_of(containers["web"])["WEB_REQUIRE_ACCESS_KEY"] == "1"


def test_bind_host_is_not_set_for_every_container_at_once():
    """The ConfigMap is consumed by all five containers via envFrom."""
    with open(os.path.join(K8S, "configmap.yaml"), encoding="utf-8") as fh:
        data = yaml.safe_load(fh)["data"]
    assert "BIND_HOST" not in data


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
    """Per container, not for all five at once -- see the loopback tests above."""
    containers = {
        c["name"]: c
        for c in _load(os.path.join(K8S, "deployment.yaml"))["spec"]["template"]["spec"]["containers"]
    }
    assert _env_of(containers["web"])["BIND_HOST"] == "0.0.0.0"


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


# --- regressions found by actually deploying to a cluster ------------------
#
# Both of these killed a real deployment, and neither is catchable by a syntax
# check -- the scripts parse perfectly fine with the bugs in them.

AKS_UP_PS1 = os.path.join(DEMO, "scripts", "aks-up.ps1")
AKS_UP_SH = os.path.join(DEMO, "scripts", "aks-up.sh")


def test_deploy_helper_does_not_use_remaining_arguments():
    """ValueFromRemainingArguments does not stop PowerShell parameter binding.

    The helper was declared that way and the script died on its first az call:
    `-o none` bound against -OutVariable/-OutBuffer and failed as ambiguous
    before the function body ever ran. An array parameter is the fix.
    """
    text = open(AKS_UP_PS1, encoding="utf-8").read()
    # The bug is named in a comment there on purpose, so match the attribute.
    assert not re.search(r"\[Parameter\([^)]*ValueFromRemainingArguments", text)
    assert re.search(r"function\s+Invoke-Az\b", text)
    assert re.search(r"\[string\[\]\]\s*\$AzArgs", text)


def test_acr_build_does_not_stream_logs():
    """az acr build's log streamer crashes on a cp1252 Windows console.

    It dies with UnicodeEncodeError *after* pushing the image, so the build has
    actually succeeded. PYTHONIOENCODING does not help; --no-logs does, and it
    still waits for the run and still fails on a real build failure.
    """
    for path in (AKS_UP_PS1, AKS_UP_SH):
        text = open(path, encoding="utf-8").read()
        assert "acr build" in text, path
        assert "--no-logs" in text, path
        assert "acr task logs" in text, path


# --- the optional Foundry wiring for the cloud demo ------------------------
# The content filter is a defence layer that lives neither in this app nor in
# MCP. Wiring it is two env vars; the tests below make sure those two vars
# cannot drift out of the manifests without someone noticing.


@pytest.fixture(scope="module")
def configmap():
    return _load(os.path.join(K8S, "configmap.yaml"))


def test_foundry_is_declared_but_empty_by_default(configmap):
    """Off by default: the demo must run with no model and no network."""
    data = configmap["data"]
    assert data["FOUNDRY_ENDPOINT"] == ""
    assert data["FOUNDRY_DEPLOYMENT"] == ""
    assert data["FOUNDRY_API_VERSION"]


def test_no_foundry_endpoint_or_credential_is_committed(configmap):
    """Real values belong in the Secret, not a ConfigMap every container reads.

    The key is the obvious one. The endpoint matters too: it names a resource
    in someone's subscription, and there is no reason for the other four
    containers to learn it.
    """
    assert "FOUNDRY_API_KEY" not in configmap["data"]
    assert configmap["data"]["FOUNDRY_ENDPOINT"] == ""
    assert configmap["data"]["FOUNDRY_DEPLOYMENT"] == ""


def test_only_the_mcp_server_receives_the_foundry_config(containers):
    """assess_refund is the only caller, so nothing else mounts the Secret."""
    holders = [
        name
        for name, c in containers.items()
        if any(
            src.get("secretRef", {}).get("name") == "refund-demo-foundry"
            for src in c.get("envFrom", [])
        )
    ]
    assert holders == ["mcp-a"]


def test_the_foundry_secret_is_optional(containers):
    """No Secret must mean a labelled offline assessment, not a crash loop."""
    ref = next(
        src["secretRef"]
        for src in containers["mcp-a"]["envFrom"]
        if "secretRef" in src
    )
    assert ref["optional"] is True
    assert ref["name"] == "refund-demo-foundry"


def test_the_secret_wins_over_the_configmap_defaults(containers):
    """Order matters in envFrom: the empty ConfigMap defaults must not win.

    If the Secret were listed first, a deployment that supplied a real endpoint
    would silently fall back to the offline path with nothing to show for it.
    """
    sources = containers["mcp-a"]["envFrom"]
    names = [next(iter(src)) for src in sources]
    assert names.index("configMapRef") < names.index("secretRef")


def test_the_mcp_server_still_binds_loopback_after_gaining_its_own_env(containers):
    """mcp-a stopped using the shared YAML anchor; it must not have lost the bind."""
    assert _env_of(containers["mcp-a"])["BIND_HOST"] == "127.0.0.1"


def test_web_learns_its_pod_and_node_from_the_downward_api(containers):
    """The runtime badge needs these, and fieldRef is the only way to get them.

    automountServiceAccountToken is false, so nothing here can ask the API
    server; if these are dropped the badge silently degrades to a bare
    "Kubernetes" with no pod or node.
    """
    env = {e["name"]: e for e in containers["web"].get("env", [])}
    paths = {
        "POD_NAME": "metadata.name",
        "NODE_NAME": "spec.nodeName",
    }
    for name, field_path in paths.items():
        assert name in env, f"{name} is not supplied to the web container"
        assert env[name]["valueFrom"]["fieldRef"]["fieldPath"] == field_path


@pytest.mark.parametrize("script", ["aks-up.ps1", "aks-up.sh"])
def test_both_deploy_scripts_expose_the_same_foundry_flags(script):
    path = os.path.join(DEMO, "scripts", script)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    for flag in (
        "FoundryEndpoint",
        "FoundryDeployment",
        "FoundryApiVersion",
        "FoundryApiKey",
    ) if script.endswith(
        ".ps1"
    ) else (
        "--foundry-endpoint",
        "--foundry-deployment",
        "--foundry-api-version",
        "--foundry-api-key",
    ):
        assert flag in text, f"{script} is missing {flag}"
    assert "refund-demo-foundry" in text
    # The values must reach the cluster as a Secret, never by patching the
    # ConfigMap -- which is the shortcut that put the endpoint in plaintext.
    assert "set env configmap" not in text, f"{script} still writes Foundry config to the ConfigMap"
    for key in (
        "FOUNDRY_ENDPOINT",
        "FOUNDRY_DEPLOYMENT",
        "FOUNDRY_API_VERSION",
        "FOUNDRY_API_KEY",
    ):
        assert f"--from-literal={key}=" in text, f"{script} does not put {key} in the Secret"
