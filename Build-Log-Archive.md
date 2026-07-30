# Build Log Archive — Sports Betting / EV

Full chronological history of how this project was built, moved out of
CURRENT_STATE.md to keep that file lean. This is HISTORY (see [[Home]] rule
1) — for what's true *right now*, read CURRENT_STATE.md instead.

---

## 2026-07-28 — Exploratory phase

Talked through real matches/props (Tommy Paul vs Kamil Majchrzak, Jakub
Mensik vs Trevor Svajda, Citi Open) to build intuition before writing code.
Established: **user bets on PrizePicks**, not a standard sportsbook — fixed
multipliers on multi-pick entries, not decimal odds with vig:
- Power Play (all picks must hit): breakeven per-leg probability ~55–58%+
  (2-pick/3x ≈ 57.7%, 6-pick/37.5x ≈ 54.7%), not the ~52.4% breakeven of a
  standard -110 sportsbook line.
- Flex Play: partial hits pay out on a curve, more forgiving but still above
  a coinflip per leg.
- "Which side is favored" (>50%) is NOT sufficient for a good PrizePicks
  pick — need real confidence above ~55–58% per leg.

A 6-pick Power Play from that night was checked and confirmed LOST (2
coinflip legs missed).

## 2026-07-28 — EV tool v1 built

`ev_tool.py`: command-line calculator — enter legs + probability estimates,
computes combined hit probability (Power) or full payout distribution
(Flex), compares to the real PrizePicks breakeven, auto-logs to
Match-Notes.md. Verified against the 6-pick and a 3-pick baseball-only
example — matched the by-hand math exactly.

## 2026-07-28 — NBA/WNBA prediction model (new direction)

User bets most on NBA. Since NBA is off-season, built against WNBA
(in-season, same prop types) as a live test bed that transfers to NBA in
October. Staying free/manual-data, no paid odds API, "slow and steady,
learn as we go" pace.

Built `nba_props_model.py`: recency-weighted average, standard deviation,
normal-distribution probability calculator, opponent adjustment factor
(opponent's defensive rating / league average).

Tested on A'ja Wilson vs Portland Fire. Portland's 111.8 defensive rating
("worst in WNBA") was verified but turned out to be **pace-adjusted**,
while the league average used (102.0) was an unverified estimate on that
same basis — an apples-to-oranges mix caught and corrected (see below).

**Data reliability lesson learned**: fetch tools repeatedly fabricated
plausible-looking results for games that hadn't been played yet (e.g.
Collier vs Toronto claimed final 100-93 hours before tipoff). Rule: never
trust a "today's result" from a single fetch — cross-check with a second
independent search first.

## 2026-07-28 — League-average verification

Verified via covers.com team-defense table (all 15 WNBA teams): league
average points-allowed/game = **86.88**, Portland Fire = **90.19** (13th of
15, NOT worst) — replacing the earlier estimate and the mismatched
pace-adjusted number. Once corrected to one consistent metric, the
"favorable matchup" effect shrank a lot: adjustment factor 1.096 -> 1.038,
projection 30.0 -> 28.4.

**Lesson**: verify the METRIC matches on both sides of a ratio, not just
that each individual number is real.

## 2026-07-28 — More players added

Refactored to a data-driven `players` list. Added Caitlin Clark (huge stdev
10.4, very volatile) and Sabrina Ionescu (vs the actual worst
points-allowed/game team, biggest adjustment factor 1.075). Dropped
Napheesa Collier as a candidate — missed ~27 games this season (dual ankle
surgery), only one real 2026 game, too small a sample coming off major
injury.

## 2026-07-28 — Small-sample uncertainty refinement

Added `predictive_stdev()` (widens raw stdev by sqrt(1+1/n)) and
`sample_size_confidence()` (HIGH/MODERATE/LOW label based on n). At n=1 the
widening is mathematically undefined — confirms why Collier's 1-game sample
can't be modeled, not just an eyeball call. Standard "prediction interval
vs confidence interval" statistical distinction.

## 2026-07-28 — Matchup-history shrinkage + interactive mode

True league-wide position-vs-defense (DVP) tables (RotoWire, Dunkest) are
JS-rendered and couldn't be fetched reliably — pivoted to real head-to-head
history instead. Found Wilson scored exactly 32 pts in BOTH her games vs
Portland this season. Built `shrink_toward_general()` — blends small-sample
matchup history toward the general model via proper statistical shrinkage
(weight = n/(n+k)), pulling the projection up (28.4 -> 29.5) without
overriding the broader model. Noted disclosed limitation: one game overlaps
between the general 10-game sample and the 2-game matchup sample.

