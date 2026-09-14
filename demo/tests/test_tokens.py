"""Token validation is the boundary that makes everything else meaningful.

These tests mint tokens with the dev IdP's real signing key and then attack
them: wrong audience, wrong issuer, expired, unsigned, HMAC-signed, app-only,
ID-token-shaped. Each must be rejected with a stable reason code.
"""

from __future__ import annotations

import time

import jwt
import pytest

from refund_demo.config import get_settings
from refund_demo.devidp.keys import ALGORITHM, load_or_create
from refund_demo.tokens import TokenValidationError, TokenValidator

SETTINGS = get_settings()


def mint(**overrides) -> str:
    key = load_or_create()
    now = int(time.time())
    claims = {
        "iss": SETTINGS.issuer,
        "aud": SETTINGS.mcp_a_audience,
        "sub": "sub-sam-0002",
        "oid": "sub-sam-0002",
        "tid": "devidp-tenant",
        "preferred_username": "sam.agent@contoso-demo.example",
        "scp": "Refunds.Read Refunds.Write",
        "azp": "copilot-demo-client",
        "idtyp": "user",
        "iat": now,
        "nbf": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key.private_pem, algorithm=ALGORITHM,
                      headers={"kid": key.kid, "typ": "at+jwt"})


@pytest.fixture(scope="module")
def validator_a():
    return TokenValidator.for_resource(SETTINGS.mcp_a_audience, SETTINGS)


@pytest.fixture(scope="module")
def validator_b():
    return TokenValidator.for_resource(SETTINGS.mcp_b_audience, SETTINGS)


def reason(validator, token) -> str:
    with pytest.raises(TokenValidationError) as exc:
        validator.validate(token)
    return exc.value.reason_code


def test_valid_token_produces_a_principal(services, validator_a):
    principal = validator_a.validate(mint())
    assert principal.subject == "sub-sam-0002"
    assert principal.audience == SETTINGS.mcp_a_audience
    assert principal.has_scope("Refunds.Write")
    assert principal.client_id == "copilot-demo-client"


def test_bearer_prefix_is_accepted(services, validator_a):
    assert validator_a.validate(f"Bearer {mint()}").subject == "sub-sam-0002"


def test_token_for_resource_b_is_rejected_at_resource_a(services, validator_a):
    """The single most important assertion in the talk."""
    assert reason(validator_a, mint(aud=SETTINGS.mcp_b_audience)) == "AUTH_WRONG_AUDIENCE"


def test_token_for_resource_a_is_rejected_at_resource_b(services, validator_b):
    assert reason(validator_b, mint(aud=SETTINGS.mcp_a_audience)) == "AUTH_WRONG_AUDIENCE"


def test_upstream_audience_is_rejected_at_the_mcp_server(services, validator_a):
    assert reason(validator_a, mint(aud=SETTINGS.upstream_api_audience)) == "AUTH_WRONG_AUDIENCE"


def test_expired_token_is_rejected(services, validator_a):
    now = int(time.time())
    assert reason(validator_a, mint(iat=now - 7200, nbf=now - 7200, exp=now - 3600)) == "AUTH_TOKEN_EXPIRED"


def test_not_yet_valid_token_is_rejected(services, validator_a):
    now = int(time.time())
    assert reason(validator_a, mint(nbf=now + 3600, exp=now + 7200)) == "AUTH_TOKEN_NOT_YET_VALID"


def test_wrong_issuer_is_rejected(services, validator_a):
    assert reason(validator_a, mint(iss="https://evil.example")) == "AUTH_WRONG_ISSUER"


def test_unsigned_token_is_rejected(validator_a):
    token = jwt.encode({"iss": SETTINGS.issuer, "aud": SETTINGS.mcp_a_audience,
                        "sub": "sub-sam-0002", "scp": "Refunds.Write",
                        "iat": int(time.time()), "exp": int(time.time()) + 3600},
                       key="", algorithm="none")
    assert reason(validator_a, token) == "AUTH_DISALLOWED_ALGORITHM"


def test_hmac_signed_token_is_rejected(validator_a):
    """Algorithm confusion: an HS256 token signed with a guessed key."""
    token = jwt.encode({"iss": SETTINGS.issuer, "aud": SETTINGS.mcp_a_audience,
                        "sub": "sub-sam-0002", "scp": "Refunds.Write",
                        "iat": int(time.time()), "exp": int(time.time()) + 3600},
                       key="public-key-material", algorithm="HS256")
    assert reason(validator_a, token) == "AUTH_DISALLOWED_ALGORITHM"


def test_token_signed_by_an_untrusted_key_is_rejected(services, validator_a):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    rogue = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = rogue.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    now = int(time.time())
    token = jwt.encode(
        {"iss": SETTINGS.issuer, "aud": SETTINGS.mcp_a_audience, "sub": "sub-sam-0002",
         "scp": "Refunds.Write", "iat": now, "exp": now + 3600},
        pem, algorithm=ALGORITHM,
        headers={"kid": load_or_create().kid, "typ": "at+jwt"},
    )
    assert reason(validator_a, token) == "AUTH_BAD_SIGNATURE"


def test_app_only_token_is_rejected(services, validator_a):
    assert reason(validator_a, mint(idtyp="app", scp=None, roles=["Refunds.All"])) == "AUTH_APP_ONLY_TOKEN"


def test_id_token_shaped_token_is_rejected(services, validator_a):
    assert reason(validator_a, mint(scp=None)) == "AUTH_NO_DELEGATED_SCOPES"


def test_empty_token_is_rejected(validator_a):
    assert reason(validator_a, "") == "AUTH_NO_TOKEN"


def test_garbage_token_is_rejected(validator_a):
    assert reason(validator_a, "not.a.jwt") == "AUTH_MALFORMED_TOKEN"


def test_wrong_tenant_is_rejected(services):
    validator = TokenValidator(
        issuer=SETTINGS.issuer, jwks_uri=SETTINGS.jwks_uri,
        audience=SETTINGS.mcp_a_audience, tenant_id="expected-tenant-guid",
    )
    assert reason(validator, mint(tid="some-other-tenant")) == "AUTH_WRONG_TENANT"


def test_a_resource_may_accept_several_identifiers_for_itself(services):
    """App ID URI and server URL are both this resource; other resources are not."""
    validator = TokenValidator.for_resource(
        [SETTINGS.mcp_a_audience, SETTINGS.mcp_a_public_url], SETTINGS
    )
    assert validator.validate(mint()).audience == SETTINGS.mcp_a_audience
    assert validator.validate(mint(aud=SETTINGS.mcp_a_public_url)).audience == SETTINGS.mcp_a_public_url
    assert reason(validator, mint(aud=SETTINGS.mcp_b_audience)) == "AUTH_WRONG_AUDIENCE"


def test_scopes_are_parsed_from_either_claim_shape(services, validator_a):
    assert validator_a.validate(mint(scp="A B")).scopes == ("A", "B")
    assert validator_a.validate(mint(scp=None, scope="A B")).scopes == ("A", "B")
