"""Figures for the README, built only from the result tables in output/.

Needs no raw or processed data, so anyone can regenerate them:
    python3 code/09_figures.py
Writes light and dark PNGs to output/figures/.
"""
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from config import LOGS, TABLES

FIGURES = TABLES.parent / "figures"

THEMES = {
    "light": dict(bg="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#e4e3df",
                  s1="#2a78d6", s2="#eb6834", neutral="#b9b8b2"),
    "dark": dict(bg="#1a1a19", ink="#ffffff", ink2="#c3c2b7", grid="#383835",
                 s1="#3987e5", s2="#d95926", neutral="#6b6a65"),
}

LABELS = {
    "tmean_anom_hq": "Mean temp. anomaly",
    "hot_hq": "Hot anomaly (+)",
    "cold_hq": "Cold anomaly (−)",
    "tmax_anom_hq": "Max temp. anomaly",
    "tmin_anom_hq": "Min temp. anomaly",
    "tmean_absanom_hq": "|Mean anomaly|",
    "hot_x_hs": "Hot × heat-sensitive",
    "cold_x_hs": "Cold × heat-sensitive",
}
OUTCOMES = {"ret_w": "Monthly return (bp per °F)",
            "sd_w": "Volatility (×10⁻⁴ per °F)"}


def style(ax, t):
    ax.set_facecolor(t["bg"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(t["grid"])
    ax.tick_params(colors=t["ink2"], labelsize=9, length=0)
    ax.xaxis.grid(True, color=t["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig, name, theme):
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{name}_{theme}.png", dpi=200, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)


def forest(ax, d, t, color, offset=0.0, label=None):
    """Point estimate + 95% CI per row; rows ordered top to bottom."""
    y = [len(d) - 1 - i + offset for i in range(len(d))]
    ax.hlines(y, d.lo, d.hi, color=color, linewidth=2, alpha=0.55)
    ax.plot(d.coef, y, "o", color=color, markersize=7,
            markeredgecolor=t["bg"], markeredgewidth=1.5, label=label)
    return y


def fig_corrected(t, theme):
    df = pd.read_csv(TABLES / "corrected_results.csv")
    df = df[df.spec.isin(["hot / cold split", "tmax / tmin anomalies",
                          "signed mean anomaly", "|mean anomaly| (thesis concept, fixed)"])]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), facecolor=t["bg"])
    for ax, (y, title) in zip(axes, OUTCOMES.items()):
        d = df[df.y == y].assign(coef=lambda x: x.coef * 1e4,
                                 lo=lambda x: x.ci95_lo * 1e4,
                                 hi=lambda x: x.ci95_hi * 1e4).reset_index(drop=True)
        style(ax, t)
        ax.axvline(0, color=t["ink2"], linewidth=1)
        rows = forest(ax, d, t, t["s1"])
        ax.set_yticks(rows)
        ax.set_yticklabels([LABELS[v] for v in d.variable], color=t["ink"])
        ax.set_title(title, color=t["ink"], fontsize=11, loc="left")
    fig.suptitle("Corrected estimates: every 95% CI includes zero",
                 color=t["ink"], fontsize=13, x=0.01, ha="left", y=1.04)
    fig.text(0.01, -0.04, "Firm + industry×year-month FE, two-way clustered SEs. "
             "N ≈ 1.86M firm-months (returns), 1.77M (volatility).",
             color=t["ink2"], fontsize=8.5)
    fig.tight_layout()
    save(fig, "corrected_effects", theme)


def fig_thesis_vs_corrected(t, theme):
    rob = pd.read_csv(TABLES / "robustness_results.csv")
    cor = pd.read_csv(TABLES / "corrected_results.csv")
    vars_ = ["tmean_anom_hq", "hot_hq", "cold_hq"]
    old = rob[(rob.check == "thesis_fe") & rob.variable.isin(vars_)]
    new = cor[cor.spec.isin(["signed mean anomaly", "hot / cold split"]) & cor.variable.isin(vars_)]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.2), facecolor=t["bg"], sharey=True)
    for ax, (y, title) in zip(axes, OUTCOMES.items()):
        style(ax, t)
        ax.axvline(0, color=t["ink2"], linewidth=1)
        for d, color, off, lab in ((new, t["s1"], 0.15, "Corrected FE (industry × year-month)"),
                                   (old, t["s2"], -0.15, "Thesis FE (industry × year)")):
            d = d[d.y == y].set_index("variable").loc[vars_].reset_index()
            se = d.se * 1e4
            d = d.assign(coef=d.coef * 1e4, lo=d.coef * 1e4 - 1.96 * se, hi=d.coef * 1e4 + 1.96 * se)
            rows = forest(ax, d, t, color, off, lab)
        ax.set_yticks([r + 0.15 for r in rows])
        ax.set_yticklabels([LABELS[v] for v in vars_], color=t["ink"])
        ax.set_title(title, color=t["ink"], fontsize=11, loc="left")
    axes[1].tick_params(labelleft=False)
    leg = fig.legend(*axes[0].get_legend_handles_labels(), loc="lower left",
                     bbox_to_anchor=(0.01, -0.1), ncol=2, frameon=False, fontsize=9)
    for txt in leg.get_texts():
        txt.set_color(t["ink2"])
    fig.suptitle("Tighter fixed effects shrink the intervals; no effect appears",
                 color=t["ink"], fontsize=13, x=0.01, ha="left", y=1.05)
    fig.tight_layout()
    save(fig, "thesis_vs_corrected", theme)


def fig_audit(t, theme):
    txt = (LOGS / "validation.txt").read_text()
    same = float(re.search(r"same location: ([\d.]+)%", txt).group(1))
    foreign = float(re.search(r"no city\+state match at all.*?: ([\d.]+)%", txt).group(1))
    fig, ax = plt.subplots(figsize=(10, 1.4), facecolor=t["bg"])
    style(ax, t)
    ax.xaxis.grid(False)
    ax.spines["bottom"].set_visible(False)
    ax.set_xticks([])
    parts = [(same, t["s1"], f"Correct HQ weather  {same:.1f}%"),
             (100 - same, t["neutral"], f"Another town's weather  {100 - same:.1f}%")]
    left = 0
    for w, color, lab in parts:
        ax.barh(0, w - 0.3, left=left, color=color, height=0.5)
        ax.text(left + 1.5, 0, lab, va="center", color=t["bg"] if color == t["s1"] else t["ink"],
                fontsize=10, fontweight="bold")
        left += w
    ax.set_xlim(0, 100)
    ax.set_yticks([])
    ax.set_ylim(-0.4, 0.4)
    fig.suptitle(f"Original thesis data: city-name-only matching gave {100 - same:.0f}% of "
                 "firm-months the wrong weather", color=t["ink"], fontsize=12, x=0.125,
                 ha="left", y=1.02)
    fig.text(0.125, -0.06, f"Share of 1.83M firm-months. {foreign:.1f}% had no (city, state) "
             "match in the continental US at all, e.g. foreign HQs. See AUDIT.md, problem #2.",
             color=t["ink2"], fontsize=8.5)
    save(fig, "data_audit", theme)


if __name__ == "__main__":
    for theme, t in THEMES.items():
        plt.rcParams["font.family"] = "DejaVu Sans"
        fig_corrected(t, theme)
        fig_thesis_vs_corrected(t, theme)
        fig_audit(t, theme)
    print("figures written to", FIGURES)
