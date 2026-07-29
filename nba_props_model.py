#!/usr/bin/env python3
"""
Player prop projection model — points props, starting point for NBA/WNBA.

Concepts this implements (explained inline, since we're learning as we build):

1. Recency-weighted average: recent games matter more than older ones. We
   use exponential weights so game N-1 counts more than game N-10.
2. Standard deviation: how much a player's actual output swings around their
   average, game to game. A player who scores 25 every night is very
   different from one who alternates between 10 and 40, even with the same
   average.
3. Normal distribution probability: assuming a player's points roughly
   follow a bell curve around their projection, we can calculate the exact
   probability their points land over/under any given line using the
   standard normal cumulative distribution function (CDF).
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
    Widens raw game-to-game stdev to also account for uncertainty in our
    ESTIMATE of the mean, which shrinks as sample size grows. This is the
    standard "prediction interval" adjustment: predicting one new game has
    to account for both the player's natural variability AND the chance our
    average itself is off because we only have n games to estimate it from.

    predictive_stdev = stdev * sqrt(1 + 1/n)

    At n=10 this only widens stdev by ~5% (sqrt(1.1)=1.05) — modest. At n=3
    it widens by ~15% (sqrt(1.33)=1.15). At n=1 it's technically undefined
    (no estimate of variance is possible from a single point at all) — a
    real illustration of why Collier's 1-game sample can't be modeled yet.
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
    """P(actual points > line)."""
    return 1 - normal_cdf(line, projection, stdev)


def shrink_toward_general(specific_avg, specific_n, general_projection, k=5):
    """
    Blends a small-sample specific value (e.g. matchup history vs one
    opponent) toward a more reliable general estimate, weighted by how much
    specific data we actually have. This is "shrinkage" / regression to the
    mean: a real, well-established statistical technique for not overweighting
    small samples, even when they're directly relevant (like head-to-head
    history), while still letting them pull the projection somewhat.

    k = how many specific-sample games it takes to reach 50% trust in the
    specific data over the general estimate. Higher k = more skeptical of
    small samples; lower k = trusts specific data faster.
    """
    weight_specific = specific_n / (specific_n + k)
    return weight_specific * specific_avg + (1 - weight_specific) * general_projection, weight_specific


def opponent_adjustment_factor(opponent_def_rating, league_avg_def_rating):
    """
    Ratio of opponent's defensive rating (points allowed per 100 possessions)
    to league average. >1.0 means the opponent is BELOW-average defensively
    (allows more than average -> good matchup for the player). <1.0 means a
    tougher-than-average defense.

    Note: this uses TEAM-wide defensive rating as a proxy, not a position-
    specific one (e.g. "points allowed to centers specifically"), which would
    be more precise but harder to source reliably. Worth upgrading later.
    """
    return opponent_def_rating / league_avg_def_rating


def project_player(games, half_life=5, opponent_def_rating=None, league_avg_def_rating=None):
    """
    Returns (projection, raw_stdev, predictive_stdev, confidence_label) for a
    player given their recent game log, optionally adjusted for the specific
    opponent's defense. Use predictive_stdev (not raw_stdev) for probability
    calculations — it correctly accounts for small-sample uncertainty.
    """
    n = len(games)
    raw_avg = weighted_average(games, half_life=half_life)
    raw_stdev = sample_stdev(games)
    pred_stdev = predictive_stdev(raw_stdev, n)
    confidence = sample_size_confidence(n)

    if opponent_def_rating is not None and league_avg_def_rating is not None:
        factor = opponent_adjustment_factor(opponent_def_rating, league_avg_def_rating)
        projection = raw_avg * factor
    else:
        projection = raw_avg

    return projection, raw_stdev, pred_stdev, confidence


# League average points allowed/game — VERIFIED via covers.com team defense
# table, all 15 WNBA teams, 2026 season. Raw points allowed/game, NOT
# pace-adjusted (per-100-possessions would be more precise but needs
# possession/pace data we haven't sourced yet). Update this if you re-verify
# a newer number, or if you're modeling NBA instead of WNBA once it's back
# in season (this number is WNBA-specific).
LEAGUE_AVG_DEF_RATING = 86.88


def analyze_player(p, league_avg_def_rating=LEAGUE_AVG_DEF_RATING):
    """Runs the full projection + prints the breakdown for one player dict."""
    games = p["games"]
    n = len(games)
    flat_avg = sum(games) / n
    weighted_avg = weighted_average(games)

    projection_no_adj, raw_stdev, pred_stdev, confidence = project_player(games)
    projection_adj, _, _, _ = project_player(
        games,
        opponent_def_rating=p["opponent_def_rating"],
        league_avg_def_rating=league_avg_def_rating,
    )
    factor = opponent_adjustment_factor(p["opponent_def_rating"], league_avg_def_rating)
    widening_pct = (pred_stdev / raw_stdev - 1) * 100

    print(f"=== {p['name']} ({p['team']}) vs {p['opponent']} ===")
    print(f"Last {n} games: {games}")
    print(f"Flat average: {flat_avg:.1f}  |  Weighted average: {weighted_avg:.1f}")
    print(f"Raw stdev: {raw_stdev:.1f}  |  Predictive stdev: {pred_stdev:.1f} (+{widening_pct:.1f}% for sample-size uncertainty)")
    print(f"Sample size confidence: {confidence}")
    print(f"Opponent points allowed/game: {p['opponent_def_rating']}  |  League avg: {league_avg_def_rating}  |  Factor: {factor:.3f}")
    print(f"Projection: {projection_no_adj:.1f} (no adj) -> {projection_adj:.1f} (opponent-adjusted)")

    final_projection = projection_adj
    matchup_history = p.get("matchup_history")
    if matchup_history:
        m_n = len(matchup_history)
        m_avg = sum(matchup_history) / m_n
        blended, weight_specific = shrink_toward_general(m_avg, m_n, projection_adj)
        print(f"Matchup history vs {p['opponent']}: {matchup_history} (avg {m_avg:.1f}, n={m_n})")
        print(f"Shrinkage weight on matchup history: {weight_specific:.1%} (rest stays on the general model)")
        print(f"Projection: {projection_adj:.1f} (opponent-adjusted) -> {blended:.1f} (matchup-blended)")
        final_projection = blended

    # Lines centered around the final projection, in realistic prop increments
    center = round(final_projection)
    lines = [center - 6.5 + i for i in range(0, 12, 3)]
    for line in lines:
        p_over = prob_over(line, final_projection, pred_stdev)
        print(f"  Over {line}: {p_over:.1%} chance")
    print()


def prompt_int(prompt):
    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("  Enter a whole number.")


def interactive_new_player():
    print("\n--- Enter a new player ---")
    name = input("Player name: ").strip()
    team = input("Team: ").strip()
    opponent = input("Tonight's opponent: ").strip()

    print("Enter their last N games' points, most recent first, one at a time.")
    print("(Type 'done' when finished — need at least 3 games.)")
    games = []
    while True:
        raw = input(f"  Game {len(games) + 1} points (or 'done'): ").strip()
        if raw.lower() == "done":
            if len(games) < 3:
                print("  Need at least 3 games to compute a standard deviation.")
                continue
            break
        try:
            games.append(int(raw))
        except ValueError:
            print("  Enter a whole number, or 'done'.")

    opp_def_rating = float(input(f"{opponent}'s points allowed/game (check covers.com team defense): ").strip())
    league_avg = input(f"League average points allowed/game [{LEAGUE_AVG_DEF_RATING}]: ").strip()
    league_avg = float(league_avg) if league_avg else LEAGUE_AVG_DEF_RATING

    matchup_history = []
    has_history = input("Any head-to-head history vs this opponent this season? [y/n]: ").strip().lower()
    if has_history == "y":
        print("Enter their points in each game vs this opponent, one at a time.")
        while True:
            raw = input("  Points (or 'done'): ").strip()
            if raw.lower() == "done":
                break
            try:
                matchup_history.append(int(raw))
            except ValueError:
                print("  Enter a whole number, or 'done'.")

    player = {
        "name": name,
        "team": team,
        "games": games,
        "opponent": opponent,
        "opponent_def_rating": opp_def_rating,
    }
    if matchup_history:
        player["matchup_history"] = matchup_history

    print()
    analyze_player(player, league_avg_def_rating=league_avg)


if __name__ == "__main__":
    print("=== NBA/WNBA Points Prop Model ===")
    print("1) Run the verified demo (Wilson, Clark, Ionescu)")
    print("2) Enter a new player")
    choice = input("Choose 1 or 2: ").strip()

    if choice == "2":
        interactive_new_player()
        raise SystemExit

    # Each player: real last-10-games log (most recent first, verified via
    # StatMuse, double-checked for no "today"/pre-game contamination) and
    # tonight's opponent with their VERIFIED points-allowed/game.
    players = [
        {
            "name": "A'ja Wilson",
            "team": "Las Vegas Aces",
            "games": [38, 26, 20, 21, 32, 30, 32, 16, 19, 33],
            "opponent": "Portland Fire",
            "opponent_def_rating": 90.19,  # 13th of 15 — NOT worst, despite pace-adjusted DRTG saying otherwise
            # VERIFIED: Wilson vs Portland specifically this season — 32 pts
            # both June 11 and July 9. Note: July 9 is ALSO one of the 10
            # games in the general log above (it's the "32" 5th from the
            # left) — there's a one-game overlap between the general sample
            # and this matchup-specific sample. Not perfectly clean
            # statistically, but a known, disclosed simplification rather
            # than a hidden one.
            "matchup_history": [32, 32],
        },
        {
            "name": "Caitlin Clark",
            "team": "Indiana Fever",
            "games": [27, 17, 45, 13, 12, 9, 19, 24, 26, 26],
            "opponent": "Seattle Storm",
            "opponent_def_rating": 87.03,
        },
        {
            "name": "Sabrina Ionescu",
            "team": "New York Liberty",
            "games": [29, 21, 12, 28, 25, 14, 17, 9, 14, 16],
            "opponent": "Los Angeles Sparks",
            "opponent_def_rating": 93.38,  # worst in the league on this metric
        },
    ]

    for p in players:
        analyze_player(p)
