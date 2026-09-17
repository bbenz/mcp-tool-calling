"""A projector-friendly web front end for the refund demo.

Why Starlette and not FastAPI
-----------------------------
FastAPI was the obvious first choice and was deliberately rejected. The MCP SDK
pins ``starlette>=1.6.0``; FastAPI carries its own Starlette range, so adding it
risks resolving Starlette *downward* and breaking the four services this page
exists to demonstrate. A talk that argues for controlling what a tool may reach
should not add a dependency it did not need, and the stage requirement is that
everything works with the Wi-Fi switched off. All four existing services are
already Starlette apps, so this one matches them.

What this surfaces
------------------
The same fourteen scenarios the operator scripts run, the ledger fingerprint
before and after each one, and the audit trail. Nothing here re-implements a
security decision: every verdict on this page was made by the MCP server, the
upstream API, or the policy engine, and this page only reports it.

What this deliberately does not do
----------------------------------
Reset is off over HTTP unless ``WEB_ALLOW_RESET=1``. An endpoint that puts the
ledger back, reachable by anything that can reach the page, is the precise
escalation this talk argues against.
"""

from __future__ import annotations

from typing import Any

import anyio
import anyio.to_thread
import hmac
import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route

from .. import audit, ledger, reset as reset_module
from ..briefings import ABOUT, BRIEFINGS, Briefing
from ..config import get_settings
from ..runtime import describe as describe_runtime
from ..scenarios import CLAIMS, SCENARIOS, run_one
from ..telemetry import configure

# One scenario at a time. Two people clicking Run at once would interleave
# ledger writes and produce a before/after digest pair that belongs to neither
# run, which would undermine the one thing this page is here to prove.
_run_lock = anyio.Lock()


def _scenario_summary() -> list[dict[str, str]]:
    """Name, formal claim, and the three-part briefing the page expands.

    A missing briefing yields empty strings rather than a KeyError: an
    explanatory gap should not take the page down mid-talk.
    """
    blank: Briefing = {"sends": "", "expects": "", "why": ""}
    out = []
    for name in SCENARIOS:
        brief = BRIEFINGS.get(name, blank)
        out.append(
            {
                "name": name,
                "claim": CLAIMS.get(name, ""),
                "sends": brief["sends"],
                "expects": brief["expects"],
                "why": brief["why"],
            }
        )
    return out


def _gate(request: Request) -> Response | None:
    """Shared-secret gate.

    An empty key means "no gate" on a laptop and under Compose, where the
    address is local. On a deployment that sets WEB_REQUIRE_ACCESS_KEY it means
    *refuse*, not *allow*: a missing or mis-keyed Secret used to remove
    authentication silently, with the pod still reporting healthy and nothing
    in the logs to say so. Failing closed turns that into a visible 503.
    """
    settings = get_settings()
    key = settings.web_access_key
    if not key:
        if settings.web_require_access_key:
            return JSONResponse(
                {
                    "error": "refusing to serve without an access key",
                    "detail": (
                        "WEB_REQUIRE_ACCESS_KEY is set but WEB_ACCESS_KEY is empty. "
                        "This deployment declares itself publicly addressable, so "
                        "serving without a key would expose the whole app."
                    ),
                },
                status_code=503,
            )
        return None
    presented = request.headers.get("x-demo-key") or request.query_params.get("k")
    if hmac.compare_digest(presented or "", key):
        return None
    return JSONResponse({"error": "access key required"}, status_code=401)


def _about_html() -> str:
    """The top expander: what this is, before anyone clicks Run.

    Built here rather than inlined in the template so the prose lives with the
    scenario briefings, and so a reader looking for "what does this app claim
    about itself" finds all of it in one file.
    """
    rows = [
        ("What this is", ABOUT["what"]),
        ("How it works", ABOUT["how"]),
        ("What to watch", ABOUT["watch"]),
        ("What it is not", ABOUT["not"]),
    ]
    body = "".join(f"<dt>{label}</dt><dd>{text}</dd>" for label, text in rows)
    return (
        '<details class="about">'
        "<summary>"
        '<span class="chev">&#9656;</span>'
        '<span class="name">About this demo</span>'
        '<span class="spacer"></span>'
        '<span class="sub">read this first</span>'
        "</summary>"
        f'<dl class="brief">{body}</dl>'
        "</details>"
    )


