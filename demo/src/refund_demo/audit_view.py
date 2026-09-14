"""Render audit records for a projector.

The full JSON record is the artifact; this view is what an audience can read
from the back of a room in a few seconds.
"""

from __future__ import annotations

import argparse
import json

from . import audit

GREEN = "\033[92m"
RED = "\033[91m"
DIM = "\033[2m"
RESET = "\033[0m"

FIELDS = [
    ("timestamp", "when"),
    ("tool", "tool"),
    ("decision", "decision"),
    ("reason_code", "reason"),
    ("policy_rule_id", "rule"),
    ("policy_version", "policy"),
    ("user_pseudonym", "user"),
    ("client_id", "client"),
    ("resource_audience", "audience"),
    ("upstream_audience", "upstream aud"),
    ("upstream_status", "upstream"),
    ("ledger_changed", "ledger changed"),
    ("identity_state", "identity"),
    ("trace_id", "trace"),
    ("mcp_request_id", "mcp request"),
]


def render(record: dict) -> str:
    decision = record.get("decision", "?")
    colour = GREEN if decision == "allow" else RED
    head = f"{colour}{decision.upper():<6}{RESET} {record.get('tool', '?')}"
    body = "\n".join(
        f"    {label:<15} {record.get(key)}"
        for key, label in FIELDS
        if record.get(key) not in (None, "", [])
    )
    args = json.dumps(record.get("arguments", {}), sort_keys=True)
    return f"{head}\n{body}\n    {DIM}arguments{RESET}       {args}"


def main() -> int:
    parser = argparse.ArgumentParser(description="show recent audit records")
    parser.add_argument("--last", type=int, default=5)
    parser.add_argument("--tool", default=None)
    parser.add_argument("--decision", default=None, choices=["allow", "deny"])
    args = parser.parse_args()

    records = audit.read_all()
    if args.tool:
        records = [r for r in records if r.get("tool") == args.tool]
    if args.decision:
        records = [r for r in records if r.get("decision") == args.decision]

    if not records:
        print("no audit records yet")
        return 0

    for record in records[-args.last:]:
        print(render(record))
        print()
    print(f"{DIM}{len(records)} records total in {audit.get_settings().audit_log_path}{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
