# Who Can Call This MCP Tool?

**OAuth, Resource Binding, and Runtime Policy**
MCP Dev Summit Toronto · 2026-10-06 · 15:40–16:05 · Brian Benz

A runnable demo of the question in the title. An MCP server exposes a `refund_order` tool that moves money. A user is signed in. A client shows an approval dialog. **None of that answers whether this principal may refund this order.**

Everything here runs locally in about ten minutes, with no Azure subscription and no Entra tenant.

```powershell
cd demo
.\scripts\bootstrap.ps1
.\scripts\start-all.ps1 -Reset
.\scripts\check.ps1          # 78 tests + 14 scenarios -> READY
```

---

## Architecture and trust boundaries

```mermaid
flowchart TB
    subgraph outside["Outside your trust boundary"]
        U([User])
        C["MCP Client<br/><i>owns approval</i>"]
        F["Foundry model<br/><i>reads attacker-influenced text</i>"]
    end
    subgraph yours["Your trust boundary"]
        AS["Authorization Server<br/>:8800<br/><i>authentication + audience binding</i>"]
        A["MCP Server — Resource A<br/>:8801<br/><b>the decision point</b>"]
        B["MCP Server — Resource B<br/>:8802<br/><i>different audience</i>"]
        API["Upstream Refund API<br/>:8803<br/><i>re-enforces independently</i>"]
        L[("Ledger<br/>SQLite")]
    end

    U --> C
    C -->|"PKCE S256 + RFC 8707 resource"| AS
    AS -.->|"aud=api://refund-mcp-a"| C
    C -->|"tools/call + Bearer"| A
    C -.->|"same token: 401 wrong audience"| B
    A -->|"advisory only"| F
    A -->|"on-behalf-of exchange"| AS
    A -->|"aud=api://refund-upstream"| API
    API --> L

    classDef red fill:#3f1d1d,stroke:#f87171,color:#fee2e2
    classDef blue fill:#1f2937,stroke:#60a5fa,color:#e5e7eb
    class U,C,F red
    class AS,A,B,API,L blue
```

Red is outside your control **even though it is part of your system**. The client runs on someone else's machine. The model reads text an attacker can write. Neither gets a vote on authorization.

---

## The five layers, and who owns each

| Layer | Owner | Answers | Cannot answer |
| --- | --- | --- | --- |
| MCP Client | The user's vendor — **not you** | *Did the human mean this?* | Whether they are allowed |
| Authorization Server | Your identity platform | *Who are they? For which resource?* | Anything about order `ORD-1003` |
| **MCP Server** | **You** | ***May this principal do this to this object, now?*** | Whether the human meant it |
| Upstream API | You | *Is this still true at mutation time?* | Who was at the keyboard |
| Foundry model | You, but inputs are hostile | *What would a reasonable analyst advise?* | **Nothing. It enforces nothing.** |

Full detail, with denial behaviour and limitations: **[docs/CONTROL-MAP.md](docs/CONTROL-MAP.md)**.

---

## Seven things to take home

1. **Bind every token to one resource.** A token that works at two services is a lateral-movement primitive. RFC 8707, checked on arrival.
2. **Scopes are verbs, not objects.** `refund.write` never named `ORD-1003`. Check the object.
3. **A confirmation dialog is not server authorization.** Assume Approve was clicked, then decide anyway.
4. **Never forward an incoming token downstream.** Exchange it — and if the exchange fails, *fail*. No app-only fallback.
5. **Annotations are hints from an untrusted process.** `readOnlyHint` is documentation, not a permission.
6. **Model output is advice about untrusted input.** Record it; never let it widen authorization.
7. **Audit at the decision point, including denials.** Pseudonymize identifiers, allowlist logged arguments, deny by default.

---

## Try the interesting parts

