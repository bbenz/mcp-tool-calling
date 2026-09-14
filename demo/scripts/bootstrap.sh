#!/usr/bin/env bash
# Create the virtual environment and install pinned dependencies.
set -euo pipefail
DEMO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DEMO"

PYTHON="${PYTHON:-python3}"
echo "using $("$PYTHON" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
[ -d .venv ] || "$PYTHON" -m venv .venv
./.venv/bin/python -m pip install --quiet --upgrade pip
./.venv/bin/python -m pip install --quiet -r requirements.txt
./.venv/bin/python -m pip install --quiet -e .
[ -f .env ] || { cp .env.example .env; echo "created .env from .env.example"; }
./.venv/bin/python -c "from refund_demo import ledger; ledger.initialize(reset=True); print('ledger ready')"
echo "bootstrap complete - next: ./scripts/start-all.sh"
