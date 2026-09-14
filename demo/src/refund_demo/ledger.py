"""The synthetic refund ledger.

Owned exclusively by the upstream refund API. The MCP server never writes here.

Atomicity and idempotency are the point of this module. A refund must be
applied exactly once even if the client retries, the model loops, or two calls
race. SQLite with ``BEGIN IMMEDIATE`` gives a real write lock, so the
check-balance-then-apply sequence cannot interleave.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Iterator

from .config import get_settings
from .fixtures import ORDERS

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    order_id            TEXT PRIMARY KEY,
    customer_ref        TEXT NOT NULL,
    assigned_to         TEXT NOT NULL,
    currency            TEXT NOT NULL,
    total_minor         INTEGER NOT NULL,
    refunded_minor      INTEGER NOT NULL DEFAULT 0,
    refundable          INTEGER NOT NULL DEFAULT 1,
    restricted          INTEGER NOT NULL DEFAULT 0,
    notes               TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS refunds (
    refund_id           TEXT PRIMARY KEY,
    idempotency_key     TEXT NOT NULL UNIQUE,
    order_id            TEXT NOT NULL,
    amount_minor        INTEGER NOT NULL,
    currency            TEXT NOT NULL,
    actor_subject       TEXT NOT NULL,
    actor_upn           TEXT NOT NULL,
    client_id           TEXT NOT NULL,
    trace_id            TEXT NOT NULL DEFAULT '',
    created_at          TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders (order_id)
);
"""


class LedgerError(Exception):
    """Raised when a mutation is refused by the ledger itself."""

    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code


@dataclass(frozen=True)
class OrderRecord:
    order_id: str
    customer_ref: str
    assigned_to: str
    currency: str
    total_minor: int
    refunded_minor: int
    refundable: bool
    restricted: bool
    notes: str

    @property
    def refundable_balance_minor(self) -> int:
        return max(0, self.total_minor - self.refunded_minor)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["refundable_balance_minor"] = self.refundable_balance_minor
        return data


@dataclass(frozen=True)
class RefundRecord:
    refund_id: str
    idempotency_key: str
    order_id: str
    amount_minor: int
    currency: str
    actor_subject: str
    actor_upn: str
    client_id: str
    trace_id: str
    created_at: str
    replayed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _db_path() -> str:
    return get_settings().ledger_path


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    path = _db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
    finally:
        conn.close()


def initialize(reset: bool = False) -> None:
    """Create the schema and seed synthetic orders.

    ``reset`` restores every order to its pristine fixture state. It is exposed
    only through operator tooling, never as an MCP tool.
    """
    with _connect() as conn:
        conn.executescript(SCHEMA)
        if reset:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM refunds")
            conn.execute("DELETE FROM orders")
            conn.execute("COMMIT")
        for order in ORDERS:
            conn.execute(
                """
                INSERT INTO orders (order_id, customer_ref, assigned_to, currency,
                                    total_minor, refunded_minor, refundable, restricted, notes)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
                ON CONFLICT(order_id) DO NOTHING
                """,
                (
                    order.order_id,
                    order.customer_ref,
                    order.assigned_to,
                    order.currency,
                    order.total_minor,
                    1 if order.refundable else 0,
                    1 if order.restricted else 0,
                    order.notes,
                ),
            )


def _row_to_order(row: sqlite3.Row) -> OrderRecord:
    return OrderRecord(
        order_id=row["order_id"],
        customer_ref=row["customer_ref"],
        assigned_to=row["assigned_to"],
        currency=row["currency"],
        total_minor=row["total_minor"],
        refunded_minor=row["refunded_minor"],
        refundable=bool(row["refundable"]),
        restricted=bool(row["restricted"]),
        notes=row["notes"],
    )


def get_order(order_id: str) -> OrderRecord | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        return _row_to_order(row) if row else None


def list_orders() -> list[OrderRecord]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM orders ORDER BY order_id").fetchall()
        return [_row_to_order(r) for r in rows]


