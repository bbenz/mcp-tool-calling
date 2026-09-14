"""Access-token validation.

This is the security core of the demo. Every protected resource (MCP Resource
A, MCP Resource B, and the upstream refund API) validates with this same code,
differing only in the audience it accepts.

Decoding a JWT is not validating it. This module:

* fetches signing keys from the issuer's published JWKS and caches them by kid
* restricts the signature algorithm to an allowlist (no ``none``, no HMAC)
* checks ``iss`` by exact string comparison
* checks ``aud`` against the resource's own identifier -- this is the audience
  binding that makes a token for Resource A useless at Resource B
* checks ``exp`` / ``nbf`` / ``iat`` with a bounded clock skew
* checks the tenant when one is configured
* rejects ID tokens and app-only tokens where delegated user access is required

Identity used for authorization is taken only from claims that survived all of
the above. Tool arguments and request headers are never trusted for identity.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

import httpx
import jwt
from jwt import PyJWKClient

from .config import Settings, get_settings

ALLOWED_ALGORITHMS = ("RS256", "RS384", "RS512")
ALLOWED_TOKEN_TYPES = {"jwt", "at+jwt", "application/at+jwt"}


class TokenValidationError(Exception):
    """A token was rejected. ``reason_code`` is stable and safe to log/show."""

    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code
        self.message = message


@dataclass(frozen=True)
class Principal:
    """Trusted identity, derived exclusively from validated claims."""

    subject: str
    object_id: str
    upn: str
    tenant_id: str
    client_id: str
    scopes: tuple[str, ...]
    audience: str
    issuer: str
    expires_at: int
    token_id: str = ""
    raw_claims: dict[str, Any] = field(default_factory=dict, repr=False)

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def safe_claims(self) -> dict[str, Any]:
        """The subset that is safe to display on a conference projector."""
        return {
            "iss": self.issuer,
            "aud": self.audience,
            "tid": self.tenant_id,
            "sub": self.subject,
            "oid": self.object_id,
            "preferred_username": self.upn,
            "client_id": self.client_id,
            "scp": " ".join(self.scopes),
            "exp": self.expires_at,
            "exp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.expires_at)),
        }


class _JwksCache:
    """Per-JWKS-URI key client cache. PyJWKClient handles kid lookup + caching."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._clients: dict[str, PyJWKClient] = {}

    def client(self, jwks_uri: str) -> PyJWKClient:
        with self._lock:
            client = self._clients.get(jwks_uri)
            if client is None:
                client = PyJWKClient(jwks_uri, cache_keys=True, lifespan=600)
                self._clients[jwks_uri] = client
            return client

    def clear(self) -> None:
        with self._lock:
            self._clients.clear()


_JWKS = _JwksCache()


def clear_key_cache() -> None:
    _JWKS.clear()


def _normalize_scopes(claims: dict[str, Any]) -> tuple[str, ...]:
    raw = claims.get("scp") or claims.get("scope") or ""
    if isinstance(raw, list):
        return tuple(str(s) for s in raw if s)
    return tuple(s for s in str(raw).split() if s)


def _client_id_from(claims: dict[str, Any]) -> str:
    for key in ("azp", "appid", "client_id", "cid"):
        value = claims.get(key)
        if value:
            return str(value)
    return ""


