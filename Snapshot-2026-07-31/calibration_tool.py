#!/usr/bin/env python3
"""
Calibration tracker — the missing piece for turning "judgment call" numbers
(elasticity values, situational factor presets) into actually-tested ones.

Every prediction we make (a probability estimate for some prop) gets logged
here with its eventual real outcome. Over time this lets us check: when we
say "65%," does that side actually hit about 65% of the time? If predictions
in the 60-70% bucket only hit 40% of the time, our model is overconfident;
if they hit 85% of the time, it's underconfident. This is what "backtesting"
actually means for a probability model — not just checking win/loss, but
checking whether the STATED CONFIDENCE matches reality.

Two things this computes:

1. Brier score: mean squared error between predicted probability and actual
   outcome (0 or 1). Lower is better. 0 = perfect, 0.25 = what you'd get by
   always guessing 50%, 1.0 = confidently wrong every time. This is the
   standard way to score a probability forecaster (used for weather
   forecasts, election models, etc.) — NOT the same as "win rate."

2. Calibration by bucket: group predictions into probability ranges (50-60%,
   60-70%, etc.) and compare the average predicted probability in each
   bucket to the actual hit rate in that bucket. A well-calibrated model has
   these roughly match; a mismatch tells you which confidence RANGE is off,
   which is more useful than a single overall score.
"""

import csv
import sys
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent / "calibration_log.csv"


def load_log():
    if not LOG_FILE.exists():
        return []
    with open(LOG_FILE, newline="") as f:
        reader = csv.DictReader(f)
        return [
            {
                "date": row["date"],
                "description": row["description"],
                "predicted_prob": float(row["predicted_prob"]),
                "actual_outcome": int(row["actual_outcome"]),
                "notes": row.get("notes", ""),
            }
            for row in reader
        ]


def brier_score(entries):
    if not entries:
        return None
    total = sum((e["predicted_prob"] - e["actual_outcome"]) ** 2 for e in entries)
    return total / len(entries)


def calibration_buckets(entries, bucket_size=0.1):
    buckets = {}
    for e in entries:
        bucket_start = int(e["predicted_prob"] / bucket_size) * bucket_size
        buckets.setdefault(bucket_start, []).append(e)

    results = []
    for start in sorted(buckets):
        bucket_entries = buckets[start]
        avg_predicted = sum(e["predicted_prob"] for e in bucket_entries) / len(bucket_entries)
        actual_hit_rate = sum(e["actual_outcome"] for e in bucket_entries) / len(bucket_entries)
        results.append({
            "range": f"{start:.0%}-{start + bucket_size:.0%}",
            "n": len(bucket_entries),
            "avg_predicted": avg_predicted,
            "actual_hit_rate": actual_hit_rate,
        })
    return results


def append_entry(date, description, predicted_prob, actual_outcome, notes=""):
    file_exists = LOG_FILE.exists()
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "description", "predicted_prob", "actual_outcome", "notes"])
        writer.writerow([date, description, predicted_prob, actual_outcome, notes])


def interactive_add():
    print("\n--- Log a new calibration entry ---")
    date = input("Date (YYYY-MM-DD): ").strip()
    description = input("Description (e.g. 'Player X over 1.5 stat'): ").strip()
    predicted_prob = float(input("Your predicted probability (0-1 or %): ").strip().rstrip("%"))
    if predicted_prob > 1:
        predicted_prob /= 100
    outcome_raw = input("Actual outcome (1=hit, 0=miss): ").strip()
    actual_outcome = int(outcome_raw)
    notes = input("Notes (optional): ").strip()
    append_entry(date, description, predicted_prob, actual_outcome, notes)
    print(f"Logged to {LOG_FILE}")


def print_report():
    entries = load_log()
    if not entries:
        print("No calibration entries logged yet.")
        return

    print(f"=== Calibration Report ({len(entries)} entries) ===\n")

    score = brier_score(entries)
    print(f"Brier score: {score:.3f}")
    print("  (0 = perfect, 0.25 = always guessing 50%, 1.0 = confidently wrong)")
    print()

    print("Calibration by predicted-probability bucket:")
    print(f"{'Range':<12}{'n':<5}{'Avg predicted':<16}{'Actual hit rate':<16}")
    for b in calibration_buckets(entries):
        print(f"{b['range']:<12}{b['n']:<5}{b['avg_predicted']:<16.1%}{b['actual_hit_rate']:<16.1%}")

    print()
    if len(entries) < 20:
        print(f"NOTE: only {len(entries)} entries logged — way too small a sample to draw")
        print("real conclusions yet. This report will get more meaningful as more")
        print("predictions get logged and checked against results over time.")


if __name__ == "__main__":
    print("=== Calibration Tracker ===")
    print("1) View calibration report")
    print("2) Log a new entry")
    choice = input("Choose 1 or 2: ").strip()

    if choice == "2":
        interactive_add()
    else:
        print_report()
