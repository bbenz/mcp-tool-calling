"""Operator-only reset of demo state.

Deliberately **not** an MCP tool. Any tool is callable by a model, and the
model in this demo reads attacker-influenced order notes. A "put the ledger
back" capability reachable from that path would be an obvious escalation, so
reset lives here, in an operator command, and nothing on the MCP surface can
reach it.

Two further guards:

* Everything removed is inside ``demo/.local``. The reset cannot touch
  anything outside it.
* It refuses to run when ``AUTH_MODE=entra``, because that mode points at a
  real directory and plausibly at shared state. Override with ``ALLOW_RESET=1``
  only when you are certain the target is your own demo data.
"""

from __future__ import annotations

import argparse
import os
import sys

from . import ledger
from .config import get_settings


class ResetRefused(RuntimeError):
    """Raised when the environment is not obviously a disposable demo."""


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


def reset(*, keep_key: bool = False) -> str:
    """Return the ledger to fixtures. Returns the new fingerprint digest."""
    guard()
    settings = get_settings()
    data_dir = os.path.dirname(os.path.abspath(settings.audit_log_path))

    removable = [settings.audit_log_path, os.path.join(data_dir, "devidp-key.json")]
    if keep_key:
        removable.pop()

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
    parser.add_argument("--keep-key", action="store_true", help="keep the local devidp signing key")
    args = parser.parse_args(argv)
    try:
        digest = reset(keep_key=args.keep_key)
    except ResetRefused as exc:
        print(f"reset refused: {exc}", file=sys.stderr)
        return 2
    print(f"ledger reset -> {digest[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
