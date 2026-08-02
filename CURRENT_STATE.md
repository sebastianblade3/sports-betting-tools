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
  calibration report (4 real settled entries so far). Supports **pending**
  predictions (logged before the outcome is known, `actual_outcome` blank)
  via `settle_entry()` — settle once the real result is in.
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

**Added 2026-08-02: Claude-assisted auto-fill.** `nba_props_model_gui.py`
and `mlb_props_model_gui.py` both have `prefill_window(app, data)` /
`launch_prefilled(data)`. Workflow: tell Claude a player's name in chat,
Claude researches + verifies their real current stats (same standard as the
demo data — cross-checked, honestly flagged if a number is weaker quality),
then calls `launch_prefilled()` to open the form already filled in. It never
auto-clicks Calculate — the human reviews the pre-filled numbers first. This
was a deliberate choice over building a scraper or paid API directly into
the app: keeps the project's standing verify-before-trust practice intact,
costs nothing extra, at the cost of only working inside a Claude Code
session (not a fully standalone one-click app feature).

**Added 2026-08-02: "Log this prediction" — closes the projection-to-
calibration loop.** `nba_props_model_gui.py` and `mlb_props_model_gui.py`
both have a "Log this prediction for calibration" panel next to the
market-check panel — after calculating, pick the line (same dropdown the
market check uses) and click Log Prediction to write it to
`calibration_log.csv` as a **pending** entry (outcome filled in later via
`calibration_tool_gui.py`'s new "Settle a pending prediction" panel). This
was the highest-priority gap identified when auditing the toolset: the
calibration and bankroll logs existed but nothing fed them without a
separate manual re-typing step, so in practice they'd stayed nearly empty.

Also fixed while building this: both prop model GUIs were calling
`self.root.geometry()` too early (before all widgets existed), and on this
Retina display (2560x1664 physical, ~832 logical px of usable height)
macOS was silently clamping the window well short of the requested size —
cutting the bottom of the form off entirely with no visible error. Fixed
by wrapping the window content in a scrollable canvas (mouse-wheel enabled)
instead of fighting fixed pixel heights. **Any future new panels added to
these two GUIs should go inside the existing `content` frame**, not a bare
`root`-parented widget, or they'll silently render off the visible area
again.

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

All 7 tools are converted to GUIs, the Claude-assisted auto-fill workflow
is built, and the projection-to-calibration logging loop is closed — all
tested and pushed. No pending build work right now.

Next natural step: actually use the tools on real, current games — research
a player, log the prediction as pending, settle it once the game result is
in. That's the only way `calibration_log.csv` grows past its current 4
entries, which is the main lever left to validate (or correct) the
judgment-call elasticity/situational values in the honest-caveats section
above. Once there's a real backlog of settled predictions, that's also the
natural trigger point for the user's longer-term goal — wiring in a real
stats API so the app can run the whole pipeline itself (see
[[sports_betting_api_roadmap]] memory) — since a real API's fetched numbers
would need the same kind of correctness check this calibration data
provides.