async def index(request: Request) -> Response:
    if (blocked := _gate(request)) is not None:
        # A 503 here means "no key configured on a public bind" -- an operator
        # error, not a visitor error. Say which one it is instead of showing a
        # lock screen that invites the visitor to find a key that cannot work.
        if blocked.status_code == 503:
            return blocked
        return HTMLResponse(_LOCKED_HTML, status_code=401)
    return HTMLResponse(PAGE.replace("<!--ABOUT-->", _about_html()))


async def health(request: Request) -> Response:
    """Liveness and readiness. Cheap on purpose - probes run often."""
    return JSONResponse({"status": "ok", "service": "web"})


async def api_scenarios(request: Request) -> Response:
    if (blocked := _gate(request)) is not None:
        return blocked
    return JSONResponse(_scenario_summary())


async def api_run(request: Request) -> Response:
    if (blocked := _gate(request)) is not None:
        return blocked
    name = request.path_params["name"]
    if name not in SCENARIOS:
        return JSONResponse({"error": f"unknown scenario {name!r}"}, status_code=404)
    async with _run_lock:
        try:
            result = await run_one(name)
        except Exception as exc:  # a scenario that raises is a failed check, not a 500
            return JSONResponse(
                {
                    "name": name,
                    "passed": False,
                    "claim": "(scenario raised)",
                    "detail": f"{type(exc).__name__}: {exc}",
                    "ledger_before": "",
                    "ledger_after": "",
                    "ledger_changed": False,
                    "evidence": {},
                }
            )
    return JSONResponse(
        {
            "name": result.name,
            "claim": result.claim,
            "passed": result.passed,
            "detail": result.detail,
            "ledger_before": result.ledger_before.get("digest", ""),
            "ledger_after": result.ledger_after.get("digest", ""),
            "ledger_changed": result.ledger_changed,
            "evidence": {k: str(v) for k, v in result.evidence.items()},
        }
    )


async def api_ledger(request: Request) -> Response:
    if (blocked := _gate(request)) is not None:
        return blocked
    return JSONResponse(
        {
            "fingerprint": ledger.ledger_fingerprint(),
            "orders": [o.to_dict() for o in ledger.list_orders()],
            "refunds": [r.to_dict() for r in ledger.list_refunds()],
        }
    )


async def api_audit(request: Request) -> Response:
    if (blocked := _gate(request)) is not None:
        return blocked
    try:
        last = max(1, int(request.query_params.get("last", "10")))
    except ValueError:
        last = 10
    records = audit.read_all()
    return JSONResponse({"total": len(records), "records": records[-last:]})


async def api_services(request: Request) -> Response:
    """Health of the four services this page depends on.

    Carries the runtime description too, because the URLs below are loopback in
    every environment: without it a room cannot tell the cluster from a laptop.
    """
    if (blocked := _gate(request)) is not None:
        return blocked
    settings = get_settings()
    targets = {
        "devidp": settings.issuer,
        "mcp-a": settings.mcp_a_public_url,
        "mcp-b": settings.mcp_b_public_url,
        "upstream": settings.upstream_api_url,
    }
    out: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, url in targets.items():
            try:
                response = await client.get(f"{url}/health")
                out[name] = {"url": url, "healthy": response.status_code == 200}
            except httpx.HTTPError as exc:
                out[name] = {"url": url, "healthy": False, "error": type(exc).__name__}
    return JSONResponse({"services": out, "runtime": describe_runtime()})


