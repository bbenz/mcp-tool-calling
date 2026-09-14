#!/usr/bin/env bash
# Create the virtual environment and install pinned dependencies.
set -euo pipefail
DEMO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DEMO"

PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" > /dev/null 2>&1 || PYTHON=python
echo "using $("$PYTHON" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
[ -d .venv ] || "$PYTHON" -m venv .venv

# The venv layout differs by platform; Git Bash on Windows gets .venv/Scripts.
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=.venv/Scripts/python.exe; fi

"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -r requirements.txt
"$PY" -m pip install --quiet -e .
[ -f .env ] || { cp .env.example .env; echo "created .env from .env.example"; }
"$PY" -c "from refund_demo import ledger; ledger.initialize(reset=True); print('ledger ready')"
echo "bootstrap complete - next: ./scripts/start-all.sh"
