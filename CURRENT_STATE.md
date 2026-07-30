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
- `stats_engine.py` — shared math: recency weighting, predictive stdev,
  matchup shrinkage, elasticity-dampened ratios, situational/park factors

All launchable via "Sports Betting Tools" double-click launcher (Desktop +
canonical copy in this folder). Repo: `github.com/sebastianblade3/sports-betting-tools`
(public). Platform: **user bets on PrizePicks** — needs ~55-58%+ per-leg
confidence, not just >50% (see [[prizepicks_platform]] memory).

Two daily cloud routines (WNBA + MLB, both 9am PT) meant to auto-refresh
player data and push updates.

## Known open items / honest caveats

- League avg K/game (8.4) for MLB is an unverified estimate — worth
  re-checking if a clean source turns up.
- Batter H+R+RBI adjustment elasticity (0.5) and pitcher K elasticity (0.7)
  are judgment calls, not backtested against real results.
- No pace-adjusted (per-100-possessions) NBA defense metric — using raw
  points-allowed/game instead; league DVP (position-vs-defense) tables are
  JS-rendered and unreachable, using matchup-history shrinkage instead.
- Situational factors (injury/usage) are rough presets, not calibrated.

## ▶ RESUME HERE

**2026-07-30**: automated daily routines fired (confirmed via `last_fired_at`
timestamps) but produced ZERO commits on GitHub over 2 days — confirmed via
both local `git pull` and the GitHub API directly, ruling out a local git
issue. Likely cause: write-back (commit+push) credentials inside the cloud
sandbox were never verified, only read (clone) access. Triggered a manual
test run (session `cse_01TLkSTnXaWgeiG3toRcjomw`) to diagnose live — **check
the repo for a new commit to see if it resolved itself, or investigate
push credentials in the cloud environment if it didn't.**
