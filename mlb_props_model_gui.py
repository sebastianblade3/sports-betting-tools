#!/usr/bin/env python3
"""
Button/form version of the MLB props model — same tested math as
mlb_props_model.py and stats_engine.py (project, pitcher_k_adjustment_factor,
batter_matchup_adjustment_factor, effective_opponent_era,
shrink_toward_general, prob_over, blend_recent_and_season, devig_two_way,
edge all imported directly, not reimplemented).
"""

import tkinter as tk
from tkinter import messagebox

from stats_engine import (
    weighted_average,
    prob_over,
    shrink_toward_general,
    project,
    blend_recent_and_season,
    SITUATIONAL_FACTORS,
)
from mlb_props_model import (
    pitcher_k_adjustment_factor,
    batter_matchup_adjustment_factor,
    effective_opponent_era,
    STARTER_WEIGHT,
    BULLPEN_WEIGHT,
    HITS_ELASTICITY,
    RUNS_ELASTICITY,
    RBI_ELASTICITY,
    BATTER_HOME_AWAY_FACTOR,
    PITCHER_REST_FACTOR,
    LEAGUE_AVG_ERA,
    LEAGUE_AVG_K_PER_GAME,
)
from devig_tool import devig_two_way, edge

SITUATION_LABELS = {
    "healthy": "Healthy",
    "playing_through_minor_injury": "Playing through a minor injury",
    "recently_returned_from_injury": "Recently returned from injury",
    "key_teammate_out": "A key teammate is out",
}


def parse_list(raw):
    parts = [x.strip() for x in raw.split(",") if x.strip()]
    return [int(x) for x in parts]


def situation_dropdown(parent, var):
    menu = tk.OptionMenu(parent, var, *SITUATION_LABELS.keys())
    menu["menu"].delete(0, "end")
    for key, label in SITUATION_LABELS.items():
        menu["menu"].add_command(label=label, command=lambda k=key: var.set(k))
    return menu


class MLBPropsModelWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("MLB Props Model")
        self.root.geometry("660x960")

        self.line_probs = {}
        self.mode = tk.StringVar(value="pitcher")
        self.batter_submode = tk.StringVar(value="combined")

        mode_frame = tk.Frame(root, pady=8)
        mode_frame.pack(fill="x")
        tk.Label(mode_frame, text="Prop type:").pack(side="left", padx=10)
        tk.Radiobutton(mode_frame, text="Pitcher (strikeouts)", variable=self.mode, value="pitcher",
                       command=self.rebuild_inputs).pack(side="left")
        tk.Radiobutton(mode_frame, text="Batter (H+R+RBI)", variable=self.mode, value="batter",
                       command=self.rebuild_inputs).pack(side="left")

        self.inputs_frame = tk.Frame(root)
        self.inputs_frame.pack(fill="x")

        tk.Button(root, text="Calculate Projection", width=22, command=self.calculate).pack(pady=8)

        market_frame = tk.LabelFrame(root, text="Optional: check a line against real market odds", padx=10, pady=8)
        market_frame.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(market_frame, text="Line:").grid(row=0, column=0, sticky="w", padx=5)
        self.line_var = tk.StringVar(value="")
        self.line_menu = tk.OptionMenu(market_frame, self.line_var, "")
        self.line_menu.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(market_frame, text="Over odds:").grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self.over_odds_entry = tk.Entry(market_frame, width=10)
        self.over_odds_entry.grid(row=1, column=1, sticky="w", padx=5, pady=3)

        tk.Label(market_frame, text="Under odds:").grid(row=2, column=0, sticky="w", padx=5, pady=3)
        self.under_odds_entry = tk.Entry(market_frame, width=10)
        self.under_odds_entry.grid(row=2, column=1, sticky="w", padx=5, pady=3)

        tk.Button(market_frame, text="Check Edge", command=self.check_edge).grid(row=3, column=0, columnspan=2, pady=6)

        output_frame = tk.Frame(root)
        output_frame.pack(padx=10, pady=(0, 10), fill="both", expand=True)
        scrollbar = tk.Scrollbar(output_frame)
        scrollbar.pack(side="right", fill="y")
        self.output = tk.Text(output_frame, height=16, width=72, wrap="word", yscrollcommand=scrollbar.set)
        self.output.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.output.yview)

        self.rebuild_inputs()

    # ---------- form construction ----------

    def rebuild_inputs(self):
        for widget in self.inputs_frame.winfo_children():
            widget.destroy()

        if self.mode.get() == "pitcher":
            self.build_pitcher_form()
        else:
            self.build_batter_form()

    def build_pitcher_form(self):
        f = self.inputs_frame
        r = 0
        tk.Label(f, text="Pitcher name:").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.p_name = tk.Entry(f, width=28)
        self.p_name.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(f, text="Team:").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.p_team = tk.Entry(f, width=28)
        self.p_team.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(f, text="Tonight's opponent:").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.p_opponent = tk.Entry(f, width=28)
        self.p_opponent.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(f, text="Last N starts' strikeouts\n(comma-separated, most recent first):").grid(
            row=r, column=0, sticky="w", padx=10, pady=3
        )
        self.p_games = tk.Entry(f, width=28)
        self.p_games.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(f, text="Opponent's strikeouts/game (as hitters):").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.p_opp_k = tk.Entry(f, width=28)
        self.p_opp_k.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(f, text="League avg K/game:").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.p_league_avg = tk.Entry(f, width=28)
        self.p_league_avg.grid(row=r, column=1, padx=10, pady=3)
        self.p_league_avg.insert(0, str(LEAGUE_AVG_K_PER_GAME))
        r += 1

        tk.Label(f, text="Season K/start average (optional):").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.p_season_avg = tk.Entry(f, width=28)
        self.p_season_avg.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(f, text="Matchup history vs opponent\n(comma-separated, optional):").grid(
            row=r, column=0, sticky="w", padx=10, pady=3
        )
        self.p_matchup = tk.Entry(f, width=28)
        self.p_matchup.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(f, text="Situational factor tonight:").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.p_situation = tk.StringVar(value="healthy")
        situation_dropdown(f, self.p_situation).grid(row=r, column=1, sticky="w", padx=10, pady=3)
        r += 1

        self.p_short_rest = tk.BooleanVar(value=False)
        tk.Checkbutton(f, text="Pitching on short rest (4 days or fewer)", variable=self.p_short_rest).grid(
            row=r, column=0, columnspan=2, sticky="w", padx=10, pady=3
        )

    def build_batter_form(self):
        f = self.inputs_frame
        r = 0
        tk.Label(f, text="Batter name:").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.b_name = tk.Entry(f, width=28)
        self.b_name.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(f, text="Team:").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.b_team = tk.Entry(f, width=28)
        self.b_team.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(f, text="Tonight's opposing starter:").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.b_opp_pitcher = tk.Entry(f, width=28)
        self.b_opp_pitcher.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(f, text="Stat log format:").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        submode_frame = tk.Frame(f)
        submode_frame.grid(row=r, column=1, sticky="w", padx=10, pady=3)
        tk.Radiobutton(submode_frame, text="Separate hits/runs/rbi", variable=self.batter_submode,
                       value="separate", command=self.rebuild_batter_substats).pack(side="left")
        tk.Radiobutton(submode_frame, text="Combined H+R+RBI", variable=self.batter_submode,
                       value="combined", command=self.rebuild_batter_substats).pack(side="left")
        r += 1

        self.batter_substats_frame = tk.Frame(f)
        self.batter_substats_frame.grid(row=r, column=0, columnspan=2, sticky="w")
        r += 1
        self.batter_substats_row_start = r

        self.rebuild_batter_substats()

        # remaining common batter fields, placed after the substats frame
        common_start = r + 6  # substats frame uses up to ~5 rows internally
        tk.Label(f, text="Opposing starter's ERA:").grid(row=common_start, column=0, sticky="w", padx=10, pady=3)
        self.b_opp_era = tk.Entry(f, width=28)
        self.b_opp_era.grid(row=common_start, column=1, padx=10, pady=3)

        tk.Label(f, text="Opponent's bullpen ERA (optional):").grid(row=common_start + 1, column=0, sticky="w", padx=10, pady=3)
        self.b_bullpen_era = tk.Entry(f, width=28)
        self.b_bullpen_era.grid(row=common_start + 1, column=1, padx=10, pady=3)

        tk.Label(f, text="League avg ERA:").grid(row=common_start + 2, column=0, sticky="w", padx=10, pady=3)
        self.b_league_avg = tk.Entry(f, width=28)
        self.b_league_avg.grid(row=common_start + 2, column=1, padx=10, pady=3)
        self.b_league_avg.insert(0, str(LEAGUE_AVG_ERA))

        tk.Label(f, text="Tonight's park factor\n(1.0=neutral, e.g. 0.97 or 1.12):").grid(
            row=common_start + 3, column=0, sticky="w", padx=10, pady=3
        )
        self.b_park_factor = tk.Entry(f, width=28)
        self.b_park_factor.grid(row=common_start + 3, column=1, padx=10, pady=3)
        self.b_park_factor.insert(0, "1.0")

        tk.Label(f, text="Matchup history vs opponent\n(comma-separated, optional):").grid(
            row=common_start + 4, column=0, sticky="w", padx=10, pady=3
        )
        self.b_matchup = tk.Entry(f, width=28)
        self.b_matchup.grid(row=common_start + 4, column=1, padx=10, pady=3)

        tk.Label(f, text="Situational factor tonight:").grid(row=common_start + 5, column=0, sticky="w", padx=10, pady=3)
        self.b_situation = tk.StringVar(value="healthy")
        situation_dropdown(f, self.b_situation).grid(row=common_start + 5, column=1, sticky="w", padx=10, pady=3)

        tk.Label(f, text="Home or away tonight:").grid(row=common_start + 6, column=0, sticky="w", padx=10, pady=3)
        home_away_frame = tk.Frame(f)
        home_away_frame.grid(row=common_start + 6, column=1, sticky="w", padx=10, pady=3)
        self.b_home_away = tk.StringVar(value="neutral")
        tk.Radiobutton(home_away_frame, text="Home", variable=self.b_home_away, value="home").pack(side="left")
        tk.Radiobutton(home_away_frame, text="Away", variable=self.b_home_away, value="away").pack(side="left")
        tk.Radiobutton(home_away_frame, text="N/A", variable=self.b_home_away, value="neutral").pack(side="left")

    def rebuild_batter_substats(self):
        for widget in self.batter_substats_frame.winfo_children():
            widget.destroy()

        if self.batter_submode.get() == "separate":
            tk.Label(self.batter_substats_frame, text="Last N games' HITS (comma-separated):").grid(
                row=0, column=0, sticky="w", padx=10, pady=2
            )
            self.b_hits = tk.Entry(self.batter_substats_frame, width=28)
            self.b_hits.grid(row=0, column=1, padx=10, pady=2)

            tk.Label(self.batter_substats_frame, text="Last N games' RUNS (comma-separated):").grid(
                row=1, column=0, sticky="w", padx=10, pady=2
            )
            self.b_runs = tk.Entry(self.batter_substats_frame, width=28)
            self.b_runs.grid(row=1, column=1, padx=10, pady=2)

            tk.Label(self.batter_substats_frame, text="Last N games' RBI (comma-separated):").grid(
                row=2, column=0, sticky="w", padx=10, pady=2
            )
            self.b_rbi = tk.Entry(self.batter_substats_frame, width=28)
            self.b_rbi.grid(row=2, column=1, padx=10, pady=2)

            tk.Label(self.batter_substats_frame, text="Season avg hits/game (optional):").grid(
                row=3, column=0, sticky="w", padx=10, pady=2
            )
            self.b_season_hits = tk.Entry(self.batter_substats_frame, width=28)
            self.b_season_hits.grid(row=3, column=1, padx=10, pady=2)

            tk.Label(self.batter_substats_frame, text="Season avg runs/game (optional):").grid(
                row=4, column=0, sticky="w", padx=10, pady=2
            )
            self.b_season_runs = tk.Entry(self.batter_substats_frame, width=28)
            self.b_season_runs.grid(row=4, column=1, padx=10, pady=2)

            tk.Label(self.batter_substats_frame, text="Season avg RBI/game (optional):").grid(
                row=5, column=0, sticky="w", padx=10, pady=2
            )
            self.b_season_rbi = tk.Entry(self.batter_substats_frame, width=28)
            self.b_season_rbi.grid(row=5, column=1, padx=10, pady=2)
        else:
            tk.Label(self.batter_substats_frame, text="Last N games' combined H+R+RBI\n(comma-separated):").grid(
                row=0, column=0, sticky="w", padx=10, pady=2
            )
            self.b_games = tk.Entry(self.batter_substats_frame, width=28)
            self.b_games.grid(row=0, column=1, padx=10, pady=2)

            tk.Label(self.batter_substats_frame, text="Season avg combined H+R+RBI (optional):").grid(
                row=1, column=0, sticky="w", padx=10, pady=2
            )
            self.b_season_avg = tk.Entry(self.batter_substats_frame, width=28)
            self.b_season_avg.grid(row=1, column=1, padx=10, pady=2)

    # ---------- calculation ----------

    def calculate(self):
        try:
            if self.mode.get() == "pitcher":
                self._calculate_pitcher()
            else:
                self._calculate_batter()
        except Exception as e:
            messagebox.showerror("Something went wrong", f"{type(e).__name__}: {e}")

    def _calculate_pitcher(self):
        name = self.p_name.get().strip() or "Pitcher"
        team = self.p_team.get().strip() or "Team"
        opponent = self.p_opponent.get().strip() or "Opponent"

        try:
            games = parse_list(self.p_games.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Strikeouts must be whole numbers, comma-separated.")
            return
        if len(games) < 3:
            messagebox.showerror("Not enough starts", "Need at least 3 starts to compute a standard deviation.")
            return

        try:
            opp_k = float(self.p_opp_k.get().strip())
            league_avg_k = float(self.p_league_avg.get().strip())
        except ValueError:
            messagebox.showerror("Invalid input", "Enter valid numbers for opponent/league K/game.")
            return

        season_avg_raw = self.p_season_avg.get().strip()
        season_avg = float(season_avg_raw) if season_avg_raw else None

        matchup_raw = self.p_matchup.get().strip()
        matchup_history = parse_list(matchup_raw) if matchup_raw else []

        situation = self.p_situation.get()
        rest = "short_rest" if self.p_short_rest.get() else "normal"

        n = len(games)
        flat_avg = sum(games) / n
        w_avg = weighted_average(games)
        context_factor = SITUATIONAL_FACTORS.get(situation, 1.0) * PITCHER_REST_FACTOR.get(rest, 1.0)

        projection_no_adj, raw_stdev, pred_stdev, confidence = project(games, season_avg=season_avg)
        factor = pitcher_k_adjustment_factor(opp_k, league_avg_k)
        projection_adj, _, _, _ = project(
            games, adjustment_factor=factor, situational_factor=context_factor, season_avg=season_avg
        )
        widening_pct = (pred_stdev / raw_stdev - 1) * 100

        lines = [f"=== {name} ({team}) vs {opponent} — STRIKEOUTS ==="]
        lines.append(f"Last {n} starts: {games}")
        avg_line = f"Flat average: {flat_avg:.1f}  |  Weighted average: {w_avg:.1f}"
        if season_avg is not None:
            blended_avg = blend_recent_and_season(w_avg, season_avg)
            avg_line += f"  |  Season avg: {season_avg:.1f}  |  Blended (70/30): {blended_avg:.1f}"
        lines.append(avg_line)
        lines.append(
            f"Raw stdev: {raw_stdev:.1f}  |  Predictive stdev: {pred_stdev:.1f} (+{widening_pct:.1f}% for sample-size uncertainty)"
        )
        lines.append(f"Sample size confidence: {confidence}")
        lines.append(f"Opponent K/game: {opp_k}  |  League avg: {league_avg_k}  |  Factor: {factor:.3f}")
        if situation != "healthy":
            lines.append(f"Situational factor ({situation}): {SITUATIONAL_FACTORS.get(situation, 1.0):.2f}")
        if rest != "normal":
            lines.append(f"Rest factor ({rest}): {PITCHER_REST_FACTOR.get(rest, 1.0):.2f}")
        lines.append(f"Projection: {projection_no_adj:.1f} (no adj) -> {projection_adj:.1f} (adjusted)")

        final_projection = projection_adj
        if matchup_history:
            m_n = len(matchup_history)
            m_avg = sum(matchup_history) / m_n
            blended, weight_specific = shrink_toward_general(m_avg, m_n, projection_adj)
            lines.append(f"Matchup history vs {opponent}: {matchup_history} (avg {m_avg:.1f}, n={m_n})")
            lines.append(f"Shrinkage weight on matchup history: {weight_specific:.1%}")
            lines.append(f"Projection: {projection_adj:.1f} -> {blended:.1f} (matchup-blended)")
            final_projection = blended

        center = round(final_projection)
        prop_lines = [center - 3 + i for i in range(0, 7, 2)]
        self.line_probs = {}
        for line in prop_lines:
            line_half = line - 0.5
            p_over = prob_over(line_half, final_projection, pred_stdev)
            self.line_probs[line_half] = p_over
            lines.append(f"  Over {line_half}: {p_over:.1%} chance")

        self._render_output(lines, list(self.line_probs.keys()))

    def _calculate_batter(self):
        name = self.b_name.get().strip() or "Batter"
        team = self.b_team.get().strip() or "Team"
        opponent_pitcher = self.b_opp_pitcher.get().strip() or "Opposing pitcher"

        try:
            opp_era = float(self.b_opp_era.get().strip())
            league_avg_era = float(self.b_league_avg.get().strip())
            park_factor = float(self.b_park_factor.get().strip() or "1.0")
        except ValueError:
            messagebox.showerror("Invalid input", "Enter valid numbers for ERA/park factor.")
            return

        bullpen_raw = self.b_bullpen_era.get().strip()
        bullpen_era = float(bullpen_raw) if bullpen_raw else None

        matchup_raw = self.b_matchup.get().strip()
        matchup_history = parse_list(matchup_raw) if matchup_raw else []

        situation = self.b_situation.get()
        home_away = self.b_home_away.get()
        situational_factor = SITUATIONAL_FACTORS.get(situation, 1.0) * BATTER_HOME_AWAY_FACTOR.get(home_away, 1.0)

        eff_era = effective_opponent_era(opp_era, bullpen_era)

        lines = []
        if bullpen_era is not None:
            lines.append(
                f"Effective opponent ERA: {STARTER_WEIGHT:.0%} starter ({opp_era}) + "
                f"{BULLPEN_WEIGHT:.0%} bullpen ({bullpen_era}) = {eff_era:.2f}"
            )

        has_substats = self.batter_submode.get() == "separate"

        if has_substats:
            try:
                hits = parse_list(self.b_hits.get())
                runs = parse_list(self.b_runs.get())
                rbi = parse_list(self.b_rbi.get())
            except ValueError:
                messagebox.showerror("Invalid input", "Hits/runs/rbi must be whole numbers, comma-separated.")
                return
            if not (len(hits) == len(runs) == len(rbi)) or len(hits) < 3:
                messagebox.showerror("Invalid input", "Hits/runs/rbi logs must be equal length and at least 3 games.")
                return

            combined_games = [h + r + rb for h, r, rb in zip(hits, runs, rbi)]
            n = len(combined_games)

            hits_factor = batter_matchup_adjustment_factor(eff_era, league_avg_era, elasticity=HITS_ELASTICITY)
            runs_factor = batter_matchup_adjustment_factor(eff_era, league_avg_era, elasticity=RUNS_ELASTICITY)
            rbi_factor = batter_matchup_adjustment_factor(eff_era, league_avg_era, elasticity=RBI_ELASTICITY)

            season_hits_raw = self.b_season_hits.get().strip()
            season_runs_raw = self.b_season_runs.get().strip()
            season_rbi_raw = self.b_season_rbi.get().strip()
            season_hits = float(season_hits_raw) if season_hits_raw else None
            season_runs = float(season_runs_raw) if season_runs_raw else None
            season_rbi = float(season_rbi_raw) if season_rbi_raw else None

            hits_proj, _, _, _ = project(hits, adjustment_factor=hits_factor, season_avg=season_hits)
            runs_proj, _, _, _ = project(runs, adjustment_factor=runs_factor, season_avg=season_runs)
            rbi_proj, _, _, _ = project(rbi, adjustment_factor=rbi_factor, season_avg=season_rbi)

            matchup_adjusted_sum = hits_proj + runs_proj + rbi_proj

            _, raw_stdev, pred_stdev, confidence = project(combined_games)
            projection_no_adj = sum(
                project(s, season_avg=sa)[0]
                for s, sa in ((hits, season_hits), (runs, season_runs), (rbi, season_rbi))
            )

            lines.append(f"=== {name} ({team}) vs {opponent_pitcher} — H+R+RBI (sub-stat model) ===")
            lines.append(f"Last {n} games — hits: {hits} | runs: {runs} | rbi: {rbi}")
            if season_hits is not None or season_runs is not None or season_rbi is not None:
                sh = f"{season_hits:.2f}" if season_hits is not None else "n/a"
                sr = f"{season_runs:.2f}" if season_runs is not None else "n/a"
                srbi = f"{season_rbi:.2f}" if season_rbi is not None else "n/a"
                lines.append(f"Season averages — hits: {sh}  runs: {sr}  rbi: {srbi}")
            lines.append(
                f"Sub-stat projections: hits {hits_proj:.2f} (factor {hits_factor:.3f}) + "
                f"runs {runs_proj:.2f} (factor {runs_factor:.3f}) + rbi {rbi_proj:.2f} (factor {rbi_factor:.3f})"
            )
            combined_factor = matchup_adjusted_sum / projection_no_adj if projection_no_adj else 1.0
            projection_adj = matchup_adjusted_sum
            flat_avg = sum(combined_games) / n
        else:
            try:
                games = parse_list(self.b_games.get())
            except ValueError:
                messagebox.showerror("Invalid input", "Combined H+R+RBI must be whole numbers, comma-separated.")
                return
            if len(games) < 3:
                messagebox.showerror("Not enough games", "Need at least 3 games to compute a standard deviation.")
                return
            n = len(games)
            season_avg_raw = self.b_season_avg.get().strip()
            season_avg = float(season_avg_raw) if season_avg_raw else None

            matchup_factor = batter_matchup_adjustment_factor(eff_era, league_avg_era)
            projection_no_adj, raw_stdev, pred_stdev, confidence = project(games, season_avg=season_avg)
            projection_adj, _, _, _ = project(games, adjustment_factor=matchup_factor, season_avg=season_avg)
            combined_factor = matchup_factor

            lines.append(f"=== {name} ({team}) vs {opponent_pitcher} — H+R+RBI (combined-stat fallback) ===")
            games_line = f"Last {n} games (combined H+R+RBI): {games}"
            if season_avg is not None:
                games_line += f"  |  Season avg: {season_avg:.1f}"
            lines.append(games_line)
            lines.append(
                f"Opponent ERA used: {eff_era:.2f}  |  League avg ERA: {league_avg_era}  |  Matchup factor: {matchup_factor:.3f}"
            )
            flat_avg = sum(games) / n

        projection_adj = projection_adj * park_factor * situational_factor
        combined_factor = combined_factor * park_factor * situational_factor
        widening_pct = (pred_stdev / raw_stdev - 1) * 100

        lines.append(f"Flat average: {flat_avg:.1f}")
        lines.append(
            f"Raw stdev: {raw_stdev:.1f}  |  Predictive stdev: {pred_stdev:.1f} (+{widening_pct:.1f}% for sample-size uncertainty)"
        )
        lines.append(f"Sample size confidence: {confidence}")
        if park_factor != 1.0:
            lines.append(f"Park factor: {park_factor:.2f}")
        if situation != "healthy":
            lines.append(f"Situational factor ({situation}): {SITUATIONAL_FACTORS.get(situation, 1.0):.2f}")
        if home_away != "neutral":
            lines.append(f"Home/away factor ({home_away}): {BATTER_HOME_AWAY_FACTOR.get(home_away, 1.0):.2f}")
        lines.append(f"Overall effective factor: {combined_factor:.3f}")
        lines.append(f"Projection: {projection_no_adj:.1f} (no adj) -> {projection_adj:.1f} (fully adjusted)")

        final_projection = projection_adj
        if matchup_history:
            m_n = len(matchup_history)
            m_avg = sum(matchup_history) / m_n
            blended, weight_specific = shrink_toward_general(m_avg, m_n, projection_adj)
            lines.append(f"Matchup history vs {opponent_pitcher}: {matchup_history} (avg {m_avg:.1f}, n={m_n})")
            lines.append(f"Shrinkage weight on matchup history: {weight_specific:.1%}")
            lines.append(f"Projection: {projection_adj:.1f} -> {blended:.1f} (matchup-blended)")
            final_projection = blended

        self.line_probs = {}
        for line in [1.5, 2.5, 3.5]:
            p_over = prob_over(line, final_projection, pred_stdev)
            self.line_probs[line] = p_over
            lines.append(f"  Over {line}: {p_over:.1%} chance")

        self._render_output(lines, list(self.line_probs.keys()))

    def _render_output(self, lines, prop_lines):
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, "\n".join(lines))

        menu = self.line_menu["menu"]
        menu.delete(0, "end")
        for line in prop_lines:
            menu.add_command(label=str(line), command=lambda l=line: self.line_var.set(str(l)))
        if prop_lines:
            self.line_var.set(str(prop_lines[0]))

    def check_edge(self):
        try:
            self._check_edge()
        except Exception as e:
            messagebox.showerror("Something went wrong", f"{type(e).__name__}: {e}")

    def _check_edge(self):
        if not self.line_probs:
            messagebox.showerror("No projection yet", "Calculate a projection first.")
            return
        line_str = self.line_var.get()
        if not line_str:
            messagebox.showerror("No line selected", "Choose a line to check.")
            return
        line = float(line_str)
        our_prob_over = self.line_probs[line]

        try:
            over_odds = int(self.over_odds_entry.get().strip())
            under_odds = int(self.under_odds_entry.get().strip())
        except ValueError:
            messagebox.showerror("Invalid odds", "Enter American odds as whole numbers, e.g. -115 or 120.")
            return

        true_over, true_under, vig_pct = devig_two_way(over_odds, under_odds)
        e = edge(our_prob_over, true_over)

        lines = [
            "",
            f"--- Market check: over/under {line} ---",
            f"Market odds: Over {over_odds:+d}  |  Under {under_odds:+d}",
            f"Vig/overround: {vig_pct:.2f} percentage points",
            f"De-vigged TRUE market probability of Over: {true_over:.1%}",
            f"Your model's probability of Over: {our_prob_over:.1%}",
            f"Edge vs true market: {e:+.1f} percentage points",
        ]
        if e > 3:
            lines.append("-> Your model thinks OVER is undervalued by the market (potential edge, IF your model is right)")
        elif e < -3:
            lines.append("-> Your model thinks UNDER is the better side (market overvalues Over, IF your model is right)")
        else:
            lines.append("-> Your model roughly agrees with the market — no meaningful edge either way")

        self.output.insert(tk.END, "\n" + "\n".join(lines))
        self.output.see(tk.END)


