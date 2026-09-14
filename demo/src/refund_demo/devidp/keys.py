"""RSA signing key management for the local development authorization server.

The key is generated once and persisted under ``.local/`` so that tokens stay
valid across restarts during a rehearsal. ``.local/`` is git-ignored.

This key signs tokens for the LOCAL demo issuer only. It is never used in the
cloud path, where Microsoft Entra ID issues and signs tokens.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ..config import get_settings

KEY_ID = "devidp-rsa-1"
ALGORITHM = "RS256"


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


@dataclass(frozen=True)
class SigningKey:
    private_pem: str
    public_pem: str
    kid: str = KEY_ID

    def jwk(self) -> dict[str, Any]:
        public = serialization.load_pem_public_key(self.public_pem.encode("utf-8"))
        numbers = public.public_numbers()  # type: ignore[attr-defined]
        return {
            "kty": "RSA",
            "use": "sig",
            "alg": ALGORITHM,
            "kid": self.kid,
            "n": _b64url_uint(numbers.n),
            "e": _b64url_uint(numbers.e),
        }

    def jwks(self) -> dict[str, Any]:
        return {"keys": [self.jwk()]}


def load_or_create() -> SigningKey:
    settings = get_settings()
    path = settings.devidp_key_path
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return SigningKey(private_pem=data["private_pem"], public_pem=data["public_pem"], kid=data.get("kid", KEY_ID))

    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = (
        private.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"private_pem": private_pem, "public_pem": public_pem, "kid": KEY_ID}, handle)
    os.chmod(path, 0o600)
    return SigningKey(private_pem=private_pem, public_pem=public_pem)
