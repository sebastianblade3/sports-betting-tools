#!/usr/bin/env python3
"""
Player prop projection model — MLB. Two prop types, since MLB props are
fundamentally different from basketball's single "points" stat:

1. Pitcher strikeouts — adjusted by the OPPOSING TEAM's strikeout rate
   (a lineup that whiffs a lot boosts the pitcher's K projection).
2. Batter combined H+R+RBI — adjusted by the OPPOSING PITCHER's quality via
   ERA (a worse ERA means more baserunners/runs/RBI opportunities).

Shared math (recency weighting, uncertainty, shrinkage, probability) lives
in stats_engine.py — this file is just the MLB-specific matchup logic.
"""

from stats_engine import (
    weighted_average,
    prob_over,
    shrink_toward_general,
    project,
    dampened_ratio,
    SITUATIONAL_FACTORS,
)


def pitcher_k_adjustment_factor(opponent_k_per_game, league_avg_k_per_game, elasticity=0.7):
    """
    Dampened ratio of the opposing team's strikeouts/game (as hitters) to
    league average. >1.0 means the opponent strikes out MORE than average ->
    good matchup for the pitcher's own strikeout projection.

    elasticity=0.7 (not 1.0): a pitcher's strikeouts do depend heavily on the
    opposing lineup's whiff tendency — more directly than the batter-side
    matchup below, since strikeouts are a head-to-head outcome between
    pitcher and hitter. But it's still not perfectly proportional (a
    pitcher's own specific pitch mix/stuff interacts with a lineup's
    tendencies in ways an average doesn't capture), so some dampening still
    applies, just less than the batter side.
    """
    return dampened_ratio(opponent_k_per_game, league_avg_k_per_game, elasticity=elasticity)


def batter_matchup_adjustment_factor(opponent_pitcher_era, league_avg_era, elasticity=0.5):
    """
    Dampened ratio of the opposing STARTING PITCHER's ERA to league average,
    generic version (used per sub-stat below with a different elasticity
    each, and kept here standalone in case you want a single combined-stat
    read without the sub-stat breakdown).

    Note: this only accounts for the starter, not the bullpen the batter
    might also face later in the game — still a real simplification even
    with the sub-stat split below.
    """
    return dampened_ratio(opponent_pitcher_era, league_avg_era, elasticity=elasticity)


# Per-sub-stat elasticities — THE fix for the crude combined-H+R+RBI
# approximation. Each stat has a genuinely different relationship to the
# opposing pitcher's quality:
#
# - HITS (elasticity 0.6): the most directly pitcher-dependent of the three
#   — closely tied to the pitcher's own hits-allowed rate/WHIP. Still not
#   fully proportional (batter's own contact skill, park, luck all matter
#   too), so still dampened, just less than the other two.
# - RUNS (elasticity 0.3): depends heavily on the batter's OWN speed/
#   baserunning and on TEAMMATES driving them in — a bad opposing pitcher
#   creates more baserunners generally, but whether THIS batter scores
#   depends much more on lineup context than on who's pitching.
# - RBI (elasticity 0.3): same logic as runs, mirrored — depends on
#   teammates being on base ahead of this batter, not mainly on the pitcher.
#
# These three numbers are still judgment calls (not backtested), same
# honesty caveat as before — but they're now at least DIFFERENTIATED by how
# directly each stat actually relates to pitcher quality, instead of forcing
# one blended number onto three different things.
HITS_ELASTICITY = 0.6
RUNS_ELASTICITY = 0.3
RBI_ELASTICITY = 0.3


# League averages — verification quality noted honestly per number:
# - LEAGUE_AVG_ERA: moderately verified (~4.10) via aggregated search
#   results, not a single clean official table. Good enough to use, but
#   less solid than the WNBA points-allowed table was.
# - LEAGUE_AVG_K_PER_GAME: VERIFIED (2026-07-31) from real per-team data via
#   StatMuse, 25 of 30 teams (Reds 9.48 down to Dodgers 7.88) — computed by
#   hand: sum=214.34, n=25, avg=8.574. Note: the source page itself claimed
#   "8.47" as the average of these same numbers, which is WRONG (verify
#   arithmetic yourself, don't trust a page's stated summary stat even when
#   the underlying data is real). Missing 5 teams, so still an approximation,
#   but real data covering 5/6 of the league beats the old flat estimate.
LEAGUE_AVG_ERA = 4.10
LEAGUE_AVG_K_PER_GAME = 8.57


