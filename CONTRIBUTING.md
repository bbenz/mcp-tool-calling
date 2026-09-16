# Contributing

Thanks for looking. This repository is the demo behind a conference talk, which
shapes what is likely to be accepted.

## What this project is optimised for

Every part of this demo has to be explainable from a stage in about 25 minutes,
and has to survive being run live in front of a room. That means the bar for a
change is not "is this better code" but **"does this make the demo clearer, or
more honest, without making it more fragile."**

Most welcome:

- A scenario that does not prove what it claims to prove.
- A control that can be bypassed — see [SECURITY.md](SECURITY.md).
- Documentation that disagrees with the code. The code wins; the docs get fixed.
- Making it run somewhere it currently does not (a shell, an OS, a Python
  version), without adding a dependency.

Likely to be declined:

- New features, new scenarios, or new services. Fourteen scenarios already
  overfill the slot.
- Swapping a working dependency for a nicer one. The web layer is Starlette
  rather than FastAPI for a documented reason, and that trade-off is settled.
- Anything that needs network access at demo time. The laptop path must run
  fully offline.

If you are unsure, open an issue before writing code.

## Getting set up

Python 3.12 is required. From the repository root:

```powershell
cd demo
.\scripts\bootstrap.ps1
```

```bash
cd demo
./scripts/bootstrap.sh
```

This creates `demo/.venv`, installs the project in editable mode, and seeds
`.env` from `.env.example`. It is safe to re-run.

Two things that cost people time, both covered in [SETUP.md](docs/SETUP.md):
a bare `python` on Windows may be the Microsoft Store stub, so the docs always
use the explicit interpreter path; and WSL needs its own bootstrap, because a
venv built on Windows contains Windows binaries.

## Before you open a pull request

The fast gate, which needs nothing running:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The full pre-flight, which starts from healthy services and also runs all 14
scenarios end to end:

```powershell
.\scripts\start-all.ps1
.\scripts\check.ps1
```

Both have `.sh` twins. A non-zero exit from `check` means the demo is not
presentable, which is the standard being held to here.

If you touched documentation, confirm no local link is dangling — the docs
cross-reference each other heavily and a moved file breaks several at once.

## Invariants the tests enforce

Some tests exist to stop a specific, previously-made mistake from coming back.
If one of these fails, the test is probably right:

- **Scenario claims may not drift.** Each scenario's stated claim lives in one
  place and is asserted against what the scenario actually does.
- **Windows-only pins need an environment marker.** `pywin32` without
  `; sys_platform == "win32"` makes the container image unbuildable while the
  laptop notices nothing.
- **Compose, Kubernetes, and the Dockerfile must keep describing the same
  demo.** Sixty-three tests fail if they diverge.
- **A reset must not rotate the signing key** while services are running.
- **MCP transport DNS-rebinding protection stays on.** Extend
  `MCP_ALLOWED_HOSTS` instead of disabling it.

## House style

- Tests are named as sentences that state the claim —
  `test_token_for_resource_b_is_rejected_at_resource_a`. A test name should read
  like something you would say out loud.
- Comments explain *why*, not *what*. The code is already the what.
- Documentation is prose, not bullet soup, and says plainly when something is
  unverified. [COMPATIBILITY-RECORD.md](docs/COMPATIBILITY-RECORD.md) keeps a
  "what is verified, and what is not" section for exactly this reason — please
  keep it accurate rather than flattering.
- Denials carry a reason code and a rule ID. A new denial path without both is
  invisible on stage.

## Do not commit

`demo/.env`, anything under `demo/.local/`, signing keys, the ledger, or the
audit log. They are gitignored; please keep it that way. No real tenant IDs,
subscription IDs, endpoints, or keys — the docs use placeholders throughout.

## Adapting it for your own talk

You do not need permission and you do not need a pull request. Fork it, and see
[prompts/](prompts/README.md) — the prompts that generated this repository are
included so it can be re-targeted rather than hand-edited.
