#!/usr/bin/env python3
"""
Button/form version of the bankroll/ROI tracker — same tested math as
bankroll_tool.py (load_log, append_bet, compute_bet imported directly,
not reimplemented).
"""

import tkinter as tk
from tkinter import messagebox

from bankroll_tool import load_log, append_bet, LOG_FILE


class BankrollToolWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Bankroll / ROI Tracker")
        self.root.geometry("560x640")

        self.outcome = tk.StringVar(value="won")

        form = tk.Frame(root, pady=10)
        form.pack(fill="x")

        tk.Label(form, text="Log a new bet result", font=("Helvetica", 13, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8)
        )

        tk.Label(form, text="Date (YYYY-MM-DD):").grid(row=1, column=0, sticky="w", padx=10, pady=3)
        self.date_entry = tk.Entry(form, width=25)
        self.date_entry.grid(row=1, column=1, padx=10, pady=3)

        tk.Label(form, text="Description:").grid(row=2, column=0, sticky="w", padx=10, pady=3)
        self.description_entry = tk.Entry(form, width=25)
        self.description_entry.grid(row=2, column=1, padx=10, pady=3)

        tk.Label(form, text="Stake ($):").grid(row=3, column=0, sticky="w", padx=10, pady=3)
        self.stake_entry = tk.Entry(form, width=25)
        self.stake_entry.grid(row=3, column=1, padx=10, pady=3)

        tk.Label(form, text="Payout multiplier if won (e.g. 5.0):").grid(row=4, column=0, sticky="w", padx=10, pady=3)
        self.multiplier_entry = tk.Entry(form, width=25)
        self.multiplier_entry.grid(row=4, column=1, padx=10, pady=3)

        tk.Label(form, text="Outcome:").grid(row=5, column=0, sticky="w", padx=10, pady=3)
        outcome_frame = tk.Frame(form)
        outcome_frame.grid(row=5, column=1, sticky="w", padx=10, pady=3)
        tk.Radiobutton(outcome_frame, text="Won", variable=self.outcome, value="won").pack(side="left")
        tk.Radiobutton(outcome_frame, text="Lost", variable=self.outcome, value="lost").pack(side="left")

        btn_frame = tk.Frame(root, pady=8)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="Log Bet", width=18, command=self.log_bet).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Refresh Report", width=18, command=self.show_report).pack(side="left", padx=10)

        self.output = tk.Text(root, height=22, width=68, wrap="word")
        self.output.pack(padx=10, pady=10, fill="both", expand=True)

        self.show_report()

    def log_bet(self):
        try:
            self._log_bet()
        except Exception as e:
            messagebox.showerror("Something went wrong", f"{type(e).__name__}: {e}")

    def _log_bet(self):
        date = self.date_entry.get().strip()
        description = self.description_entry.get().strip()
        if not date or not description:
            messagebox.showerror("Missing info", "Enter a date and description.")
            return
        try:
            stake = float(self.stake_entry.get().strip())
            multiplier = float(self.multiplier_entry.get().strip())
        except ValueError:
            messagebox.showerror("Invalid input", "Stake and multiplier must be numbers.")
            return

        payout, profit = append_bet(date, description, stake, multiplier, self.outcome.get())
        messagebox.showinfo("Logged", f"Payout: ${payout:.2f}\nProfit: ${profit:+.2f}\nLogged to {LOG_FILE.name}")

        self.date_entry.delete(0, tk.END)
        self.description_entry.delete(0, tk.END)
        self.stake_entry.delete(0, tk.END)
        self.multiplier_entry.delete(0, tk.END)

        self.show_report()

    def show_report(self):
        try:
            self._show_report()
        except Exception as e:
            messagebox.showerror("Something went wrong", f"{type(e).__name__}: {e}")

    def _show_report(self):
        entries = load_log()
        lines = []
        if not entries:
            lines.append("No bets logged yet.")
        else:
            total_staked = sum(e["stake"] for e in entries)
            total_payout = sum(e["payout"] for e in entries)
            net_profit = total_payout - total_staked
            roi_pct = (net_profit / total_staked * 100) if total_staked else 0.0
            wins = sum(1 for e in entries if e["outcome"] == "won")
            win_rate = wins / len(entries)

            lines.append(f"=== Bankroll Report ({len(entries)} bets logged) ===")
            lines.append("")
            lines.append(f"Total staked: ${total_staked:,.2f}")
            lines.append(f"Total returned: ${total_payout:,.2f}")
            lines.append(f"Net profit/loss: ${net_profit:+,.2f}")
            lines.append(f"ROI: {roi_pct:+.1f}%")
            lines.append(f"Win rate: {wins}/{len(entries)} ({win_rate:.1%})")
            lines.append("")
            lines.append("Running cumulative profit over time:")
            running = 0.0
            for e in entries:
                running += e["profit"]
                marker = "+" if e["profit"] >= 0 else "-"
                lines.append(
                    f"  {e['date']}  {e['description']:<30s} {marker}${abs(e['profit']):>8.2f}  (running: ${running:+,.2f})"
                )

            if len(entries) < 10:
                lines.append("")
                lines.append(f"NOTE: only {len(entries)} bets logged — too small a sample to draw")
                lines.append("real conclusions about long-run ROI yet.")

        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, "\n".join(lines))


def open_window():
    win = tk.Toplevel()
    BankrollToolWindow(win)


if __name__ == "__main__":
    root = tk.Tk()
    BankrollToolWindow(root)
    root.mainloop()
