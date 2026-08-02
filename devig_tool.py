#!/usr/bin/env python3
"""
De-vig calculator — strips the bookmaker's built-in edge (vig/juice) out of
American odds to find the market's TRUE implied probability, then compares
it against your own model's probability to see if there's an actual edge.

Why this matters: both sides of a two-way market are priced slightly worse
than fair (that's how books make money) — implied probabilities from raw
odds always sum to MORE than 100%. The excess is the vig. Stripping it out
(normalizing so the two sides sum to exactly 100%) gives you the market's
real, fair-value probability — which is what your model's own probability
should be compared against, not the raw odds.
"""


def american_to_implied_prob(odds):
    """Converts American odds (+150 or -200 style) to raw implied probability."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return -odds / (-odds + 100)


def implied_prob_to_american(prob):
    """Converts a probability back to the FAIR American odds for that probability
    (no vig — useful for seeing what odds *should* be given a probability)."""
    if prob >= 0.5:
        return -round(100 * prob / (1 - prob))
    else:
        return round(100 * (1 - prob) / prob)


def devig_two_way(odds_a, odds_b):
    """
    Given both sides of a two-way market, returns (true_prob_a, true_prob_b,
    vig_pct) — the vig removed, proportionally normalized so both sides sum
    to exactly 100%. This is the simplest standard de-vig method
    (proportional/multiplicative) — more sophisticated methods exist (e.g.
    power method, Shin's method) but this is a solid, honest starting point.
    """
    raw_a = american_to_implied_prob(odds_a)
    raw_b = american_to_implied_prob(odds_b)
    overround = raw_a + raw_b
    vig_pct = (overround - 1) * 100
    true_a = raw_a / overround
    true_b = raw_b / overround
    return true_a, true_b, vig_pct


def edge(our_prob, market_true_prob):
    """Our probability minus the market's true (de-vigged) probability, in
    percentage points. Positive = we think the market is underpricing this
    side (a real edge, if our probability is actually right)."""
    return (our_prob - market_true_prob) * 100


def analyze_market(label_a, odds_a, label_b, odds_b, our_prob_a=None):
    true_a, true_b, vig_pct = devig_two_way(odds_a, odds_b)
    raw_a = american_to_implied_prob(odds_a)
    raw_b = american_to_implied_prob(odds_b)

    print(f"\n=== {label_a} ({odds_a:+d}) vs {label_b} ({odds_b:+d}) ===")
    print(f"Raw implied probabilities: {label_a} {raw_a:.1%}  |  {label_b} {raw_b:.1%}  (sum: {raw_a+raw_b:.1%})")
    print(f"Vig/overround: {vig_pct:.2f} percentage points")
    print(f"De-vigged (TRUE market) probabilities: {label_a} {true_a:.1%}  |  {label_b} {true_b:.1%}")
    print(f"Fair odds equivalent: {label_a} {implied_prob_to_american(true_a):+d}  |  {label_b} {implied_prob_to_american(true_b):+d}")

    if our_prob_a is not None:
        e = edge(our_prob_a, true_a)
        print(f"\nYour model's probability for {label_a}: {our_prob_a:.1%}")
        print(f"Edge vs true market probability: {e:+.1f} percentage points")
        if e > 3:
            print(f"-> Your model thinks {label_a} is UNDERVALUED by the market (potential edge, IF your model is right)")
        elif e < -3:
            print(f"-> Your model thinks {label_a} is OVERVALUED by the market (potential edge on {label_b}, IF your model is right)")
        else:
            print("-> Your model roughly agrees with the market — no meaningful edge either way")


def check_prop_edge(line, our_prob_over, over_odds, under_odds):
    """
    Purpose-built wrapper around devig_two_way/edge for an over/under PROP
    (as opposed to a two-team moneyline) — this is what nba_props_model.py
    and mlb_props_model.py call directly after computing their own
    probability, so you don't have to re-type numbers into a separate tool.
    Returns (true_prob_over, edge_pct) and prints the same breakdown as
    analyze_market.
    """
    true_over, true_under, vig_pct = devig_two_way(over_odds, under_odds)
    e = edge(our_prob_over, true_over)

    print(f"\n--- Market check: over/under {line} ---")
    print(f"Market odds: Over {over_odds:+d}  |  Under {under_odds:+d}")
    print(f"Vig/overround: {vig_pct:.2f} percentage points")
    print(f"De-vigged TRUE market probability of Over: {true_over:.1%}")
    print(f"Your model's probability of Over: {our_prob_over:.1%}")
    print(f"Edge vs true market: {e:+.1f} percentage points")
    if e > 3:
        print("-> Your model thinks OVER is undervalued by the market (potential edge, IF your model is right)")
    elif e < -3:
        print("-> Your model thinks UNDER is the better side (market overvalues Over, IF your model is right)")
    else:
        print("-> Your model roughly agrees with the market — no meaningful edge either way")

    return true_over, e


def prompt_market_check(line, our_prob_over, already_confirmed=False):
    """
    Optional interactive prompt to be called from the end of any prop
    analysis (NBA/MLB models) — asks if the user wants to check this specific
    line against real market odds, and if so, does it right there instead of
    requiring a separate trip to devig_tool.py.

    already_confirmed=True skips the y/n gate (use when the caller already
    asked "do you want to check odds" itself, to avoid asking twice).
    """
    if not already_confirmed:
        has_odds = input(f"\nCheck this {line} line against real market odds? [y/n]: ").strip().lower()
        if has_odds != "y":
            return
    over_odds = int(input("Market 'Over' American odds (e.g. -115): ").strip())
    under_odds = int(input("Market 'Under' American odds (e.g. -105): ").strip())
    check_prop_edge(line, our_prob_over, over_odds, under_odds)


def interactive_devig():
    print("\n--- De-vig a market ---")
    label_a = input("Side A name (e.g. team/player): ").strip()
    odds_a = int(input(f"{label_a}'s American odds (e.g. -140 or +120): ").strip())
    label_b = input("Side B name: ").strip()
    odds_b = int(input(f"{label_b}'s American odds: ").strip())

    has_model = input(f"Do you have your own model probability for {label_a}? [y/n]: ").strip().lower()
    our_prob_a = None
    if has_model == "y":
        raw = input(f"Your model's probability for {label_a} (0-1 or %): ").strip().rstrip("%")
        our_prob_a = float(raw)
        if our_prob_a > 1:
            our_prob_a /= 100

    analyze_market(label_a, odds_a, label_b, odds_b, our_prob_a=our_prob_a)


if __name__ == "__main__":
    print("=== De-Vig Calculator ===")
    print("1) Run the verified demo (Tigers vs Orioles, real market odds)")
    print("2) De-vig a new market")
    choice = input("Choose 1 or 2: ").strip()

    if choice == "2":
        interactive_devig()
        raise SystemExit

    # Real market odds, verified 2026-07-28 (Tigers vs Orioles, multiple
    # sportsbooks agreed closely: -140/-142/-144 and +119/+120)
    analyze_market("Tigers", -140, "Orioles", 120, our_prob_a=None)

    print("\n--- Same market, WITH a hypothetical model probability for comparison ---")
    analyze_market("Tigers", -140, "Orioles", 120, our_prob_a=0.62)
