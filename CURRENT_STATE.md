# Current State — Sports Betting / EV

Rewritten in place at every checkpoint (see [[Home]] rule 1).

## Status

Exploratory phase — talking through real matches/props to build intuition
before writing any code. EV tool itself not started yet.

**Platform: user bets on PrizePicks**, not a standard sportsbook. This matters
a lot — PrizePicks pays fixed multipliers on multi-pick entries rather than
per-bet decimal odds with vig, so the breakeven bar is different:
- Power Play (all picks must hit): breakeven per-leg probability is ~55–58%+
  (e.g. 2-pick/3x ≈ 57.7%, 6-pick/37.5x ≈ 54.7%), NOT the ~52.4% breakeven of
  a standard -110 sportsbook line.
- Flex Play: partial hits still pay out on a curve, more forgiving than Power
  but still meaningfully above a coinflip per leg.
- Practical implication: "which side is favored" (>50%) is NOT sufficient for
  a good PrizePicks pick — need real confidence above ~55–58% per leg. Any
  future EV tool must model PrizePicks' specific payout curve, not generic
  sportsbook vig.

## Done

- Discussed Tommy Paul vs Kamil Majchrzak (Citi Open, 2026-07-28) — win + total
  games props, corrected match-total vs player-total-games-won distinction.
- Discussed Jakub Mensik vs Trevor Svajda (Citi Open, 2026-07-28) — same props,
  compared blowout risk vs the Paul match.

## In flight

- Talking through more of tomorrow's (2026-07-28) Citi Open Washington card.

## Done

- 6-pick Power Play from 7/28 checked and confirmed LOST (2 coinflip legs
  missed — see Match-Notes.md).
- **EV tool v1 built**: `ev_tool.py` in this folder. Command-line calculator
  — enter legs + your probability estimates, it computes combined hit
  probability (Power) or full payout distribution (Flex), compares to the
  real PrizePicks breakeven, and can auto-log the entry to Match-Notes.md.
  Verified against both the 6-pick and the 3-pick baseball-only example —
  matches the by-hand math exactly.

## Done (2026-07-28, NBA/WNBA prediction model — new direction)

User bets most on NBA (now saved to memory). Since NBA is off-season, we're
building the model against WNBA (in-season, same prop types) as a live test
bed that transfers directly to NBA in October. Staying free/manual-data for
now, no paid odds API yet, "slow and steady, learn as we go" pace.

