"""Operator-only reset of demo state.

Deliberately **not** an MCP tool. Any tool is callable by a model, and the
model in this demo reads attacker-influenced order notes. A "put the ledger
back" capability reachable from that path would be an obvious escalation, so
reset lives here, in an operator command, and nothing on the MCP surface can
reach it.

Three further guards:

* Everything removed is inside ``demo/.local``. The reset cannot touch
  anything outside it.
* It refuses to run when ``AUTH_MODE=entra``, because that mode points at a
  real directory and plausibly at shared state. Override with ``ALLOW_RESET=1``
  only when you are certain the target is your own demo data.
* It keeps the local signing key by default. The key is infrastructure, not
  demo state: deleting it underneath running services makes ``devidp`` mint
  tokens with a new key while every service still serves and caches the old
  JWKS, and the demo then fails with misleading "invalid token" errors. Use
  ``--new-key`` to rotate it, which is refused while ``devidp`` is listening.
"""

from __future__ import annotations

import argparse
import os
import socket
import sys

from . import ledger
from .config import get_settings


class ResetRefused(RuntimeError):
    """Raised when the environment is not obviously a disposable demo."""


def _devidp_is_running() -> bool:
    """True when something is listening on the local issuer port."""
    settings = get_settings()
    host, _, port = settings.issuer.split("//", 1)[1].partition(":")
    try:
        with socket.create_connection((host, int(port or 80)), timeout=0.5):
            return True
    except (OSError, ValueError):
        return False


def guard(*, allow_override: bool | None = None) -> None:
    settings = get_settings()
    if settings.auth_mode != "entra":
        return
    override = os.environ.get("ALLOW_RESET") == "1" if allow_override is None else allow_override
    if override:
        return
    raise ResetRefused(
        "refusing to reset while AUTH_MODE=entra: this mode targets a real directory "
        "and possibly shared state. Set ALLOW_RESET=1 if this is your own demo data."
    )


def reset(*, new_key: bool = False) -> str:
    """Return the ledger to fixtures. Returns the new fingerprint digest.

    The signing key survives unless ``new_key`` is set, so this is safe to run
    between segments with the services up -- which is exactly how the runbook
    uses it.
    """
    guard()
    settings = get_settings()
    data_dir = os.path.dirname(os.path.abspath(settings.audit_log_path))

    removable = [settings.audit_log_path]
    if new_key:
        if _devidp_is_running():
            raise ResetRefused(
                "refusing to rotate the signing key while devidp is running: the running "
                "services would keep serving the old JWKS and every token would fail to "
                "validate. Stop the services first (scripts/stop-all), or drop --new-key."
            )
        removable.append(settings.devidp_key_path)

    for path in removable:
        # Never delete outside the data directory, whatever configuration says.
        absolute = os.path.abspath(path)
        if os.path.commonpath([data_dir, absolute]) != data_dir:
            continue
        if os.path.exists(absolute):
            os.remove(absolute)

    ledger.initialize(reset=True)
    return ledger.ledger_fingerprint()["digest"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="reset demo ledger and audit state")
    parser.add_argument(
        "--new-key",
        action="store_true",
        help="also rotate the local devidp signing key (services must be stopped)",
    )
    parser.add_argument(
        "--keep-key",
        action="store_true",
        help=argparse.SUPPRESS,  # now the default; accepted so older notes keep working
    )
    args = parser.parse_args(argv)
    try:
        digest = reset(new_key=args.new_key and not args.keep_key)
    except ResetRefused as exc:
        print(f"reset refused: {exc}", file=sys.stderr)
        return 2
    print(f"ledger reset -> {digest[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
