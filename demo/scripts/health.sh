#!/usr/bin/env bash
# Report health for every demo service.
set -uo pipefail
ok=0
for entry in "devidp 8800" "mcp-a 8801" "mcp-b 8802" "upstream 8803"; do
  set -- $entry
  if curl -fsS "http://localhost:$2/health" > /dev/null 2>&1; then
    printf '  OK    %-9s http://localhost:%s\n' "$1" "$2"
  else
    printf '  DOWN  %-9s http://localhost:%s\n' "$1" "$2"; ok=1
  fi
done
exit $ok
