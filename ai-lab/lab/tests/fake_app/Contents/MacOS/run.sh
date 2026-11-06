#!/bin/bash
# Фейк движка для тестов: поведение задаёт FAKE_MODE (win|draw|timeout|crash|hang)
RESULT=""; SEED=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    -aiResult) RESULT="$2"; shift ;;
    -aiSeed) SEED="$2"; shift ;;
  esac
  shift
done
mkdir -p "$HOME/Library/Application Support/GeneralsX"
touch "$HOME/Library/Application Support/GeneralsX/touched"
echo "fake engine mode=${FAKE_MODE:-win}"
case "${FAKE_MODE:-win}" in
  win)     OUT=win;     W0=true;  S2="5, 6"; T=1810.7 ;;
  draw)    OUT=draw;    W0=false; S2="5, 6"; T=900.0 ;;
  timeout) OUT=timeout; W0=false; S2="null, null"; T=60.0 ;;
  crash)   exit 1 ;;
  hang)    python3 -c 'import time; time.sleep(600)' "${FAKE_MARKER:-fake-hang}" & wait; exit 0 ;;
esac
read A B <<< "${S2//,/}"
cat > "$RESULT" <<JSON
{"schema": 1, "seed": $SEED, "map": "m", "outcome": "$OUT", "end_frame": 54321, "game_seconds": $T,
 "final_crc": 2882400001,
 "players": [{"slot": 0, "faction": "FactionGLA", "difficulty": "hard", "won": $W0, "structures_at_start": 1, "structures_at_2min": $A},
             {"slot": 1, "faction": "FactionAmerica", "difficulty": "hard", "won": false, "structures_at_start": 1, "structures_at_2min": $B}]}
JSON