def list_refunds(order_id: str | None = None) -> list[RefundRecord]:
    query = "SELECT * FROM refunds"
    params: tuple[Any, ...] = ()
    if order_id:
        query += " WHERE order_id = ?"
        params = (order_id,)
    query += " ORDER BY created_at"
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        RefundRecord(
            refund_id=r["refund_id"],
            idempotency_key=r["idempotency_key"],
            order_id=r["order_id"],
            amount_minor=r["amount_minor"],
            currency=r["currency"],
            actor_subject=r["actor_subject"],
            actor_upn=r["actor_upn"],
            client_id=r["client_id"],
            trace_id=r["trace_id"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


def ledger_fingerprint() -> dict[str, Any]:
    """A cheap, screen-friendly snapshot used to prove 'nothing changed'.

    ``digest`` is the single value to put on a slide: if it is identical before
    and after a denied call, no state moved.
    """
    with _connect() as conn:
        orders = conn.execute(
            "SELECT order_id, refunded_minor FROM orders ORDER BY order_id"
        ).fetchall()
        count = conn.execute("SELECT COUNT(*) AS c FROM refunds").fetchone()["c"]
    by_order = {r["order_id"]: r["refunded_minor"] for r in orders}
    material = json.dumps({"refund_count": count, "orders": by_order}, sort_keys=True)
    return {
        "refund_count": count,
        "refunded_minor_by_order": by_order,
        "total_refunded_minor": sum(by_order.values()),
        "digest": hashlib.sha256(material.encode("utf-8")).hexdigest(),
    }


def apply_refund(
    *,
    order_id: str,
    amount_minor: int,
    currency: str,
    idempotency_key: str,
    actor_subject: str,
    actor_upn: str,
    client_id: str,
    trace_id: str = "",
    per_call_limit_minor: int | None = None,
) -> RefundRecord:
    """Apply a refund exactly once.

    Business rules are re-checked *here*, at mutation time, even though the MCP
    server already checked them. The upstream API does not trust its caller to
    have enforced anything.
    """
    settings = get_settings()
    limit = per_call_limit_minor if per_call_limit_minor is not None else settings.refund_per_call_limit_minor

    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool):
        raise LedgerError("AMOUNT_NOT_INTEGER", "amount_minor must be an integer number of minor units")
    if amount_minor <= 0:
        raise LedgerError("AMOUNT_NOT_POSITIVE", "amount_minor must be greater than zero")
    if amount_minor > limit:
        raise LedgerError(
            "AMOUNT_EXCEEDS_PER_CALL_LIMIT",
            f"amount_minor {amount_minor} exceeds the per-call limit {limit}",
        )
    if not idempotency_key:
        raise LedgerError("IDEMPOTENCY_KEY_REQUIRED", "idempotency_key is required")

    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            existing = conn.execute(
                "SELECT * FROM refunds WHERE idempotency_key = ?", (idempotency_key,)
            ).fetchone()
            if existing is not None:
                # An idempotency key belongs to one specific request. Replaying
                # it with different parameters is not a retry, it is a second
                # request wearing the first one's key, and returning the
                # original record would report a success that never happened.
                conflicts = {
                    "order_id": (existing["order_id"], order_id),
                    "amount_minor": (existing["amount_minor"], amount_minor),
                    "currency": (existing["currency"], currency),
                    "actor_subject": (existing["actor_subject"], actor_subject),
                }
                differing = {k: v for k, v in conflicts.items() if v[0] != v[1]}
                if differing:
                    detail = ", ".join(f"{k}: {was!r} -> {now!r}" for k, (was, now) in differing.items())
                    raise LedgerError(
                        "IDEMPOTENCY_KEY_REUSED",
                        f"idempotency key {idempotency_key!r} was already used for a different "
                        f"request ({detail})",
                    )
                conn.execute("COMMIT")
                return RefundRecord(
                    refund_id=existing["refund_id"],
                    idempotency_key=existing["idempotency_key"],
                    order_id=existing["order_id"],
                    amount_minor=existing["amount_minor"],
                    currency=existing["currency"],
                    actor_subject=existing["actor_subject"],
                    actor_upn=existing["actor_upn"],
                    client_id=existing["client_id"],
                    trace_id=existing["trace_id"],
                    created_at=existing["created_at"],
                    replayed=True,
                )

            row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
            if row is None:
                raise LedgerError("ORDER_NOT_FOUND", f"order {order_id} does not exist")
            order = _row_to_order(row)

            if not order.refundable:
                raise LedgerError("ORDER_NOT_REFUNDABLE", f"order {order_id} is not eligible for refund")
            if currency != order.currency:
                raise LedgerError(
                    "CURRENCY_MISMATCH",
                    f"currency {currency} does not match order currency {order.currency}",
                )
            if amount_minor > order.refundable_balance_minor:
                raise LedgerError(
                    "AMOUNT_EXCEEDS_BALANCE",
                    f"amount_minor {amount_minor} exceeds remaining refundable balance "
                    f"{order.refundable_balance_minor}",
                )

            record = RefundRecord(
                refund_id=f"RFND-{uuid.uuid4().hex[:12]}",
                idempotency_key=idempotency_key,
                order_id=order_id,
                amount_minor=amount_minor,
                currency=currency,
                actor_subject=actor_subject,
                actor_upn=actor_upn,
                client_id=client_id,
                trace_id=trace_id,
                created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
            conn.execute(
                """
                INSERT INTO refunds (refund_id, idempotency_key, order_id, amount_minor, currency,
                                     actor_subject, actor_upn, client_id, trace_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.refund_id,
                    record.idempotency_key,
                    record.order_id,
                    record.amount_minor,
                    record.currency,
                    record.actor_subject,
                    record.actor_upn,
                    record.client_id,
                    record.trace_id,
                    record.created_at,
                ),
            )
            conn.execute(
                "UPDATE orders SET refunded_minor = refunded_minor + ? WHERE order_id = ?",
                (amount_minor, order_id),
            )
            conn.execute("COMMIT")
            return record
        except Exception:
            conn.execute("ROLLBACK")
            raise
