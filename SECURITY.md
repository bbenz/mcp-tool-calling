# Security Policy

## What this project is

This is a **conference demo**. It exists to show how MCP tool calls can be
bound to an identity, an audience, and a policy decision — and to show those
controls failing safely when they are attacked.

It is not a product, it is not supported, and **nothing here should be run in
production or against real money, real customers, or real credentials.** The
ledger is a local SQLite file full of invented orders.

## Things that look like vulnerabilities and are deliberate

Please read this list before reporting. Several parts of this repository are
insecure *on purpose*, because the demo needs something to attack.

| Behaviour | Why it is there |
| --- | --- |
| `devidp` mints tokens for whatever audience is asked for, with no real user authentication | It is a local development authorization server that stands in for Entra so the demo runs offline. It binds to `127.0.0.1` and must never be exposed. See defect 17 in [COMPATIBILITY-RECORD.md](docs/COMPATIBILITY-RECORD.md) for what happened the one time it was not. |
| Order `ORD-1005` contains a hostile instruction in its free-text notes | That is the prompt-injection fixture. The demo's whole claim is that this text reaches the model and still changes no authorization decision. |
| Resource B accepts tokens that Resource A rejects | Resource B exists to be rejected. That is the `wrong-audience` scenario. |
| `validate_token_resource=False` on the MCP server | The SDK's check compares the token's `resource` to an HTTP URL, while these tokens are bound to an App ID URI. Audience validation still happens, in `refund_demo.tokens.TokenValidator`, on every request. The reasoning is written out in [COMPATIBILITY-RECORD.md](docs/COMPATIBILITY-RECORD.md) §2. |
| The optional AKS deployment serves plain HTTP with the access key in the URL | Known, documented, and deliberately not fixed — see [DEPLOYMENT.md](docs/DEPLOYMENT.md) §8, which also explains how to reduce the exposure. Treat any such deployment as disposable. |
| `demo/infra` Bicep and `demo/identity` Entra scripts | Never executed. They compile and they are readable; that is the entire claim. `AUTH_MODE=entra` has never been run. |

## What is worth reporting

A report is valuable if it would make the demo **teach the wrong lesson**. For
example:

- A way to get a refund applied that the policy engine should have denied.
- A token check that does not actually hold — a wrong audience, a bad
  signature, an expired token, or a passthrough token that is accepted anywhere.
- A way to make the audit trail disagree with what really happened, or to
  suppress an audit record for a decision that was taken.
- A way for tool annotations, tool descriptions, or order content to influence
  an authorization decision.
- Anything in the optional Docker Compose or AKS paths that exposes more than
  §8 of DEPLOYMENT.md says it exposes.

Findings of that kind have been taken seriously before: §3 of
[COMPATIBILITY-RECORD.md](docs/COMPATIBILITY-RECORD.md) records the defects
found during the build, including four security fixes made against a live
endpoint.

## How to report

Please use **GitHub's private vulnerability reporting** on this repository
(*Security* → *Report a vulnerability*) rather than opening a public issue, so
there is a chance to fix an embarrassing one before it is on a projector.

Include the scenario or command you ran, what you expected, and what happened —
the ledger digest before and after is especially useful, since that is how this
demo proves whether anything actually changed.

Please do not test against anyone else's deployment. Run it locally; that takes
one bootstrap command.

## Expectations

This is a personal demo repository maintained around conference dates, so there
is no response-time commitment. Reports will be read, and anything that breaks a
claim the demo makes on stage will be fixed with priority.
