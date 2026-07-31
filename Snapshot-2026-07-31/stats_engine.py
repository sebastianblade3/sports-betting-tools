#!/usr/bin/env python3
"""
Shared statistical engine for player-prop projection models — sport-agnostic.
Used by both nba_props_model.py and mlb_props_model.py so the actual math
(recency weighting, uncertainty, shrinkage, probability) lives in one place
and stays consistent across sports.

Concepts implemented here:

1. Recency-weighted average: recent games matter more than older ones.
2. Standard deviation: how much a player's output swings around their average.
3. Predictive stdev: widens raw stdev to account for uncertainty in our
   ESTIMATE of the mean (shrinks as sample size grows) — the standard
   "prediction interval" adjustment.
4. Normal distribution probability: converts a projection + stdev into an
   exact P(over line) using the standard normal CDF.
5. Shrinkage: blends a small-sample specific value (e.g. head-to-head
   history) toward a more reliable general estimate, weighted by sample size.
"""

import math


def weighted_average(games, half_life=5):
    """
    Recency-weighted average. `games` is most-recent-first.
    `half_life` = games until a past result's weight halves.
    """
    decay = math.log(2) / half_life
    total_weight = 0.0
    total_value = 0.0
    for i, value in enumerate(games):
        weight = math.exp(-decay * i)
        total_weight += weight
        total_value += weight * value
    return total_value / total_weight


def sample_stdev(games):
    """Standard deviation of the game log — how much it swings around the mean."""
    n = len(games)
    mean = sum(games) / n
    variance = sum((x - mean) ** 2 for x in games) / (n - 1)
    return math.sqrt(variance)


def predictive_stdev(stdev, n):
    """
    predictive_stdev = stdev * sqrt(1 + 1/n)

    At n=10 this only widens stdev by ~5% — modest. At n=3 it's ~15%. At n=1
    it's undefined (no variance estimate possible from one point) — why a
    single-game sample can't be modeled reliably.
    """
    return stdev * math.sqrt(1 + 1 / n)


def sample_size_confidence(n):
    """Plain-English flag for how much to trust the estimate itself."""
    if n >= 15:
        return "HIGH confidence (large sample)"
    elif n >= 8:
        return "MODERATE confidence (typical last-10 sample)"
    elif n >= 3:
        return "LOW confidence (small sample — treat projection cautiously)"
    else:
        return "NOT ENOUGH DATA to estimate variance reliably"


def normal_cdf(x, mean, stdev):
    """P(actual value <= x), assuming a normal distribution."""
    z = (x - mean) / (stdev * math.sqrt(2))
    return 0.5 * (1 + math.erf(z))


def prob_over(line, projection, stdev):
    """P(actual value > line)."""
    return 1 - normal_cdf(line, projection, stdev)


def shrink_toward_general(specific_avg, specific_n, general_projection, k=5):
    """
    Blends a small-sample specific value (e.g. matchup history vs one
    opponent) toward a more reliable general estimate, weighted by how much
    specific data we actually have — real statistical shrinkage, not just
    overriding the general model with a hot/cold small sample.

    k = how many specific-sample games it takes to reach 50% trust in the
    specific data over the general estimate.
    """
    weight_specific = specific_n / (specific_n + k)
    blended = weight_specific * specific_avg + (1 - weight_specific) * general_projection
    return blended, weight_specific


def dampened_ratio(value, reference, elasticity=1.0):
    """
    Ratio of value/reference, dampened by a fractional exponent when the
    underlying relationship isn't fully proportional (1:1). elasticity=1.0
    is the full raw ratio (assumes perfect proportionality); elasticity=0.0
    means no effect at all (ratio always returns 1.0, ignoring the input
    entirely); values in between (e.g. 0.5, a square root) reflect "this
    factor matters, but doesn't scale linearly with the input" — useful when
    a stat is influenced by the matchup but also by other things outside it
    (e.g. a batter's combined H+R+RBI depends on teammates, not just the
    opposing pitcher, so the full ERA ratio would overstate the pitcher's
    specific influence).
    """
    ratio = value / reference
    return ratio ** elasticity


def project(games, adjustment_factor=None, half_life=5, situational_factor=None):
    """
    Returns (projection, raw_stdev, predictive_stdev, confidence_label) for
    any counting-stat game log, generically. `adjustment_factor` is a
    pre-computed matchup multiplier (e.g. opponent quality ratio) — each
    sport module computes its own factor with its own domain logic.

    `situational_factor` is a SEPARATE multiplier for context the game log
    itself doesn't capture yet — most commonly injury/health status or a
    teammate being out (usage bump). Kept distinct from the matchup factor
    so each can be reasoned about and displayed separately, rather than one
    opaque combined number.
    """
    n = len(games)
    raw_avg = weighted_average(games, half_life=half_life)
    raw_stdev = sample_stdev(games)
    pred_stdev = predictive_stdev(raw_stdev, n)
    confidence = sample_size_confidence(n)

    projection = raw_avg
    if adjustment_factor is not None:
        projection *= adjustment_factor
    if situational_factor is not None:
        projection *= situational_factor

    return projection, raw_stdev, pred_stdev, confidence


# Situational factor presets — deliberately rough, judgment-call multipliers,
# NOT derived from a backtest. Treat as a reasonable starting point to tune
# later against real results, same honesty caveat as the elasticity values.
# If MULTIPLE apply at once (e.g. playing hurt AND a teammate is out), the
# simplest approach is to multiply them together — but be aware that's a
# simplification too: real interaction effects between factors aren't
# necessarily just the product of each in isolation. Good enough for now,
# worth revisiting with real data later.
SITUATIONAL_FACTORS = {
    "healthy": 1.0,
    "playing_through_minor_injury": 0.90,   # -10%: nagging injury, still playing
    "recently_returned_from_injury": 0.85,  # -15%: rust/reduced role, compounds with the small-sample LOW-confidence flag this player will likely already get
    "key_teammate_out": 1.15,               # +15%: usage bump from a teammate's absence
}
