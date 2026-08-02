# Current State — Sports Betting / EV

Rewritten in place at every checkpoint (see [[Home]] rule 1). Full build
history and reasoning archived in [[Build-Log-Archive]] — this file is just
the current status.

## Status

Full toolset built and working, all in `Projects/Sports-Betting/`:
- `ev_tool.py` — EV/parlay calculator (PrizePicks payout math), integrates
  Kelly stake sizing on +EV results
- `nba_props_model.py` — NBA/WNBA points prop model (season blend, matchup
  shrinkage, situational/home-away/rest factors, opponent def rating)
- `mlb_props_model.py` — MLB props model (pitcher K's, batter H+R+RBI
  sub-stats, bullpen blend, park factor) — full feature parity with NBA
- `devig_tool.py` — strips vig from real odds, compares vs model probability
- `kelly_tool.py` — Kelly criterion stake sizing (binary + multi-outcome)
- `bankroll_tool.py` + `bankroll_log.csv` — real bet log, ROI/win-rate report
- `calibration_tool.py` + `calibration_log.csv` — Brier score + bucketed
  calibration report (4 real logged entries so far)
- `stats_engine.py` — shared math: recency weighting, predictive stdev,
  matchup shrinkage, elasticity-dampened ratios, situational/park factors

**All 7 tools are now real button/form GUIs** (`*_gui.py`, tkinter) —
launched via `launcher_gui.py`, which opens every tool directly in-app with
no typing into Terminal anywhere. Each GUI reuses its tool's existing tested
functions directly (never reimplements the math) and was verified to
produce byte-for-byte identical output to the original CLI on a known
example before being wired in. Full conversion history (including the Tk
8.5-vs-8.6 rendering bug and its fix) is in [[Build-Log-Archive]].

Both the launcher and every `*_gui.py` **must be run with the modern Python**
(`/Library/Frameworks/Python.framework/Versions/3.13/bin/python3`) — the
system Python's bundled Tcl/Tk 8.5.9 has real widget-rendering bugs. Both
`Sports Betting Tools.command` launchers (Desktop + vault) already point at
this path, falling back to system `python3` if it's missing.

The original text-menu CLI version is preserved untouched in
`Snapshot-2026-07-31/` and `Sports Betting Tools (Text Menu).command` on the
Desktop, per explicit standing instruction — **never modify these**.

Repo: `github.com/sebastianblade3/sports-betting-tools` (public). Platform:
**user bets on PrizePicks** — needs ~55-58%+ per-leg confidence, not just
>50% (see [[prizepicks_platform]] memory).

Two daily cloud routines (WNBA + MLB) were built but **disabled 2026-07-31**
after confirming write-back (commit+push) never worked despite firing daily.
Back to manual/on-demand use of the tools. Routines still exist (disabled,
not deleted) at trig_01LeubQPFubYkh1qU6diLpKW (WNBA) and
trig_01RaDzAHsJaXdnGUCZAbZAXi (MLB) if worth debugging properly later.

## Known open items / honest caveats

- Elasticity values (3 for batters, 1 for pitchers) and situational factors
  are judgment-call estimates, not backtested — this is what
  `calibration_tool.py` is for, but needs more logged predictions +
  outcomes to accumulate before it can meaningfully inform these values.
  Only 4 entries logged so far.
- Position-specific defense (DVP) still not used — league tables are
  JS-rendered and unreachable; matchup-history shrinkage is the workaround.
- Pitcher short-rest factor (MLB) is honestly the weakest-evidence factor
  in the project — an analogy to the NBA back-to-back effect, not a direct
  MLB citation (see [[Build-Log-Archive]] for detail).
- MLB starter/bullpen ERA blend weight (65/35) is a round-number assumption
  about innings split, not precisely derived per pitcher.

## ▶ RESUME HERE

All 7 tools are converted to GUIs, tested, and pushed — this was the last
open task from the "yes lets keep going for all of the tools" request. No
pending build work right now.

Next natural step, if the user wants to keep building: start actually using
the tools for real, current games and **log every real prediction +
outcome into calibration_log.csv** — only 4 entries exist so far, nowhere
near enough for calibration_tool.py's report to be meaningful. That's the
main lever left to actually validate (or correct) the judgment-call
elasticity/situational values above.
