#!/bin/bash
# Double-click launcher for the sports betting tools.
cd "$(dirname "$0")"

while true; do
  echo ""
  echo "=== Sports Betting Tools ==="
  echo "1) EV / Parlay Calculator"
  echo "2) NBA/WNBA Points Prop Model"
  echo "3) Quit"
  echo ""
  read -p "Choose 1, 2, or 3: " choice

  case "$choice" in
    1) python3 ev_tool.py ;;
    2) python3 nba_props_model.py ;;
    3) exit 0 ;;
    *) echo "Please enter 1, 2, or 3." ;;
  esac
done