class TokenValidator:
    """Validates bearer tokens for one specific resource (one audience)."""

    def __init__(
        self,
        *,
        issuer: str,
        jwks_uri: str,
        audience: str | list[str],
        tenant_id: str | None = None,
        require_delegated: bool = True,
        leeway_seconds: int = 60,
        allowed_algorithms: Iterable[str] = ALLOWED_ALGORITHMS,
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self.jwks_uri = jwks_uri
        self.audiences = [audience] if isinstance(audience, str) else list(audience)
        self.audience = self.audiences[0]
        self.tenant_id = tenant_id
        self.require_delegated = require_delegated
        self.leeway_seconds = leeway_seconds
        self.allowed_algorithms = list(allowed_algorithms)

    @classmethod
    def for_resource(
        cls,
        audience: str | list[str],
        settings: Settings | None = None,
        *,
        require_delegated: bool = True,
    ) -> "TokenValidator":
        s = settings or get_settings()
        return cls(
            issuer=s.issuer,
            jwks_uri=s.jwks_uri,
            audience=audience,
            tenant_id=s.expected_tenant_id,
            require_delegated=require_delegated,
            leeway_seconds=s.clock_skew_seconds,
        )

    def validate(self, raw_token: str) -> Principal:
        if not raw_token or not raw_token.strip():
            raise TokenValidationError("AUTH_NO_TOKEN", "no bearer token was presented")

        token = raw_token.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()

        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise TokenValidationError("AUTH_MALFORMED_TOKEN", f"token is not a well-formed JWT: {exc}") from exc

        alg = header.get("alg", "")
        if alg not in self.allowed_algorithms:
            raise TokenValidationError(
                "AUTH_DISALLOWED_ALGORITHM",
                f"signature algorithm {alg!r} is not in the allowlist {self.allowed_algorithms}",
            )

        typ = str(header.get("typ", "jwt")).lower()
        if typ not in ALLOWED_TOKEN_TYPES:
            raise TokenValidationError("AUTH_WRONG_TOKEN_TYPE", f"unexpected token type {typ!r}")

        try:
            signing_key = _JWKS.client(self.jwks_uri).get_signing_key_from_jwt(token)
        except httpx.HTTPError as exc:
            raise TokenValidationError("AUTH_JWKS_UNAVAILABLE", f"could not fetch issuer keys: {exc}") from exc
        except jwt.PyJWTError as exc:
            raise TokenValidationError("AUTH_UNKNOWN_SIGNING_KEY", f"no trusted key matches the token: {exc}") from exc
        except Exception as exc:  # PyJWKClient raises its own error types
            raise TokenValidationError("AUTH_UNKNOWN_SIGNING_KEY", f"no trusted key matches the token: {exc}") from exc

        try:
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=self.allowed_algorithms,
                audience=self.audiences,
                issuer=self.issuer,
                leeway=self.leeway_seconds,
                options={
                    "require": ["exp", "iat", "iss", "aud"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenValidationError("AUTH_TOKEN_EXPIRED", "the access token has expired") from exc
        except jwt.ImmatureSignatureError as exc:
            raise TokenValidationError("AUTH_TOKEN_NOT_YET_VALID", "the access token is not yet valid") from exc
        except jwt.InvalidAudienceError as exc:
            raise TokenValidationError(
                "AUTH_WRONG_AUDIENCE",
                f"token audience does not match this resource (expected one of {self.audiences})",
            ) from exc
        except jwt.InvalidIssuerError as exc:
            raise TokenValidationError("AUTH_WRONG_ISSUER", "token issuer is not trusted by this resource") from exc
        except jwt.InvalidSignatureError as exc:
            raise TokenValidationError("AUTH_BAD_SIGNATURE", "token signature failed verification") from exc
        except jwt.MissingRequiredClaimError as exc:
            raise TokenValidationError("AUTH_MISSING_CLAIM", f"token is missing a required claim: {exc}") from exc
        except jwt.PyJWTError as exc:
            raise TokenValidationError("AUTH_INVALID_TOKEN", f"token failed validation: {exc}") from exc

        if self.tenant_id and str(claims.get("tid", "")) != self.tenant_id:
            raise TokenValidationError("AUTH_WRONG_TENANT", "token was issued for a different tenant")

        scopes = _normalize_scopes(claims)

        if self.require_delegated:
            # An Entra app-only token carries `roles` and no `scp`, and marks
            # itself with idtyp=app. A delegated user token carries `scp`.
            if str(claims.get("idtyp", "")).lower() == "app":
                raise TokenValidationError(
                    "AUTH_APP_ONLY_TOKEN",
                    "an application-only token was presented where a delegated user token is required",
                )
            if not scopes:
                raise TokenValidationError(
                    "AUTH_NO_DELEGATED_SCOPES",
                    "token carries no delegated scopes; it is an ID token or an app-only token",
                )
            if not claims.get("sub"):
                raise TokenValidationError("AUTH_NO_SUBJECT", "token carries no subject claim")

        audience_claim = claims.get("aud")
        if isinstance(audience_claim, list):
            matched = next((a for a in self.audiences if a in audience_claim), None)
            audience_value = matched or str(audience_claim[0])
        else:
            audience_value = str(audience_claim)

        return Principal(
            subject=str(claims.get("sub", "")),
            object_id=str(claims.get("oid", claims.get("sub", ""))),
            upn=str(claims.get("preferred_username") or claims.get("upn") or claims.get("email") or ""),
            tenant_id=str(claims.get("tid", "")),
            client_id=_client_id_from(claims),
            scopes=scopes,
            audience=audience_value,
            issuer=str(claims.get("iss", "")),
            expires_at=int(claims.get("exp", 0)),
            token_id=str(claims.get("uti") or claims.get("jti") or ""),
            raw_claims=claims,
        )