async def api_reset(request: Request) -> Response:
    if (blocked := _gate(request)) is not None:
        return blocked
    if not get_settings().web_allow_reset:
        return JSONResponse(
            {
                "error": "reset is not exposed over HTTP",
                "detail": "Set WEB_ALLOW_RESET=1 to enable it. It is off by default, "
                          "and stays off in the cloud deployment, on purpose.",
            },
            status_code=403,
        )
    try:
        digest = await anyio.to_thread.run_sync(reset_module.reset)
    except reset_module.ResetRefused as exc:
        return JSONResponse({"error": str(exc)}, status_code=403)
    return JSONResponse({"digest": digest})


routes = [
    Route("/", index),
    Route("/health", health),
    Route("/api/scenarios", api_scenarios),
    Route("/api/scenarios/{name}/run", api_run, methods=["POST"]),
    Route("/api/ledger", api_ledger),
    Route("/api/audit", api_audit),
    Route("/api/services", api_services),
    Route("/api/reset", api_reset, methods=["POST"]),
]


def create_app() -> Starlette:
    configure("web")
    ledger.initialize()
    return Starlette(routes=routes)


app = create_app()


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.bind("0.0.0.0"), port=settings.web_port, log_level="warning")


_LOCKED_HTML = """<!doctype html><meta charset="utf-8"><title>Refund demo</title>
<body style="background:#0d1117;color:#e6edf3;font:16px system-ui;padding:3rem">
<h1>Access key required</h1>
<p>This deployment sets <code>WEB_ACCESS_KEY</code>. Append <code>?k=&lt;key&gt;</code>.</p>
</body>"""


