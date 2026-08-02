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

## 2026-08-01 — Four refinement ideas, one by one

User asked for refinement ideas; picked all 4 offered, done in order: (1)
de-vig integration, (2) Kelly criterion sizing, (3) bankroll/ROI tracker,
(4) home/away + rest-days context.

**De-vig integration**: added `check_prop_edge()`/`prompt_market_check()` to
`devig_tool.py` — after either prop model shows its probability table, you
can pick a line and check it against real market odds right there. Fixed a
redundant double "check odds?" prompt via an `already_confirmed` param.

**Kelly criterion**: built `kelly_tool.py` — `kelly_fraction_binary()`
(closed-form, verified against the textbook 60%-at-even-money case, exactly
0.2000) and `kelly_fraction_general()` (Flex Play has no closed form since
it's multi-outcome, uses ternary/golden-section search maximizing expected
log wealth — verified: real 3-pick edge gives 16.9%, all-coinflip bet
correctly returns 0%). Defaults to quarter-Kelly, not full Kelly — standard
risk-reduction practice. Integrated into `ev_tool.py` right after a +EV
result.

**Bankroll/ROI tracker**: built `bankroll_tool.py` + `bankroll_log.csv` —
logs real bets, computes payout/profit, running report (total staked/
returned, net profit, ROI%, win rate, cumulative profit). Deliberately
separate from `calibration_tool.py` (that tracks probability accuracy, this
tracks actual money — you can be well-calibrated and still lose on bad
sizing, or vice versa). Verified with synthetic data then cleared before
committing (real log started genuinely empty).

**Home/away + rest-days context**: NBA/WNBA got `HOME_AWAY_FACTOR` (home
1.03/away 0.97, from real research on 0.04-0.16 pts/min home scoring boost)
and `REST_FACTOR` (back-to-back 0.96, from documented 3-5% scoring decline
on zero rest). MLB got `BATTER_HOME_AWAY_FACTOR` (same 1.03/0.97, from
documented 30-50pt home/away OPS gaps) and `PITCHER_REST_FACTOR` (short rest
0.95 — honestly flagged as the weakest-evidence factor in the project, an
analogy to the NBA number rather than a direct MLB citation). All wired into
the existing situational_factor pipeline for both sports.

## 2026-08-01/02 — Converted all 7 CLI tools to real button/form GUIs

Starting point: a typed-number text-menu CLI for every tool, launched via
`launcher_gui.py` which only distinguished "gui" (in-app window) vs
"terminal" (opens a new Terminal running the old script) per tool.

**Blocking bug hit first**: `ev_tool_gui.py` (the first conversion)
wouldn't render its dynamically-added leg-entry widgets after clicking "Set
Up Legs" — direct Tk introspection confirmed the widgets WERE created and
mapped correctly, just not painting. Root cause: system Python's bundled
Tcl/Tk 8.5.9 (2009) has known widget-rendering bugs on modern macOS. Fixed
by installing Python 3.13.9 from python.org (MD5-verified installer, ships
Tcl/Tk 8.6.17) and repointing both `Sports Betting Tools.command` launchers
at it explicitly (falling back to system `python3` if that path is missing).
**Every GUI tool from this point on was tested with the modern Python
path**, not the system one.

Converted in order, each following the same pattern — reuse the existing
tested calculation functions directly (never reimplement the math), verify
the GUI's output is identical to the CLI's output on a known/verified
example, take a screenshot to confirm the layout actually renders, then wire
into `launcher_gui.py`'s `TOOLS` list and commit:

1. **EV/Parlay Calculator** (`ev_tool_gui.py`) — Power/Flex radio buttons,
   leg-count spinner, dynamic label+probability rows, Kelly stake
   recommendation on +EV. Verified against the known 3-pick example.
2. **De-Vig Calculator** (`devig_tool_gui.py`) — verified against the real
   Tigers(-140)/Orioles(+120) market (56.2%/43.8%, 3.79pp vig).
3. **Kelly Stake Sizing** (`kelly_tool_gui.py`) — Power/Flex mode selector,
   dynamic leg-probability rows for Flex. Verified: p=0.60/3.0x -> 40% full
   Kelly, $100 stake on $1000 bankroll at quarter-Kelly.
4. **Bankroll/ROI Tracker** (`bankroll_tool_gui.py`) — log-a-bet form +
   live report. Verified on a temp log ($10@5x won + $20@3x lost -> +66.7%
   ROI); confirmed the real `bankroll_log.csv` was untouched by testing.
5. **Calibration Tracker** (`calibration_tool_gui.py`) — log-a-prediction
   form + live Brier score/bucket report. Verified Brier score math on a
   temp log; confirmed the real `calibration_log.csv` (4 verified entries,
   including Ty France's real 7/28 result) displays correctly and was
   untouched.
6. **NBA/WNBA Points Prop Model** (`nba_props_model_gui.py`) — full form
   (games, opponent def rating, season avg, matchup history, situational
   factor, home/away, rest) plus a market-check panel with a line dropdown
   populated after calculating. Verified byte-for-byte identical output
   against the real `analyze_player()` call on the verified A'ja Wilson vs
   Portland Fire example (30.7 final projection).
7. **MLB Props Model** (`mlb_props_model_gui.py`) — most complex conversion:
   a Pitcher/Batter mode selector, with a further Separate-substats/Combined
   sub-mode for batters (sub-stat mode supports optional bullpen ERA blend
   and park factor). Verified byte-for-byte identical output against the
   real `analyze_pitcher()`/`analyze_batter()` calls on the verified Troy
   Melton (6.4 K projection) and Ty France (3.5 H+R+RBI projection)
   examples, including the market-check edge math.

End state: `launcher_gui.py` now opens every tool as a real in-app GUI form
— no typing into Terminal anywhere in the toolset. The original text-menu
version is preserved untouched in `Snapshot-2026-07-31/` and
`Sports Betting Tools (Text Menu).command` on the Desktop per explicit
standing instruction — never to be modified.
