#!/usr/bin/env python3
"""
Player prop projection model — points props, NBA/WNBA.
Shared math (recency weighting, uncertainty, shrinkage, probability) lives in
stats_engine.py; this file is just the NBA/WNBA-specific opponent logic.
"""

from stats_engine import (
    weighted_average,
    prob_over,
    shrink_toward_general,
    project,
    blend_recent_and_season,
    SITUATIONAL_FACTORS,
)


def opponent_adjustment_factor(opponent_def_rating, league_avg_def_rating):
    """
    Ratio of opponent's PACE-ADJUSTED defensive rating (points allowed per
    100 possessions) to league average. >1.0 means the opponent is
    BELOW-average defensively -> good matchup for the player. <1.0 means a
    tougher-than-average defense.

    UPGRADED 2026-07-31: now genuinely pace-adjusted, computed by hand from
    two separately-verified real inputs (points allowed/game from covers.com,
    pace/possessions-per-game from StatMuse), rather than raw points
    allowed/game. This is the actual fix for the earlier "mixed pace-adjusted
    with non-pace-adjusted" lesson — Portland's original 111.8 DRTG claim
    ("worst in WNBA") turned out to be roughly right after all (our own
    calculation: 114.21, still 2nd-worst) once we had a properly-computed
    league average to check it against, rather than an ESTIMATED one.

    Position-specific defense (DVP) is still not used — league DVP tables
    are JS-rendered and couldn't be fetched reliably. Worth upgrading later
    if a reliable source turns up.
    """
    return opponent_def_rating / league_avg_def_rating


# League average PACE-ADJUSTED defensive rating (points allowed per 100
# possessions) — VERIFIED 2026-07-31, computed by hand from two real,
# independently-sourced inputs: points-allowed/game (covers.com team defense
# table) and pace/possessions-per-game (StatMuse), all 15 WNBA teams, 2026
# season. avg = 108.51. Replaces the earlier raw points-allowed/game metric
# (86.88), which wasn't wrong, just less precise (didn't account for pace).
LEAGUE_AVG_DEF_RATING = 108.51


def analyze_player(p, league_avg_def_rating=LEAGUE_AVG_DEF_RATING):
    """Runs the full projection + prints the breakdown for one player dict."""
    games = p["games"]
    n = len(games)
    flat_avg = sum(games) / n
    weighted_avg = weighted_average(games)

    situation = p.get("situation", "healthy")
    situational_factor = SITUATIONAL_FACTORS.get(situation, 1.0)
    season_avg = p.get("season_avg")  # optional: full-season PPG, blended with recent form

    projection_no_adj, raw_stdev, pred_stdev, confidence = project(games, season_avg=season_avg)
    factor = opponent_adjustment_factor(p["opponent_def_rating"], league_avg_def_rating)
    projection_adj, _, _, _ = project(
        games, adjustment_factor=factor, situational_factor=situational_factor, season_avg=season_avg
    )
    widening_pct = (pred_stdev / raw_stdev - 1) * 100

    print(f"=== {p['name']} ({p['team']}) vs {p['opponent']} ===")
    print(f"Last {n} games: {games}")
    print(f"Flat average: {flat_avg:.1f}  |  Weighted average (last-{n}): {weighted_avg:.1f}", end="")
    if season_avg is not None:
        blended = blend_recent_and_season(weighted_avg, season_avg)
        print(f"  |  Season avg: {season_avg:.1f}  |  Blended (70/30): {blended:.1f}")
    else:
        print()
    print(f"Raw stdev: {raw_stdev:.1f}  |  Predictive stdev: {pred_stdev:.1f} (+{widening_pct:.1f}% for sample-size uncertainty)")
    print(f"Sample size confidence: {confidence}")
    print(f"Opponent points allowed/game: {p['opponent_def_rating']}  |  League avg: {league_avg_def_rating}  |  Factor: {factor:.3f}")
    if situation != "healthy":
        print(f"Situational factor ({situation}): {situational_factor:.2f}")
    print(f"Projection: {projection_no_adj:.1f} (no adj) -> {projection_adj:.1f} (opponent + situational adjusted)")

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

    season_avg_raw = input("Their full-season points/game average, if known (blank to skip): ").strip()
    season_avg = float(season_avg_raw) if season_avg_raw else None

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

    print("\nAny situational factor tonight?")
    print("  1) Healthy  2) Playing through a minor injury  3) Recently returned from injury  4) A key teammate is out")
    situation_choice = input("Choose 1-4 [1]: ").strip() or "1"
    situation_map = {
        "1": "healthy",
        "2": "playing_through_minor_injury",
        "3": "recently_returned_from_injury",
        "4": "key_teammate_out",
    }
    situation = situation_map.get(situation_choice, "healthy")

    player = {
        "name": name,
        "team": team,
        "games": games,
        "opponent": opponent,
        "opponent_def_rating": opp_def_rating,
        "situation": situation,
    }
    if matchup_history:
        player["matchup_history"] = matchup_history
    if season_avg is not None:
        player["season_avg"] = season_avg

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
    # tonight's opponent with their VERIFIED pace-adjusted defensive rating
    # (points allowed per 100 possessions, computed by hand 2026-07-31 from
    # covers.com points-allowed/game + StatMuse pace, see opponent_adjustment_factor).
    players = [
        {
            "name": "A'ja Wilson",
            "team": "Las Vegas Aces",
            "games": [38, 26, 20, 21, 32, 30, 32, 16, 19, 33],
            "opponent": "Portland Fire",
            "opponent_def_rating": 114.21,  # 2nd-worst pace-adjusted DRTG in the league
            # VERIFIED: season PPG 31.6 (StatMuse) — notably ABOVE her last-10
            # weighted average (27.4), meaning this specific 10-game window
            # caught a cooler stretch than her season as a whole. The blend
            # pulls the projection back up toward her real full-season level.
            "season_avg": 31.6,
            # VERIFIED: Wilson vs Portland specifically this season — 32 pts
            # both June 11 and July 9. Note: July 9 is ALSO one of the 10
            # games in the general log above — a one-game overlap between
            # the general sample and this matchup-specific sample. Not
            # perfectly clean statistically, but a disclosed simplification.
            "matchup_history": [32, 32],
        },
        {
            "name": "Caitlin Clark",
            "team": "Indiana Fever",
            "games": [27, 17, 45, 13, 12, 9, 19, 24, 26, 26],
            "opponent": "Seattle Storm",
            "opponent_def_rating": 108.08,  # right at league average now
            "season_avg": 21.5,  # VERIFIED (StatMuse) — close to her last-10 (22.3), small effect
        },
        {
            "name": "Sabrina Ionescu",
            "team": "New York Liberty",
            "games": [29, 21, 12, 28, 25, 14, 17, 9, 14, 16],
            "opponent": "Los Angeles Sparks",
            "opponent_def_rating": 113.23,  # 3rd-worst pace-adjusted DRTG in the league
            "season_avg": 21.6,  # VERIFIED (StatMuse) — a bit above her last-10 (20.1), modest boost
        },
    ]

    for p in players:
        analyze_player(p)