# Single self-contained page: no CDN, no build step, no network at render time.
# The stage requirement is that this works with the Wi-Fi off.
PAGE = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Who Can Call This MCP Tool?</title>
<style>
  :root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;--dim:#8b949e;
        --ok:#3fb950;--bad:#f85149;--warn:#d29922;--accent:#58a6ff}
  *{box-sizing:border-box}
  /* Sized for a projector at the back of a room, not a laptop at arm's length.
     Everything below is in rem, so the A-/A+ control scales the whole page. */
  html{font-size:20px}
  body{margin:0;background:var(--bg);color:var(--fg);
       font:1rem/1.55 ui-monospace,SFMono-Regular,Consolas,monospace}
  header{padding:1.2rem 1.5rem;border-bottom:1px solid var(--line);
         display:flex;flex-wrap:wrap;gap:1rem;align-items:baseline}
  h1{font-size:1.9rem;margin:0;font-weight:600}
  .sub{color:var(--dim);font-size:1rem}
  main{display:grid;grid-template-columns:minmax(420px,1fr) minmax(420px,1fr);
       gap:1.2rem;padding:1.2rem 1.5rem}
  @media(max-width:1100px){main{grid-template-columns:1fr}}
  section{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:1rem}
  h2{font-size:1.15rem;margin:0 0 .8rem;color:var(--accent);
     text-transform:uppercase;letter-spacing:.06em}
  button{font:inherit;font-size:1rem;background:#21262d;color:var(--fg);
         border:1px solid var(--line);border-radius:6px;padding:.45rem .8rem;cursor:pointer}
  button:hover:not(:disabled){border-color:var(--accent)}
  button:disabled{opacity:.5;cursor:wait}
  .zoom{display:flex;gap:.3rem;margin-left:auto;align-items:center}
  .zoom button{padding:.2rem .6rem;font-size:1rem;line-height:1}
  .row{display:flex;justify-content:space-between;align-items:center;gap:.6rem;
       padding:.5rem 0;border-bottom:1px solid #21262d}
  .row:last-child{border-bottom:0}
  .name{font-size:1.05rem}
  .badge{font-size:.85rem;padding:.15rem .5rem;border-radius:4px;border:1px solid}
  .pass{color:var(--ok);border-color:var(--ok)}
  .fail{color:var(--bad);border-color:var(--bad)}
  .digest{font-size:2.1rem;color:var(--warn);word-break:break-all;line-height:1.25}
  .changed{color:var(--bad)} .same{color:var(--ok)}
  pre{background:#0b0f14;border:1px solid var(--line);border-radius:6px;
      padding:.8rem;overflow:auto;max-height:24rem;font-size:.95rem;
      line-height:1.5;margin:0}
  .toolbar{display:flex;gap:.5rem;margin-bottom:.8rem;flex-wrap:wrap;align-items:center}
  .kv{display:grid;grid-template-columns:auto 1fr;gap:.35rem .9rem;font-size:1rem}
  .kv dt{color:var(--dim)} .kv dd{margin:0;word-break:break-all}
  .note{color:var(--dim);font-size:.9rem;margin-top:.8rem;line-height:1.5}
  /* Where this page is running. Loud on purpose: every service URL on this
     page is loopback in every environment, so this badge is the only thing
     distinguishing a cluster from a laptop at the back of a room. */
  .env{font-size:.95rem;padding:.2rem .7rem;border-radius:5px;border:1px solid var(--accent);
       color:var(--accent);white-space:nowrap}
  .env.k8s{border-color:var(--ok);color:var(--ok)}
  .env .where{color:var(--dim);margin-left:.45rem;font-size:.85rem}
  .dot{display:inline-block;width:.55rem;height:.55rem;border-radius:50%;margin-right:.4rem}
  .up{background:var(--ok)} .down{background:var(--bad)}
  /* Expanders. A room reads this page without narration as often as with it,
     so every scenario can explain itself -- but collapsed by default, because
     a wall of prose behind the presenter is worse than none. */
  details{border-bottom:1px solid #21262d}
  details:last-child{border-bottom:0}
  summary{display:flex;align-items:center;gap:.6rem;padding:.55rem 0;cursor:pointer;
          list-style:none}
  summary::-webkit-details-marker{display:none}
  .chev{color:var(--dim);font-size:.8rem;transition:transform .12s;width:.8rem;flex:none}
  details[open] .chev{transform:rotate(90deg)}
  summary:hover .name{color:var(--accent)}
  .spacer{flex:1}
  .brief{padding:.2rem 0 1rem 1.4rem;font-size:.95rem;line-height:1.6}
  .brief dt{color:var(--accent);font-size:.8rem;text-transform:uppercase;
            letter-spacing:.06em;margin-top:.7rem}
  .brief dt:first-child{margin-top:0}
  .brief dd{margin:.15rem 0 0;color:#c9d1d9}
  .brief code{background:#0b0f14;border:1px solid var(--line);border-radius:4px;
              padding:.05rem .3rem;font-size:.88rem;color:var(--warn);white-space:nowrap}
  .brief em{color:var(--fg);font-style:italic}
  .brief strong{color:var(--fg)}
  .about{background:var(--panel);border:1px solid var(--line);border-radius:8px;
         padding:.6rem 1rem;grid-column:1/-1;border-bottom:1px solid var(--line)}
  .about > summary{padding:.5rem 0}
  .about .name{font-size:1.15rem;color:var(--accent);text-transform:uppercase;
               letter-spacing:.06em}
  .about .brief{max-width:80ch}
</style>
<header>
  <h1>Who Can Call This MCP Tool?</h1>
  <span class="sub">OAuth &middot; resource binding &middot; runtime policy &mdash; synthetic data only</span>
  <span class="zoom">
    <span class="env" id="env" title="Where this page is running">&hellip;</span>
    <span class="sub" id="svc" style="margin-right:.6rem"></span>
    <button onclick="zoom(-2)" title="Smaller text">A&minus;</button>
    <button onclick="zoom(2)" title="Larger text">A+</button>
    <button onclick="zoom(0)" title="Reset text size">Reset</button>
  </span>
</header>
<main>
  <!--ABOUT-->
  <section>
    <h2>Scenarios</h2>
    <div class="toolbar">
      <button onclick="runAll()" id="runall">Run all 14</button>
      <button onclick="refreshLedger()">Refresh ledger</button>
      <button onclick="toggleAll()" id="expandall">Expand all</button>
    </div>
    <div id="list"></div>
    <p class="note">Every verdict here is produced by the MCP server, the upstream API, or the
    policy engine. This page reports decisions; it never makes one.</p>
  </section>
  <section>
    <h2>Ledger fingerprint</h2>
    <div class="digest" id="digest">&hellip;</div>
    <div class="note" id="ledgermeta"></div>
    <h2 style="margin-top:1.2rem">Last result</h2>
    <dl class="kv" id="detail"><dt>&mdash;</dt><dd>run a scenario</dd></dl>
    <p class="note" id="loopback"></p>
  </section>
  <section style="grid-column:1/-1">
    <h2>Audit trail</h2>
    <div class="toolbar">
      <button onclick="loadAudit(5)">Last 5</button>
      <button onclick="loadAudit(20)">Last 20</button>
    </div>
    <pre id="audit">no records loaded</pre>
    <p class="note">Records contain validated claims only, a pseudonymous subject, and no tokens,
    codes, verifiers, or customer content. This is a JSONL file &mdash; it is evidence, not
    tamper-evident storage.</p>
  </section>
</main>
<script>
const KEY = new URLSearchParams(location.search).get('k');
const q = p => KEY ? (p + (p.includes('?') ? '&' : '?') + 'k=' + encodeURIComponent(KEY)) : p;
const $ = id => document.getElementById(id);
let scenarios = [];

const esc = t => (t||'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

// Room sizes vary and projectors lie. Let the presenter fix it from the stage
// rather than discovering the back row cannot read the digest.
const ZOOM_MIN = 14, ZOOM_MAX = 40, ZOOM_DEFAULT = 20;
function applyZoom(px){
  document.documentElement.style.fontSize = px + 'px';
  try{ localStorage.setItem('demoZoom', px); }catch(e){}
}
function zoom(delta){
  if(delta === 0) return applyZoom(ZOOM_DEFAULT);
  const now = parseFloat(document.documentElement.style.fontSize) || ZOOM_DEFAULT;
  applyZoom(Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, now + delta)));
}
(function restoreZoom(){
  let saved = null;
  try{ saved = localStorage.getItem('demoZoom'); }catch(e){}
  applyZoom(saved ? parseFloat(saved) : ZOOM_DEFAULT);
})();
document.addEventListener('keydown', e => {
  if(!e.ctrlKey && !e.metaKey && !e.altKey && e.target.tagName !== 'INPUT'){
    if(e.key === '+' || e.key === '=') zoom(2);
    else if(e.key === '-' || e.key === '_') zoom(-2);
    else if(e.key === '0') zoom(0);
  }
});

async function boot(){
  scenarios = await (await fetch(q('/api/scenarios'))).json();
  $('list').innerHTML = scenarios.map(s => `
    <details id="d-${esc(s.name)}">
      <summary>
        <span class="chev">&#9656;</span>
        <span class="name">${esc(s.name)}</span>
        <span class="spacer"></span>
        <span id="b-${esc(s.name)}"></span>
        <button id="r-${esc(s.name)}"
                onclick="event.preventDefault();event.stopPropagation();run('${esc(s.name)}')">Run</button>
      </summary>
      <dl class="brief">
        <dt>Sends</dt><dd>${s.sends}</dd>
        <dt>Expects</dt><dd>${s.expects}</dd>
        <dt>Why it matters</dt><dd>${s.why}</dd>
        <dt>Claim under test</dt><dd>${esc(s.claim)}</dd>
      </dl>
    </details>`).join('');
  refreshLedger(); services();
}

// The briefings are authored server-side and contain intentional markup, so
// they are inserted as HTML. Everything that originates from a scenario *run*
// stays escaped -- see show().
function toggleAll(){
  const b = $('expandall');
  const open = b.textContent === 'Expand all';
  scenarios.forEach(s => { $('d-'+s.name).open = open; });
  b.textContent = open ? 'Collapse all' : 'Expand all';
}

async function runOne(name){
  // Assumes the caller already owns the busy flag.
  const btn = $('r-'+name); const label = btn.textContent; btn.textContent = '...';
  try{
    const r = await (await fetch(q(`/api/scenarios/${name}/run`), {method:'POST'})).json();
    $('b-'+name).innerHTML =
      `<span class="badge ${r.passed?'pass':'fail'}">${r.passed?'PASS':'FAIL'}</span>`;
    show(r);
    // Awaited, not fired and forgotten: the digest on screen must be current
    // before the buttons come back, or the next click is made against a stale
    // reading of the ledger.
    await refreshLedger();
  } finally { btn.textContent = label; }
}

// One run at a time, enforced here as well as on the server. The server already
// serializes with a lock, but a queued click still executes when its turn comes
// -- so three fast clicks were three real runs. Dropping them at the source is
// what makes the page agree with what the server is doing.
let busy = false;
function setBusy(on){
  busy = on;
  scenarios.forEach(s => { const b = $('r-'+s.name); if (b) b.disabled = on; });
  $('runall').disabled = on;
}

async function run(name){
  if (busy) return;
  setBusy(true);
  try { await runOne(name); } finally { setBusy(false); }
}

async function runAll(){
  if (busy) return;
  setBusy(true);
  const b = $('runall');
  try { for (const s of scenarios){ b.textContent = 'Running ' + s.name; await runOne(s.name); } }
  finally { b.textContent = 'Run all 14'; setBusy(false); }
}

function show(r){
  const rows = [
    ['scenario', r.name], ['claim', r.claim], ['result', r.detail],
    ['ledger', r.ledger_changed
        ? `<span class="changed">CHANGED ${esc(r.ledger_before)} &rarr; ${esc(r.ledger_after)}</span>`
        : `<span class="same">unchanged ${esc(r.ledger_before||'')}</span>`],
  ].concat(Object.entries(r.evidence||{}));
  $('detail').innerHTML = rows.map(([k,v]) =>
    `<dt>${esc(k)}</dt><dd>${k==='ledger'?v:esc(String(v))}</dd>`).join('');
}

async function refreshLedger(){
  const d = await (await fetch(q('/api/ledger'))).json();
  $('digest').textContent = d.fingerprint.digest.slice(0,12);
  $('ledgermeta').textContent =
    `${d.orders.length} orders / ${d.refunds.length} refunds / full digest ${d.fingerprint.digest}`;
}

async function loadAudit(n){
  const d = await (await fetch(q('/api/audit?last='+n))).json();
  $('audit').textContent = d.records.length
    ? d.records.map(r => JSON.stringify(r, null, 2)).join('\\n\\n')
    : 'no audit records yet';
}

async function services(){
  try{
    const d = await (await fetch(q('/api/services'))).json();
    $('svc').innerHTML = Object.entries(d.services).map(([n,v]) =>
      `<span class="dot ${v.healthy?'up':'down'}"></span>${esc(n)}`).join('&nbsp;&nbsp;');
    const r = d.runtime || {};
    const badge = $('env');
    badge.className = 'env' + (r.platform === 'kubernetes' ? ' k8s' : '');
    badge.title = r.full || '';
    badge.innerHTML = esc(r.label || '') +
      (r.detail ? `<span class="where">${esc(r.detail)}</span>` : '');
    const note = $('loopback');
    if (note && r.loopback_note) note.textContent = r.loopback_note;
  }catch(e){ $('svc').textContent = 'service health unavailable'; }
}
boot(); setInterval(services, 10000);
</script>
</html>"""


if __name__ == "__main__":
    main()