def analyze_pitcher(p, league_avg_k_per_game=LEAGUE_AVG_K_PER_GAME):
    """Prints the strikeout-prop breakdown for one pitcher dict."""
    games = p["games"]
    n = len(games)
    flat_avg = sum(games) / n
    weighted_avg = weighted_average(games)

    situation = p.get("situation", "healthy")
    situational_factor = SITUATIONAL_FACTORS.get(situation, 1.0)

    projection_no_adj, raw_stdev, pred_stdev, confidence = project(games)
    factor = pitcher_k_adjustment_factor(p["opponent_k_per_game"], league_avg_k_per_game)
    projection_adj, _, _, _ = project(
        games, adjustment_factor=factor, situational_factor=situational_factor
    )
    widening_pct = (pred_stdev / raw_stdev - 1) * 100

    print(f"=== {p['name']} ({p['team']}) vs {p['opponent']} — STRIKEOUTS ===")
    print(f"Last {n} starts: {games}")
    print(f"Flat average: {flat_avg:.1f}  |  Weighted average: {weighted_avg:.1f}")
    print(f"Raw stdev: {raw_stdev:.1f}  |  Predictive stdev: {pred_stdev:.1f} (+{widening_pct:.1f}% for sample-size uncertainty)")
    print(f"Sample size confidence: {confidence}")
    print(f"Opponent K/game: {p['opponent_k_per_game']}  |  League avg: {league_avg_k_per_game}  |  Factor: {factor:.3f}")
    if situation != "healthy":
        print(f"Situational factor ({situation}): {situational_factor:.2f}")
    print(f"Projection: {projection_no_adj:.1f} (no adj) -> {projection_adj:.1f} (adjusted)")

    final_projection = projection_adj
    matchup_history = p.get("matchup_history")
    if matchup_history:
        m_n = len(matchup_history)
        m_avg = sum(matchup_history) / m_n
        blended, weight_specific = shrink_toward_general(m_avg, m_n, projection_adj)
        print(f"Matchup history vs {p['opponent']}: {matchup_history} (avg {m_avg:.1f}, n={m_n})")
        print(f"Shrinkage weight on matchup history: {weight_specific:.1%}")
        print(f"Projection: {projection_adj:.1f} -> {blended:.1f} (matchup-blended)")
        final_projection = blended

    center = round(final_projection)
    lines = [center - 3 + i for i in range(0, 7, 2)]
    for line in lines:
        line_half = line - 0.5
        p_over = prob_over(line_half, final_projection, pred_stdev)
        print(f"  Over {line_half}: {p_over:.1%} chance")
    print()