```powershell
.\scripts\scenario.ps1 discovery              # 401 -> PRM -> AS metadata -> PKCE -> audience-bound token
.\scripts\scenario.ps1 allowed-refund         # applied once; retry does not double-spend
.\scripts\scenario.ps1 wrong-audience         # valid token for Resource B, rejected at Resource A
.\scripts\scenario.ps1 ownership-denial       # the confused deputy: right scope, someone else's order
.\scripts\scenario.ps1 prompt-injection       # hostile note in order data; policy unmoved
.\scripts\scenario.ps1 annotation-tampering   # client lies about readOnlyHint; nothing changes
.\scripts\scenario.ps1 token-passthrough-blocked
.\scripts\scenario.ps1 -All                   # all 14
.\scripts\audit.ps1 -Last 5                   # the evidence trail
```

Every scenario prints the ledger digest **before and after**, so "nothing happened" is demonstrated rather than asserted.

---

## Documentation

| Document | For |
| --- | --- |
| **[SETUP.md](docs/SETUP.md)** | Prerequisites, bootstrap, configuration, troubleshooting |
| **[CONTROL-MAP.md](docs/CONTROL-MAP.md)** | The one-page attendee takeaway |
| **[COVERAGE-MATRIX.md](docs/COVERAGE-MATRIX.md)** | Every promise → implementation → test → evidence |
| [RUNBOOK.md](docs/RUNBOOK.md) | Presenter: timed schedule, tiers, stop-times, recovery |
| [ONSTAGE-SCRIPT.md](docs/ONSTAGE-SCRIPT.md) | Presenter: literal prompts and narration |
| [RISKS-AND-FALLBACKS.md](docs/RISKS-AND-FALLBACKS.md) | 15 failure modes, detection, prepared fallback |
| [COMPATIBILITY-RECORD.md](docs/COMPATIBILITY-RECORD.md) | Verified versions, SDK API facts, defects found |
| [CLIENT-APPROVAL-CHECKLIST.md](docs/CLIENT-APPROVAL-CHECKLIST.md) | Manual checks no test can prove |
| [APPENDIX.md](docs/APPENDIX.md) | Sequence diagrams, sanitized audit records, KQL, design trade-offs, sources |

---

## Layout

```
demo/
  src/refund_demo/
    tokens.py            # signature, algorithm, issuer, tenant, audience, expiry
    policy.py            # deny-by-default decision point, R001-R299
    ledger.py            # atomic, idempotent mutation
    delegation.py        # on-behalf-of exchange -- no passthrough, no fallback
    audit.py             # pseudonymized evidence at the decision point
    mcp_server/          # Resource A  :8801
    resource_b/          # Resource B  :8802 -- exists to be rejected
    upstream_api/        # refund API  :8803 -- re-enforces everything
    devidp/              # local OAuth AS :8800 -- real RS256/PKCE/RFC 8707
    client.py            # OAuth client + protocol trace
    scenarios.py         # 14 named stage scenarios
  tests/                 # 78 tests
  scripts/               # PowerShell + bash operator commands
  infra/                 # Bicep -- compiles; never deployed
  identity/              # Entra registration scripts -- never executed
docs/
```

---

## Honest limitations

Stated here because a talk about authorization should not overclaim.

- **Resource binding stops cross-resource token reuse. It does not stop replay of a stolen token at its intended resource.** Different problem: sender-constrained tokens.
- **The audit log is a JSONL file.** Structured and pseudonymized — but not immutable and not tamper-proof.
- **`AUTH_MODE=entra` has never been executed.** No tenant was authorized for this build. The default and the rehearsed path is the local authorization server, which is a real OAuth server validated by the same code.
- **`demo/infra` has never been deployed.** The Bicep compiles; that is the entire claim.
- **The client approval UI is verified by hand only.** No automated test can prove a dialog appeared.
- **A cancelled request is client-only evidence.** The server never saw it, so it cannot show you a record of refusing it.

Full list: [COVERAGE-MATRIX.md](docs/COVERAGE-MATRIX.md#not-proven--say-so-if-asked).

---

## Security notes

`devidp` issues tokens to anyone who asks. **It must never run anywhere but localhost.** All fixtures are synthetic; there is no real customer data. No secret, token, authorization code, or PKCE verifier is ever logged, printed, or committed — `.env` files, keys, and certificates are git-ignored.
