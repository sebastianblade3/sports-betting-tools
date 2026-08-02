#!/usr/bin/env python3
"""
Button/form version of the Kelly criterion tool — same tested math as
kelly_tool.py (kelly_fraction_binary, kelly_fraction_general, recommend_stake
imported directly, not reimplemented).
"""

import tkinter as tk
from tkinter import messagebox

from kelly_tool import kelly_fraction_binary, kelly_fraction_general, recommend_stake
from ev_tool import FLEX_MULTIPLIERS


class KellyToolWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Kelly Stake Sizing")
        self.root.geometry("480x580")

        self.mode = tk.StringVar(value="power")
        self.num_legs = tk.IntVar(value=3)
        self.leg_entries = []

        top = tk.Frame(root, pady=10)
        top.pack(fill="x")

        tk.Label(top, text="Mode:").grid(row=0, column=0, sticky="w", padx=10)
        tk.Radiobutton(top, text="Power Play", variable=self.mode, value="power", command=self.rebuild_inputs).grid(row=0, column=1)
        tk.Radiobutton(top, text="Flex Play", variable=self.mode, value="flex", command=self.rebuild_inputs).grid(row=0, column=2)

        common = tk.Frame(root, pady=5)
        common.pack(fill="x")
        tk.Label(common, text="Bankroll ($):").grid(row=0, column=0, sticky="w", padx=10, pady=3)
        self.bankroll_entry = tk.Entry(common, width=15)
        self.bankroll_entry.grid(row=0, column=1, padx=10, pady=3)

        tk.Label(common, text="Kelly fraction (e.g. 0.25):").grid(row=1, column=0, sticky="w", padx=10, pady=3)
        self.fractional_entry = tk.Entry(common, width=15)
        self.fractional_entry.grid(row=1, column=1, padx=10, pady=3)
        self.fractional_entry.insert(0, "0.25")

        self.inputs_frame = tk.Frame(root, pady=10)
        self.inputs_frame.pack(fill="x")

        tk.Button(root, text="Calculate", width=20, command=self.calculate).pack(pady=10)

        self.output = tk.Text(root, height=16, width=58, wrap="word")
        self.output.pack(padx=10, pady=10, fill="both", expand=True)

        self.rebuild_inputs()

    def rebuild_inputs(self):
        for widget in self.inputs_frame.winfo_children():
            widget.destroy()
        self.leg_entries = []

        if self.mode.get() == "power":
            tk.Label(self.inputs_frame, text="Combined win probability (0-1 or %):").grid(row=0, column=0, sticky="w", padx=10, pady=3)
            self.prob_entry = tk.Entry(self.inputs_frame, width=15)
            self.prob_entry.grid(row=0, column=1, padx=10, pady=3)

            tk.Label(self.inputs_frame, text="Payout multiplier (e.g. 5.0):").grid(row=1, column=0, sticky="w", padx=10, pady=3)
            self.multiplier_entry = tk.Entry(self.inputs_frame, width=15)
            self.multiplier_entry.grid(row=1, column=1, padx=10, pady=3)
        else:
            tk.Label(self.inputs_frame, text="Number of legs:").grid(row=0, column=0, sticky="w", padx=10, pady=3)
            tk.Spinbox(self.inputs_frame, from_=3, to=6, textvariable=self.num_legs, width=5,
                       command=self.rebuild_leg_rows).grid(row=0, column=1, sticky="w", padx=10, pady=3)
            self.legs_subframe = tk.Frame(self.inputs_frame)
            self.legs_subframe.grid(row=1, column=0, columnspan=2, sticky="w")
            self.rebuild_leg_rows()

    def rebuild_leg_rows(self):
        for widget in self.legs_subframe.winfo_children():
            widget.destroy()
        self.leg_entries = []
        n = self.num_legs.get()
        for i in range(n):
            tk.Label(self.legs_subframe, text=f"Leg {i+1} probability:").grid(row=i, column=0, sticky="w", padx=10, pady=2)
            e = tk.Entry(self.legs_subframe, width=12)
            e.grid(row=i, column=1, padx=10, pady=2)
            self.leg_entries.append(e)

    def parse_prob(self, raw):
        raw = raw.strip().rstrip("%")
        val = float(raw)
        if val > 1:
            val /= 100
        return val

    def calculate(self):
        try:
            self._calculate()
        except Exception as e:
            messagebox.showerror("Something went wrong", f"{type(e).__name__}: {e}")

    def _calculate(self):
        try:
            bankroll = float(self.bankroll_entry.get().strip())
            fractional = float(self.fractional_entry.get().strip())
        except ValueError:
            messagebox.showerror("Invalid input", "Bankroll and Kelly fraction must be numbers.")
            return

        if self.mode.get() == "power":
            try:
                prob = self.parse_prob(self.prob_entry.get())
                multiplier = float(self.multiplier_entry.get().strip())
            except ValueError:
                messagebox.showerror("Invalid input", "Enter valid probability and multiplier.")
                return
            f = kelly_fraction_binary(prob, multiplier)
        else:
            try:
                probs = [self.parse_prob(e.get()) for e in self.leg_entries]
            except ValueError:
                messagebox.showerror("Invalid input", "Enter a probability for every leg.")
                return
            n = len(probs)
            dp = [1.0]
            for p in probs:
                new_dp = [0.0] * (len(dp) + 1)
                for k, prob_k in enumerate(dp):
                    new_dp[k] += prob_k * (1 - p)
                    new_dp[k + 1] += prob_k * p
                dp = new_dp
            payout_table = FLEX_MULTIPLIERS.get(n)
            if payout_table is None:
                messagebox.showerror("No table", f"No standard Flex table on file for {n} picks.")
                return
            f = kelly_fraction_general(dp, payout_table)

        stake, f_clipped = recommend_stake(bankroll, f, fractional=fractional)

        lines = ["--- Kelly stake recommendation ---", f"Full Kelly fraction of bankroll: {f_clipped:.1%}"]
        if f_clipped <= 0:
            lines.append("This is NOT a positive-EV bet by your own numbers — Kelly says stake $0.")
        else:
            lines.append(f"Using {fractional:.0%} Kelly (recommended, not full Kelly): {f_clipped * fractional:.1%} of bankroll")
            lines.append(f"On a ${bankroll:,.0f} bankroll: recommended stake = ${stake:,.2f}")
            lines.append("")
            lines.append("Why fractional, not full Kelly: full Kelly maximizes long-run growth")
            lines.append("mathematically, but is extremely sensitive to your probability estimate")
            lines.append("being wrong — which it sometimes will be. Fractional Kelly trades a bit")
            lines.append("of growth rate for a lot less variance/risk of ruin. 1/4 to 1/2 Kelly is")
            lines.append("standard practice among real practitioners.")

        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, "\n".join(lines))


def open_window():
    win = tk.Toplevel()
    KellyToolWindow(win)


if __name__ == "__main__":
    root = tk.Tk()
    KellyToolWindow(root)
    root.mainloop()