def open_window():
    win = tk.Toplevel()
    MLBPropsModelWindow(win)


def prefill_window(app, data):
    """
    Fills in form fields from a data dict of researched-and-verified stats —
    used by launch_prefilled() so a player can be looked up once (by Claude,
    in chat) and opened ready-to-review instead of re-typed by hand. Only
    fills fields present in the dict; everything else keeps its default.
    Does NOT click Calculate — the human always reviews before running it.

    data['mode'] must be 'pitcher' or 'batter' (default 'pitcher'). For
    batters, data['submode'] must be 'separate' or 'combined' (default
    'combined') — this picks which stat-log fields get filled.
    """
    mode = data.get("mode", "pitcher")
    app.mode.set(mode)
    app.rebuild_inputs()

    if mode == "pitcher":
        if "name" in data:
            app.p_name.insert(0, data["name"])
        if "team" in data:
            app.p_team.insert(0, data["team"])
        if "opponent" in data:
            app.p_opponent.insert(0, data["opponent"])
        if "games" in data:
            app.p_games.insert(0, ", ".join(str(g) for g in data["games"]))
        if "opponent_k_per_game" in data:
            app.p_opp_k.insert(0, str(data["opponent_k_per_game"]))
        if "league_avg_k_per_game" in data:
            app.p_league_avg.delete(0, tk.END)
            app.p_league_avg.insert(0, str(data["league_avg_k_per_game"]))
        if "season_avg" in data:
            app.p_season_avg.insert(0, str(data["season_avg"]))
        if "matchup_history" in data:
            app.p_matchup.insert(0, ", ".join(str(g) for g in data["matchup_history"]))
        if "situation" in data:
            app.p_situation.set(data["situation"])
        if "short_rest" in data:
            app.p_short_rest.set(data["short_rest"])
    else:
        submode = data.get("submode", "combined")
        app.batter_submode.set(submode)
        app.rebuild_batter_substats()

        if "name" in data:
            app.b_name.insert(0, data["name"])
        if "team" in data:
            app.b_team.insert(0, data["team"])
        if "opponent_pitcher" in data:
            app.b_opp_pitcher.insert(0, data["opponent_pitcher"])

        if submode == "separate":
            if "hits" in data:
                app.b_hits.insert(0, ", ".join(str(x) for x in data["hits"]))
            if "runs" in data:
                app.b_runs.insert(0, ", ".join(str(x) for x in data["runs"]))
            if "rbi" in data:
                app.b_rbi.insert(0, ", ".join(str(x) for x in data["rbi"]))
            if "season_avg_hits" in data:
                app.b_season_hits.insert(0, str(data["season_avg_hits"]))
            if "season_avg_runs" in data:
                app.b_season_runs.insert(0, str(data["season_avg_runs"]))
            if "season_avg_rbi" in data:
                app.b_season_rbi.insert(0, str(data["season_avg_rbi"]))
        else:
            if "games" in data:
                app.b_games.insert(0, ", ".join(str(x) for x in data["games"]))
            if "season_avg" in data:
                app.b_season_avg.insert(0, str(data["season_avg"]))

        if "opponent_pitcher_era" in data:
            app.b_opp_era.insert(0, str(data["opponent_pitcher_era"]))
        if "opponent_bullpen_era" in data:
            app.b_bullpen_era.insert(0, str(data["opponent_bullpen_era"]))
        if "league_avg_era" in data:
            app.b_league_avg.delete(0, tk.END)
            app.b_league_avg.insert(0, str(data["league_avg_era"]))
        if "park_factor" in data:
            app.b_park_factor.delete(0, tk.END)
            app.b_park_factor.insert(0, str(data["park_factor"]))
        if "matchup_history" in data:
            app.b_matchup.insert(0, ", ".join(str(x) for x in data["matchup_history"]))
        if "situation" in data:
            app.b_situation.set(data["situation"])
        if "home_away" in data:
            app.b_home_away.set(data["home_away"])


def launch_prefilled(data):
    """Opens a standalone window with the form pre-filled from `data`.
    See prefill_window() for the accepted keys."""
    root = tk.Tk()
    app = MLBPropsModelWindow(root)
    prefill_window(app, data)
    root.mainloop()


if __name__ == "__main__":
    root = tk.Tk()
    MLBPropsModelWindow(root)
    root.mainloop()
