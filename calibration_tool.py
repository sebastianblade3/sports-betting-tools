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
                "actual_outcome": int(row["actual_outcome"]) if row["actual_outcome"] not in ("", None) else None,
                "notes": row.get("notes", ""),
            }
            for row in reader
        ]


def settled_entries(entries):
    """Entries with a known outcome — the only ones a Brier score or
    calibration bucket can meaningfully use."""
    return [e for e in entries if e["actual_outcome"] is not None]


def pending_entries(entries):
    """Entries logged before the outcome was known yet — waiting on
    settle_entry() once the real result is in."""
    return [e for e in entries if e["actual_outcome"] is None]


def brier_score(entries):
    settled = settled_entries(entries)
    if not settled:
        return None
    total = sum((e["predicted_prob"] - e["actual_outcome"]) ** 2 for e in settled)
    return total / len(settled)


def calibration_buckets(entries, bucket_size=0.1):
    buckets = {}
    for e in settled_entries(entries):
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


def append_entry(date, description, predicted_prob, actual_outcome=None, notes=""):
    """actual_outcome=None logs this as a PENDING prediction (outcome not
    known yet) — settle it later with settle_entry() once the result is in."""
    file_exists = LOG_FILE.exists()
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "description", "predicted_prob", "actual_outcome", "notes"])
        outcome_str = "" if actual_outcome is None else str(actual_outcome)
        writer.writerow([date, description, predicted_prob, outcome_str, notes])


def settle_entry(index, actual_outcome):
    """Fills in the real outcome for a previously-logged pending prediction,
    identified by its position in load_log() (0-based), and rewrites the
    log file. Returns the now-settled entry."""
    entries = load_log()
    if index < 0 or index >= len(entries):
        raise IndexError(f"No entry at index {index}")
    entries[index]["actual_outcome"] = actual_outcome
    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "description", "predicted_prob", "actual_outcome", "notes"])
        for e in entries:
            outcome_str = "" if e["actual_outcome"] is None else str(e["actual_outcome"])
            writer.writerow([e["date"], e["description"], e["predicted_prob"], outcome_str, e["notes"]])
    return entries[index]


def interactive_add():
    print("\n--- Log a new calibration entry ---")
    date = input("Date (YYYY-MM-DD): ").strip()
    description = input("Description (e.g. 'Player X over 1.5 stat'): ").strip()
    predicted_prob = float(input("Your predicted probability (0-1 or %): ").strip().rstrip("%"))
    if predicted_prob > 1:
        predicted_prob /= 100
    outcome_raw = input("Actual outcome (1=hit, 0=miss, blank if not known yet): ").strip()
    actual_outcome = int(outcome_raw) if outcome_raw else None
    notes = input("Notes (optional): ").strip()
    append_entry(date, description, predicted_prob, actual_outcome, notes)
    print(f"Logged to {LOG_FILE}")


def interactive_settle():
    entries = load_log()
    pending = pending_entries(entries)
    if not pending:
        print("No pending predictions to settle.")
        return
    print("\n--- Pending predictions ---")
    for i, e in enumerate(entries):
        if e["actual_outcome"] is None:
            print(f"  [{i}] {e['date']}  {e['description']}  (predicted {e['predicted_prob']:.1%})")
    index = int(input("Which one? (enter the number in brackets): ").strip())
    outcome_raw = input("Actual outcome (1=hit, 0=miss): ").strip()
    settle_entry(index, int(outcome_raw))
    print("Settled.")


def print_report():
    entries = load_log()
    if not entries:
        print("No calibration entries logged yet.")
        return

    settled = settled_entries(entries)
    pending = pending_entries(entries)

    print(f"=== Calibration Report ({len(entries)} entries: {len(settled)} settled, {len(pending)} pending) ===\n")

    score = brier_score(entries)
    if score is None:
        print("No settled entries yet — nothing to score.")
    else:
        print(f"Brier score: {score:.3f}")
        print("  (0 = perfect, 0.25 = always guessing 50%, 1.0 = confidently wrong)")
        print()

        print("Calibration by predicted-probability bucket:")
        print(f"{'Range':<12}{'n':<5}{'Avg predicted':<16}{'Actual hit rate':<16}")
        for b in calibration_buckets(entries):
            print(f"{b['range']:<12}{b['n']:<5}{b['avg_predicted']:<16.1%}{b['actual_hit_rate']:<16.1%}")

    if pending:
        print()
        print("Pending predictions (no outcome yet):")
        for i, e in enumerate(entries):
            if e["actual_outcome"] is None:
                print(f"  [{i}] {e['date']}  {e['description']}  (predicted {e['predicted_prob']:.1%})")

    print()
    if len(settled) < 20:
        print(f"NOTE: only {len(settled)} settled entries logged — way too small a sample to draw")
        print("real conclusions yet. This report will get more meaningful as more")
        print("predictions get logged and checked against results over time.")


if __name__ == "__main__":
    print("=== Calibration Tracker ===")
    print("1) View calibration report")
    print("2) Log a new entry")
    print("3) Settle a pending prediction")
    choice = input("Choose 1, 2, or 3: ").strip()

    if choice == "2":
        interactive_add()
    elif choice == "3":
        interactive_settle()
    else:
        print_report()
