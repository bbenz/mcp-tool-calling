"""Configuration for every service in the refund demo.

Two authorization modes are supported and they share one code path:

* ``devidp``  - a real, standards-based OAuth authorization server that runs on
  localhost (see :mod:`refund_demo.devidp`). It signs RS256 tokens with a real
  key, publishes real JWKS and RFC 8414 metadata, and honours PKCE S256 and RFC
  8707 ``resource`` indicators. It exists so the complete protocol trace can be
  exercised without a tenant. It is NOT a bypass: tokens are validated by the
  same validator used for Entra.
* ``entra``   - Microsoft Entra ID.

Switching modes changes only issuer metadata. It never relaxes validation.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

AuthMode = Literal["devidp", "entra"]

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _local_path(*parts: str) -> str:
    return os.path.join(REPO_ROOT, ".local", *parts)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(REPO_ROOT, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    auth_mode: AuthMode = "devidp"

    entra_tenant_id: str = ""
    entra_authority: str = ""

    devidp_port: int = 8800
    devidp_issuer: str = "http://localhost:8800"

    mcp_a_public_url: str = "http://localhost:8801"
    mcp_a_audience: str = "api://refund-mcp-a"
    mcp_a_port: int = 8801
    mcp_a_client_id: str = ""
    mcp_a_client_secret: str = ""

    mcp_b_public_url: str = "http://localhost:8802"
    mcp_b_audience: str = "api://refund-mcp-b"
    mcp_b_port: int = 8802

    upstream_api_url: str = "http://localhost:8803"
    upstream_api_audience: str = "api://refund-upstream"
    upstream_api_scope: str = "api://refund-upstream/Ledger.Refund"
    upstream_api_port: int = 8803

    web_port: int = 8080
    # Empty means "use each service's own default". devidp binds loopback only,
    # everything else binds all interfaces. Containers set BIND_HOST=0.0.0.0,
    # because a loopback bind is unreachable from outside the container.
    bind_host: str = ""
    # Reset is an operator action. It is off by default over HTTP, and stays off
    # in the cloud deployment: a "put the ledger back" endpoint reachable from
    # the internet is precisely the escalation this talk argues against.
    web_allow_reset: bool = False
    # Optional shared secret for the web UI. Empty means no gate, which is fine
    # on a laptop and is NOT fine on a public IP.
    web_access_key: str = ""

    # Extra Host header values the MCP transport will accept, comma separated,
    # e.g. "mcp-a:8801,mcp-a:*". The SDK turns on DNS rebinding protection and
    # allows only loopback; behind a service name (Compose, an ingress) the Host
    # header is something else and the transport answers 421 Misdirected
    # Request. This extends the allowlist rather than disabling the check.
    mcp_allowed_hosts: str = ""

    scope_read: str = "Refunds.Read"
    scope_write: str = "Refunds.Write"

    allowed_client_ids: str = "copilot-demo-client"
    demo_client_id: str = "copilot-demo-client"
    unapproved_client_id: str = "rogue-demo-client"

    foundry_endpoint: str = ""
    foundry_deployment: str = ""
    foundry_api_version: str = "2024-10-21"
    foundry_api_key: str = ""

    applicationinsights_connection_string: str = ""

    refund_per_call_limit_minor: int = 25_000
    refund_currency: str = "CAD"
    policy_version: str = "refund-policy/2026-10-06.1"

    audit_log_path: str = Field(default_factory=lambda: _local_path("audit.jsonl"))
    ledger_path: str = Field(default_factory=lambda: _local_path("ledger.sqlite3"))
    devidp_key_path: str = Field(default_factory=lambda: _local_path("devidp-key.json"))

    clock_skew_seconds: int = 60

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_client_id_list(self) -> list[str]:
        return [c.strip() for c in self.allowed_client_ids.split(",") if c.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def issuer(self) -> str:
        if self.auth_mode == "entra":
            if self.entra_authority:
                return self.entra_authority.rstrip("/")
            return f"https://login.microsoftonline.com/{self.entra_tenant_id}/v2.0"
        return self.devidp_issuer.rstrip("/")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def authorization_server_metadata_url(self) -> str:
        """RFC 8414 well-known location for the issuer."""
        if self.auth_mode == "entra":
            return f"{self.issuer}/.well-known/openid-configuration"
        return f"{self.issuer}/.well-known/oauth-authorization-server"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def jwks_uri(self) -> str:
        if self.auth_mode == "entra":
            return f"https://login.microsoftonline.com/{self.entra_tenant_id}/discovery/v2.0/keys"
        return f"{self.issuer}/jwks"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def expected_tenant_id(self) -> str | None:
        return self.entra_tenant_id or None

    def ensure_local_dir(self) -> None:
        os.makedirs(_local_path(), exist_ok=True)

    def bind(self, default: str) -> str:
        """Interface to bind, honouring a BIND_HOST override."""
        return self.bind_host or default

    def transport_security(self) -> "TransportSecuritySettings":
        """DNS rebinding protection for the MCP transport.

        Always enabled. The loopback entries keep a laptop run working; anything
        in MCP_ALLOWED_HOSTS is added on top for container and cluster hostnames.
        """
        from mcp.server.transport_security import TransportSecuritySettings

        hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
        origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
        for extra in (h.strip() for h in self.mcp_allowed_hosts.split(",")):
            if not extra or extra in hosts:
                continue
            hosts.append(extra)
            origins.append(f"http://{extra}")
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=hosts,
            allowed_origins=origins,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_local_dir()
    return settings


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
