# Current State — Sports Betting / EV

Rewritten in place at every checkpoint (see [[Home]] rule 1). Full build
history and reasoning archived in [[Build-Log-Archive]] — this file is just
the current status.

## Status

Full toolset built and working, all in `Projects/Sports-Betting/`:
- `ev_tool.py` — EV/parlay calculator (PrizePicks payout math)
- `nba_props_model.py` — NBA/WNBA points prop model
- `mlb_props_model.py` — MLB props model (pitcher K's, batter H+R+RBI)
- `devig_tool.py` — strips vig from real odds, compares vs model probability
- `calibration_tool.py` — Brier score + bucketed calibration report, tracks
  whether stated probabilities actually match real outcomes over time
- `stats_engine.py` — shared math: recency weighting, predictive stdev,
  matchup shrinkage, elasticity-dampened ratios, situational/park factors

All launchable via "Sports Betting Tools" double-click launcher (Desktop +
canonical copy in this folder) — **now a real button-based GUI window**
(`launcher_gui.py`, tkinter), added 2026-07-31, instead of a typed-number
text menu. Clicking a button opens that tool in its own Terminal window.
Repo: `github.com/sebastianblade3/sports-betting-tools`
(public). Platform: **user bets on PrizePicks** — needs ~55-58%+ per-leg
confidence, not just >50% (see [[prizepicks_platform]] memory).

Two daily cloud routines (WNBA + MLB) were built but **disabled 2026-07-31**
after confirming they fired daily for 2+ days without ever producing a
commit — read (clone) access worked, write-back (commit+push) silently
never did. Back to manual/on-demand use of the tools for now. See
[[Build-Log-Archive]] for the full diagnostic. Routines still exist
(disabled, not deleted) at trig_01LeubQPFubYkh1qU6diLpKW (WNBA) and
trig_01RaDzAHsJaXdnGUCZAbZAXi (MLB) if worth debugging properly later.

## Known open items / honest caveats

- ~~League avg K/game unverified~~ **RESOLVED 2026-07-31**: verified 8.57
  from real per-team data (25/30 teams), was a flat 8.4 estimate.
- ~~No pace-adjusted NBA defense metric~~ **RESOLVED 2026-07-31**: computed
  real pace-adjusted DRTG by hand (points-allowed/game × pace, both
  independently verified) for all 15 WNBA teams. League avg 108.51. This
  also confirmed the original "Portland worst in WNBA" claim we'd flagged as
  mismatched was actually roughly right (114.21 by our own calc, 2nd-worst).
- ~~Batter H+R+RBI single crude elasticity~~ **PARTIALLY RESOLVED 2026-07-31**:
  split into separate hits/runs/rbi sub-models with differentiated elasticity
  (hits 0.6, runs/rbi 0.3 each — hits are more directly pitcher-dependent),
  summed for the final projection. Still judgment-call VALUES though (0.6,
  0.3, 0.7 for pitcher K's) — genuinely differentiated now, not backtested.
  `analyze_batter()` falls back to the old combined approach if only a
  combined game log is given (e.g. from interactive mode).
- Elasticity values (now 3 for batters + 1 for pitchers) and situational
  factors are still not backtested — this is what `calibration_tool.py`
  (new) is for, but needs real logged predictions + outcomes to accumulate
  over time before it can actually inform these values. Only 3 entries
  logged so far (all from 7/28) — nowhere near enough.
- Situational factors (injury/usage) are still rough presets, not
  calibrated — same story, needs calibration data over time.
- Position-specific defense (DVP) still not used — league tables are
  JS-rendered and unreachable; matchup-history shrinkage is the workaround.
- ~~Batter model only accounts for starter, ignores bullpen~~ **RESOLVED
  2026-07-31**: added `effective_opponent_era()` — blends starter ERA with
  bullpen ERA (65%/35% weighted, a round-number assumption about innings
  split, not precisely derived). Real find on Rockies specifically: bullpen
  ERA is genuinely volatile (3.77 in April vs 5.79 last-7-days as of 7/30) —
  used the more current number but flagged the volatility honestly rather
  than pretending it's a stable input. Full-season bullpen ERA was
  paywalled everywhere checked.
- ~~NBA: no season-long context, last-10 window could be skewed~~ **RESOLVED
  2026-07-31**: added `blend_recent_and_season()` (70/30 weighted toward
  recent form) to stats_engine.py. Real find: Wilson's last-10 average
  (27.4) was notably BELOW her verified season average (31.6) — this window
  happened to catch a cooler stretch — blend pulls her projection up to 28.7.
  Clark/Ionescu saw smaller effects since their recent/season averages were
  already close. This was the last of the original 3 refinement options
  offered early on (small-sample uncertainty, position-specific defense,
  this one) — all 3 now done in some form.

- ~~MLB missing season-avg blend + batter matchup-shrinkage; interactive
  mode behind the demo~~ **RESOLVED 2026-07-31**: brought MLB to full parity
  with NBA — season-avg blending added for both pitchers and batter
  sub-stats (real data: France's season hits/game 0.89, runs/game 0.40,
  rbi/game 0.56, all from a verified 82-game/73-hit/33-run/46-RBI season
  line — pulled his hot last-10 projection DOWN, opposite direction from
  Wilson's up-pull, same underlying lesson either way); matchup-history
  shrinkage added for batters (tested with synthetic data, works correctly);
  interactive mode rewritten to prompt for ALL of these (season avg, bullpen
  ERA, sub-stats vs combined choice, matchup history) for both pitchers and
  batters — no longer behind the hardcoded demo data.
- **Real calibration data point found**: while researching France's season
  numbers, discovered the actual 7/28 Padres-Rockies box score already
  existed — France went 1-for-5, 1 R, 0 RBI = 2 combined, clearing the 1.5
  line (a HIT). Logged to calibration_log.csv with the model's estimate at
  the time (83.8%) — calibration_log.csv now has 4 real entries.

## Done (2026-08-01): fixed the "Set Up Legs" rendering bug — root cause found

Started converting tools to real GUI forms (buttons/fields instead of typing
into Terminal) — built `ev_tool_gui.py` first. Hit a real, persistent bug:
clicking "Set Up Legs" (or even the automatic initial build) showed nothing
— the leg entry fields never appeared, though the button itself visually
pressed correctly.

**Root cause, confirmed by direct Tk introspection**: the system Python
(`/usr/bin/python3`, from Xcode Command Line Tools) bundles **Tcl/Tk 8.5.9,
from 2009** — a well-known-buggy, ancient version with real widget-rendering
issues on modern macOS (especially after dynamically adding widgets post
initial window display). Confirmed the widgets WERE being created correctly
in Tk's own model (mapped, correctly sized) but weren't visually painting.

**Fix**: installed modern Python 3.13.9 from python.org (official installer,
MD5-verified against the published checksum) — ships with **Tcl/Tk 8.6.17**,
which fixed the bug completely (confirmed visually — all leg rows now render
correctly). Updated both `Sports Betting Tools.command` launchers (Desktop +
vault) to use `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3`
explicitly, falling back to system `python3` if that path doesn't exist.
Also added `update_idletasks()` after building leg rows in `ev_tool_gui.py`
as a defensive redraw-forcing measure (harmless either way).

**Important for future GUI conversions**: any new `*_gui.py` tool must be
tested with the MODERN Python — the old system Python will likely show the
same rendering bugs for any dynamically-created widgets.

## Done (2026-08-01): started converting tools to real GUI forms

`ev_tool_gui.py` built and tested working (Power/Flex radio buttons, leg
count spinner, dynamic label+probability entry rows, Calculate button,
Log-to-Match-Notes button) — reuses `evaluate_power`/`evaluate_flex` from
`ev_tool.py` unchanged, verified against the known 3-pick baseball example
(24.82% combined, matches exactly). `launcher_gui.py` now distinguishes
GUI-converted tools (opens directly in-app) from not-yet-converted ones
(still opens a Terminal running the old CLI script) via a `TOOLS` list with
`"gui"`/`"terminal"` markers — makes it easy to convert the remaining 4
tools (NBA/WNBA model, MLB model, De-Vig, Calibration Tracker) one at a time.

## ▶ RESUME HERE

**GUI conversion in progress**: EV Calculator done and working (with the
Python version fix). Next: convert De-Vig Calculator, then Calibration
Tracker, then the bigger ones (NBA/WNBA model, MLB model — most fields).
Remember to test each with the modern Python
(`/Library/Frameworks/Python.framework/Versions/3.13/bin/python3`), not the
system one, to avoid re-hitting the Tk 8.5 rendering bug.

Automation disabled, using tools manually/on-demand. NBA and MLB models are
at full feature parity (season blend, matchup shrinkage, situational
factors, opponent adjustment all compose for both sports), interactive mode
supports every field the demo data does. Remaining honest gaps (elasticity
values, situational factor presets) genuinely need calibration data over
time — **log every real prediction + outcome into calibration_log.csv going
forward** (only 4 entries so far) so calibration_tool.py's report actually
becomes meaningful.
