#!/usr/bin/env python3
"""
Bankroll/ROI tracker — the financial companion to calibration_tool.py.

calibration_tool.py answers "were our stated probabilities actually
accurate?" This tool answers a different question: "how much money have we
actually won or lost, and what's our real return on investment?" You can
have a well-calibrated model (probabilities match reality) and still lose
money overall if stakes weren't sized sensibly, or vice versa — these are
genuinely separate things worth tracking separately.
"""

import csv
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent / "bankroll_log.csv"


def load_log():
    if not LOG_FILE.exists():
        return []
    with open(LOG_FILE, newline="") as f:
        reader = csv.DictReader(f)
        return [
            {
                "date": row["date"],
                "description": row["description"],
                "stake": float(row["stake"]),
                "multiplier": float(row["multiplier"]),
                "outcome": row["outcome"],
                "payout": float(row["payout"]),
                "profit": float(row["profit"]),
            }
            for row in reader
        ]


def compute_bet(stake, multiplier, outcome):
    """outcome: 'won' or 'lost'. Returns (payout, profit)."""
    if outcome == "won":
        payout = stake * multiplier
    else:
        payout = 0.0
    profit = payout - stake
    return payout, profit


def append_bet(date, description, stake, multiplier, outcome):
    payout, profit = compute_bet(stake, multiplier, outcome)
    file_exists = LOG_FILE.exists() and LOG_FILE.stat().st_size > 0
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "description", "stake", "multiplier", "outcome", "payout", "profit"])
        writer.writerow([date, description, stake, multiplier, outcome, f"{payout:.2f}", f"{profit:.2f}"])
    return payout, profit


def interactive_add():
    print("\n--- Log a new bet result ---")
    date = input("Date (YYYY-MM-DD): ").strip()
    description = input("Description (e.g. '6-pick Power Play'): ").strip()
    stake = float(input("Stake ($): ").strip())
    multiplier = float(input("Payout multiplier if it won (e.g. 5.0 for 5x): ").strip())
    outcome = ""
    while outcome not in ("won", "lost"):
        outcome = input("Outcome [won/lost]: ").strip().lower()
    payout, profit = append_bet(date, description, stake, multiplier, outcome)
    print(f"Payout: ${payout:.2f}  |  Profit: ${profit:+.2f}")
    print(f"Logged to {LOG_FILE}")


def print_report():
    entries = load_log()
    if not entries:
        print("No bets logged yet.")
        return

    total_staked = sum(e["stake"] for e in entries)
    total_payout = sum(e["payout"] for e in entries)
    net_profit = total_payout - total_staked
    roi_pct = (net_profit / total_staked * 100) if total_staked else 0.0
    wins = sum(1 for e in entries if e["outcome"] == "won")
    win_rate = wins / len(entries)

    print(f"=== Bankroll Report ({len(entries)} bets logged) ===\n")
    print(f"Total staked: ${total_staked:,.2f}")
    print(f"Total returned: ${total_payout:,.2f}")
    print(f"Net profit/loss: ${net_profit:+,.2f}")
    print(f"ROI: {roi_pct:+.1f}%")
    print(f"Win rate: {wins}/{len(entries)} ({win_rate:.1%})")
    print()

    print("Running cumulative profit over time:")
    running = 0.0
    for e in entries:
        running += e["profit"]
        marker = "+" if e["profit"] >= 0 else "-"
        print(f"  {e['date']}  {e['description']:<40s} {marker}${abs(e['profit']):>8.2f}  (running: ${running:+,.2f})")

    if len(entries) < 10:
        print(f"\nNOTE: only {len(entries)} bets logged — too small a sample to draw")
        print("real conclusions about long-run ROI yet.")


if __name__ == "__main__":
    print("=== Bankroll / ROI Tracker ===")
    print("1) View report")
    print("2) Log a new bet result")
    choice = input("Choose 1 or 2: ").strip()

    if choice == "2":
        interactive_add()
    else:
        print_report()
