# Manual Client Approval Checklist

Some claims in this talk **cannot be proven by an automated test.** A direct API call can show that the server denied a request; it cannot show that a human saw a consent screen, or that an approval dialog appeared before a refund was applied. Those are client-side UI behaviours and they need human eyes.

Run this checklist during rehearsal and again on the morning of the talk. Record the date and the client version.

| Field | Value |
| --- | --- |
| Client and version | `__________` |
| Checked by | `__________` |
| Date | `__________` |

---

## A. First connection and consent

| # | Step | Expected | Pass |
| --- | --- | --- | --- |
| A1 | Clear cached client sessions/tokens (see §D), then connect to `refund-demo` | Client contacts the server and receives **401** with a `WWW-Authenticate` header naming Protected Resource Metadata | ☐ |
| A2 | Observe the client's sign-in prompt | Client opens the **authorization server** it discovered — not a URL you typed into config | ☐ |
| A3 | Read the consent screen | Requested scopes are listed and are **only** the ones this resource declares. No tenant-wide or admin-level permission is requested | ☐ |
| A4 | Complete sign-in as `dana.reader` | Client reports connected; `tools/list` succeeds | ☐ |
| A5 | Decline consent instead (repeat A1–A3 in a fresh session) | Client surfaces a clear failure; **no tool call reaches the server**. Confirm with `scripts\audit.ps1` — there must be no new record | ☐ |

## B. Per-call approval on the consequential tool

| # | Step | Expected | Pass |
| --- | --- | --- | --- |
| B1 | Ask the client to read order `ORD-1001` | `get_order` runs. Read-only tools may not prompt — note whether yours does | ☐ |
| B2 | Ask the client to refund `ORD-1001` | An **approval prompt appears before** the tool executes | ☐ |
| B3 | Press **Cancel** | Client reports cancellation. Verify with `scripts\audit.ps1` that **no** `refund_order` record exists, and with `scripts\scenario.ps1 allowed-refund` preconditions that the ledger digest is unchanged | ☐ |
| B4 | Ask again and **Approve** | Refund applies exactly once; audit shows one `allow` record for `refund_order` | ☐ |
| B5 | Ask for the same refund a second time and approve | Server replays the idempotency key; ledger total does **not** increase | ☐ |

> **B3 is the important one.** It is the moment that separates "the user clicked no" from "the server refused". Cancel proves the client stopped it. Everything in section C proves the server would have stopped it anyway.

## C. Approval is not authorization

| # | Step | Expected | Pass |
| --- | --- | --- | --- |
| C1 | Sign in as `sam.agent` (no write scope) and ask for a refund on an owned order | If the client prompts, **approve it**. The server still denies with `POLICY_MISSING_SCOPE` (R003) | ☐ |
| C2 | Sign in as `riley.lead` and request a refund on `ORD-1003` (belongs to another user) | Approve at the client. Server still denies with `POLICY_ORDER_NOT_ASSIGNED` (R006) | ☐ |
| C3 | Request a refund above the per-call limit and approve it | Server denies with `POLICY_AMOUNT_EXCEEDS_PER_CALL_LIMIT` (R203) | ☐ |
| C4 | Confirm the ledger after C1–C3 | Digest unchanged; three `deny` records in the audit trail | ☐ |

Clicking **Approve** in C1–C3 is the entire point. The user consented; the server refused anyway.

## D. Session reset between rehearsals

| # | Step | Expected | Pass |
| --- | --- | --- | --- |
| D1 | Sign out of the `refund-demo` server in the client | Client forgets the account | ☐ |
| D2 | Clear the client's cached MCP authorization for `localhost:8801` | Next connect re-runs the full OAuth flow | ☐ |
| D3 | Reconnect | 401 → discovery → consent appears again (A1–A4 repeat cleanly) | ☐ |

If consent does **not** reappear, the client is reusing a cached token. That is fine for a working demo but it removes the discovery moment from the stage. See `docs/RISKS-AND-FALLBACKS.md` → *Consent prompt does not reappear*.

---

## If the client cannot be made to work

This is an accepted outcome and it does not cost you the talk. The client is **Tier B**: every claim it supports is also proven by `scripts\scenario.ps1`, which needs no client at all.

Fall back to:

- `scripts\scenario.ps1 discovery` — prints the full 401 → PRM → AS metadata → PKCE → resource-indicator → token trace.
- `scripts\scenario.ps1 over-limit-denial` — a server-side denial that no dialog can override.
- Say the honest sentence out loud: *"The client approval dialog is the user's control. What I'm showing you here is the server's control. You need both, and only one of them is yours."*
