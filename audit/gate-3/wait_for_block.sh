#!/usr/bin/env bash
# Upgrade the gate 3 bundle's OpenTimestamps proof every 10 minutes (up to about 110 minutes per call) until it is in
# a Bitcoin block, then check it against the block header. Exit 0 = confirmed and checked; exit 2 = still pending.
OTS=/c/Users/joshd/Desktop/Moonshots/tools/ots/.venv/Scripts/ots.exe
PY=/c/Users/joshd/Desktop/Moonshots/tools/ots/.venv/Scripts/python.exe
export PATH="/c/Users/joshd/Desktop/Moonshots/tools/ots/lib:$PATH"
D=/c/Users/joshd/Private/claims/2026-10-03-gate3-exam
F="$D/GATE3-BUNDLE-MANIFEST-SHA256.txt.ots"
for round in $(seq 1 12); do
  "$OTS" upgrade "$F" >/dev/null 2>&1
  if "$OTS" info "$F" 2>/dev/null | grep -q BitcoinBlockHeaderAttestation; then
    echo "round $round $(date -u +%H:%M:%SZ): in a block"
    "$PY" /c/Users/joshd/Desktop/Moonshots/tools/ots/check_blocks.py "$D" "$D" 2>&1 | tail -6
    exit 0
  fi
  echo "round $round $(date -u +%H:%M:%SZ): pending"
  [ "$round" -lt 12 ] && sleep 540
done
exit 2
