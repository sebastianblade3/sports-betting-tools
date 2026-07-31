#!/bin/bash
# Double-click launcher for the sports betting tools.
cd "$(dirname "$0")"

while true; do
  echo ""
  echo "=== Sports Betting Tools ==="
  echo "1) EV / Parlay Calculator"
  echo "2) NBA/WNBA Points Prop Model"
  echo "3) MLB Props Model (pitcher K's, batter H+R+RBI)"
  echo "4) De-Vig Calculator (find edge vs real market odds)"
  echo "5) Calibration Tracker (how good are our predictions, really?)"
  echo "6) Quit"
  echo ""
  read -p "Choose 1-6: " choice

  case "$choice" in
    1) python3 ev_tool.py ;;
    2) python3 nba_props_model.py ;;
    3) python3 mlb_props_model.py ;;
    4) python3 devig_tool.py ;;
    5) python3 calibration_tool.py ;;
    6) exit 0 ;;
    *) echo "Please enter 1-6." ;;
  esac
done
