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
    blend_recent_and_season,
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
    Dampened ratio of an opposing pitcher's (or blended pitcher+bullpen, see
    effective_opponent_era below) ERA to league average, generic version
    (used per sub-stat below with a different elasticity each).
    """
    return dampened_ratio(opponent_pitcher_era, league_avg_era, elasticity=elasticity)


# Rough assumption for how much of a batter's game is against the starter
# vs the bullpen — a typical batter gets ~4 PA/game; if the starter goes
# ~5-6 innings (a common modern outing length), the batter likely sees the
# starter for their first 2-3 PA and the bullpen for the last 1-2. 65/35 is
# a reasonable round-number split, NOT derived from precise inning-by-inning
# data — a real refinement would use the specific pitcher's typical innings
# per start and the batter's actual lineup spot, but this is a meaningful
# upgrade over ignoring the bullpen entirely.
STARTER_WEIGHT = 0.65
BULLPEN_WEIGHT = 0.35


def effective_opponent_era(starter_era, bullpen_era=None):
    """
    Blends starter ERA with bullpen ERA using STARTER_WEIGHT/BULLPEN_WEIGHT.
    Falls back to starter-only if no bullpen ERA is available (previous
    behavior, still fine when bullpen data isn't sourced for a matchup).
    """
    if bullpen_era is None:
        return starter_era
    return STARTER_WEIGHT * starter_era + BULLPEN_WEIGHT * bullpen_era


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
    season_avg = p.get("season_avg")  # optional: full-season K/start average

    projection_no_adj, raw_stdev, pred_stdev, confidence = project(games, season_avg=season_avg)
    factor = pitcher_k_adjustment_factor(p["opponent_k_per_game"], league_avg_k_per_game)
    projection_adj, _, _, _ = project(
        games, adjustment_factor=factor, situational_factor=situational_factor, season_avg=season_avg
    )
    widening_pct = (pred_stdev / raw_stdev - 1) * 100

    print(f"=== {p['name']} ({p['team']}) vs {p['opponent']} — STRIKEOUTS ===")
    print(f"Last {n} starts: {games}")
    print(f"Flat average: {flat_avg:.1f}  |  Weighted average: {weighted_avg:.1f}", end="")
    if season_avg is not None:
        blended = blend_recent_and_season(weighted_avg, season_avg)
        print(f"  |  Season avg: {season_avg:.1f}  |  Blended (70/30): {blended:.1f}")
    else:
        print()
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

    Optional fields: 'season_avg_hits'/'season_avg_runs'/'season_avg_rbi' (or
    just 'season_avg' in fallback mode) blend recent form with full-season
    averages, same concept as the NBA model. 'matchup_history' (combined
    H+R+RBI per game vs this specific opponent) applies shrinkage on top of
    everything else, same as the pitcher side above.
    """
    situation = b.get("situation", "healthy")
    situational_factor = SITUATIONAL_FACTORS.get(situation, 1.0)
    park_factor = b.get("park_factor", 1.0)  # 1.0 = neutral park; already a ratio-to-average, no dampening needed

    bullpen_era = b.get("opponent_bullpen_era")
    eff_era = effective_opponent_era(b["opponent_pitcher_era"], bullpen_era)
    if bullpen_era is not None:
        print(f"Effective opponent ERA: {STARTER_WEIGHT:.0%} starter ({b['opponent_pitcher_era']}) + "
              f"{BULLPEN_WEIGHT:.0%} bullpen ({bullpen_era}) = {eff_era:.2f}")

    has_substats = "hits" in b and "runs" in b and "rbi" in b

    if has_substats:
        hits, runs, rbi = b["hits"], b["runs"], b["rbi"]
        combined_games = [h + r + rb for h, r, rb in zip(hits, runs, rbi)]
        n = len(combined_games)

        hits_factor = batter_matchup_adjustment_factor(eff_era, league_avg_era, elasticity=HITS_ELASTICITY)
        runs_factor = batter_matchup_adjustment_factor(eff_era, league_avg_era, elasticity=RUNS_ELASTICITY)
        rbi_factor = batter_matchup_adjustment_factor(eff_era, league_avg_era, elasticity=RBI_ELASTICITY)

        season_hits = b.get("season_avg_hits")
        season_runs = b.get("season_avg_runs")
        season_rbi = b.get("season_avg_rbi")

        hits_proj, _, _, _ = project(hits, adjustment_factor=hits_factor, season_avg=season_hits)
        runs_proj, _, _, _ = project(runs, adjustment_factor=runs_factor, season_avg=season_runs)
        rbi_proj, _, _, _ = project(rbi, adjustment_factor=rbi_factor, season_avg=season_rbi)

        matchup_adjusted_sum = hits_proj + runs_proj + rbi_proj

        # stdev/confidence come from the real combined game log directly —
        # that part was never the problem, only the MEAN estimate was crude.
        _, raw_stdev, pred_stdev, confidence = project(combined_games)
        projection_no_adj = sum(
            project(s, season_avg=sa)[0]
            for s, sa in ((hits, season_hits), (runs, season_runs), (rbi, season_rbi))
        )

        print(f"=== {b['name']} ({b['team']}) vs {b['opponent_pitcher']} — H+R+RBI (sub-stat model) ===")
        print(f"Last {n} games — hits: {hits} | runs: {runs} | rbi: {rbi}")
        if season_hits is not None or season_runs is not None or season_rbi is not None:
            sh = f"{season_hits:.2f}" if season_hits is not None else "n/a"
            sr = f"{season_runs:.2f}" if season_runs is not None else "n/a"
            srbi = f"{season_rbi:.2f}" if season_rbi is not None else "n/a"
            print(f"Season averages — hits: {sh}  runs: {sr}  rbi: {srbi}")
        print(f"Sub-stat projections: hits {hits_proj:.2f} (factor {hits_factor:.3f}) + "
              f"runs {runs_proj:.2f} (factor {runs_factor:.3f}) + rbi {rbi_proj:.2f} (factor {rbi_factor:.3f})")
        combined_factor = matchup_adjusted_sum / projection_no_adj if projection_no_adj else 1.0
        projection_adj = matchup_adjusted_sum
    else:
        games = b["games"]  # combined H+R+RBI only, no split available
        n = len(games)
        season_avg = b.get("season_avg")

        matchup_factor = batter_matchup_adjustment_factor(eff_era, league_avg_era)
        projection_no_adj, raw_stdev, pred_stdev, confidence = project(games, season_avg=season_avg)
        projection_adj, _, _, _ = project(games, adjustment_factor=matchup_factor, season_avg=season_avg)
        combined_factor = matchup_factor

        print(f"=== {b['name']} ({b['team']}) vs {b['opponent_pitcher']} — H+R+RBI (combined-stat fallback) ===")
        print(f"Last {n} games (combined H+R+RBI): {games}", end="")
        if season_avg is not None:
            print(f"  |  Season avg: {season_avg:.1f}")
        else:
            print()
        print(f"Opponent ERA used: {eff_era:.2f}  |  League avg ERA: {league_avg_era}  |  Matchup factor: {matchup_factor:.3f}")

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

    final_projection = projection_adj
    matchup_history = b.get("matchup_history")
    if matchup_history:
        m_n = len(matchup_history)
        m_avg = sum(matchup_history) / m_n
        blended, weight_specific = shrink_toward_general(m_avg, m_n, projection_adj)
        print(f"Matchup history vs {b['opponent_pitcher']}: {matchup_history} (avg {m_avg:.1f}, n={m_n})")
        print(f"Shrinkage weight on matchup history: {weight_specific:.1%}")
        print(f"Projection: {projection_adj:.1f} -> {blended:.1f} (matchup-blended)")
        final_projection = blended

    center = round(final_projection)
    for line in [1.5, 2.5, 3.5]:
        p_over = prob_over(line, final_projection, pred_stdev)
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


def prompt_game_log(label, minimum=3):
    print(f"Enter {label}, most recent first. (Type 'done' when finished — need at least {minimum}.)")
    values = []
    while True:
        raw = input(f"  Game {len(values) + 1} (or 'done'): ").strip()
        if raw.lower() == "done":
            if len(values) < minimum:
                print(f"  Need at least {minimum}.")
                continue
            break
        try:
            values.append(int(raw))
        except ValueError:
            print("  Enter a whole number, or 'done'.")
    return values


def prompt_optional_float(prompt_text):
    raw = input(prompt_text).strip()
    return float(raw) if raw else None


def prompt_matchup_history(opponent_label):
    has_history = input(f"Any head-to-head history vs {opponent_label} this season? [y/n]: ").strip().lower()
    if has_history != "y":
        return None
    return prompt_game_log("their totals in each game vs this opponent", minimum=1)


def interactive_new_entry():
    print("\n1) Pitcher (strikeouts)  2) Batter (H+R+RBI)")
    kind = input("Which kind? [1/2]: ").strip()

    if kind == "1":
        name = input("Pitcher name: ").strip()
        team = input("Team: ").strip()
        opponent = input("Tonight's opponent: ").strip()
        games = prompt_game_log("their last N starts' strikeouts")
        opp_k = float(input(f"{opponent}'s strikeouts/game (as hitters): ").strip())
        league_avg = input(f"League avg K/game [{LEAGUE_AVG_K_PER_GAME}]: ").strip()
        league_avg = float(league_avg) if league_avg else LEAGUE_AVG_K_PER_GAME
        season_avg = prompt_optional_float("Their full-season K/start average, if known (blank to skip): ")
        matchup_history = prompt_matchup_history(opponent)
        situation = prompt_situation()
        pitcher = {
            "name": name, "team": team, "opponent": opponent, "games": games,
            "opponent_k_per_game": opp_k, "situation": situation,
        }
        if season_avg is not None:
            pitcher["season_avg"] = season_avg
        if matchup_history:
            pitcher["matchup_history"] = matchup_history
        print()
        analyze_pitcher(pitcher, league_avg_k_per_game=league_avg)
    else:
        name = input("Batter name: ").strip()
        team = input("Team: ").strip()
        opponent_pitcher = input("Tonight's opposing starter: ").strip()

        use_substats = input("Enter separate hits/runs/rbi logs (more precise) or just combined H+R+RBI? [separate/combined]: ").strip().lower()
        batter = {"name": name, "team": team, "opponent_pitcher": opponent_pitcher}

        if use_substats.startswith("s"):
            hits = prompt_game_log("their last N games' HITS")
            runs = prompt_game_log("their last N games' RUNS")
            rbi = prompt_game_log("their last N games' RBI")
            batter["hits"], batter["runs"], batter["rbi"] = hits, runs, rbi

            season_hits = prompt_optional_float("Their full-season hits/game average, if known (blank to skip): ")
            season_runs = prompt_optional_float("Their full-season runs/game average, if known (blank to skip): ")
            season_rbi = prompt_optional_float("Their full-season RBI/game average, if known (blank to skip): ")
            if season_hits is not None:
                batter["season_avg_hits"] = season_hits
            if season_runs is not None:
                batter["season_avg_runs"] = season_runs
            if season_rbi is not None:
                batter["season_avg_rbi"] = season_rbi
        else:
            games = prompt_game_log("their combined H+R+RBI for each of their last N games")
            batter["games"] = games
            season_avg = prompt_optional_float("Their full-season combined H+R+RBI/game average, if known (blank to skip): ")
            if season_avg is not None:
                batter["season_avg"] = season_avg

        opp_era = float(input(f"{opponent_pitcher}'s ERA: ").strip())
        bullpen_era = prompt_optional_float("Opponent's bullpen ERA, if known (blank to skip): ")
        league_avg = input(f"League avg ERA [{LEAGUE_AVG_ERA}]: ").strip()
        league_avg = float(league_avg) if league_avg else LEAGUE_AVG_ERA
        park_factor_raw = input("Tonight's park factor (1.0 = neutral, e.g. 0.97 pitcher-friendly, 1.12 hitter-friendly) [1.0]: ").strip()
        park_factor = float(park_factor_raw) if park_factor_raw else 1.0
        matchup_history = prompt_matchup_history(opponent_pitcher)
        situation = prompt_situation()

        batter["opponent_pitcher_era"] = opp_era
        if bullpen_era is not None:
            batter["opponent_bullpen_era"] = bullpen_era
        batter["park_factor"] = park_factor
        batter["situation"] = situation
        if matchup_history:
            batter["matchup_history"] = matchup_history

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
            # No season_avg here deliberately: Melton has made exactly 10
            # starts this season (5-1, 60.0 IP in 10 starts per earlier
            # research) — his "season" IS this last-10 log, so a season
            # blend would be a meaningless no-op, not a missing feature.
            # season_avg IS supported here (see analyze_pitcher) for any
            # pitcher with more starts than the window shown.
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
            # VERIFIED (StatMuse): full 2026 season = 82 G, 73 H, 33 R, 46 RBI
            # (internally consistent: 73/256 AB = .285, matches stated avg).
            # Per-game: hits 0.89, runs 0.40, rbi 0.56 — all notably LOWER
            # than his last-10 pace (which has been a hot stretch), so this
            # blend pulls the projection back down toward his real season
            # level, same direction-of-effect lesson as Wilson but opposite
            # sign (hers pulled UP, his pulls DOWN).
            "season_avg_hits": 73 / 82,
            "season_avg_runs": 33 / 82,
            "season_avg_rbi": 46 / 82,
            "opponent_pitcher_era": 6.91,  # VERIFIED (from earlier tonight's research)
            # VERIFIED but genuinely volatile: Rockies bullpen ERA was 3.77
            # in April 2026 (good) and 5.79 over the last 7 days as of
            # 7/30/2026 (mediocre) — this specific bullpen is documented as
            # swinging wildly month to month (great in April, bad in May,
            # good again in July per Purple Row). Using the more CURRENT
            # last-7-days number since recency matters more than an old
            # snapshot, but flagging honestly that this is a small, volatile
            # sample, not a stable season-long number (full-season bullpen
            # ERA was paywalled everywhere I checked).
            "opponent_bullpen_era": 5.79,
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
