#!/usr/bin/env python3
"""
PrizePicks EV calculator — codifies the by-hand math from Match-Notes.md.

For a given set of legs (each with your own probability estimate), computes:
  - Power Play: probability ALL legs hit, vs the real breakeven for that
    payout multiplier.
  - Flex Play: full win/partial-win distribution using each leg's own
    probability, vs the Flex payout curve.

Logs the result into Match-Notes.md in the same format used throughout this
project, with blank result fields to fill in after the games finish.
"""

import datetime
from pathlib import Path

from kelly_tool import kelly_fraction_binary, kelly_fraction_general, print_recommendation

VAULT_PROJECT_DIR = Path(__file__).resolve().parent
MATCH_NOTES = VAULT_PROJECT_DIR / "Match-Notes.md"

# Power Play: picks -> multiplier (all legs must hit)
POWER_MULTIPLIERS = {
    2: 3.0,
    3: 5.0,
    4: 10.0,
    5: 20.0,
    6: 37.5,
}

# Flex Play: picks -> {correct_count: multiplier}, missing keys pay 0
FLEX_MULTIPLIERS = {
    3: {3: 3.0, 2: 1.0},
    4: {4: 6.0, 3: 1.5},
    5: {5: 10.0, 4: 2.0, 3: 0.4},
    6: {6: 25.0, 5: 2.0, 4: 0.4},
}


def prompt_float(prompt, lo=0.0, hi=1.0):
    while True:
        raw = input(prompt).strip().rstrip("%")
        try:
            val = float(raw)
        except ValueError:
            print("  Enter a number (e.g. 0.62 or 62).")
            continue
        if val > 1:
            val /= 100.0
        if lo <= val <= hi:
            return val
        print(f"  Must be between {lo} and {hi} (or a %).")


def exact_count_distribution(probs):
    """dp[k] = probability of exactly k legs hitting, given each leg's own p."""
    dp = [1.0]
    for p in probs:
        new_dp = [0.0] * (len(dp) + 1)
        for k, prob_k in enumerate(dp):
            new_dp[k] += prob_k * (1 - p)
            new_dp[k + 1] += prob_k * p
        dp = new_dp
    return dp  # dp[k] for k = 0..n


def evaluate_power(probs, multiplier):
    combined = 1.0
    for p in probs:
        combined *= p
    breakeven = 1.0 / multiplier
    ev_per_dollar = combined * multiplier - 1.0
    return combined, breakeven, ev_per_dollar


def evaluate_flex(probs, payout_table):
    dp = exact_count_distribution(probs)
    n = len(probs)
    expected_return = 0.0
    breakdown = []
    for k in range(n, -1, -1):
        mult = payout_table.get(k, 0.0)
        contribution = dp[k] * mult
        expected_return += contribution
        if mult > 0:
            breakdown.append((k, dp[k], mult))
    ev_per_dollar = expected_return - 1.0
    return breakdown, ev_per_dollar


def main():
    print("=== PrizePicks EV Calculator ===\n")

    n = int(input("How many legs in this entry? ").strip())

    mode = ""
    while mode not in ("power", "flex"):
        mode = input("Power or Flex play? [power/flex]: ").strip().lower()

    legs = []
    probs = []
    print("\nEnter each leg (label, then your probability estimate):")
    for i in range(1, n + 1):
        label = input(f"  Leg {i} label (e.g. 'Ty France over 1.5 H+R+RBI'): ").strip()
        p = prompt_float(f"  Leg {i} probability estimate (0-1 or %): ")
        legs.append(label)
        probs.append(p)

    print("\n--- Per-leg summary ---")
    for label, p in zip(legs, probs):
        print(f"  {label}: {p:.0%}")

    print("\n--- Result ---")
    if mode == "power":
        multiplier = POWER_MULTIPLIERS.get(n)
        if multiplier is None:
            print(f"No standard Power multiplier on file for {n} picks — enter it manually.")
            multiplier = float(input("Multiplier: ").strip())
        combined, breakeven, ev = evaluate_power(probs, multiplier)
        print(f"Multiplier: {multiplier}x")
        print(f"Combined hit probability (all legs): {combined:.2%}")
        print(f"Breakeven probability needed: {breakeven:.2%}")
        print(f"EV per $1 staked: {ev:+.3f}  ({'+EV' if ev > 0 else '-EV'})")
        if ev > 0:
            margin = combined / breakeven - 1
            print(f"Margin above breakeven: {margin:+.1%} (thin if under ~20%)")
    else:
        payout_table = FLEX_MULTIPLIERS.get(n)
        if payout_table is None:
            print(f"No standard Flex table on file for {n} picks.")
            return
        breakdown, ev = evaluate_flex(probs, payout_table)
        print("Correct legs -> probability -> payout contribution:")
        for k, dp_k, mult in breakdown:
            print(f"  {k}/{n} correct: {dp_k:.2%} chance, pays {mult}x")
        print(f"Expected return per $1 staked: {ev + 1:.3f}")
        print(f"EV per $1 staked: {ev:+.3f}  ({'+EV' if ev > 0 else '-EV'})")

    if ev > 0:
        want_kelly = input("\nGet a Kelly-criterion stake size recommendation? [y/n]: ").strip().lower()
        if want_kelly == "y":
            bankroll = float(input("Your total bankroll ($): ").strip())
            fractional_raw = input("Kelly fraction to use (e.g. 0.25 for quarter-Kelly) [0.25]: ").strip()
            fractional = float(fractional_raw) if fractional_raw else 0.25
            if mode == "power":
                f = kelly_fraction_binary(combined, multiplier)
            else:
                dp = exact_count_distribution(probs)
                f = kelly_fraction_general(dp, payout_table)
            print_recommendation(bankroll, f, fractional=fractional)

    log_it = input("\nLog this entry to Match-Notes.md? [y/n]: ").strip().lower()
    if log_it == "y":
        append_to_vault(mode, n, legs, probs, multiplier if mode == "power" else None)
        print(f"Logged to {MATCH_NOTES}")


def append_to_vault(mode, n, legs, probs, multiplier):
    today = datetime.date.today().isoformat()
    lines = [f"\n## {today} — EV TOOL: {n}-pick {mode.title()} Play\n"]
    if multiplier:
        lines.append(f"Multiplier: {multiplier}x\n\n")
    lines.append("Legs:\n\n")
    for i, (label, p) in enumerate(zip(legs, probs), 1):
        lines.append(f"{i}. {label} (estimate: {p:.0%})\n")
    lines.append("\n### Result (fill in after games complete)\n\n")
    for i, label in enumerate(legs, 1):
        lines.append(f"- Leg {i} ({label}): \n")
    lines.append("- Overall entry: WON / LOST\n")

    with open(MATCH_NOTES, "a") as f:
        f.writelines(lines)


if __name__ == "__main__":
    main()