**Built `nba_props_model.py`** in this folder — a real points-prop projection
model, not a guess:
- Recency-weighted average (recent games count more, half-life=5 games)
- Standard deviation (how volatile the player's output is)
- Normal-distribution probability calculator (exact P(over line) given a
  projection + stdev)
- Opponent adjustment factor (opponent's defensive rating / league average)

Tested on A'ja Wilson (verified real last-10-games log: 38,26,20,21,32,30,32,
16,19,33) vs tonight's Portland Fire matchup. Portland's 111.8 defensive
rating (worst in WNBA) is VERIFIED. League average (used 102.0) is an
ESTIMATE — repeated fetch attempts to confirm the real 2026 number were
blocked. Result: adjusted projection 30.0 +/- 7.3, e.g. 68.5% over 26.5.

**Data reliability lesson learned (important):** hit repeated cases of
fetch tools fabricating plausible-looking results for games that hadn't been
played yet (Collier vs Toronto claimed final 100-93 hours before tipoff) —
same pattern as the earlier Melton/Lee box score issues. Rule going forward:
never trust a "today's result" from a single fetch — cross-check with a
second independent search before treating it as real.

## Done (2026-07-28, league-average verification)

Verified via covers.com team-defense table (all 15 WNBA teams, 2026): league
average points-allowed/game = **86.88**, Portland Fire = **90.19** (13th of
15, NOT worst). This replaces the earlier ESTIMATE (102.0) and the earlier
mismatched pace-adjusted Portland number (111.8 DRTG).

**Real lesson learned:** the original version mixed a pace-adjusted stat
(Portland's 111.8 defensive rating, "worst in WNBA") with an estimated
league average on that same pace-adjusted basis — apples to oranges. Once
corrected to a single consistent metric (raw points allowed/game, fully
verified for all teams), the "favorable matchup" effect shrank a lot:
adjustment factor 1.096 -> 1.038, projection 30.0 -> 28.4. Mixing partially-
verified numbers, even when each individual number is real, can still
produce a misleading combined result — verify the METRIC matches, not just
that each number is real.

## Done (2026-07-28, more players added)

Refactored to a data-driven `players` list, added two more real worked
examples alongside Wilson (all verified game logs + verified opponent
points-allowed/game):
- Caitlin Clark (Fever) vs Seattle Storm — notably huge stdev (10.4), very
  volatile scorer (9 to 45 in the same 10-game window); Seattle's defense is
  almost exactly league average so she gets ~zero adjustment (good sanity
  check the model doesn't invent an edge where none exists).
- Sabrina Ionescu (Liberty) vs LA Sparks — Sparks are the actual worst
  points-allowed/game team in the league, biggest adjustment factor (1.075).

Dropped Napheesa Collier as a candidate: she missed ~27 games this season
(dual ankle surgery, ~300 day injury layoff) and only has ONE real 2026 game
— too small a sample and coming off major injury, not representative.

## Done (2026-07-28, small-sample uncertainty refinement)

Added `predictive_stdev()` (widens raw stdev by sqrt(1+1/n) to account for
uncertainty in the estimate of the mean itself, not just game-to-game
variance) and `sample_size_confidence()` (plain-English HIGH/MODERATE/LOW
label based on n). Verified behaving correctly: at n=10 the widening is a
modest ~5% (probabilities compress slightly toward 50% symmetrically around
the projection); at n=3 it'd be ~15%; at n=1 it's undefined — mathematically
confirms why Collier's 1-game sample can't be modeled, not just an eyeball
call. This is the standard statistical "prediction interval vs confidence
interval" distinction.

## Done (2026-07-28, matchup-history shrinkage + interactive mode)

- **Matchup-history shrinkage**: true league-wide position-vs-defense (DVP)
  tables (RotoWire, Dunkest) are JS-rendered and couldn't be fetched despite
  several tries — pivoted to something arguably better: real head-to-head
  history. Found Wilson has scored exactly 32 pts in BOTH her games vs
  Portland this season (verified). Built `shrink_toward_general()` — blends
  small-sample matchup history toward the general model using proper
  statistical shrinkage (weight = n/(n+k)), so a hot 2-game history pulls the
  projection up (28.4 -> 29.5) without overriding the broader model. Noted
  disclosed limitation: one game overlaps between the general 10-game sample
  and the 2-game matchup sample (not perfectly clean, but transparent about it).
- **Interactive mode added**: script now opens with a menu — run the 3-player
  demo, or enter a brand-new player's data interactively (name, team,
  opponent, game log, opponent def rating, optional matchup history). Tested
  end-to-end, correctly flags LOW confidence on a small test sample.
- The Desktop "Sports Betting Tools" launcher needs no changes — it just
  calls this script, so the new menu appears automatically.

## ▶ RESUME HERE

nba_props_model.py now runs on fully verified data end to end, 3 demo
players, interactive mode for new ones, small-sample-uncertainty and
matchup-history shrinkage built in. Next steps:
(1) add more players/opponents as worked examples, (2) consider proper
pace-adjusted defensive rating as a future refinement (would need
possessions/pace data per team, not yet sourced), (3) eventually build the
de-vig calculator (Phase 3) and a local frontend (Phase 4). ev_tool.py
(parlay/EV calculator) is separate and already working — this model feeds
probability estimates into that tool rather than replacing it. Both tools
are launchable via the "Sports Betting Tools" double-click launcher (copy
on Desktop, canonical copy in this folder).