def analyze_batter(b, league_avg_era=LEAGUE_AVG_ERA):
    """
    Prints the H+R+RBI-prop breakdown for one batter dict.

    If separate 'hits'/'runs'/'rbi' game logs are provided, uses the sub-stat
    approach (each projected + adjusted separately with its own elasticity,
    then summed) — this is the real fix for the crude combined-stat
    approximation. Falls back to the old single-elasticity combined approach
    if only a combined 'games' list is given (e.g. from the interactive mode,
    where asking for 3 separate logs would be a lot of typing).
    """
    situation = b.get("situation", "healthy")
    situational_factor = SITUATIONAL_FACTORS.get(situation, 1.0)
    park_factor = b.get("park_factor", 1.0)  # 1.0 = neutral park; already a ratio-to-average, no dampening needed

    has_substats = "hits" in b and "runs" in b and "rbi" in b

    if has_substats:
        hits, runs, rbi = b["hits"], b["runs"], b["rbi"]
        combined_games = [h + r + rb for h, r, rb in zip(hits, runs, rbi)]
        n = len(combined_games)

        hits_factor = batter_matchup_adjustment_factor(b["opponent_pitcher_era"], league_avg_era, elasticity=HITS_ELASTICITY)
        runs_factor = batter_matchup_adjustment_factor(b["opponent_pitcher_era"], league_avg_era, elasticity=RUNS_ELASTICITY)
        rbi_factor = batter_matchup_adjustment_factor(b["opponent_pitcher_era"], league_avg_era, elasticity=RBI_ELASTICITY)

        hits_proj, _, _, _ = project(hits, adjustment_factor=hits_factor)
        runs_proj, _, _, _ = project(runs, adjustment_factor=runs_factor)
        rbi_proj, _, _, _ = project(rbi, adjustment_factor=rbi_factor)

        matchup_adjusted_sum = hits_proj + runs_proj + rbi_proj

        # stdev/confidence come from the real combined game log directly —
        # that part was never the problem, only the MEAN estimate was crude.
        _, raw_stdev, pred_stdev, confidence = project(combined_games)
        projection_no_adj = sum(project(s)[0] for s in (hits, runs, rbi))

        print(f"=== {b['name']} ({b['team']}) vs {b['opponent_pitcher']} — H+R+RBI (sub-stat model) ===")
        print(f"Last {n} games — hits: {hits} | runs: {runs} | rbi: {rbi}")
        print(f"Sub-stat projections: hits {hits_proj:.2f} (factor {hits_factor:.3f}) + "
              f"runs {runs_proj:.2f} (factor {runs_factor:.3f}) + rbi {rbi_proj:.2f} (factor {rbi_factor:.3f})")
        combined_factor = matchup_adjusted_sum / projection_no_adj if projection_no_adj else 1.0
        projection_adj = matchup_adjusted_sum
    else:
        games = b["games"]  # combined H+R+RBI only, no split available
        n = len(games)

        matchup_factor = batter_matchup_adjustment_factor(b["opponent_pitcher_era"], league_avg_era)
        projection_no_adj, raw_stdev, pred_stdev, confidence = project(games)
        projection_adj, _, _, _ = project(games, adjustment_factor=matchup_factor)
        combined_factor = matchup_factor

        print(f"=== {b['name']} ({b['team']}) vs {b['opponent_pitcher']} — H+R+RBI (combined-stat fallback) ===")
        print(f"Last {n} games (combined H+R+RBI): {games}")
        print(f"Opponent pitcher ERA: {b['opponent_pitcher_era']}  |  League avg ERA: {league_avg_era}  |  Matchup factor: {matchup_factor:.3f}")

    # Apply park + situational on top of the matchup-adjusted sum either way
    projection_adj = projection_adj * park_factor * situational_factor
    combined_factor = combined_factor * park_factor * situational_factor
    widening_pct = (pred_stdev / raw_stdev - 1) * 100

    flat_avg = sum([h + r + rb for h, r, rb in zip(b["hits"], b["runs"], b["rbi"])]) / n if has_substats else sum(b["games"]) / n
    print(f"Flat average: {flat_avg:.1f}")
    print(f"Raw stdev: {raw_stdev:.1f}  |  Predictive stdev: {pred_stdev:.1f} (+{widening_pct:.1f}% for sample-size uncertainty)")
    print(f"Sample size confidence: {confidence}")
    if park_factor != 1.0:
        print(f"Park factor: {park_factor:.2f}")
    if situation != "healthy":
        print(f"Situational factor ({situation}): {situational_factor:.2f}")
    print(f"Overall effective factor: {combined_factor:.3f}")
    print(f"Projection: {projection_no_adj:.1f} (no adj) -> {projection_adj:.1f} (fully adjusted)")

    center = round(projection_adj)
    for line in [1.5, 2.5, 3.5]:
        p_over = prob_over(line, projection_adj, pred_stdev)
        print(f"  Over {line}: {p_over:.1%} chance")
    print()


def prompt_situation():
    print("Any situational factor tonight?")
    print("  1) Healthy  2) Playing through a minor injury  3) Recently returned from injury  4) A key teammate is out")
    choice = input("Choose 1-4 [1]: ").strip() or "1"
    return {
        "1": "healthy",
        "2": "playing_through_minor_injury",
        "3": "recently_returned_from_injury",
        "4": "key_teammate_out",
    }.get(choice, "healthy")


