#!/usr/bin/env python3
"""
Button/form version of the NBA/WNBA points prop model — same tested math as
nba_props_model.py and stats_engine.py (project, opponent_adjustment_factor,
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
from nba_props_model import (
    opponent_adjustment_factor,
    LEAGUE_AVG_DEF_RATING,
    HOME_AWAY_FACTOR,
    REST_FACTOR,
)
from devig_tool import devig_two_way, edge

SITUATION_LABELS = {
    "healthy": "Healthy",
    "playing_through_minor_injury": "Playing through a minor injury",
    "recently_returned_from_injury": "Recently returned from injury",
    "key_teammate_out": "A key teammate is out",
}


class NBAPropsModelWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("NBA/WNBA Points Prop Model")
        self.root.geometry("620x820")

        self.line_probs = {}

        form = tk.Frame(root, pady=10)
        form.pack(fill="x")

        r = 0
        tk.Label(form, text="Player name:").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.name_entry = tk.Entry(form, width=28)
        self.name_entry.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(form, text="Team:").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.team_entry = tk.Entry(form, width=28)
        self.team_entry.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(form, text="Tonight's opponent:").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.opponent_entry = tk.Entry(form, width=28)
        self.opponent_entry.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(form, text="Last N games' points\n(comma-separated, most recent first):").grid(
            row=r, column=0, sticky="w", padx=10, pady=3
        )
        self.games_entry = tk.Entry(form, width=28)
        self.games_entry.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(form, text="Opponent's points allowed/game\n(pace-adjusted def rating):").grid(
            row=r, column=0, sticky="w", padx=10, pady=3
        )
        self.opp_def_entry = tk.Entry(form, width=28)
        self.opp_def_entry.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(form, text="League average points allowed/game:").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.league_avg_entry = tk.Entry(form, width=28)
        self.league_avg_entry.grid(row=r, column=1, padx=10, pady=3)
        self.league_avg_entry.insert(0, str(LEAGUE_AVG_DEF_RATING))
        r += 1

        tk.Label(form, text="Season points/game average (optional):").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.season_avg_entry = tk.Entry(form, width=28)
        self.season_avg_entry.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(form, text="Matchup history vs opponent this season\n(comma-separated, optional):").grid(
            row=r, column=0, sticky="w", padx=10, pady=3
        )
        self.matchup_entry = tk.Entry(form, width=28)
        self.matchup_entry.grid(row=r, column=1, padx=10, pady=3)
        r += 1

        tk.Label(form, text="Situational factor tonight:").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        self.situation = tk.StringVar(value="healthy")
        situation_menu = tk.OptionMenu(form, self.situation, *SITUATION_LABELS.keys())
        situation_menu.grid(row=r, column=1, sticky="w", padx=10, pady=3)
        self.situation.set("healthy")
        situation_menu["menu"].delete(0, "end")
        for key, label in SITUATION_LABELS.items():
            situation_menu["menu"].add_command(label=label, command=lambda k=key: self.situation.set(k))
        r += 1

        tk.Label(form, text="Home or away tonight:").grid(row=r, column=0, sticky="w", padx=10, pady=3)
        home_away_frame = tk.Frame(form)
        home_away_frame.grid(row=r, column=1, sticky="w", padx=10, pady=3)
        self.home_away = tk.StringVar(value="neutral")
        tk.Radiobutton(home_away_frame, text="Home", variable=self.home_away, value="home").pack(side="left")
        tk.Radiobutton(home_away_frame, text="Away", variable=self.home_away, value="away").pack(side="left")
        tk.Radiobutton(home_away_frame, text="N/A", variable=self.home_away, value="neutral").pack(side="left")
        r += 1

        self.back_to_back = tk.BooleanVar(value=False)
        tk.Checkbutton(form, text="Back-to-back (0 days rest)", variable=self.back_to_back).grid(
            row=r, column=0, columnspan=2, sticky="w", padx=10, pady=3
        )
        r += 1

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
        self.output = tk.Text(output_frame, height=16, width=68, wrap="word", yscrollcommand=scrollbar.set)
        self.output.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.output.yview)

    def parse_games(self, raw):
        parts = [x.strip() for x in raw.split(",") if x.strip()]
        return [int(x) for x in parts]

    def calculate(self):
        try:
            self._calculate()
        except Exception as e:
            messagebox.showerror("Something went wrong", f"{type(e).__name__}: {e}")

    def _calculate(self):
        name = self.name_entry.get().strip() or "Player"
        team = self.team_entry.get().strip() or "Team"
        opponent = self.opponent_entry.get().strip() or "Opponent"

        try:
            games = self.parse_games(self.games_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Games must be whole numbers, comma-separated.")
            return
        if len(games) < 3:
            messagebox.showerror("Not enough games", "Need at least 3 games to compute a standard deviation.")
            return

        try:
            opp_def_rating = float(self.opp_def_entry.get().strip())
            league_avg = float(self.league_avg_entry.get().strip())
        except ValueError:
            messagebox.showerror("Invalid input", "Enter valid numbers for opponent/league defensive rating.")
            return

        season_avg_raw = self.season_avg_entry.get().strip()
        season_avg = float(season_avg_raw) if season_avg_raw else None

        matchup_raw = self.matchup_entry.get().strip()
        matchup_history = self.parse_games(matchup_raw) if matchup_raw else []

        situation = self.situation.get()
        home_away = self.home_away.get()
        rest = "back_to_back" if self.back_to_back.get() else "normal"

        n = len(games)
        flat_avg = sum(games) / n
        w_avg = weighted_average(games)

        context_factor = (
            SITUATIONAL_FACTORS.get(situation, 1.0)
            * HOME_AWAY_FACTOR.get(home_away, 1.0)
            * REST_FACTOR.get(rest, 1.0)
        )

        projection_no_adj, raw_stdev, pred_stdev, confidence = project(games, season_avg=season_avg)
        factor = opponent_adjustment_factor(opp_def_rating, league_avg)
        projection_adj, _, _, _ = project(
            games, adjustment_factor=factor, situational_factor=context_factor, season_avg=season_avg
        )
        widening_pct = (pred_stdev / raw_stdev - 1) * 100

        lines = [f"=== {name} ({team}) vs {opponent} ==="]
        lines.append(f"Last {n} games: {games}")
        avg_line = f"Flat average: {flat_avg:.1f}  |  Weighted average (last-{n}): {w_avg:.1f}"
        if season_avg is not None:
            blended_avg = blend_recent_and_season(w_avg, season_avg)
            avg_line += f"  |  Season avg: {season_avg:.1f}  |  Blended (70/30): {blended_avg:.1f}"
        lines.append(avg_line)
        lines.append(
            f"Raw stdev: {raw_stdev:.1f}  |  Predictive stdev: {pred_stdev:.1f} (+{widening_pct:.1f}% for sample-size uncertainty)"
        )
        lines.append(f"Sample size confidence: {confidence}")
        lines.append(f"Opponent points allowed/game: {opp_def_rating}  |  League avg: {league_avg}  |  Factor: {factor:.3f}")
        if situation != "healthy":
            lines.append(f"Situational factor ({situation}): {SITUATIONAL_FACTORS.get(situation, 1.0):.2f}")
        if home_away != "neutral":
            lines.append(f"Home/away factor ({home_away}): {HOME_AWAY_FACTOR.get(home_away, 1.0):.2f}")
        if rest != "normal":
            lines.append(f"Rest factor ({rest}): {REST_FACTOR.get(rest, 1.0):.2f}")
        lines.append(f"Projection: {projection_no_adj:.1f} (no adj) -> {projection_adj:.1f} (fully adjusted)")

        final_projection = projection_adj
        if matchup_history:
            m_n = len(matchup_history)
            m_avg = sum(matchup_history) / m_n
            blended, weight_specific = shrink_toward_general(m_avg, m_n, projection_adj)
            lines.append(f"Matchup history vs {opponent}: {matchup_history} (avg {m_avg:.1f}, n={m_n})")
            lines.append(f"Shrinkage weight on matchup history: {weight_specific:.1%} (rest stays on the general model)")
            lines.append(f"Projection: {projection_adj:.1f} (opponent-adjusted) -> {blended:.1f} (matchup-blended)")
            final_projection = blended

        center = round(final_projection)
        prop_lines = [center - 6.5 + i for i in range(0, 12, 3)]
        self.line_probs = {}
        for line in prop_lines:
            p_over = prob_over(line, final_projection, pred_stdev)
            self.line_probs[line] = p_over
            lines.append(f"  Over {line}: {p_over:.1%} chance")

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
    NBAPropsModelWindow(win)


if __name__ == "__main__":
    root = tk.Tk()
    NBAPropsModelWindow(root)
    root.mainloop()
