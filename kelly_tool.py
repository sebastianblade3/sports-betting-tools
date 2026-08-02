#!/usr/bin/env python3
"""
Kelly criterion bet sizing — given a real edge (from ev_tool.py) and your
bankroll, recommends how much to actually stake. This was part of the
original project roadmap (Phase 2, discussed at the very start) and never
got built until now.

Core idea: betting too much on a real edge is just as harmful long-run as
not betting at all — you can go broke on a string of bad luck even with a
positive-EV strategy if you bet too large a fraction of your bankroll each
time. The Kelly criterion is the stake size that maximizes long-run
GROWTH RATE of your bankroll (technically: maximizes expected log wealth),
not just expected value — which is why it's the right tool here, not just
"bet proportional to your edge."

Two cases, because they're mathematically different:

1. POWER PLAY (binary win/lose everything): closed-form formula.
2. FLEX PLAY (multiple partial-payout outcomes): no simple formula — this
   requires numerically finding the stake fraction that maximizes expected
   log growth across the WHOLE payout distribution, not just win/lose.
"""

import math


def kelly_fraction_binary(prob_win, multiplier):
    """
    Classic Kelly formula for a single win/lose bet (Power Play): win
    `multiplier`x your stake, or lose it all.

    f* = p - (1-p)/(b)   where b = net odds = multiplier - 1

    Returns the fraction of bankroll to stake. Can be negative (meaning:
    this isn't actually a positive-EV bet at all, don't bet) — caller should
    clip to 0 in that case, which recommend_stake does.
    """
    b = multiplier - 1
    q = 1 - prob_win
    return prob_win - q / b


def kelly_fraction_general(dp, payout_table, precision=0.0001):
    """
    Generalized Kelly for a Flex Play (or any multi-outcome bet): numerically
    finds the stake fraction f in [0, 1] that maximizes expected log wealth:

        E[log(1 + f * (payout_k - 1))]  summed over all outcomes k,
        weighted by dp[k] (probability of that outcome)

    dp: probability distribution over outcomes (e.g. from
        stats_engine-style exact_count_distribution — dp[k] = P(k correct))
    payout_table: {k: multiplier} for outcomes that pay out (others pay 0)

    Uses a simple, dependency-free ternary/golden-section-style search since
    the expected-log-wealth function is concave in f (well-behaved, single
    maximum) — no need for a full optimization library for this.
    """
    def expected_log_wealth(f):
        total = 0.0
        for k, prob_k in enumerate(dp):
            payout = payout_table.get(k, 0.0)
            wealth_multiple = 1 - f + f * payout  # what $1 becomes
            if wealth_multiple <= 0:
                return float("-inf")  # betting this much risks total ruin on this outcome
            total += prob_k * math.log(wealth_multiple)
        return total

    lo, hi = 0.0, 1.0
    while hi - lo > precision:
        m1 = lo + (hi - lo) / 3
        m2 = hi - (hi - lo) / 3
        if expected_log_wealth(m1) < expected_log_wealth(m2):
            lo = m1
        else:
            hi = m2
    return (lo + hi) / 2


def recommend_stake(bankroll, kelly_fraction, fractional=0.25):
    """
    Converts a Kelly fraction into an actual dollar recommendation.

    fractional=0.25 (quarter-Kelly) is the DEFAULT, not full Kelly, and
    that's a deliberate, standard practice: full Kelly is mathematically
    "optimal" for long-run growth but extremely high-variance in practice —
    a single bad estimate of your true edge (which you WILL have sometimes,
    since these are estimates, not certainties) can lead to full Kelly
    recommending a dangerously large bet. Most real practitioners use
    1/4 to 1/2 Kelly specifically to trade a little growth rate for a lot
    less variance/risk of ruin.
    """
    f = max(0.0, kelly_fraction)  # never recommend a negative stake
    stake = bankroll * f * fractional
    return stake, f


def print_recommendation(bankroll, kelly_fraction, fractional=0.25):
    stake, f = recommend_stake(bankroll, kelly_fraction, fractional=fractional)
    print(f"\n--- Kelly stake recommendation ---")
    print(f"Full Kelly fraction of bankroll: {f:.1%}")
    if f <= 0:
        print("This is NOT a positive-EV bet by your own numbers — Kelly says stake $0.")
        return
    print(f"Using {fractional:.0%} Kelly (recommended, not full Kelly — see note below): {f * fractional:.1%} of bankroll")
    print(f"On a ${bankroll:,.0f} bankroll: recommended stake = ${stake:,.2f}")
    print()
    print("Why fractional, not full Kelly: full Kelly maximizes long-run growth")
    print("mathematically, but is extremely sensitive to your probability estimate")
    print("being wrong — which it sometimes will be, since these are estimates, not")
    print("certainties. Fractional Kelly trades a bit of growth rate for a lot less")
    print("variance and risk of a bad losing streak wiping out a big chunk of your")
    print("bankroll. 1/4 to 1/2 Kelly is standard practice among real practitioners.")


def interactive_kelly():
    print("=== Kelly Criterion Stake Sizing ===")
    print("1) Power Play (binary win/lose)  2) Flex Play (partial payouts)")
    mode = input("Choose 1 or 2: ").strip()

    bankroll = float(input("Your total bankroll ($): ").strip())
    fractional_raw = input("Kelly fraction to use (e.g. 0.25 for quarter-Kelly) [0.25]: ").strip()
    fractional = float(fractional_raw) if fractional_raw else 0.25

    if mode == "1":
        prob_win = float(input("Combined probability of winning (0-1 or %): ").strip().rstrip("%"))
        if prob_win > 1:
            prob_win /= 100
        multiplier = float(input("Payout multiplier (e.g. 5.0 for 5x): ").strip())
        f = kelly_fraction_binary(prob_win, multiplier)
        print_recommendation(bankroll, f, fractional=fractional)
    else:
        n = int(input("Number of legs: ").strip())
        probs = []
        for i in range(n):
            p = float(input(f"  Leg {i+1} probability (0-1 or %): ").strip().rstrip("%"))
            if p > 1:
                p /= 100
            probs.append(p)

        # Build the exact outcome distribution (same method as ev_tool.py)
        dp = [1.0]
        for p in probs:
            new_dp = [0.0] * (len(dp) + 1)
            for k, prob_k in enumerate(dp):
                new_dp[k] += prob_k * (1 - p)
                new_dp[k + 1] += prob_k * p
            dp = new_dp

        from ev_tool import FLEX_MULTIPLIERS
        payout_table = FLEX_MULTIPLIERS.get(n)
        if payout_table is None:
            print(f"No standard Flex table on file for {n} picks.")
            return

        f = kelly_fraction_general(dp, payout_table)
        print_recommendation(bankroll, f, fractional=fractional)


if __name__ == "__main__":
    interactive_kelly()