def interactive_new_entry():
    print("\n1) Pitcher (strikeouts)  2) Batter (H+R+RBI)")
    kind = input("Which kind? [1/2]: ").strip()

    if kind == "1":
        name = input("Pitcher name: ").strip()
        team = input("Team: ").strip()
        opponent = input("Tonight's opponent: ").strip()
        print("Enter their last N starts' strikeouts, most recent first.")
        games = []
        while True:
            raw = input(f"  Start {len(games) + 1} strikeouts (or 'done'): ").strip()
            if raw.lower() == "done":
                if len(games) < 3:
                    print("  Need at least 3 starts.")
                    continue
                break
            try:
                games.append(int(raw))
            except ValueError:
                print("  Enter a whole number, or 'done'.")
        opp_k = float(input(f"{opponent}'s strikeouts/game (as hitters): ").strip())
        league_avg = input(f"League avg K/game [{LEAGUE_AVG_K_PER_GAME}]: ").strip()
        league_avg = float(league_avg) if league_avg else LEAGUE_AVG_K_PER_GAME
        situation = prompt_situation()
        pitcher = {"name": name, "team": team, "opponent": opponent, "games": games, "opponent_k_per_game": opp_k, "situation": situation}
        print()
        analyze_pitcher(pitcher, league_avg_k_per_game=league_avg)
    else:
        name = input("Batter name: ").strip()
        team = input("Team: ").strip()
        opponent_pitcher = input("Tonight's opposing starter: ").strip()
        print("Enter their combined H+R+RBI for each of their last N games, most recent first.")
        games = []
        while True:
            raw = input(f"  Game {len(games) + 1} H+R+RBI total (or 'done'): ").strip()
            if raw.lower() == "done":
                if len(games) < 3:
                    print("  Need at least 3 games.")
                    continue
                break
            try:
                games.append(int(raw))
            except ValueError:
                print("  Enter a whole number, or 'done'.")
        opp_era = float(input(f"{opponent_pitcher}'s ERA: ").strip())
        league_avg = input(f"League avg ERA [{LEAGUE_AVG_ERA}]: ").strip()
        league_avg = float(league_avg) if league_avg else LEAGUE_AVG_ERA
        park_factor_raw = input("Tonight's park factor (1.0 = neutral, e.g. 0.97 pitcher-friendly, 1.12 hitter-friendly) [1.0]: ").strip()
        park_factor = float(park_factor_raw) if park_factor_raw else 1.0
        situation = prompt_situation()
        batter = {
            "name": name, "team": team, "opponent_pitcher": opponent_pitcher, "games": games,
            "opponent_pitcher_era": opp_era, "park_factor": park_factor, "situation": situation,
        }
        print()
        analyze_batter(batter, league_avg_era=league_avg)


if __name__ == "__main__":
    print("=== MLB Props Model ===")
    print("1) Run the verified demo (Melton strikeouts, France H+R+RBI)")
    print("2) Enter a new pitcher or batter")
    choice = input("Choose 1 or 2: ").strip()

    if choice == "2":
        interactive_new_entry()
        raise SystemExit

    # Real, verified data (ESPN gamelogs, 2026 season):
    pitchers = [
        {
            "name": "Troy Melton",
            "team": "Detroit Tigers",
            "opponent": "Baltimore Orioles",
            "games": [5, 9, 9, 7, 6, 5, 5, 5, 1, 3],  # last 10 starts, most recent first
            "opponent_k_per_game": 9.18,  # VERIFIED: 983 SO / 107 games (fantasyteamadvice.com)
        },
    ]

    batters = [
        {
            "name": "Ty France",
            "team": "San Diego Padres",
            "opponent_pitcher": "Michael Lorenzen (COL)",
            # VERIFIED (ESPN gamelog), last 10 games, most recent first,
            # SEPARATED into sub-stats (this is the upgrade from the earlier
            # combined-only version) — hits+runs+rbi sums to the same
            # [2,6,2,4,0,3,4,9,2,4] combined log used before.
            "hits": [2, 2, 2, 1, 0, 2, 2, 2, 2, 1],
            "runs": [0, 1, 0, 1, 0, 0, 1, 2, 0, 2],
            "rbi":  [0, 3, 0, 2, 0, 1, 1, 5, 0, 1],
            "opponent_pitcher_era": 6.91,  # VERIFIED (from earlier tonight's research)
            # VERIFIED: Petco Park RHB run factor 0.97 (fantasyteamadvice.com) —
            # France bats right-handed (verified). Petco is a pitcher's park
            # (marine layer suppresses offense), so this slightly DAMPENS the
            # otherwise-favorable pitcher matchup.
            "park_factor": 0.97,
        },
    ]

    for p in pitchers:
        analyze_pitcher(p)
    for b in batters:
        analyze_batter(b)
