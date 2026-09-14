#!/usr/bin/env bash
# Shared setup for the bash operator scripts. Source this, do not execute it.
#
# Resolves DEMO and PY. The venv layout differs by platform -- POSIX puts the
# interpreter in .venv/bin, Windows puts it in .venv/Scripts -- and Git Bash on
# Windows runs these scripts against a Windows venv, so neither path can be
# assumed. Look for both.

DEMO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

resolve_python() {
  local candidate
  for candidate in "$DEMO/.venv/bin/python" "$DEMO/.venv/Scripts/python.exe"; do
    if [ -x "$candidate" ]; then printf '%s' "$candidate"; return 0; fi
  done
  return 1
}

PY="$(resolve_python || true)"

require_venv() {
  if [ -z "$PY" ]; then
    echo "venv missing - run ./scripts/bootstrap.sh first" >&2
    exit 1
  fi
}
