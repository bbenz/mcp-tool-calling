"""Where this process is actually running.

The demo addresses its own services over loopback in every environment. On a
laptop that is obvious. In Kubernetes it is still true -- the five containers
share one pod, and therefore one network namespace -- but it does not *look*
true: a room watching ``resource_metadata="http://localhost:8801/..."`` on a
projector has no way to tell the cluster from the laptop, and reasonably
concludes the cloud deployment is not really being exercised.

The honest fix is to say where the process is, not to rewrite the URL. Only the
``web`` container is exposed by the Service; ``mcp-a`` binds ``127.0.0.1`` on
purpose, so there is no external address for it. Advertising one would publish
a discovery document pointing at a port nothing answers -- a bad lesson in a
talk about doing OAuth discovery correctly.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict

Platform = Literal["kubernetes", "compose", "local"]


class RuntimeInfo(TypedDict):
    platform: Platform
    label: str
    detail: str
    full: str
    loopback_note: str


_LOOPBACK_NOTE = {
    "kubernetes": (
        "Addresses below are loopback inside this pod. All five containers share one "
        "network namespace, so they reach each other on 127.0.0.1 exactly as they do on "
        "a laptop. Only the web container is published by the Service; mcp-a, mcp-b, "
        "devidp and upstream bind loopback and are unreachable from the rest of the "
        "cluster, which is why no external URL is advertised for them."
    ),
    "compose": (
        "Addresses below are Compose service names on the demo's private network. "
        "Only the web container publishes a port to the host."
    ),
    "local": "Addresses below are loopback on this machine. Nothing is published.",
}


def _in_kubernetes() -> bool:
    # Set by the kubelet in every pod, and independent of the service account
    # token -- this deployment sets automountServiceAccountToken: false, so the
    # token path is deliberately absent and cannot be used as the signal.
    return bool(os.environ.get("KUBERNETES_SERVICE_HOST"))


def _in_container() -> bool:
    if Path("/.dockerenv").exists():
        return True
    try:
        return "docker" in Path("/proc/1/cgroup").read_text(encoding="utf-8")
    except OSError:
        return False


@lru_cache(maxsize=1)
def describe() -> RuntimeInfo:
    """Identify the platform, with whatever detail it is willing to give us."""
    if _in_kubernetes():
        # Supplied by the downward API in deployment.yaml. Absent if someone
        # applies the manifests by hand without them, so neither is required.
        pod = os.environ.get("POD_NAME", "")
        node = os.environ.get("NODE_NAME", "")
        # The badge sits in the header next to the service dots, so it shows the
        # pod only -- node names run to 30-odd characters and would push the
        # zoom controls off a narrow projector. The full pair is the tooltip.
        full = " · ".join(b for b in (f"pod {pod}" if pod else "", f"node {node}" if node else "") if b)
        return {
            "platform": "kubernetes",
            "label": "Kubernetes",
            "detail": f"pod {pod}" if pod else "single pod, five containers",
            "full": full or "single pod, five containers",
            "loopback_note": _LOOPBACK_NOTE["kubernetes"],
        }
    if _in_container():
        host = os.environ.get("HOSTNAME", "container")
        return {
            "platform": "compose",
            "label": "Docker Compose",
            "detail": host,
            "full": host,
            "loopback_note": _LOOPBACK_NOTE["compose"],
        }
    return {
        "platform": "local",
        "label": "Local",
        "detail": "processes on this machine",
        "full": "processes on this machine",
        "loopback_note": _LOOPBACK_NOTE["local"],
    }
