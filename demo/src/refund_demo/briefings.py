"""Plain-language briefings for the web front end.

Why this exists
---------------
The operator scripts are read by someone who already knows the argument. The web
page is read by a room, often over a presenter's shoulder, and increasingly by
people browsing it after the talk with no narration at all. A scenario name and
a one-line claim are enough for the first audience and not the second.

Each briefing answers three questions in the order an audience actually asks
them: *what did it send*, *what should come back*, and *why does that matter*.
The third is the only one that is hard, and it is the reason the demo exists.

Why here and not in ``scenarios.py``
------------------------------------
``CLAIMS`` is the formal assertion each scenario proves, and it is load-bearing:
it is printed by the scripts and asserted against. This is explanatory prose for
a reader. Keeping them apart means nobody is tempted to soften a claim to make
it read better on a slide. A test pins that every scenario has a briefing, so
the separation cannot rot into an omission.
"""

from __future__ import annotations

from typing import TypedDict


class Briefing(TypedDict):
    """What a scenario sends, what should come back, and why it matters."""

    sends: str
    expects: str
    why: str


ABOUT = {
    "what": (
        "A deliberately small refund desk, built to answer one question: when a model "
        "calls a tool that moves money, who decided that was allowed? Five services run "
        "here \u2014 an OAuth authorization server, two independent MCP servers, an upstream "
        "refund API, and this page. Every verdict you see was made by one of the first "
        "four. This page only reports them."
    ),
    "how": (
        "Each scenario is a complete, real exchange: a token is minted by a real "
        "authorization server with PKCE and an RFC 8707 resource indicator, then "
        "presented to a real MCP server over HTTP, which applies policy and \u2014 if it "
        "allows the call \u2014 exchanges the token for a second one before touching the "
        "upstream API. Nothing is stubbed and nothing is mocked. The refund ledger is a "
        "real database, and its fingerprint is shown on the right."
    ),
    "watch": (
        "Watch the ledger fingerprint. Twelve of the fourteen scenarios must leave it "
        "untouched \u2014 that is the proof a denial actually denied something rather than "
        "just printing a refusal. Exactly one scenario is supposed to move it, and it "
        "moves it once even though it calls the tool twice."
    ),
    "not": (
        "Every order, customer, and employee here is invented. The audit trail is a JSONL "
        "file \u2014 it is evidence you can read, not tamper-evident storage. And the model, "
        "when one is configured, enforces nothing at all: it writes advice, and the "
        "advice is ignored by the code that decides."
    ),
}