Interactive mode added: script opens with a menu — run the demo, or enter a
new player's data interactively. Tested end-to-end.

## 2026-07-28 — Scheduled daily cloud automation set up

Installed GitHub CLI (verified checksum), authenticated as `sebastianblade3`,
created repo `sebastianblade3/sports-betting-tools` (originally private),
pushed the project. Created a daily cloud routine (9am PT) to refresh real
data and push updates.

**Root cause of initial failures**: repeated `403` errors even after
connecting GitHub at claude.ai/customize/connectors. Turned out to be a
**private-repo scope issue** — switching the repo to PUBLIC fixed it
immediately. Repo is public now (code + betting projections only, no
personal/financial info).

**Important**: the cloud agent pushes to GitHub only — local vault files do
NOT auto-update. Someone needs to `git pull` to sync down to Obsidian.

## 2026-07-28 — MLB props model built + second automation

Extracted `stats_engine.py` — shared, sport-agnostic math pulled out of
nba_props_model.py so both sports use identical, tested code. Verified the
refactor produced byte-identical results.

Built `mlb_props_model.py` with two prop types: pitcher strikeouts (adjusted
by opposing team's K rate) and batter combined H+R+RBI (adjusted by
opposing starter's ERA). Real demo data: Troy Melton (last 10 starts via
ESPN gamelog — this CORRECTED an earlier stale "9 K in each of last two
starts" claim) vs Orioles; Ty France vs Lorenzen (6.91 ERA, verified).
League avg ERA (~4.10) moderately verified; league avg K/game (8.4) is an
explicit unverified estimate.

**Flagged honest limitation**: the batter ERA-ratio adjustment is cruder
than the NBA defense adjustment — applying the full ratio to a combined
3-stat category overstated the effect (94.8% vs an earlier qualitative ~65%
estimate). Documented as a known issue, not swept under the rug.

Desktop launcher updated (EV calculator, NBA/WNBA model, MLB model). Second
daily cloud routine created for MLB, same 9am PT schedule.

## 2026-07-28 — Elasticity dampening for MLB adjustments

Added `dampened_ratio()` — a ratio raised to a fractional "elasticity"
exponent, for when a matchup factor is real but not fully proportional.
Pitcher K factor: elasticity=0.7. Batter H+R+RBI factor: elasticity=0.5
(more dampened — combined stat mixes pitcher-dependent and
teammate-dependent pieces). Verified effect: Ty France's factor dropped
1.685 -> 1.298, probability 94.8% -> 86.9%. Noted honestly: 0.5/0.7 are
reasonable starting points, not precisely derived — a real backtest would
calibrate these properly. The "real" fix (separate hits/runs/RBI
sub-models) is a bigger future refinement.

## 2026-07-28 — De-vig calculator + situational/park factors

Built `devig_tool.py` (Phase 3 of the original roadmap): strips vig from
real two-sided American odds to get the market's TRUE implied probability,
compares against a model probability for edge. Tested on a real market
(Tigers -140 / Orioles +120): 3.79pp vig, true probs 56.2%/43.8%. Added to
Desktop launcher (5 options).

Added `SITUATIONAL_FACTORS` to stats_engine.py — injury/usage context as a
separate multiplier: healthy (1.0), playing through minor injury (0.90),
recently returned from injury (0.85), key teammate out (1.15). Rough
judgment-call starting points, not backtested. Applied to both sports.

Added MLB park factors to the batter model — real verified example: Petco
Park RHB run factor 0.97, confirmed Ty France bats right-handed. Already a
ratio-to-average, no elasticity dampening needed.

Considered height/weight-based physical mismatch modeling — decided against
it for a player's own projection (no clear standalone mechanism); MLB park
factors turned out to be the tractable real version of "physical mismatch"
for batters. NBA defender-height matchup data would need paywalled tracking
services (Synergy Sports-type) — not pursued.

## 2026-07-30 — Automation diagnostic

Two days after setup, `git pull` showed zero new commits from either daily
routine, despite both showing `last_fired_at` timestamps confirming they
did trigger. Confirmed independently via GitHub API (no new commits there
either) — ruled out a local git issue. Likely cause: read access (cloning)
was fixed by making the repo public, but write-back (commit + push) may
need separate credentials inside the cloud sandbox that were never
verified. Triggered a manual test run to diagnose live — see
CURRENT_STATE.md for the outcome.
