"""Reset is safe to run mid-demo.

The runbook tells the presenter to reset at T-5 and again between segments,
with the services already up. An earlier version also deleted the local signing
key, which looked harmless: the file is regenerated on demand. It was not.
`devidp` kept minting tokens with a freshly generated key while every service
in the system went on serving and caching the *old* JWKS, so every token failed
validation with a misleading "invalid token". On stage that is unrecoverable
without a restart nobody has budgeted 25 minutes for.

So: the key is infrastructure, not demo state. It survives a reset, and
rotating it is refused while the issuer is listening.
"""

from __future__ import annotations

import os

import pytest

from refund_demo import ledger, reset as reset_module
from refund_demo.config import get_settings


CLEAN_DIGEST = "211597d92491"


def key_path() -> str:
    return get_settings().devidp_key_path


def test_reset_returns_the_ledger_to_the_known_fixture_digest():
    assert reset_module.reset().startswith(CLEAN_DIGEST)


def test_reset_preserves_the_signing_key():
    """The whole point: a reset must not invalidate tokens for running services."""
    path = key_path()
    if not os.path.exists(path):
        pytest.skip("no local signing key on disk yet (start the services once)")
    before = open(path, "rb").read()
    reset_module.reset()
    assert os.path.exists(path), "reset deleted the signing key"
    assert open(path, "rb").read() == before, "reset rotated the signing key"


def test_rotating_the_key_is_refused_while_devidp_is_running(services):
    with pytest.raises(reset_module.ResetRefused, match="devidp is running"):
        reset_module.reset(new_key=True)


def test_refusal_leaves_the_key_in_place(services):
    path = key_path()
    before = open(path, "rb").read()
    with pytest.raises(reset_module.ResetRefused):
        reset_module.reset(new_key=True)
    assert open(path, "rb").read() == before


def test_reset_refuses_in_entra_mode_without_an_explicit_override(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "entra")
    monkeypatch.delenv("ALLOW_RESET", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(reset_module.ResetRefused, match="AUTH_MODE=entra"):
            reset_module.reset()
    finally:
        get_settings.cache_clear()


def test_reset_only_ever_removes_files_inside_the_data_directory(monkeypatch, tmp_path):
    """Point the audit log somewhere else and confirm nothing outside it is touched."""
    outsider = tmp_path / "do-not-delete.txt"
    outsider.write_text("kept")

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    audit = data_dir / "audit.jsonl"
    audit.write_text("{}\n")

    monkeypatch.setenv("AUDIT_LOG_PATH", str(audit))
    get_settings.cache_clear()
    try:
        reset_module.reset()
        assert not audit.exists(), "the in-scope audit log should have been removed"
        assert outsider.exists(), "reset escaped its data directory"
    finally:
        get_settings.cache_clear()
        ledger.initialize(reset=True)