BRIEFINGS: dict[str, Briefing] = {
    "no-token": {
        "sends": (
            "A bare <code>tools/list</code> request to Resource A with no "
            "<code>Authorization</code> header at all."
        ),
        "expects": (
            "<code>HTTP 401</code>, and a <code>WWW-Authenticate</code> header containing "
            "<code>resource_metadata=</code> pointing at this server's metadata document."
        ),
        "why": (
            "Refusing is the easy half. The header is the interesting half: it tells the "
            "client <em>where to go and get authenticated</em>, so discovery never has to "
            "be guessed or hard-coded. This is the first step of every other scenario."
        ),
    },
    "discovery": {
        "sends": (
            "The whole handshake, in order: the 401 challenge, the protected-resource "
            "metadata it points to, the authorization server's metadata, then an "
            "authorization request carrying a PKCE <code>S256</code> challenge and an "
            "RFC 8707 <code>resource</code> indicator."
        ),
        "expects": (
            "A token whose <code>aud</code> is <code>api://refund-mcp-a</code> and nothing "
            "else, plus the three tools this server publishes."
        ),
        "why": (
            "The audience is fixed when the token is <em>minted</em>, not when it is "
            "checked. That single property is what makes the wrong-audience scenario "
            "further down possible \u2014 and it costs one request parameter."
        ),
    },
    "missing-resource-indicator": {
        "sends": (
            "A correctly formed authorization request \u2014 valid client, valid redirect URI, "
            "proper S256 challenge \u2014 with the <code>resource</code> parameter omitted."
        ),
        "expects": (
            "<code>HTTP 400</code> with <code>error: invalid_target</code>. No token is "
            "issued."
        ),
        "why": (
            "Without a resource indicator the authorization server has no way to know what "
            "audience to stamp on the token, so it would have to mint something usable "
            "anywhere. An authorization server that guesses here is minting a skeleton key. "
            "Refusing is the only safe answer."
        ),
    },
    "pkce-downgrade": {
        "sends": (
            "A token request that asks for <code>code_challenge_method=plain</code> instead "
            "of <code>S256</code> \u2014 the classic downgrade."
        ),
        "expects": (
            "The authorization server refuses to issue a code at all \u2014 the downgrade is "
            "rejected at the authorize step, before any token exists."
        ),
        "why": (
            "<code>plain</code> puts the verifier on the wire in readable form, so anyone "
            "who can see the authorization request can finish the exchange. Supporting it "
            "for compatibility quietly removes the protection PKCE exists to provide."
        ),
    },
    "allowed-refund": {
        "sends": (
            "<code>refund_order</code> for <code>ORD-1001</code>, CAD&nbsp;40.00, as a user "
            "who holds the write scope and owns the order \u2014 then the <em>identical</em> "
            "call again, reusing the same idempotency key."
        ),
        "expects": (
            "First call: a real <code>RFND-\u2026</code> id and <code>idempotent_replay: "
            "false</code>. Second call: <code>idempotent_replay: true</code>. The ledger "
            "digest changes <strong>once</strong>, and the refunded total rises by 4000 "
            "minor units, not 8000. The key is fixed rather than freshly minted, so this "
            "holds across <em>runs</em> too: press Run as many times as you like and "
            "exactly one refund will ever exist. Later runs report "
            "<code>refund_applied_by_this_run: False</code> and a ledger that does not "
            "move at all. <code>scripts/reset.ps1</code> clears the refunds table and "
            "restores the first-call demonstration."
        ),
        "why": (
            "A demo that only ever says no proves nothing \u2014 a server that refuses "
            "everything is trivially secure and useless. This is the control. It also shows "
            "the on-behalf-of exchange: the subject is preserved end to end while the "
            "audience changes to <code>api://refund-upstream</code>."
        ),
    },
    "scope-denial": {
        "sends": (
            "<code>refund_order</code> on an order the caller <em>does</em> own \u2014 but "
            "with a token carrying only <code>Refund.Read</code>."
        ),
        "expects": "<code>MISSING_SCOPE</code>, and a ledger digest that does not move.",
        "why": (
            "The straightforward check, included because it is the one most teams already "
            "have. Note what it is checking: a <em>verb</em>. Reading is not writing. The "
            "next scenario is the one that verb checks cannot answer."
        ),
    },
    "ownership-denial": {
        "sends": (
            "<code>refund_order</code> for <code>ORD-1003</code>, CAD&nbsp;990.00, by a user "
            "who genuinely holds <code>Refund.Write</code>. The order belongs to a different "
            "employee."
        ),
        "expects": (
            "<code>POLICY_ORDER_NOT_ASSIGNED</code> (rule <code>R006</code>). Ledger "
            "unchanged."
        ),
        "why": (
            "<strong>This is the confused-deputy problem, and the centre of the talk.</strong> "
            "A scope is a verb, not an object: <code>Refund.Write</code> says the caller may "
            "issue refunds, and says nothing whatsoever about <em>which order</em>. Nothing "
            "in the token can express this. Only the server, at call time, knows who "
            "<code>ORD-1003</code> belongs to."
        ),
    },
    "business-rule-denial": {
        "sends": (
            "<code>refund_order</code> for <code>ORD-1004</code> by a fully authorized user "
            "who owns it \u2014 an order whose state makes it ineligible."
        ),
        "expects": (
            "<code>NOT_REFUNDABLE</code> \u2014 a denial about the <em>order</em>, not about the "
            "caller, who was never the problem. Ledger unchanged."
        ),
        "why": (
            "Authorization is not only about identity. Eligibility is a fact about the "
            "object, it changes over time, and it is knowable only at the moment of the "
            "call. No token minted minutes earlier could have encoded it."
        ),
    },
    "over-limit-denial": {
        "sends": (
            "<code>refund_order</code> for one minor unit more than the server's per-call "
            "ceiling, by an authorized owner."
        ),
        "expects": (
            "A <code>LIMIT</code> reason code carrying the server's actual ceiling, so the "
            "caller learns the rule rather than just the refusal. Ledger unchanged."
        ),
        "why": (
            "Value caps are frequently implemented in the client's confirmation dialog, "
            "which means they are implemented nowhere. The dialog is a UI affordance the "
            "user's vendor controls; the server is the only place a limit is actually a "
            "limit."
        ),
    },
    "unapproved-client": {
        "sends": (
            "A perfectly valid token \u2014 right user, right scopes, right audience \u2014 issued "
            "to a client application this server has never approved."
        ),
        "expects": "A <code>CLIENT</code> reason code on the <code>azp</code> claim.",
        "why": (
            "The <code>azp</code> claim records <em>which application</em> is acting for the "
            "user. Consent granted to one client is not consent for every client that can "
            "obtain a token on that user's behalf \u2014 which, with dynamic registration, can "
            "be quite a lot of them."
        ),
    },
    "wrong-audience": {
        "sends": (
            "A genuine, unexpired, correctly signed token minted for Resource B, presented "
            "to Resource A. Then the control: the same token, to Resource B."
        ),
        "expects": (
            "Resource A answers <code>401 AUTH_WRONG_AUDIENCE</code> with a challenge "
            "header. Resource B accepts it. Ledger unchanged."
        ),
        "why": (
            "The control is what makes this evidence rather than assertion \u2014 it proves the "
            "token is <em>bound</em>, not broken. Without resource binding, any MCP server a "
            "user connects to could replay their token at every other one. Be precise about "
            "the limit: this stops cross-resource reuse, not replay at the intended resource."
        ),
    },
    "prompt-injection": {
        "sends": (
            "<code>assess_refund</code> on <code>ORD-1005</code>, whose customer notes "
            "contain instructions aimed at the assistant, telling it to refund someone "
            "else's order. The harness then <strong>obeys them verbatim</strong>."
        ),
        "expects": (
            "The injected instructions are flagged in the notes, and the forced refund is "
            "denied with <code>POLICY_ORDER_NOT_ASSIGNED</code> \u2014 the identical denial as "
            "the ownership scenario. Ledger unchanged."
        ),
        "why": (
            "The defence is not that the model refused. The harness skips the model's "
            "judgement entirely and issues the call anyway, because an attacker would. "
            "Authorization has to hold when the reasoning layer has already been captured. "
            "Two honest caveats: this is a harness replay rather than a live model attack, "
            "and if a platform content filter is configured it may refuse the prompt first "
            "\u2014 a third layer, outside this app and outside MCP, and also not the boundary."
        ),
    },
    "annotation-tampering": {
        "sends": (
            "A client lists the tools, rewrites the annotations it received to claim "
            "<code>readOnlyHint: true</code> and <code>destructiveHint: false</code>, then "
            "calls <code>refund_order</code> as if it were a harmless read."
        ),
        "expects": (
            "Exactly the same <code>MISSING_SCOPE</code> denial, with the same reason code."
        ),
        "why": (
            "Annotations never travel back to the server \u2014 rewriting them changes nothing "
            "on the wire, which is precisely the point. They are documentation for the "
            "client, and useful as such. <code>readOnlyHint</code> is not a permission, and "
            "a server that treats it as one has outsourced authorization to the caller."
        ),
    },
    "token-passthrough-blocked": {
        "sends": (
            "The MCP server's own access token, forwarded unchanged to the upstream refund "
            "API \u2014 the shortcut that removes an entire token exchange."
        ),
        "expects": (
            "<code>HTTP 401 AUTH_WRONG_AUDIENCE</code> from the upstream, which expects "
            "<code>api://refund-upstream</code>."
        ),
        "why": (
            "Token passthrough is explicitly forbidden by the MCP specification, and this is "
            "why: it makes one stolen token valid everywhere downstream and destroys any "
            "chance of knowing which service actually made a change. The upstream refusing "
            "it is what makes the delegation in <code>allowed-refund</code> meaningful."
        ),
    },
}
